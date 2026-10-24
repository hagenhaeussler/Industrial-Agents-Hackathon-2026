import copy
import json
from pathlib import Path
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from agent.budget import Budget
from bench.agent import load_base
from bench.llm_fallback import FIELDS, Interpretation, interpret


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
            self.tools["submit_answer"].call({"kind": "count", "inputs_json": json.dumps({"asset_type": "toilet", "floor_id": "osm-way22744230-F2"})})
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


def assert_provider_schema(schema):
    if isinstance(schema, dict):
        unsupported = {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
                       "minLength", "maxLength", "minItems", "maxItems", "minProperties", "maxProperties", "const"}
        assert not unsupported.intersection(schema)
        if schema.get("type") == "object":
            assert schema["additionalProperties"] is False
            assert set(schema.get("required", [])) == set(schema["properties"])
        for value in schema.values():
            assert_provider_schema(value)
    elif isinstance(schema, list):
        for value in schema:
            assert_provider_schema(value)


def test_strict_fallback_tools_adapt_bounds_without_mutating_solver_input_catalogue():
    original = copy.deepcopy(FIELDS)
    tools = Interpretation(load_base(Path("data/dev/osm-way22744230"))).tools()
    definitions = {tool.name: tool.to_dict() for tool in tools}
    for definition in definitions.values():
        assert definition["strict"] is True
        assert_provider_schema(definition["input_schema"])
    assert FIELDS == original
    for name in ("solve", "submit_answer"):
        schema = definitions[name]["input_schema"]
        assert set(schema["properties"]) == {"kind", "inputs_json"}
        assert schema["properties"]["inputs_json"]["type"] == "string"
        assert "anyOf" not in json.dumps(schema)
        assert len(json.dumps(schema)) < 1000
    assert definitions["submit_answer"]["cache_control"] == {"type": "ephemeral"}


@pytest.mark.parametrize(("kind", "inputs"), [
    ("wide_delivery_count", {"start": "absent", "floor_id": "absent", "min_width": -1}),
    ("count", {"asset_type": "", "floor_id": "osm-way22744230-F2"}),
    ("tour", {"stops": ["only-one"], "keep_order": True}),
    ("tour", {"stops": ["a", "b"], "keep_order": False}),
])
def test_solver_rejects_bounds_removed_from_provider_grammar(kind, inputs):
    interpretation = Interpretation(load_base(Path("data/dev/osm-way22744230")))
    response = json.loads(interpretation.submit(kind, inputs))
    assert response["ok"] is False
    assert interpretation.submitted is None


@pytest.mark.parametrize("inputs_json", ["not json", "[]", "null", '"text"', "7", "x" * 65_537])
def test_json_tool_envelope_rejects_invalid_and_nonobject_inputs(inputs_json):
    interpretation = Interpretation(load_base(Path("data/dev/osm-way22744230")))
    response = json.loads(interpretation.submit_json("count", inputs_json))
    assert response["ok"] is False
    assert "Invalid inputs_json" in response["error"]
    assert interpretation.submitted is None
    assert interpretation.invalid_inputs == 1


def test_json_envelope_uses_the_same_typed_solver_before_committing():
    interpretation = Interpretation(load_base(Path("data/dev/osm-way22744230")))
    invalid = json.loads(interpretation.submit_json("count", json.dumps({"start": "irrelevant"})))
    assert invalid["ok"] is False
    assert interpretation.submitted is None
    valid = json.loads(interpretation.submit_json("count", json.dumps({"asset_type": "toilet", "floor_id": "osm-way22744230-F2"})))
    assert valid["ok"] is True
    assert interpretation.submitted.reply == "Answer: 3"
    assert interpretation.submitted.inputs == {"asset_type": "toilet", "floor_id": "osm-way22744230-F2"}


def test_invalid_json_and_invalid_typed_inputs_share_the_single_repair_limit():
    interpretation = Interpretation(load_base(Path("data/dev/osm-way22744230")))
    interpretation.compute_json("count", "not json")
    interpretation.compute_json("count", json.dumps({"start": "irrelevant"}))
    response = json.loads(interpretation.submit_json("count", json.dumps({"asset_type": "toilet", "floor_id": "osm-way22744230-F2"})))
    assert response == {"ok": False, "error": "Input repair limit reached."}
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
    return {"calls": [("submit_answer", {"kind": "count", "inputs_json": json.dumps({"asset_type": "toilet", "floor_id": "osm-way22744230-F2"})})]}


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
        for tool in payload["tools"]:
            assert_provider_schema(tool["input_schema"])
        return httpx2.Response(200, json={
            "id": "offline-message", "type": "message", "role": "assistant", "model": payload["model"],
            "content": [{"type": "tool_use", "id": "offline-call", "name": "submit_answer",
                         "input": {"kind": "count", "inputs_json": json.dumps({"asset_type": "toilet", "floor_id": "osm-way22744230-F2"})}}],
            "stop_reason": "tool_use", "stop_sequence": None, "usage": {"input_tokens": 10, "output_tokens": 2},
        })

    with httpx2.Client(transport=httpx2.MockTransport(respond)) as http:
        client = anthropic.Anthropic(api_key="offline-placeholder", http_client=http, max_retries=0)
        result = run_script(client)
    assert result.reply == "Answer: 3"
