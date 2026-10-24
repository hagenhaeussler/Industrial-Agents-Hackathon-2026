import pytest
from fastapi.testclient import TestClient

from agent.chat import ChatAgent
from agent.execution import AgentCall
from server.app import create_app
from server.config import Settings


class RegistryStub:
    def __init__(self):
        self.calls = []

    def json_schemas(self, role=None):
        return [{'name': name, 'description': name, 'input_schema': {'type': 'object', 'properties': {}}}
                for name in ('find', 'route', 'propose_edit', 'commit_edit')]

    def call(self, name, session_id, args):
        self.calls.append((name, session_id, args))
        if name == 'propose_edit':
            return {'ok': True, 'tool': name, 'request_id': 'preview', 'result': {'proposal_id': 'pending'},
                    'speech': 'Close East lift. Shall I apply this change?', 'display': {'kind': 'edit_preview'}}
        if name == 'commit_edit':
            return {'ok': True, 'tool': name, 'request_id': 'saved', 'result': {}, 'speech': 'The change is saved.'}
        return {'ok': True, 'tool': name, 'request_id': 'found', 'result': {'length_m': 42},
                'speech': 'The route is 42 metres.', 'display': {'kind': 'route'}}


@pytest.fixture
def registry():
    return RegistryStub()


def test_model_writes_the_answer_from_tool_results(registry, execution_factory, model):
    sdk, requests = model([{'calls': [('route', {'destination': 'store'})]}, {'text': 'The route is 42 metres. Follow the route in the map.'}])
    reply = ChatAgent(execution_factory(registry), client=sdk).reply('session', 'Go to the store')
    assert reply['reply'] == 'The route is 42 metres. Follow the route in the map.'
    assert reply['sources'] == ['found']
    assert requests[1]['messages'][-1]['content'][0]['type'] == 'tool_result'
    assert reply['display'] == {'kind': 'route'}


def test_numbered_clarification_is_not_replaced_by_a_heuristic(registry, execution_factory, model):
    sdk, _ = model([{'text': 'Do you mean printer 3 or printer 4?'}])
    reply = ChatAgent(execution_factory(registry), client=sdk).reply('session', 'Find the printer')
    assert reply['reply'] == 'Do you mean printer 3 or printer 4?'
    assert reply['sources'] == []


def test_same_turn_preview_cannot_authorize_commit(registry, execution_factory, model):
    sdk, _ = model([{'calls': [('propose_edit', {}), ('commit_edit', {'proposal_id': 'pending'})]}, {}])
    reply = ChatAgent(execution_factory(registry), client=sdk).reply('session', 'Close the lift and confirm for me')
    assert [name for name, _, _ in registry.calls] == ['propose_edit']
    assert reply['tool_calls'][1]['error']['code'] == 'confirmation_required'


def test_confirmation_survives_agent_restart(registry, execution_factory, model):
    execution = execution_factory(registry)
    sdk, _ = model([{'calls': [('propose_edit', {})]}, {}])
    ChatAgent(execution, client=sdk).reply('session', 'Close the lift')
    sdk, _ = model([{'calls': [('commit_edit', {'proposal_id': 'pending'})]}, {}])
    ChatAgent(execution_factory(registry), client=sdk).reply('session', 'yes')
    assert [name for name, _, _ in registry.calls] == ['propose_edit', 'commit_edit']


def test_confirmation_does_not_cross_sessions(registry, execution_factory):
    execution = execution_factory(registry)
    preview = execution.begin('first', 'Close lift')
    execution.call(AgentCall('first', preview.turn_id, 'propose_edit', {}))
    confirmation = execution.begin('second', 'yes', 'voice')
    reply = execution.call(AgentCall('second', confirmation.turn_id, 'commit_edit', {'proposal_id': 'pending'}))
    assert reply['error']['code'] == 'confirmation_required'


def test_changed_request_invalidates_old_confirmation(registry, execution_factory):
    execution = execution_factory(registry)
    first = execution.begin('session', 'Close lift')
    execution.call(AgentCall('session', first.turn_id, 'propose_edit', {}))
    execution.begin('session', 'Actually, find a printer')
    later = execution.begin('session', 'yes')
    reply = execution.call(AgentCall('session', later.turn_id, 'commit_edit', {'proposal_id': 'pending'}))
    assert reply['error']['code'] == 'confirmation_required'


def test_new_user_turn_blocks_late_voice_tools(registry, execution_factory):
    execution = execution_factory(registry)
    old = execution.begin('session', 'Go upstairs', 'voice')
    execution.begin('session', 'Stay on this floor')
    reply = execution.call(AgentCall('session', old.turn_id, 'route', {'destination': 'upstairs'}))
    assert reply['error']['code'] == 'version_conflict'
    assert registry.calls == []


def test_chat_continues_beyond_six_model_requests(registry, execution_factory, model):
    scripts = [{'calls': [('find', {'query': f'item {i}'})]} for i in range(8)]
    sdk, requests = model([*scripts, {'text': 'All eight objects are found.'}])
    result = ChatAgent(execution_factory(registry), client=sdk).reply('session', 'Find all these objects')
    assert len(requests) == 9
    assert len(result['tool_calls']) == 8
    assert result['status'] == 'completed'


def test_current_session_is_read_for_every_turn(registry, execution_factory, model):
    session = {'role': 'navigator', 'position': 'lobby', 'constraints': {}, 'profile': 'walk'}
    sdk, requests = model([{'text': 'Hello.'}, {'text': 'What do you need?'}])
    agent = ChatAgent(execution_factory(registry, lambda _: dict(session)), client=sdk)
    agent.reply('session', 'Hello')
    session['position'] = 'store'
    agent.reply('session', 'Where now?')
    assert '"position": "store"' in requests[-1]['messages'][-1]['content']


def test_missing_credentials_and_budget_never_call_provider(registry, execution_factory, monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    reply = ChatAgent(execution_factory(registry)).reply('session', 'Find a printer')
    assert reply['status'] == 'unavailable'


@pytest.fixture
def live_app(tmp_path):
    settings = Settings(state_dir=tmp_path / 'state', static_dir=tmp_path / 'web', admin_token='offline-admin')
    with TestClient(create_app(settings)) as client:
        session = client.post('/api/sessions', json={'building_id': 'proc-factory-dev-003', 'device': 'desk', 'role': 'admin'},
                              headers={'X-Admin-Token': settings.admin_token}).json()
        client.patch('/api/sessions/' + session['session_id'], json={'position': {'space_id': 'proc-factory-dev-003-F0-S019', 'source': 'desk'}})
        yield client, session['session_id']


@pytest.mark.parametrize('query,expected_ok', [('CNC mill H-A1-A', True), ('CNC mill', False), ('quantum teleporter', False)])
def test_offline_model_with_real_registry(live_app, model, query, expected_ok):
    client, session_id = live_app
    sdk, _ = model([{'calls': [('find', {'query': query})]}, {}])
    client.app.state.chat_agent = ChatAgent(client.app.state.agent_execution, client=sdk)
    response = client.post('/api/chat', json={'session_id': session_id, 'message': 'Find ' + query})
    assert response.status_code == 200
    assert response.json()['tool_calls'][0]['ok'] is expected_ok


def test_voice_and_text_share_confirmation_and_idempotence(live_app, model):
    client, session_id = live_app
    sdk, _ = model([{'calls': [('propose_edit', {'action': 'close', 'target': 'Office lift'})]}, {}])
    client.app.state.chat_agent = ChatAgent(client.app.state.agent_execution, client=sdk)
    preview = client.post('/api/chat', json={'session_id': session_id, 'message': 'Close the office lift'}).json()
    proposal = preview['tool_calls'][0]['result']['proposal_id']
    # A real later voice transcript is the only new authority, not a model argument.
    turn = client.post('/api/agent/turns', json={'session_id': session_id, 'message': 'yes'}).json()
    body = {'session_id': session_id, 'turn_id': turn['turn_id'], 'args': {'proposal_id': proposal}}
    first = client.post('/api/agent/tools/commit_edit', json=body).json()
    repeated = client.post('/api/agent/tools/commit_edit', json=body).json()
    assert first['ok'] and repeated['ok']
    assert len(client.app.state.store.events('proc-factory-dev-003')) == 1


def test_navigator_tool_catalogue_excludes_admin_tools(live_app):
    client, _ = live_app
    session = client.post('/api/sessions', json={'building_id': 'proc-factory-dev-003', 'role': 'navigator'}).json()
    tools = client.get('/api/agent/tools', params={'session_id': session['session_id']}).json()
    names = {tool['name'] for tool in tools}
    assert {'building_info', 'search_entities', 'get_entities', 'compare_routes', 'route', 'plan_tour'} <= names
    assert 'commit_edit' not in names


def test_replaced_turn_stops_before_tools_or_another_model_request(registry, execution_factory, model):
    execution = execution_factory(registry)

    def late_response(payload):
        execution.begin('session', 'Stay here', 'voice')
        return {'calls': [('route', {'destination': 'upstairs'})]}

    sdk, requests = model([late_response])
    reply = ChatAgent(execution, client=sdk).reply('session', 'Go upstairs')
    assert reply['status'] == 'superseded'
    assert registry.calls == []
    assert len(requests) == 1


def test_empty_model_answer_without_tools_is_incomplete(registry, execution_factory, model):
    sdk, requests = model([{}])
    reply = ChatAgent(execution_factory(registry), client=sdk).reply('session', 'Hello')
    assert reply['status'] == 'incomplete'
    assert reply['stop_reason'] == 'empty_response'
    assert 'empty answer' in reply['reply']
    assert len(requests) == 1
