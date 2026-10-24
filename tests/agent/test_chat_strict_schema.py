"""Inspect real SDK request JSON and retain registry validation after adaptation."""

import copy
import json
from types import SimpleNamespace

import anthropic
import httpx2

from agent.chat import ChatAgent, MODEL
from agent.schema import strict_schema
from server.tools import REGISTRY, ToolRegistry


UNSUPPORTED = {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
               "minLength", "maxLength", "maxItems", "minProperties", "maxProperties"}


def assert_supported(schema):
    if isinstance(schema, dict):
        assert not UNSUPPORTED.intersection(schema)
        if schema.get("type") == "object":
            assert schema["additionalProperties"] is False
            assert set(schema.get("required", [])) <= set(schema["properties"])
        for value in schema.values():
            assert_supported(value)
    elif isinstance(schema, list):
        for value in schema:
            assert_supported(value)


def test_registry_schemas_adapt_without_mutating_original_validation():
    for definition in REGISTRY.values():
        original = definition.json_schema
        pristine = copy.deepcopy(original)
        adapted = strict_schema(original)
        assert_supported(adapted)
        assert original == pristine
        assert adapted.get("required", []) == original.get("required", [])
    route = strict_schema(REGISTRY["route"].json_schema)
    assert "minimum: 0" in route["properties"]["min_door_width_m"]["description"]
    assert route["properties"]["min_door_width_m"]["type"] == "number"
    assert "min_door_width_m" not in route["required"]
    find = strict_schema(REGISTRY["find"].json_schema)
    assert "minLength: 1" in find["properties"]["query"]["description"]
    assert "maxLength: 1000" in find["properties"]["query"]["description"]
    assert REGISTRY["route"].json_schema["properties"]["min_door_width_m"]["anyOf"][0]["minimum"] == 0


def test_required_nullable_fields_remain_nullable_and_property_names_survive():
    schema = {"type": "object", "properties": {
        "default": {"type": "string"},
        "nullable": {"anyOf": [{"type": "number", "minimum": 0}, {"type": "null"}]}},
        "required": ["default", "nullable"]}
    adapted = strict_schema(schema)
    assert set(adapted["properties"]) == {"default", "nullable"}
    assert adapted["properties"]["nullable"]["anyOf"][1] == {"type": "null"}


def test_actual_sdk_payload_keeps_domain_schemas_and_registry_rejects_bad_width(execution_factory):
    # The bad width fails in the real registry's Pydantic model before any
    # geometry operation, so only its session/version read seam needs a stub.
    session = {"session_id": "offline", "building_id": "unit", "role": "navigator",
               "position": {"space_id": "a"}, "profile": "walk", "constraints": {}}
    store = SimpleNamespace(get_session=lambda _: dict(session), version=lambda _: 0)
    registry = ToolRegistry(SimpleNamespace(store=store))
    requests = []

    def respond(request):
        payload = json.loads(request.content)
        requests.append(payload)
        assert {tool["name"] for tool in payload["tools"]} == {definition.name for definition in REGISTRY.values() if "navigator" in definition.roles}
        for tool in payload["tools"]:
            assert tool["strict"] is False
            assert tool["input_schema"] == REGISTRY[tool["name"]].json_schema
        first = len(requests) == 1
        content = ([{"type": "tool_use", "id": "offline-route", "name": "route",
                     "input": {"destination": "a", "step_free": False, "min_door_width_m": -1}}]
                   if first else [{"type": "text", "text": ""}])
        return httpx2.Response(200, json={"id": f"offline-{len(requests)}", "type": "message",
            "role": "assistant", "model": MODEL, "content": content,
            "stop_reason": "tool_use" if first else "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 100, "output_tokens": 10}})

    with httpx2.Client(transport=httpx2.MockTransport(respond)) as transport:
        sdk = anthropic.Anthropic(api_key="offline-test-only", max_retries=0, http_client=transport)
        result = ChatAgent(execution_factory(registry, store.get_session), client=sdk).reply("offline", "Use a negative door width.")
    assert len(requests) == 2
    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["ok"] is False
    assert result["tool_calls"][0]["error"]["code"] == "invalid_args"
