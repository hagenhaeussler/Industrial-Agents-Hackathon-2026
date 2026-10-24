"""An explicit stairs choice can replace a tour's retained mobility constraint."""
import json

from fastapi.testclient import TestClient
import pytest

from server.app import create_app
from server.config import REPO_ROOT, Settings
from server.errors import ServiceError


@pytest.fixture(params=['core', 'kit'])
def blocked_tour(tmp_path, monkeypatch, request):
    if request.param == 'kit':
        from server import core_adapter
        monkeypatch.setattr(core_adapter, 'core_function', lambda module, name: None)
    raw = json.loads((REPO_ROOT / 'data/dev/proc-factory-dev-003/building.json').read_text())
    lift = next(item for item in raw['vertical_connectors'] if item['kind'] == 'lift')
    start, destination = lift['space_ids']
    retained = {'step_free': True, 'min_door_width_m': 0.6,
                'closed': [raw['spaces'][0]['id']], 'no_transit_room_types': ['toilet']}
    settings = Settings(state_dir=tmp_path / 'state', hero_dir=tmp_path / 'hero', static_dir=tmp_path / 'dist', admin_token='server-test-admin-code')
    with TestClient(create_app(settings)) as client:
        def session(role, profile='walk'):
            response = client.post('/api/sessions', json={
                'building_id': raw['building']['id'], 'role': role, 'profile': profile},
                headers={'X-Admin-Token': settings.admin_token} if role == 'admin' else {})
            assert response.status_code == 200, response.text
            return response.json()['session_id']

        nav, admin = session('navigator', 'wheelchair'), session('admin')
        response = client.patch('/api/sessions/' + nav, json={
            'position': {'space_id': start}, 'constraints': retained})
        assert response.status_code == 200, response.text
        response = client.post('/api/tours', json={
            'session_id': nav, 'items': [start, destination], 'keep_order': True})
        assert response.status_code == 200, response.text
        tour = response.json()
        assert not tour['unreachable_stops']
        collected_id = tour['order'][0]
        response = client.post(f"/api/tours/{tour['tour_id']}/progress", json={
            'stop_id': collected_id, 'status': 'collected'}, headers={'X-Session-ID': nav})
        assert response.status_code == 200, response.text
        tour = response.json()
        response = client.post('/api/tools/propose_edit', json={
            'session_id': admin, 'args': {'action': 'close', 'target': lift['id']}})
        assert response.status_code == 200 and response.json()['ok'], response.text
        response = client.post('/api/tools/commit_edit', json={
            'session_id': admin, 'args': {'proposal_id': response.json()['result']['proposal_id']}})
        assert response.status_code == 200 and response.json()['ok'], response.text
        yield client, nav, tour, start, collected_id, retained, lift


def replan(client, nav, tour, start, **overrides):
    return client.post(f"/api/tours/{tour['tour_id']}/replan", json={
        'session_id': nav, 'from': {'space_id': start}, **overrides})


def choose_stairs(client, nav):
    response = client.patch('/api/sessions/' + nav, json={
        'profile': 'walk', 'constraints': {'step_free': False}})
    assert response.status_code == 200, response.text


def test_explicit_stairs_override_restores_route_and_retains_other_tour_constraints(blocked_tour):
    client, nav, tour, start, collected_id, retained, lift = blocked_tour
    blocked = replan(client, nav, tour, start)
    assert blocked.status_code == 200, blocked.text
    assert blocked.json()['unreachable_stops']
    choose_stairs(client, nav)
    response = replan(client, nav, tour, start, constraints={'step_free': False})
    assert response.status_code == 200, response.text
    restored = response.json()
    assert restored['constraints'] == {**retained, 'step_free': False}
    assert restored['mobility_profile'] == 'walk'
    assert not restored['unreachable_stops']
    assert restored['order'] == tour['order']
    assert restored['order_policy'] == 'fixed'
    assert {stop['stop_id'] for stop in restored['stops']} == {stop['stop_id'] for stop in tour['stops']}
    assert next(stop for stop in restored['stops'] if stop['stop_id'] == collected_id)['status'] == 'collected'
    assert collected_id not in restored['order']
    assert any(segment['kind'] == 'stairs' for leg in restored['legs'] for segment in leg['segments'])
    stored = client.get('/api/tours/' + tour['tour_id']).json()
    assert stored['constraints'] == restored['constraints']
    assert stored['order'] == restored['order']
    session = client.get('/api/sessions/' + nav).json()
    assert session['profile'] == 'walk' and session['constraints'] == {'step_free': False}
    again = replan(client, nav, tour, start).json()
    assert again['constraints'] == restored['constraints']
    assert again['order'] == restored['order'] and not again['unreachable_stops']


@pytest.mark.parametrize('overrides', [{}, {'constraints': None}, {'constraints': {}}], ids=['missing', 'null', 'empty'])
def test_no_explicit_fields_preserves_tour_safety_after_walk_profile_patch(blocked_tour, overrides):
    client, nav, tour, start, collected_id, retained, lift = blocked_tour
    choose_stairs(client, nav)
    response = replan(client, nav, tour, start, **overrides)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['constraints'] == retained
    assert result['unreachable_stops']
    assert collected_id not in result['order']


@pytest.mark.parametrize('profile', ['wheelchair', 'pram', 'trolley'])
def test_stairs_override_cannot_bypass_session_profile_safety(blocked_tour, profile):
    client, nav, tour, start, collected_id, retained, lift = blocked_tour
    response = client.patch('/api/sessions/' + nav, json={
        'profile': profile, 'constraints': {'step_free': False}})
    assert response.status_code == 200, response.text
    response = replan(client, nav, tour, start, constraints={'step_free': False})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['constraints']['step_free'] is True
    assert result['unreachable_stops']


def test_explicit_empty_closures_cannot_remove_session_closure(blocked_tour):
    client, nav, tour, start, collected_id, retained, lift = blocked_tour
    session_closed = [lift['id']]
    response = client.patch('/api/sessions/' + nav, json={
        'profile': 'walk', 'constraints': {'step_free': False, 'closed': session_closed}})
    assert response.status_code == 200, response.text
    response = replan(client, nav, tour, start, constraints={'step_free': False, 'closed': []})
    assert response.status_code == 200, response.text
    assert response.json()['constraints']['closed'] == session_closed
    assert response.json()['constraints']['min_door_width_m'] == retained['min_door_width_m']
    assert client.get('/api/sessions/' + nav).json()['constraints']['closed'] == session_closed


@pytest.mark.parametrize('invalid', [
    {'min_door_width_m': -0.1}, {'min_door_width_m': 'NaN'}, {'closed': 'all'},
    {'step_free': 'perhaps'}, {'no_transit_room_types': [1]}, {'unknown': True},
])
def test_malformed_override_is_422_without_tour_or_session_mutation(blocked_tour, invalid):
    client, nav, tour, start, *_ = blocked_tour
    before_tour = client.get('/api/tours/' + tour['tour_id']).json()
    before_session = client.get('/api/sessions/' + nav).json()
    response = replan(client, nav, tour, start, constraints=invalid)
    assert response.status_code == 422, response.text
    assert response.json()['error']['code'] == 'invalid_args'
    assert client.get('/api/tours/' + tour['tour_id']).json() == before_tour
    assert client.get('/api/sessions/' + nav).json() == before_session


def test_direct_service_replan_rejects_unknown_constraint_fields(blocked_tour):
    client, nav, tour, start, *_ = blocked_tour
    before = client.get('/api/tours/' + tour['tour_id']).json()
    with pytest.raises(ServiceError) as error:
        client.app.state.service.replan_tour(tour['tour_id'], nav, {'space_id': start}, constraints={'unknown': True})
    assert error.value.code == 'invalid_args'
    assert client.get('/api/tours/' + tour['tour_id']).json() == before
