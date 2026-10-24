"""No speculative provider requests after terminal, truncated or refused output."""

import pytest

from agent.budget import Budget, BudgetExceeded, cost
from agent.runtime import AgentLoop, LoopOptions, RunRequest, ToolSet


class OneRequestBudget(Budget):
    def __init__(self):
        super().__init__(1)
        self.reservations = 0

    def reserve(self, request):
        self.reservations += 1
        if self.reservations > 1:
            raise BudgetExceeded('No second request is permitted.')
        return super().reserve(request)


@pytest.mark.parametrize('stop_reason', ['end_turn', 'stop_sequence', 'max_tokens', 'model_context_window_exceeded', 'refusal'])
def test_terminal_response_does_not_reserve_another_request(model, stop_reason):
    sdk, requests = model([{'text': 'The model response.', 'stop_reason': stop_reason}])
    budget = OneRequestBudget()
    result = AgentLoop(sdk.beta.messages, budget).run(RunRequest([], [{'role': 'user', 'content': 'Hello'}], ToolSet([], lambda *_: {})))
    assert len(requests) == 1
    assert budget.reservations == 1
    assert budget.spent == pytest.approx(cost('claude-sonnet-5-5', {'input_tokens': 100, 'output_tokens': 10}))
    assert result.reason == ('end_turn' if stop_reason == 'stop_sequence' else stop_reason)


def test_pause_reserves_before_another_provider_request(model):
    sdk, requests = model([{'text': 'Continuing.', 'stop_reason': 'pause_turn'}])
    result = AgentLoop(sdk.beta.messages, OneRequestBudget()).run(RunRequest([], [{'role': 'user', 'content': 'Hello'}], ToolSet([], lambda *_: {})))
    assert len(requests) == 1
    assert result.reason == 'budget_limit'


def test_exhausted_budget_stops_before_first_request(model):
    sdk, requests = model([])
    result = AgentLoop(sdk.beta.messages, Budget(.000001)).run(RunRequest([], [{'role': 'user', 'content': 'Hello'}], ToolSet([], lambda *_: {})))
    assert requests == []
    assert result.reason == 'budget_limit'


def test_truncated_tool_call_cannot_commit(model):
    sdk, _ = model([{'calls': [('commit_edit', {'proposal_id': 'pending'})], 'stop_reason': 'max_tokens'}])
    calls = []
    tools = ToolSet([{'name': 'commit_edit', 'input_schema': {'type': 'object', 'properties': {}}}], lambda name, args: calls.append(name))
    result = AgentLoop(sdk.beta.messages).run(RunRequest([], [{'role': 'user', 'content': 'yes'}], tools))
    assert result.reason == 'max_tokens'
    assert calls == []


def test_tool_limit_is_enforced_before_remaining_batch_and_next_request(model):
    sdk, requests = model([{'calls': [('find', {'query': 'a'}), ('find', {'query': 'b'}), ('find', {'query': 'c'})]}])
    calls = []
    tools = ToolSet([{'name': 'find', 'input_schema': {'type': 'object', 'properties': {}}}], lambda name, args: calls.append(args) or {'ok': True})
    result = AgentLoop(sdk.beta.messages).run(RunRequest([], [{'role': 'user', 'content': 'Find all'}], tools, LoopOptions(max_tool_calls=2)))
    assert len(requests) == 1
    assert len(calls) == len(result.calls) == 2
    assert result.reason == 'tool_limit'
    assert len(result.messages[-1]['content']) == 3  # Every requested call has a matching result.


def test_repeated_tool_call_id_does_not_repeat_execution(model):
    block = {'type': 'tool_use', 'id': 'same', 'name': 'find', 'input': {'query': 'a'}}
    sdk, _ = model([{'content': [block, block]}, {}])
    calls = []
    tools = ToolSet([{'name': 'find', 'input_schema': {'type': 'object', 'properties': {}}}], lambda name, args: calls.append(args) or {'ok': True})
    AgentLoop(sdk.beta.messages).run(RunRequest([], [{'role': 'user', 'content': 'Find a'}], tools))
    assert calls == [{'query': 'a'}]


def test_request_timeout_uses_remaining_turn_deadline(model, monkeypatch):
    import agent.runtime as runtime
    sdk, requests = model([{'calls': [('find', {})]}])
    clock = iter([0, 0, 2])
    monkeypatch.setattr(runtime.time, 'monotonic', lambda: next(clock))
    tools = ToolSet([{'name': 'find', 'input_schema': {'type': 'object', 'properties': {}}}], lambda *_: pytest.fail('Expired tools must not run'))
    result = AgentLoop(sdk.beta.messages).run(RunRequest([], [{'role': 'user', 'content': 'Find'}], tools, LoopOptions(max_seconds=1)))
    assert result.reason == 'time_limit'
    assert len(requests) == 1


def test_context_limit_stops_before_reserving_or_sending(model):
    sdk, requests = model([])
    result = AgentLoop(sdk.beta.messages, Budget(1)).run(RunRequest([], [{'role': 'user', 'content': 'x' * 10000}], ToolSet([], lambda *_: {}), LoopOptions(max_context_bytes=5000)))
    assert requests == []
    assert result.reason == 'context_limit'
