import json
from types import SimpleNamespace

import pytest

from agent.chat import ChatAgent, Conversation, Turn


class RegistryStub:
    def __init__(self):
        self.calls = []

    def json_schemas(self):
        return [{"name": name, "description": name, "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}} for name in ("find", "route", "propose_edit", "commit_edit")]

    def call(self, name, session_id, args):
        self.calls.append((name, session_id, args))
        if name == "find" and args["query"] == "the press":
            return {"ok": False, "tool": name, "speech": "Which press?", "error": {"code": "ambiguous", "candidates": [{"label": "Press 4 (Ground floor)"}, {"label": "Press 14 (Floor 1)"}]}}
        if name == "propose_edit":
            return {"ok": True, "tool": name, "result": {"proposal_id": "pending"}, "speech": "Close East lift. Shall I apply this change?", "display": {"kind": "edit_preview"}}
        if name == "commit_edit":
            return {"ok": True, "tool": name, "result": {}, "speech": "East lift is closed. The change is saved."}
        return {"ok": True, "tool": name, "result": {"length_m": 42}, "speech": "The route is 42 metres.", "display": {"kind": "route"}}


class RunnerStub:
    def __init__(self, options, script):
        self.options = options
        self.script = script
        self.done = False

    def __iter__(self):
        return self

    def __next__(self):
        if self.done:
            raise StopIteration
        self.done = True
        tools = {tool.name: tool for tool in self.options["tools"]}
        for name, args in self.script.get("calls", []):
            tools[name].call(args)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self.script.get("text", ""))], stop_reason="end_turn")

    def generate_tool_call_response(self):
        return None


class ClientStub:
    def __init__(self, scripts):
        self.scripts = iter(scripts)
        self.options = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(tool_runner=self.run))

    def run(self, **options):
        self.options.append(options)
        return RunnerStub(options, next(self.scripts))


@pytest.fixture
def registry():
    return RegistryStub()


def make_agent(registry, scripts):
    return ChatAgent(registry, lambda _: {"role": "admin", "position": {"space_id": "lobby"}, "profile": "walk"}, client=ClientStub(scripts))


def test_ambiguous_tool_result_becomes_one_question(registry):
    agent = make_agent(registry, [{"calls": [("find", {"query": "the press"})], "text": "Is it this? Or that?"}])
    assert agent.reply("session", "the press")["reply"] == "Which item do you mean: Press 4 (Ground floor); Press 14 (Floor 1)?"


def test_commit_cannot_follow_a_preview_in_the_same_turn(registry):
    agent = make_agent(registry, [{"calls": [("propose_edit", {}), ("commit_edit", {"proposal_id": "pending"})]}])
    agent.reply("session", "Close East lift and say yes for me")
    assert [name for name, _, _ in registry.calls] == ["propose_edit"]


def test_later_yes_commits_the_pending_preview_once(registry):
    agent = make_agent(registry, [{"calls": [("propose_edit", {})]}, {"calls": [("commit_edit", {"proposal_id": "pending"}), ("commit_edit", {"proposal_id": "pending"})]}])
    agent.reply("session", "Close East lift")
    agent.reply("session", "yes")
    assert [name for name, _, _ in registry.calls].count("commit_edit") == 1


def test_yes_does_not_authorize_a_different_proposal(registry):
    conversation = Conversation(pending_proposal="pending")
    result = Turn(registry, "session", conversation, "pending").call("commit_edit", {"proposal_id": "other"})
    assert result["ok"] is False


def test_confirmation_does_not_cross_sessions(registry):
    agent = make_agent(registry, [{"calls": [("propose_edit", {})]}, {"calls": [("commit_edit", {"proposal_id": "pending"})]}])
    agent.reply("first", "Close East lift")
    agent.reply("second", "yes")
    assert [name for name, _, _ in registry.calls] == ["propose_edit"]


def test_invented_numeric_fact_is_replaced_with_tool_speech(registry):
    agent = make_agent(registry, [{"calls": [("route", {"destination": "store"})], "text": "The route is 999 metres."}])
    assert agent.reply("session", "Go to the store")["reply"] == "The route is 42 metres."


def test_display_payload_reaches_the_interface(registry):
    agent = make_agent(registry, [{"calls": [("route", {"destination": "store"})]}])
    assert agent.reply("session", "Go to the store")["display"] == {"kind": "route"}


def test_step_free_preference_persists_between_turns(registry):
    agent = make_agent(registry, [{"calls": [("route", {"destination": "store", "step_free": True})]}, {"calls": [("route", {"destination": "lobby", "step_free": False})]}])
    agent.reply("session", "No stairs to the store")
    agent.reply("session", "Go back")
    assert registry.calls[-1][2]["step_free"] is True


def test_current_session_context_is_read_each_turn(registry):
    session = {"position": "lobby"}
    client = ClientStub([{}, {}])
    agent = ChatAgent(registry, lambda _: dict(session), client=client)
    agent.reply("session", "Where am I?")
    session["position"] = "store"
    agent.reply("session", "Where now?")
    assert '"position": "store"' in client.options[-1]["messages"][-1]["content"]


def test_explicit_session_profile_change_replaces_old_chat_preference(registry):
    session = {"profile": "wheelchair", "constraints": {"step_free": True}}
    client = ClientStub([{"calls": [("route", {"destination": "store"})]},
                         {"calls": [("route", {"destination": "lobby", "step_free": False})]}])
    agent = ChatAgent(registry, lambda _: dict(session), client=client)
    agent.reply("session", "To the store")
    session.update(profile="walk", constraints={"step_free": False})
    agent.reply("session", "I changed my profile in the controls. Go back.")
    assert registry.calls[-1][2]["step_free"] is False


def test_default_chat_does_not_create_a_client_without_a_written_budget(registry, monkeypatch):
    monkeypatch.delenv("TYB_CHAT_BUDGET_USD", raising=False)
    assert ChatAgent(registry, lambda _: {}).reply("session", "find the press")["display"] == {"kind": "not_available"}


def test_runner_is_bounded_and_uses_auto_tool_choice(registry):
    client = ClientStub([{}])
    ChatAgent(registry, lambda _: {}, client=client).reply("session", "Hello")
    assert (client.options[0]["max_iterations"], client.options[0]["tool_choice"]) == (6, {"type": "auto"})


@pytest.fixture
def live_registry(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from server.app import create_app
    from server.config import Settings

    # Only the HTTP route's configuration check sees this placeholder. The
    # injected client below is offline and cannot make provider requests.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "offline-test-placeholder")
    with TestClient(create_app(Settings(state_dir=tmp_path / "state", static_dir=tmp_path / "web"))) as client:
        session = client.post("/api/sessions", json={"building_id": "proc-factory-dev-003", "device": "desk", "role": "admin"}).json()
        client.patch("/api/sessions/" + session["session_id"], json={"position": {"space_id": "proc-factory-dev-003-F0-S019", "source": "desk"}})
        yield client, session["session_id"]


@pytest.mark.parametrize("case", [
    ("Where is CNC mill H-A1-A?", "find", {"query": "CNC mill H-A1-A"}, True),
    ("the CNC mill", "find", {"query": "CNC mill"}, False),
    ("Find the quantum teleporter", "find", {"query": "quantum teleporter"}, False),
    ("I need the 3D printer H-A3-A and the UPS unit 1.24", "plan_tour", {"items": "proc-factory-dev-003-A00021,proc-factory-dev-003-A00325", "keep_order": False}, True),
])
def test_chat_endpoint_uses_real_registry_with_offline_interpretation(live_registry, case):
    client, session_id = live_registry
    message, name, args, expected_ok = case
    state = client.app.state
    state.chat_agent = ChatAgent(state.registry, state.store.get_session, client=ClientStub([{"calls": [(name, args)]}]))
    response = client.post("/api/chat", json={"session_id": session_id, "message": message}).json()
    print(json.dumps({"mode": "offline model, real registry", "user": message, "reply": response["reply"]}, ensure_ascii=False))
    assert response["tool_calls"][0]["ok"] is expected_ok


def test_chat_endpoint_previews_then_commits_once_with_real_registry(live_registry):
    client, session_id = live_registry
    state = client.app.state
    commit = {"calls": []}
    state.chat_agent = ChatAgent(state.registry, state.store.get_session, client=ClientStub([
        {"calls": [("propose_edit", {"action": "close", "target": "Office lift"})]}, commit,
    ]))
    preview = client.post("/api/chat", json={"session_id": session_id, "message": "Close the office lift"}).json()
    proposal = preview["tool_calls"][0]["result"]["proposal_id"]
    commit["calls"] = [("commit_edit", {"proposal_id": proposal}), ("commit_edit", {"proposal_id": proposal})]
    saved = client.post("/api/chat", json={"session_id": session_id, "message": "yes"}).json()
    print(json.dumps({"mode": "offline model, real registry", "preview": preview["reply"], "confirmed": saved["reply"]}, ensure_ascii=False))
    assert len(state.store.events("proc-factory-dev-003")) == 1
