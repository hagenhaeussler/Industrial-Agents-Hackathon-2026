"""HTTP navigation and explicit arrival for an optional final destination (CR-H-4)."""
import json

from fastapi.testclient import TestClient
import pytest

from server.app import create_app
from server.config import REPO_ROOT, Settings


@pytest.fixture(params=['core', 'kit'])
def journey(tmp_path, monkeypatch, request):
    if request.param == 'kit':
        from server import core_adapter
        monkeypatch.setattr(core_adapter, 'core_function', lambda module, name: None)
    raw = json.loads((REPO_ROOT / 'data/dev/proc-factory-dev-003/building.json').read_text())
    start, end = [space['id'] for space in raw['spaces'][:2]]
    settings = Settings(state_dir=tmp_path / 'state', hero_dir=tmp_path / 'hero', static_dir=tmp_path / 'dist', admin_token='server-test-admin-code')
    with TestClient(create_app(settings)) as client:
        def session(role):
            response = client.post('/api/sessions', json={'building_id': raw['building']['id'], 'role': role},
                                   headers={'X-Admin-Token': settings.admin_token} if role == 'admin' else {})
            assert response.status_code == 200, response.text
            return response.json()['session_id']
        nav, admin = session('navigator'), session('admin')
        response = client.patch('/api/sessions/' + nav, json={'position': {'space_id': start}})
        assert response.status_code == 200, response.text
        yield client, nav, admin, start, end, settings


def create(client, nav, start, end):
    response = client.post('/api/tours', json={
        'session_id': nav, 'items': [start], 'end': end, 'keep_order': True})
    assert response.status_code == 200, response.text
    return response.json()


def progress(client, nav, tour, stop_id, status='collected'):
    return client.post(f"/api/tours/{tour['tour_id']}/progress", json={
        'stop_id': stop_id, 'status': status}, headers={'X-Session-ID': nav})


def collect(client, nav, tour):
    response = progress(client, nav, tour, tour['stops'][0]['stop_id'])
    assert response.status_code == 200, response.text
    return response.json()


def next_step(client, nav):
    response = client.post('/api/tools/next_step', json={'session_id': nav, 'args': {}})
    assert response.status_code == 200, response.text
    return response.json()


def test_final_leg_remains_active_through_instructions_until_explicit_arrival(journey):
    client, nav, admin, start, end, settings = journey
    tour = collect(client, nav, create(client, nav, start, end))
    assert tour['status'] == 'active'
    assert tour['order'] == [] and tour['length_m'] == pytest.approx(17.1)
    assert len(tour['legs']) == 1 and tour['legs'][0]['reachable']
    original_stops = tour['stops']
    original_position = client.get('/api/sessions/' + nav).json()['position']
    for maneuver in tour['legs'][0]['maneuvers']:
        response = next_step(client, nav)
        assert response['ok'], response
        instruction = response['result']
        assert instruction['text'] == maneuver['text']
        assert instruction['stop_id'] == 'end' and instruction['complete'] is False
        assert client.get('/api/tours/' + tour['tour_id']).json()['status'] == 'active'
    confirmation = next_step(client, nav)
    assert confirmation['ok'] and confirmation['result']['at_end'] is True
    assert confirmation['result']['stop_id'] == 'end' and confirmation['result']['complete'] is False
    assert client.get('/api/sessions/' + nav).json()['position'] == original_position
    response = progress(client, nav, tour, 'end')
    assert response.status_code == 200, response.text
    arrived = response.json()
    assert arrived['status'] == 'completed' and arrived['length_m'] == 0
    assert arrived['order'] == [] and arrived['stops'] == original_stops
    assert arrived['end']['space_id'] == end
    position = client.get('/api/sessions/' + nav).json()['position']
    assert position['space_id'] == end and position['point'] == arrived['end']['point']
    assert next_step(client, nav)['result']['complete'] is True
    duplicate = progress(client, nav, tour, 'end')
    assert duplicate.status_code == 200 and duplicate.json() == arrived


def test_end_confirmation_requires_finished_collection_and_existing_destination(journey):
    client, nav, admin, start, end, settings = journey
    tour = create(client, nav, start, end)
    before_session = client.get('/api/sessions/' + nav).json()
    response = progress(client, nav, tour, 'end')
    assert response.status_code == 400 and response.json()['error']['code'] == 'invalid_args'
    assert client.get('/api/tours/' + tour['tour_id']).json() == tour
    assert client.get('/api/sessions/' + nav).json() == before_session
    tour = collect(client, nav, tour)
    response = progress(client, nav, tour, 'end', status='pending')
    assert response.status_code == 400 and response.json()['error']['code'] == 'invalid_args'
    without_end = collect(client, nav, create(client, nav, start, None))
    response = progress(client, nav, without_end, 'end')
    assert response.status_code == 400 and response.json()['error']['code'] == 'invalid_args'


def test_closed_end_cannot_be_confirmed_and_reopening_resumes_final_navigation(journey):
    client, nav, admin, start, end, settings = journey
    tour = collect(client, nav, create(client, nav, start, end))

    def edit(action):
        response = client.post('/api/tools/propose_edit', json={
            'session_id': admin, 'args': {'action': action, 'target': end}})
        assert response.status_code == 200 and response.json()['ok'], response.text
        response = client.post('/api/tools/commit_edit', json={
            'session_id': admin, 'args': {'proposal_id': response.json()['result']['proposal_id']}})
        assert response.status_code == 200 and response.json()['ok'], response.text

    def replan():
        response = client.post(f"/api/tours/{tour['tour_id']}/replan", json={
            'session_id': nav, 'from': {'space_id': start}})
        assert response.status_code == 200, response.text
        return response.json()

    edit('close')
    # Confirmation checks the live building even before a client has replanned.
    before_tour = client.get('/api/tours/' + tour['tour_id']).json()
    before_session = client.get('/api/sessions/' + nav).json()
    response = progress(client, nav, tour, 'end')
    assert response.status_code == 400 and response.json()['error']['code'] == 'no_route'
    assert response.json()['error']['reason'] == 'blocked_by_closure'
    assert client.get('/api/tours/' + tour['tour_id']).json() == before_tour
    assert client.get('/api/sessions/' + nav).json() == before_session
    blocked = replan()
    assert blocked['status'] == 'blocked' and blocked['unreachable_stops'][0]['stop_id'] == 'end'
    instruction = next_step(client, nav)
    assert not instruction['ok'] and instruction['error']['code'] == 'no_route'
    assert instruction['error']['reason'] == 'blocked_by_closure'
    edit('open')
    restored = replan()
    assert restored['status'] == 'active' and restored['stops'] == tour['stops']
    assert next_step(client, nav)['result']['complete'] is False
    assert progress(client, nav, tour, 'end').json()['status'] == 'completed'


def test_restart_retains_final_leg_instruction_progress_without_implied_arrival(journey):
    client, nav, admin, start, end, settings = journey
    tour = collect(client, nav, create(client, nav, start, end))
    assert next_step(client, nav)['result'].get('complete') is False
    before = client.get('/api/tours/' + tour['tour_id']).json()
    assert before['navigation_index'] == 1
    with TestClient(create_app(settings)) as restarted:
        assert restarted.get('/api/tours/' + tour['tour_id']).json() == before
        response = next_step(restarted, nav)
        assert response['ok'] and response['result']['complete'] is False
        assert response['result']['text'] == before['legs'][0]['maneuvers'][1]['text']
        assert restarted.get('/api/tours/' + tour['tour_id']).json()['status'] == 'active'
        assert progress(restarted, nav, tour, 'end').json()['status'] == 'completed'


def test_confirmed_session_position_and_replan_can_complete_at_exact_end(journey):
    client, nav, admin, start, end, settings = journey
    tour = collect(client, nav, create(client, nav, start, end))
    response = client.patch('/api/sessions/' + nav, json={'position': {**tour['end'], 'source': 'manual'}})
    assert response.status_code == 200, response.text
    response = client.post(f"/api/tours/{tour['tour_id']}/replan", json={
        'session_id': nav, 'from': response.json()['position']})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['status'] == 'completed' and result['length_m'] == 0
    assert result['stops'] == tour['stops'] and result['order'] == []
    assert next_step(client, nav)['result']['complete'] is True


def test_final_arrival_records_explicit_destination_point_without_creating_a_stop(journey):
    client, nav, admin, start, end, settings = journey
    anchor = create(client, nav, start, end)['end']['point']
    destination = {'space_id': end, 'point': [anchor[0] + 0.25, anchor[1]]}
    tour = collect(client, nav, create(client, nav, start, destination))
    assert tour['status'] == 'active' and tour['end']['point'] == destination['point']
    response = progress(client, nav, tour, 'end')
    assert response.status_code == 200, response.text
    arrived = response.json()
    assert arrived['status'] == 'completed' and arrived['start']['point'] == destination['point']
    assert arrived['end']['point'] == destination['point'] and arrived['stops'] == tour['stops']
    assert arrived['order'] == [] and all(stop['stop_id'] != 'end' for stop in arrived['stops'])
    assert client.get('/api/sessions/' + nav).json()['position']['point'] == destination['point']


def test_next_step_refreshes_stale_tour_from_latest_confirmed_position(journey):
    client, nav, admin, start, end, settings = journey
    tour = collect(client, nav, create(client, nav, start, end))
    assert next_step(client, nav)['result']['complete'] is False
    current = client.get('/api/sessions/' + nav).json()['position']
    confirmed = {**current, 'point': [current['point'][0] + 0.25, current['point'][1]], 'source': 'manual'}
    assert client.patch('/api/sessions/' + nav, json={'position': confirmed}).status_code == 200

    def edit(action):
        preview = client.post('/api/tools/propose_edit', json={
            'session_id': admin, 'args': {'action': action, 'target': end}}).json()
        assert preview['ok'], preview
        commit = client.post('/api/tools/commit_edit', json={
            'session_id': admin, 'args': {'proposal_id': preview['result']['proposal_id']}}).json()
        assert commit['ok'], commit

    edit('close')
    blocked = next_step(client, nav)  # No client replan between commit and next_step.
    assert not blocked['ok'] and blocked['error']['code'] == 'no_route'
    assert blocked['error']['reason'] == 'blocked_by_closure'
    stored = client.get('/api/tours/' + tour['tour_id']).json()
    assert stored['building_version'] == blocked['building_version'] == 1
    assert stored['status'] == 'blocked' and stored['start']['point'] == confirmed['point']
    assert stored['stops'] == tour['stops']
    edit('open')
    restored = next_step(client, nav)
    assert restored['ok'] and restored['result']['complete'] is False
    assert restored['result']['kind'] == 'depart' and restored['result']['at'] == confirmed['point']
    stored = client.get('/api/tours/' + tour['tour_id']).json()
    assert stored['building_version'] == restored['building_version'] == 2
    assert stored['status'] == 'active' and stored['stops'] == tour['stops']
    assert stored['navigation_index'] == 1
    assert next_step(client, nav)['ok']
    assert client.get('/api/tours/' + tour['tour_id']).json()['navigation_index'] == 2


@pytest.mark.parametrize('offset', [0, 0.25], ids=['identical', 'distinct'])
def test_same_room_final_leg_retains_actual_point_distance_until_arrival(journey, offset):
    client, nav, admin, start, end, settings = journey
    origin = client.get('/api/sessions/' + nav).json()['position']['point']
    destination = {'space_id': start, 'point': [origin[0] + offset, origin[1]]}
    tour = collect(client, nav, create(client, nav, start, destination))
    assert tour['length_m'] == pytest.approx(offset)
    assert tour['status'] == ('active' if offset else 'completed')
    assert tour['order'] == [] and tour['stops'][0]['status'] == 'collected'
    if offset:
        leg = tour['legs'][0]
        assert leg['start_position'] == origin and leg['destination_position'] == destination['point']
        assert leg['segments'][0]['points'] == [origin, destination['point']]
        if tour.get('_adapter') == 'kit':
            assert leg['geometry'] == 'provisional' and leg['segments'][0]['geometry'] == 'provisional'
        assert leg['maneuvers'][0]['at'] == origin
        assert leg['maneuvers'][-1]['at'] == destination['point']
        assert next_step(client, nav)['result']['complete'] is False
        arrived = progress(client, nav, tour, 'end')
        assert arrived.status_code == 200, arrived.text
        assert arrived.json()['status'] == 'completed' and arrived.json()['length_m'] == 0
        assert client.get('/api/sessions/' + nav).json()['position']['point'] == destination['point']
    else:
        assert next_step(client, nav)['result']['complete'] is True


def test_identical_same_room_end_never_bypasses_current_room_closure(journey):
    client, nav, admin, start, end, settings = journey
    origin = client.get('/api/sessions/' + nav).json()['position']['point']
    preview = client.post('/api/tools/propose_edit', json={
        'session_id': admin, 'args': {'action': 'close', 'target': start}}).json()
    assert preview['ok'], preview
    commit = client.post('/api/tools/commit_edit', json={
        'session_id': admin, 'args': {'proposal_id': preview['result']['proposal_id']}}).json()
    assert commit['ok'], commit
    tour = create(client, nav, start, {'space_id': start, 'point': origin})
    assert tour['status'] == 'blocked'
    assert any(item['stop_id'] == 'end' and item['reason'] == 'blocked_by_closure'
               for item in tour['unreachable_stops'])


def test_next_step_refreshes_profile_safety_without_another_building_event(journey):
    client, nav, admin, start, end, settings = journey
    bid = client.get('/api/sessions/' + nav).json()['building_id']
    raw = client.get('/api/buildings/' + bid).json()['building']
    lift = next(item for item in raw['vertical_connectors'] if item['kind'] == 'lift')
    start, end = lift['space_ids']
    assert client.patch('/api/sessions/' + nav, json={'position': {'space_id': start}}).status_code == 200
    preview = client.post('/api/tools/propose_edit', json={
        'session_id': admin, 'args': {'action': 'close', 'target': lift['id']}}).json()
    assert preview['ok'], preview
    commit = client.post('/api/tools/commit_edit', json={
        'session_id': admin, 'args': {'proposal_id': preview['result']['proposal_id']}}).json()
    assert commit['ok'], commit
    tour = collect(client, nav, create(client, nav, start, end))
    assert tour['building_version'] == 1 and tour['constraints']['step_free'] is False
    assert any(segment['kind'] == 'stairs' for segment in tour['legs'][0]['segments'])
    assert client.patch('/api/sessions/' + nav, json={'profile': 'wheelchair'}).status_code == 200
    response = next_step(client, nav)
    assert not response['ok'] and response['error']['code'] == 'no_route'
    stored = client.get('/api/tours/' + tour['tour_id']).json()
    assert stored['building_version'] == 1 and stored['constraints']['step_free'] is True
    assert stored['status'] == 'blocked' and stored['stops'] == tour['stops']
