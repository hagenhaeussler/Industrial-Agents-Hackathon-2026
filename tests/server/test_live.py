"""Exercise the real desk -> phone -> closure -> replan transport seam."""
from dataclasses import replace
import json
import sys
from types import SimpleNamespace
from time import perf_counter

from fastapi.testclient import TestClient
import pytest

from server.app import create_app
from server.config import Settings, REPO_ROOT


@pytest.fixture
def settings(tmp_path):
    return Settings(state_dir=tmp_path / 'state', hero_dir=tmp_path / 'hero', static_dir=tmp_path / 'dist', admin_token='server-test-admin-code')


@pytest.fixture
def raw():
    return json.loads((REPO_ROOT / 'data/dev/proc-factory-dev-003/building.json').read_text())


def session(client, building_id, role='navigator', device='desk', profile='walk'):
    response = client.post('/api/sessions', json={'building_id': building_id, 'role': role, 'device': device, 'profile': profile},
                           headers={'X-Admin-Token': client.app.state.settings.admin_token} if role == 'admin' else {})
    assert response.status_code == 200, response.text
    return response.json()


def tool(client, sid, name, args):
    response = client.post('/api/tools/' + name, json={'session_id': sid, 'args': args})
    assert response.status_code == 200, response.text
    return response.json()


def test_desk_phone_commit_broadcast_replan_restart(settings, raw):
    bid = raw['building']['id']
    lift = next(v for v in raw['vertical_connectors'] if v['kind'] == 'lift')
    start, target = lift['space_ids'][:2]
    with TestClient(create_app(settings)) as client:
        desk = session(client, bid)
        sid = desk['session_id']
        response = client.patch('/api/sessions/' + sid, json={'position': {'space_id': start, 'source': 'desk'}})
        assert response.status_code == 200, response.text
        tour_response = client.post('/api/tours', json={'session_id': sid, 'items': [start, target], 'keep_order': True})
        assert tour_response.status_code == 200, tour_response.text
        tour = tour_response.json()
        tid = tour['tour_id']
        assert len(tour['stops']) == 2 and tour['legs'][1]['reachable']
        from server import core_adapter
        if client.app.state.service.current(bid).core is None or core_adapter.core_function('tour', 'plan_tour') is None:
            assert tour['geometry'] == 'provisional'  # Kit fallback must never imply exact H02 geometry.
        phone = session(client, bid, device='phone')
        admin = session(client, bid, role='admin')
        with client.websocket_connect('/ws/buildings/' + bid) as ws:
            assert ws.receive_json()['type'] == 'hello'
            response = client.patch('/api/sessions/' + phone['session_id'], json={'active_tour_id': tid})
            assert response.status_code == 200, response.text
            handoff = response.json()
            assert handoff['position']['source'] == 'tour_start'
            assert handoff['position']['confidence'] == 'low'
            assert ws.receive_json()['type'] == 'tour_opened'
            stop = tour['stops'][0]
            response = client.post(f'/api/tours/{tid}/progress', json={'stop_id': stop['stop_id'], 'status': 'collected'}, headers={'X-Session-ID': phone['session_id']})
            assert response.status_code == 200, response.text
            assert ws.receive_json()['type'] == 'tour_updated'
            proposal = tool(client, admin['session_id'], 'propose_edit', {'action': 'close', 'target': lift['id']})
            assert proposal['ok'], proposal
            begun = perf_counter()
            event = tool(client, admin['session_id'], 'commit_edit', {'proposal_id': proposal['result']['proposal_id'], 'op_id': 'transport-once'})
            assert event['ok'], event
            changed = ws.receive_json()
            assert changed['type'] == 'building_changed'
            assert client.get(f'/api/buildings/{bid}/events').json()[0]['event_id'] == changed['event']['event_id']
            replan = client.post(f'/api/tours/{tid}/replan', json={'session_id': phone['session_id'], 'from': handoff['position'], 'reason': 'Lift closed'})
            assert replan.status_code == 200, replan.text
            elapsed_ms = (perf_counter() - begun) * 1000
            print(f'commit-broadcast-replan: {elapsed_ms:.1f} ms')
            replanned = replan.json()
            assert replanned['revision'] == 3
            assert replanned['stops'][0]['stop_id'] == stop['stop_id']
            assert replanned['stops'][0]['status'] == 'collected'
            assert ws.receive_json()['type'] == 'tour_updated'
            duplicate = tool(client, admin['session_id'], 'commit_edit', {'proposal_id': proposal['result']['proposal_id'], 'op_id': 'transport-once'})
            assert duplicate['result']['event_id'] == event['result']['event_id']
            assert len(client.get(f'/api/buildings/{bid}/events').json()) == 1
            snapshot = client.get('/api/buildings/' + bid).json()
            assert snapshot['building_version'] == 1 and lift['id'] in snapshot['closed']
            assert client.get('/api/buildings/' + bid + '?version=0').json()['closed'] == []
    with TestClient(create_app(settings)) as restarted:
        assert restarted.get('/api/sessions/' + phone['session_id']).json()['active_tour_id'] == tid
        assert restarted.get('/api/tours/' + tid).json()['stops'][0]['status'] == 'collected'
        assert restarted.get('/api/buildings/' + bid).json()['building_version'] == 1
        undone = tool(restarted, admin['session_id'], 'undo', {})
        assert undone['ok'], undone
        assert restarted.get('/api/buildings/' + bid).json()['closed'] == []


def test_permissions_stale_preview_position_and_voice_fallback(settings, raw, monkeypatch):
    bid = raw['building']['id']
    lift = next(v for v in raw['vertical_connectors'] if v['kind'] == 'lift')
    with TestClient(create_app(settings)) as client:
        nav = session(client, bid, profile='wheelchair')
        admin = session(client, bid, role='admin')
        sid, aid = nav['session_id'], admin['session_id']
        denied = tool(client, sid, 'propose_edit', {'action': 'close', 'target': lift['id']})
        assert not denied['ok'] and denied['error']['code'] == 'forbidden'
        assert client.patch('/api/sessions/' + sid, json={'role': 'admin'}).status_code == 422
        assert client.patch('/api/sessions/' + sid, json={'profile': None}).status_code == 422
        assert client.patch('/api/sessions/' + sid, json={'position': {'space_id': lift['space_ids'][0], 'point': [9999, 9999]}}).status_code == 422
        assert client.patch('/api/sessions/' + sid, json={'position': {'space_id': lift['space_ids'][0]}}).status_code == 200
        first = tool(client, aid, 'propose_edit', {'action': 'close', 'target': lift['id']})
        stale = tool(client, aid, 'propose_edit', {'action': 'close', 'target': lift['id']})
        assert tool(client, aid, 'commit_edit', {'proposal_id': first['result']['proposal_id']})['ok']
        conflict = tool(client, aid, 'commit_edit', {'proposal_id': stale['result']['proposal_id']})
        assert not conflict['ok'] and conflict['error']['code'] == 'version_conflict'
        blocked = tool(client, sid, 'route', {'destination': lift['space_ids'][1]})
        assert not blocked['ok'] and blocked['error']['code'] == 'no_route'
        monkeypatch.delenv('ELEVENLABS_API_KEY', raising=False)
        assert client.get('/api/voice/token').status_code == 503
        monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
        response = client.post('/api/chat', json={'session_id': sid, 'message': 'hello'})
        assert response.status_code == 503 and response.json()['error']['code'] == 'not_available'


def test_markers_sheet_and_demo_reset(settings, raw):
    bid = raw['building']['id']
    with TestClient(create_app(replace(settings, demo_mode=True))) as client:
        admin = session(client, bid, role='admin')
        sid = admin['session_id']
        space = raw['spaces'][0]
        from starter_agent.building_map import outline
        point = outline(space['polygon']).representative_point()
        body = {'markers': [{'space_id': space['id'], 'point': [point.x, point.y], 'heading_deg': 90, 'label': '<script>alert(1)</script>'}]}
        assert client.post(f'/api/buildings/{bid}/markers', json=body).status_code == 403
        response = client.post(f'/api/buildings/{bid}/markers', json=body, headers={'X-Session-ID': sid})
        assert response.status_code == 200, response.text
        marker = response.json()[0]
        assert client.get('/api/markers/' + marker['marker_id']).json() == marker
        updated = client.patch('/api/sessions/' + sid, json={'position': {'space_id': space['id'], 'source': 'marker', 'marker_id': marker['marker_id']}})
        assert updated.json()['position']['confidence'] == 'high'
        sheet = client.get(f'/api/buildings/{bid}/markers/sheet')
        assert sheet.status_code == 200 and 'width:12cm' in sheet.text
        assert '<script>alert' not in sheet.text and '&lt;script&gt;' in sheet.text
        with client.websocket_connect('/ws/buildings/' + bid) as ws:
            assert ws.receive_json()['building_version'] == 0
            reset = client.post('/api/demo/reset', json={'building_id': bid}, headers={'X-Session-ID': sid})
            assert reset.status_code == 200, reset.text
            assert ws.receive_json()['type'] == 'building_reset'
    with TestClient(create_app(settings)) as client:
        assert client.post('/api/demo/reset', json={'building_id': bid}, headers={'X-Session-ID': sid}).status_code == 404


def test_chat_adapter_uses_contract_constructor(settings, raw, monkeypatch):
    class ChatAgent:
        def __init__(self, execution):
            self.execution = execution
        def reply(self, session_id, message):
            assert self.execution.context(session_id)['building_id'] == raw['building']['id']
            assert "search_entities" in {tool["name"] for tool in self.execution.definitions(session_id)}
            return {'reply': 'Ready.', 'tool_calls': [], 'display': {}}
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-only-not-used')
    monkeypatch.setitem(sys.modules, 'agent.chat', SimpleNamespace(ChatAgent=ChatAgent))
    with TestClient(create_app(settings)) as client:
        sid = session(client, raw['building']['id'])['session_id']
        response = client.post('/api/chat', json={'session_id': sid, 'message': 'hello'})
        assert response.status_code == 200, response.text
        assert response.json()['reply'] == 'Ready.'


def test_upload_validates_and_assigns_server_id_without_overwriting_kit(settings, raw, monkeypatch):
    import copy
    seen = []
    def validate(building):
        seen.append(copy.deepcopy(building))
        return {'ok': True, 'errors': [], 'warnings': [], 'stats': {}}
    monkeypatch.setitem(sys.modules, 'core.validate', SimpleNamespace(validate_building=validate))
    with TestClient(create_app(settings)) as client:
        admin = session(client, raw['building']['id'], role='admin')
        response = client.post('/api/buildings', json=raw, headers={'X-Session-ID': admin['session_id']})
        assert response.status_code == 200, response.text
        upload_id = response.json()['building_id']
        assert upload_id.startswith('upl-') and len(upload_id.rsplit('-', 1)[1]) == 6
        assert seen[0]['building']['id'] == upload_id
        snapshot = client.get('/api/buildings/' + upload_id)
        assert snapshot.status_code == 200, snapshot.text
        assert snapshot.json()['building']['spaces'] == raw['spaces']
        assert client.get('/api/buildings/' + raw['building']['id']).json()['building']['building']['id'] == raw['building']['id']
        assert len(client.get('/api/buildings').json()) == 281


def test_marker_semantics_reject_bad_or_foreign_points(settings, raw):
    with TestClient(create_app(settings)) as client:
        sid = session(client, raw['building']['id'], role='admin')['session_id']
        response = client.post('/api/buildings/' + raw['building']['id'] + '/markers',
                               json={'markers': [{'space_id': raw['spaces'][0]['id'], 'point': [9999, 9999], 'heading_deg': 0, 'label': 'outside'}]},
                               headers={'X-Session-ID': sid})
        assert response.status_code == 422
        assert client.get('/api/buildings/unknown/markers/sheet').status_code == 404


@pytest.mark.parametrize('invalid_building', [None, [], 'not an object'])
def test_upload_malformed_building_metadata_returns_validation_error(settings, raw, monkeypatch, invalid_building):
    validator = SimpleNamespace(validate_building=lambda _: {'ok': False, 'errors': ['Building metadata must be an object.'], 'warnings': [], 'stats': {}})
    monkeypatch.setitem(sys.modules, 'core.validate', validator)
    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        sid = session(client, raw['building']['id'], role='admin')['session_id']
        response = client.post('/api/buildings', json={'building': invalid_building}, headers={'X-Session-ID': sid})
        assert response.status_code == 422, response.text
        assert response.json()['error']['code'] == 'invalid_args'
        assert len(client.get('/api/buildings').json()) == 280


def test_ws_commit_during_hello_cannot_leave_client_with_stale_version(settings, raw, monkeypatch):
    import asyncio

    application = create_app(settings)
    bid = raw['building']['id']
    lift = next(connector for connector in raw['vertical_connectors'] if connector['kind'] == 'lift')
    with TestClient(application) as client:
        sid = session(client, bid, role='admin')['session_id']
        preview = tool(client, sid, 'propose_edit', {'action': 'close', 'target': lift['id']})
        proposal_id = preview['result']['proposal_id']
        original_version = application.state.store.version
        inserted = False

        def version_with_concurrent_commit(building_id):
            nonlocal inserted
            version = original_version(building_id)
            if not inserted:
                inserted = True
                application.state.service.commit_edit(sid, proposal_id)
                # Let the queued broadcast run before the worker returns. With a
                # registered socket it waits for hello's send lock; without one
                # the old implementation loses this update entirely.
                asyncio.run_coroutine_threadsafe(asyncio.sleep(0), application.state.hub.loop).result(timeout=2)
            return version

        monkeypatch.setattr(application.state.store, 'version', version_with_concurrent_commit)
        with client.websocket_connect('/ws/buildings/' + bid) as socket:
            greeting = socket.receive_json()
            assert greeting['type'] == 'hello'
            if greeting['building_version'] == 0:
                socket.send_text('ping')
                update = socket.receive_json()
                assert update['type'] == 'building_changed', update
                assert update['building_version'] == 1
            else:
                assert greeting['building_version'] == 1
        assert client.get('/api/buildings/' + bid).json()['building_version'] == 1


def test_openapi_exposes_c2_mobility_handoff_field(settings):
    schema = create_app(settings).openapi()
    properties = schema['components']['schemas']['TourResult']['properties']
    assert properties['mobility_profile']['enum'] == ['walk', 'wheelchair', 'pram', 'trolley']
