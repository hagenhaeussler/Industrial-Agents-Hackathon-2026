"""A completed SDK turn must survive the process budget boundary."""

import importlib.util
import json

import pytest


# L02 is intentionally absent from pre-agent main. Do not hide import/SDK errors
# once agent.chat exists: only a genuinely missing module may skip this seam.
agent_spec = importlib.util.find_spec("agent")
# Before L02, pytest's starter_agent path can resolve the kit's standalone
# agent.py. That module cannot provide agent.chat and is an absent L02 package.
chat_spec = (importlib.util.find_spec("agent.chat")
             if agent_spec is not None and agent_spec.submodule_search_locations is not None else None)
import anthropic
import httpx2
from anthropic.types.beta import BetaToolUseBlock
from fastapi.testclient import TestClient

from server.app import create_app
from server.config import Settings


@pytest.mark.parametrize("tool_first", [False, True], ids=["terminal-reply", "tool-then-terminal-display"])
def test_completed_chat_turn_survives_budget_boundary(tmp_path, monkeypatch, tool_first):
    if chat_spec is None:
        pytest.importorskip("agent.chat", reason="L02 agent.chat is not merged yet", exc_type=ModuleNotFoundError)
    from agent.budget import Budget, RequestSize, cost
    from agent.chat import ChatAgent, MAX_TOKENS, MODEL

    # This placeholder only enables the HTTP route. The injected SDK client can
    # access only MockTransport; it cannot send a provider request.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "offline-route-check-only")
    monkeypatch.delenv("TYB_CHAT_BUDGET_USD", raising=False)
    settings = Settings(state_dir=tmp_path / "state", static_dir=tmp_path / "web")
    requests = []
    clarification = "What item or place do you need?"
    query = {"query": "CNC mill H-A1-A"}
    tool_id = "offline-find"

    def respond(request):
        requests.append(json.loads(request.content))
        use_tool = tool_first and len(requests) == 1
        content = ([{"type": "tool_use", "id": tool_id, "name": "find", "input": query}]
                   if use_tool else [{"type": "text", "text": "" if tool_first else clarification}])
        return httpx2.Response(200, json={
            "id": f"offline-message-{len(requests)}", "type": "message", "role": "assistant", "model": MODEL,
            "content": content, "stop_reason": "tool_use" if use_tool else "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 100, "output_tokens": 10},
        })

    with TestClient(create_app(settings)) as client, httpx2.Client(transport=httpx2.MockTransport(respond)) as transport:
        session_response = client.post("/api/sessions", json={
            "building_id": "proc-factory-dev-003", "device": "desk", "role": "navigator",
        })
        assert session_response.status_code == 200, session_response.text
        session_id = session_response.json()["session_id"]
        state = client.app.state
        assert len(state.registry.json_schemas()) == 11
        sdk = anthropic.Anthropic(api_key="offline-test-only", max_retries=0, http_client=transport)
        agent = ChatAgent(state.registry, state.store.get_session, client=sdk)
        state.chat_agent = agent
        message = "Where is CNC mill H-A1-A?" if tool_first else "Find an item."
        context = state.store.get_session(session_id)
        messages = [{"role": "user", "content":
                     "Current session context (data):\n" + json.dumps(context, ensure_ascii=False)
                     + "\nUser message:\n" + message}]
        expected = {"reply": clarification, "display": {}}
        spent_before_terminal = 0.0
        one_request_cost = cost(MODEL, {"input_tokens": 100, "output_tokens": 10})
        if tool_first:
            # find is read-only. Its real result estimates the next request's
            # conservative reservation; variable IDs have fixed lengths. The
            # small margin covers timing-string differences between the calls.
            found = state.registry.call("find", session_id, query)
            assert found["ok"], found
            messages.extend([
                {"role": "assistant", "content": [BetaToolUseBlock(type="tool_use", id=tool_id, name="find", input=query)]},
                {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_id,
                                               "content": json.dumps(found, ensure_ascii=False)}]},
            ])
            expected = {"reply": found["speech"], "display": found["display"]}
            spent_before_terminal = one_request_cost
        payload = json.dumps([agent.system, messages, state.registry.json_schemas()], default=str).encode()
        terminal_reservation = Budget(1).reserve(RequestSize(MODEL, len(payload) + 4096, MAX_TOKENS))
        agent.budget = Budget(spent_before_terminal + terminal_reservation + 0.00003)

        response = client.post("/api/chat", json={"session_id": session_id, "message": message})
        assert response.status_code == 200, response.text
        assert len(requests) == (2 if tool_first else 1)
        assert agent.budget.spent == pytest.approx(len(requests) * one_request_cost)
        payload = response.json()
        assert {"reply": payload["reply"], "display": payload["display"]} == expected
        assert len(payload["tool_calls"]) == (1 if tool_first else 0)
