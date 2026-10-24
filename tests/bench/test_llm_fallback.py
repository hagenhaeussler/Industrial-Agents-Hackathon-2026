"""Submission uses real platform tools through the product agent and SDK transport."""

import json
from pathlib import Path

import pytest

from agent.budget import Budget
from agent.chat import ChatAgent
from agent.execution import AgentCall
from agent.prompts import chat_prompt
from bench.agent import load_base
from bench.llm_fallback import interpret
from bench.session import submission_session
from bench.submission import Submission

QUESTION = 'How many toilet items are on floor two?'
COUNT = {'kind': 'count', 'asset_type': 'toilet', 'floor': 'osm-way22744230-F2'}


@pytest.fixture
def building():
    return load_base(Path('data/dev/osm-way22744230'))


def last_result(payload):
    return json.loads(payload['messages'][-1]['content'][-1]['content'])


def submit_result(payload):
    source = last_result(payload)
    return {'calls': [('submit_answer', {'request_id': source['request_id']})]}


def test_submission_and_chat_use_the_same_agent_tools_and_prompt(building, model):
    chat_sdk, chat_requests = model([{'calls': [('spatial_query', COUNT)]}, {'text': 'There are three toilets.'}])
    with submission_session(building) as (execution, session_id):
        chat = ChatAgent(execution, client=chat_sdk).reply(session_id, QUESTION)
    sdk, requests = model([{'calls': [('spatial_query', COUNT)]}, submit_result])
    result = interpret(building, QUESTION, (Budget(1), sdk))
    assert result.reply == 'Answer: 3'
    assert result.result['value'] == chat['tool_calls'][0]['result']['value']
    chat_tools = {tool['name']: tool['input_schema'] for tool in chat_requests[0]['tools']}
    submission_tools = {tool['name']: tool['input_schema'] for tool in requests[0]['tools'] if tool['name'] != 'submit_answer'}
    assert submission_tools == chat_tools
    assert requests[0]['system'][0]['text'].startswith(chat_prompt())
    assert requests[0]['model'] == chat_requests[0]['model']
    assert requests[0]['max_tokens'] == chat_requests[0]['max_tokens']
    assert requests[0]['messages'][0]['content'].endswith(QUESTION)


def test_only_the_serializer_can_commit_an_answer(building, model):
    sdk, requests = model([{'text': 'Answer: 999999'}])
    result = interpret(building, QUESTION, (Budget(1), sdk))
    assert not result.reply.startswith('Answer:')
    assert result.method == 'unanswered'
    assert len(requests) == 1


@pytest.mark.parametrize('arguments', [
    {}, {'request_id': 'invented'}, {'request_id': 7},
    {'request_id': 'x', 'answer': 'Answer: 3'},
    {'kind': 'count', 'inputs_json': json.dumps(COUNT)},
])
def test_submission_rejects_unobserved_or_model_supplied_values(building, arguments):
    submission = Submission(building)
    assert submission.submit(arguments)['ok'] is False
    assert not submission.done()


def test_result_references_cannot_cross_runs(building):
    with submission_session(building) as (execution, session_id):
        turn = execution.begin(session_id, QUESTION)
        reply = execution.call(AgentCall(session_id, turn.turn_id, 'spatial_query', COUNT))
        first, second = Submission(building), Submission(building)
        first.observe(reply)
        assert second.submit({'request_id': reply['request_id']})['ok'] is False
        assert first.submit({'request_id': reply['request_id']})['ok'] is True


def test_discovery_is_not_a_submittable_calculation(building, model):
    sdk, _ = model([{'calls': [('building_info', {})]}, submit_result, {}])
    result = interpret(building, QUESTION, (Budget(1), sdk))
    assert result.method == 'unanswered'


def test_invalid_arguments_can_be_repaired_through_the_shared_registry(building, model):
    def repaired(payload):
        assert last_result(payload)['error']['code'] == 'invalid_args'
        return {'calls': [('spatial_query', COUNT)]}
    sdk, _ = model([{'calls': [('spatial_query', {**COUNT, 'floor': 7})]}, repaired, submit_result])
    result = interpret(building, QUESTION, (Budget(1), sdk))
    assert result.reply == 'Answer: 3'
    assert result.tool_calls == 3


def test_submit_does_not_recompute_the_observed_result(building, monkeypatch):
    with submission_session(building) as (execution, session_id):
        turn = execution.begin(session_id, QUESTION)
        reply = execution.call(AgentCall(session_id, turn.turn_id, 'spatial_query', COUNT))
        sink = Submission(building)
        sink.observe(reply)
        reply['result']['value'] = 999
        monkeypatch.setattr('core.spatial.solve', lambda *_args, **_kwargs: pytest.fail('Submission must only format'))
        assert sink.submit({'request_id': reply['request_id']})['ok'] is True
        assert sink.prediction.reply == 'Answer: 3'


def test_post_submit_calls_do_not_execute_or_reserve_again(building, model, monkeypatch):
    executed = []
    from agent.execution import AgentExecution
    call = AgentExecution.call
    def record(self, request):
        executed.append(request.name)
        return call(self, request)
    monkeypatch.setattr(AgentExecution, 'call', record)
    def submit_batch(payload):
        return {'calls': [('submit_answer', {'request_id': last_result(payload)['request_id']}), ('building_info', {})]}
    sdk, requests = model([{'calls': [('spatial_query', COUNT)]}, submit_batch])
    budget = TrackingBudget()
    result = interpret(building, QUESTION, (budget, sdk))
    assert result.reply == 'Answer: 3'
    assert executed == ['spatial_query']
    assert len(requests) == budget.reservations == 2
    assert result.tool_calls == 2


class TrackingBudget(Budget):
    def __init__(self):
        super().__init__(1)
        self.reservations = 0
    def reserve(self, request):
        self.reservations += 1
        return super().reserve(request)


@pytest.mark.parametrize('stop', ['end_turn', 'max_tokens', 'refusal', 'model_context_window_exceeded'])
def test_terminal_output_stops_without_escalation_or_extra_reservation(building, model, stop):
    sdk, requests = model([{'stop_reason': stop}])
    budget = TrackingBudget()
    result = interpret(building, QUESTION, (budget, sdk))
    assert len(requests) == budget.reservations == 1
    assert not result.reply.startswith('Answer:')
    assert result.cost == pytest.approx(budget.spent)
    assert result.tokens['input_tokens'] == 100


def test_truncated_submission_is_not_executed(building, model):
    def truncated(payload):
        return {**submit_result(payload), 'stop_reason': 'max_tokens'}
    sdk, requests = model([{'calls': [('spatial_query', COUNT)]}, truncated])
    result = interpret(building, QUESTION, (Budget(1), sdk))
    assert result.method == 'unanswered'
    assert len(requests) == 2


def test_tool_limit_stops_at_the_completed_batch(building, model, monkeypatch):
    monkeypatch.setenv('TYB_AGENT_MAX_TOOL_CALLS', '2')
    sdk, requests = model([{'calls': [('building_info', {}), ('building_info', {}), ('building_info', {})]}])
    budget = TrackingBudget()
    result = interpret(building, QUESTION, (budget, sdk))
    assert len(requests) == budget.reservations == 1
    assert result.tool_calls == 2
    assert 'tool_limit' in result.error


def test_budget_stops_before_a_request(building, model):
    sdk, requests = model([])
    result = interpret(building, QUESTION, (Budget(.00000001), sdk))
    assert requests == []
    assert 'budget_limit' in result.error


def test_provider_failure_keeps_prior_usage_and_uncertain_reservation(building, model):
    sdk, requests = model([{'calls': [('building_info', {})]}, {'http_status': 500}])
    budget = TrackingBudget()
    result = interpret(building, QUESTION, (budget, sdk))
    assert result.cost == pytest.approx(budget.spent)
    assert result.cost > 0
    assert result.tokens['input_tokens'] == 100
    assert result.method == 'unanswered'
    assert len(requests) == 2


def test_each_question_has_a_new_session_without_previous_turns(building, model):
    sdk, requests = model([{'text': 'first'}, {'text': 'second'}])
    for _ in range(2):
        interpret(building, QUESTION, (Budget(1), sdk))
    assert [len(request['messages']) for request in requests] == [1, 1]
    assert all('"position": null' in request['messages'][0]['content'] for request in requests)


def test_common_configuration_selects_model_and_request_limit(building, model, monkeypatch):
    monkeypatch.setenv('TYB_AGENT_MODEL', 'claude-haiku-5-5')
    monkeypatch.setenv('TYB_AGENT_MAX_STEPS', '1')
    sdk, requests = model([{'calls': [('building_info', {})]}])
    result = interpret(building, QUESTION, (Budget(1), sdk))
    assert result.model == requests[0]['model'] == 'claude-haiku-5-5'
    assert len(requests) == 1
    assert 'step_limit' in result.error


def route_pair(building):
    opening = next(item for item in building.openings.values()
                   if len(item['space_ids']) == 2 and all(sid in building.spaces for sid in item['space_ids']))
    return opening['space_ids']


def test_explicit_route_can_submit_without_a_session_position(building, model):
    start, destination = route_pair(building)
    sdk, _ = model([{'calls': [('query_route', {'start': start, 'destination': destination})]}, submit_result])
    result = interpret(building, 'How do I get between these rooms?', (Budget(1), sdk))
    assert result.result['route']['reachable'] is True
    assert result.inputs['start'] == start
    assert result.inputs['destination'] == destination
    assert result.reply.startswith('Answer: ')


def test_supplied_constraints_enter_the_common_session_before_tools(building, model):
    start, destination = route_pair(building)
    def query(payload):
        assert '"min_door_width_m": 100' in payload['messages'][0]['content']
        return {'calls': [('query_route', {'start': start, 'destination': destination, 'min_door_width_m': 0})]}
    sdk, _ = model([query, submit_result])
    result = interpret(building, 'Get there with this load', (Budget(1), sdk), constraints={'min_door_width_m': 100})
    assert result.reply == 'Answer: no route'
    assert result.result['route']['constraints']['min_door_width_m'] == 100


def test_temporary_closures_are_computed_and_submitted_without_an_edit(building, model):
    start, destination = route_pair(building)
    sdk, _ = model([{'calls': [('query_route', {'start': start, 'destination': destination, 'closed': [destination]})]}, submit_result])
    result = interpret(building, 'Could I go there if that room were closed?', (Budget(1), sdk))
    assert result.reply == 'Answer: no route'
    assert result.result['route']['constraints']['closed'] == [destination]
    assert building.closed == set()


def test_fixed_tour_submits_the_actual_shared_plan(building, model):
    start, destination = route_pair(building)
    sdk, _ = model([{'calls': [('query_tour', {'start': start, 'items': [destination], 'keep_order': True})]}, submit_result])
    result = interpret(building, 'Visit this room from there', (Budget(1), sdk))
    assert result.kind == 'tour'
    assert result.result['reachable'] is True
    assert result.result['order_policy'] == 'fixed'
    assert result.result['legs']
    assert result.inputs['stops'] == [start, destination]


def test_invalid_supplied_constraints_stop_before_model_request(building, model):
    sdk, requests = model([])
    with pytest.raises(ValueError):
        interpret(building, QUESTION, (Budget(1), sdk), constraints={'closed': ['missing']})
    assert requests == []
