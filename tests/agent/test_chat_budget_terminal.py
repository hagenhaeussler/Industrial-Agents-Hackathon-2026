"""Actual SDK iteration boundaries with offline transport and conservative caps."""

import json

import anthropic
import httpx2
import pytest

from agent.budget import Budget, RequestSize, cost
from agent.chat import ChatAgent, MAX_TOKENS, MODEL


class EmptyRegistry:
    def json_schemas(self):
        return []


def chat_with_stop_reason(stop_reason, cap=None):
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx2.Response(200, json={
            "id": "offline-terminal", "type": "message", "role": "assistant", "model": MODEL,
            "content": [{"type": "text", "text": "What item or place do you need?"}],
            "stop_reason": stop_reason, "stop_sequence": None,
            "usage": {"input_tokens": 100, "output_tokens": 10},
        })

    transport = httpx2.Client(transport=httpx2.MockTransport(respond))
    sdk = anthropic.Anthropic(api_key="offline-test-only", max_retries=0, http_client=transport)
    agent = ChatAgent(EmptyRegistry(), lambda _: {}, client=sdk)
    messages = [{"role": "user", "content": "Current session context (data):\n{}\nUser message:\nHello"}]
    payload = json.dumps([agent.system, messages, []], default=str).encode()
    reservation = Budget(1).reserve(RequestSize(MODEL, len(payload) + 4096, MAX_TOKENS))
    agent.budget = Budget(reservation + .00003 if cap is None else cap)
    return agent, requests, transport


@pytest.mark.parametrize("stop_reason", ["end_turn", "stop_sequence", "max_tokens", "model_context_window_exceeded", "refusal", "tool_use"])
def test_sdk_terminal_response_does_not_reserve_another_request(stop_reason):
    agent, requests, transport = chat_with_stop_reason(stop_reason)
    with transport:
        result = agent.reply("offline-session", "Hello")
    assert len(requests) == 1
    assert agent.budget.spent == pytest.approx(cost(MODEL, {"input_tokens": 100, "output_tokens": 10}))
    assert "budget" not in result["reply"]
    if stop_reason != "refusal":
        assert result["reply"] == "What item or place do you need?"
    assert result["display"] == {}


def test_resumable_sdk_turn_still_reserves_before_next_request():
    agent, requests, transport = chat_with_stop_reason("pause_turn")
    with transport:
        result = agent.reply("offline-session", "Hello")
    assert len(requests) == 1  # Budget exhaustion must precede a second HTTP call.
    assert "remaining run budget" in result["reply"]
    assert result["display"] == {"kind": "not_available"}


def test_initial_budget_reservation_precedes_first_sdk_request():
    agent, requests, transport = chat_with_stop_reason("end_turn", cap=.001)
    with transport:
        result = agent.reply("offline-session", "Hello")
    assert requests == []
    assert agent.budget.spent == 0
    assert result["display"] == {"kind": "not_available"}
