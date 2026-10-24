import json
from pathlib import Path
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from agent.budget import Budget
from bench.agent import load_base
from bench.llm_fallback import Interpretation, interpret


class OfflineRunner:
    def __init__(self, options, submit):
        self.tools = {tool.name: tool for tool in options["tools"]}
        self.submit = submit
        self.done = False

    def __iter__(self):
        return self

    def __next__(self):
        if self.done:
            raise StopIteration
        self.done = True
        return SimpleNamespace(content=[SimpleNamespace(type="text", text="Answer: 999999")], stop_reason="end_turn", usage=SimpleNamespace(input_tokens=0, output_tokens=0))

    def generate_tool_call_response(self):
        if self.submit:
            self.tools["submit_answer"].call({"kind": "count", "inputs": {"asset_type": "toilet", "floor_id": "osm-way22744230-F2"}})
        return None


def client_for(submit):
    return SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(tool_runner=lambda **options: OfflineRunner(options, submit))))


def test_model_prose_cannot_create_a_committed_answer():
    result = interpret(load_base(Path("data/dev/osm-way22744230")), "Count toilets on floor two", (Budget(1), client_for(False)))
    assert "Answer:" not in result.reply


def test_only_solver_and_serializer_write_the_answer():
    result = interpret(load_base(Path("data/dev/osm-way22744230")), "Count toilets on floor two", (Budget(1), client_for(True)))
    assert result.reply == "Answer: 3"


def test_invalid_submission_cannot_set_the_result():
    interpretation = Interpretation(load_base(Path("data/dev/osm-way22744230")))
    interpretation.submit("count", {"asset_type": "toilet", "floor_id": "not-a-floor"})
    assert interpretation.submitted is None


class ScriptClient:
    def __init__(self, attempts):
        self.attempts = iter(attempts)
        self.options = []
        self.requests = 0
        self.beta = SimpleNamespace(messages=SimpleNamespace(tool_runner=self.runner))

    def runner(self, **options):
        self.options.append(options)
        return ScriptRunner(self, options, next(self.attempts))


class ScriptRunner:
    def __init__(self, client, options, steps):
        self.client = client
        self.tools = {tool.name: tool for tool in options["tools"]}
        self.steps = iter(steps)
        self.step = {}

    def __iter__(self):
        return self

    def __next__(self):
        self.step = next(self.steps)
        self.client.requests += 1
        if "error" in self.step:
            raise self.step["error"]
        return SimpleNamespace(content=[], stop_reason=self.step.get("stop_reason", "tool_use"),
                               usage=SimpleNamespace(input_tokens=10, output_tokens=2, cache_read_input_tokens=3))

    def generate_tool_call_response(self):
        for name, args in self.step.get("calls", []):
            self.tools[name].call(args)
        return None


def submit_step():
    return {"calls": [("submit_answer", {"kind": "count", "inputs": {"asset_type": "toilet", "floor_id": "osm-way22744230-F2"}})]}


def run_script(client, budget=None):
    return interpret(load_base(Path("data/dev/osm-way22744230")), "Count toilets on floor two", (budget or Budget(1), client))


def test_exhausted_budget_refuses_before_any_request():
    client = ScriptClient([[submit_step()]])
    run_script(client, Budget(0.000000001))
    assert client.requests == 0


def test_unsubmitted_haiku_attempt_escalates_once():
    client = ScriptClient([[{}], [submit_step()]])
    run_script(client)
    assert [options["model"] for options in client.options] == ["claude-haiku-5-5", "claude-sonnet-5-5"]


def test_usage_includes_both_model_attempts():
    result = run_script(ScriptClient([[{}], [submit_step()]]))
    assert result.tokens == {"input_tokens": 20, "output_tokens": 4, "cache_read_input_tokens": 6, "cache_creation_input_tokens": 0}


def test_eight_response_limit_applies_across_models():
    client = ScriptClient([[{}] * 20, [{}] * 20])
    run_script(client)
    assert client.requests == 8


def test_refusal_can_escalate_without_committing_prose():
    client = ScriptClient([[{"stop_reason": "refusal"}], [submit_step()]])
    assert run_script(client).reply == "Answer: 3"


def test_api_errors_keep_the_reservation_when_usage_is_unknown():
    error = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://offline.invalid"))
    budget = Budget(1)
    result = run_script(ScriptClient([[{"error": error}], [{"error": error}]]), budget)
    assert result.cost == pytest.approx(budget.spent)


def test_tool_repair_is_limited_to_one_retry():
    interpretation = Interpretation(load_base(Path("data/dev/osm-way22744230")))
    for _ in range(2):
        interpretation.submit("count", {"asset_type": "toilet", "floor_id": "absent"})
    interpretation.submit("count", {"asset_type": "toilet", "floor_id": "osm-way22744230-F2"})
    assert interpretation.submitted is None


def test_deadline_prevents_new_requests(monkeypatch):
    from bench import llm_fallback

    clock = iter([0, 61, 61])
    monkeypatch.setattr(llm_fallback.time, "monotonic", lambda: next(clock))
    client = ScriptClient([[submit_step()]])
    run_script(client)
    assert client.requests == 0


def test_real_sdk_tool_loop_commits_only_the_computed_result():
    def respond(request):
        payload = json.loads(request.content)
        return httpx2.Response(200, json={
            "id": "offline-message", "type": "message", "role": "assistant", "model": payload["model"],
            "content": [{"type": "tool_use", "id": "offline-call", "name": "submit_answer",
                         "input": {"kind": "count", "inputs": {"asset_type": "toilet", "floor_id": "osm-way22744230-F2"}}}],
            "stop_reason": "tool_use", "stop_sequence": None, "usage": {"input_tokens": 10, "output_tokens": 2},
        })

    with httpx2.Client(transport=httpx2.MockTransport(respond)) as http:
        client = anthropic.Anthropic(api_key="offline-placeholder", http_client=http, max_retries=0)
        result = run_script(client)
    assert result.reply == "Answer: 3"
