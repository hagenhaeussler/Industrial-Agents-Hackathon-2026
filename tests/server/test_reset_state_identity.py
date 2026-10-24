"""A reset must not let a reused version number authenticate old directions."""

from fastapi.testclient import TestClient
import pytest

from server.app import create_app
from server.config import Settings


class Journey:
    def __init__(self, settings):
        self.settings = settings
        self.client = None
        self.restart()
        self.bid = 'proc-factory-dev-003'
        raw = self.get('/api/buildings/' + self.bid)['building']
        self.lift = next(value['id'] for value in raw['vertical_connectors'] if value['kind'] == 'lift')
        self.stairs = next(value['id'] for value in raw['vertical_connectors'] if value['kind'] == 'stairs')
        self.printer = next(value for value in raw['assets'] if value['id'].endswith('A00021'))
        self.cnc = next(value for value in raw['assets'] if value['name'] == 'CNC mill H-A1-A')
        self.ups = next(value for value in raw['assets'] if value['id'].endswith('A00325'))
        self.nav = self.post('/api/sessions', {'building_id': self.bid, 'profile': 'wheelchair'})['session_id']
        self.admin = self.post('/api/sessions', {'building_id': self.bid, 'role': 'admin'},
                               {'X-Admin-Token': settings.admin_token})['session_id']
        self.call('PATCH', '/api/sessions/' + self.nav, {
            'position': {'space_id': self.printer['space_id']},
            'constraints': {'min_door_width_m': 0.6, 'no_transit_room_types': ['toilet']},
        })

    def restart(self):
        self.close()
        self.client = TestClient(create_app(self.settings))
        self.client.__enter__()

    def close(self):
        if self.client is not None:
            self.client.__exit__(None, None, None)
            self.client = None

    def call(self, method, path, body=None, headers=None):
        response = self.client.request(method, path, json=body, headers=headers)
        assert response.status_code == 200, (path, response.status_code, response.text)
        return response.json()

    def get(self, path):
        return self.call('GET', path)

    def post(self, path, body, headers=None):
        return self.call('POST', path, body, headers)

    def tool(self, name, args, *, admin=False):
        return self.post('/api/tools/' + name, {'session_id': self.admin if admin else self.nav, 'args': args})

    def snapshot(self):
        return self.get('/api/buildings/' + self.bid)

    def state_id(self, payload):
        value = payload['building_state_id']
        assert isinstance(value, str) and len(value) >= 32
        assert all(secret not in value for secret in (self.nav, self.admin, self.settings.admin_token))
        return value

    def plan(self, destination='pending'):
        items = [self.printer['id'], self.cnc['id']]
        if destination == 'pending':
            items.append(self.ups['id'])
        body = {'session_id': self.nav, 'items': items, 'keep_order': True}
        if destination == 'end':
            body['end'] = self.ups['id']
        tour = self.post('/api/tours', body)
        for stop in tour['stops'][:2]:
            tour = self.post('/api/tours/' + tour['tour_id'] + '/progress',
                             {'stop_id': stop['stop_id'], 'status': 'collected'},
                             {'X-Session-ID': self.nav})
        assert tour['status'] == 'active'
        assert len([stop for stop in tour['stops'] if stop['status'] == 'collected']) == 2
        return tour

    def close_target(self, target):
        proposal = self.tool('propose_edit', {'action': 'close', 'target': target}, admin=True)
        assert proposal['ok'], proposal
        result = self.tool('commit_edit', {'proposal_id': proposal['result']['proposal_id']}, admin=True)
        assert result['ok'], result
        return result['result']

    def replan(self, tour):
        return self.post('/api/tours/' + tour['tour_id'] + '/replan', {
            'session_id': self.nav, 'from': self.get('/api/sessions/' + self.nav)['position'],
        })

    def reset(self):
        result = self.post('/api/demo/reset', {'building_id': self.bid}, {'X-Session-ID': self.admin})
        assert result == {'building_id': self.bid, 'building_version': 0}


@pytest.fixture(params=['core', 'kit'])
def journey(request, monkeypatch, tmp_path):
    if request.param == 'kit':
        from server import core_adapter
        monkeypatch.setattr(core_adapter, 'core_function', lambda module, name: None)
    # Exercise the secure constructor and real token header, including demo reset.
    settings = Settings(state_dir=tmp_path / 'state', hero_dir=tmp_path / 'hero',
                        static_dir=tmp_path / 'dist', demo_mode=True,
                        admin_token='reset-identity-test-admin-code')
    assert settings.allow_unauthenticated_demo_admin is False
    current = Journey(settings)
    try:
        yield current
    finally:
        current.close()


def assert_preserved(before, after):
    assert [(stop['stop_id'], stop['status'], stop['asset_ids']) for stop in after['stops']] == [
        (stop['stop_id'], stop['status'], stop['asset_ids']) for stop in before['stops']]
    assert after['constraints'] == before['constraints']
    assert after['constraints']['step_free'] is True
    assert after['constraints']['min_door_width_m'] == 0.6
    assert after['constraints']['no_transit_room_types'] == ['toilet']
    assert after['order_policy'] == before['order_policy'] == 'fixed'
    assert all(stop['stop_id'] not in after['order'] for stop in after['stops'] if stop['status'] == 'collected')
    assert after.get('end') == before.get('end')


@pytest.mark.parametrize('destination', ['pending', 'end'])
@pytest.mark.parametrize('old_blocked', [True, False], ids=['blocked-to-open', 'open-to-blocked'])
def test_next_step_refreshes_a_different_state_with_the_same_version(journey, destination, old_blocked):
    tour = journey.plan(destination)
    old_edit = journey.close_target(journey.lift if old_blocked else journey.stairs)
    old = journey.replan(tour)
    assert old['status'] == ('blocked' if old_blocked else 'active')
    old_snapshot = journey.snapshot()
    old_id = journey.state_id(old)
    assert old_id == journey.state_id(old_snapshot)
    pending_ids = [stop['stop_id'] for stop in old['stops'] if stop['status'] == 'pending']
    position = journey.get('/api/sessions/' + journey.nav)['position']

    journey.reset()
    new_edit = journey.close_target(journey.stairs if old_blocked else journey.lift)
    current = journey.snapshot()
    assert old_edit['building_version'] == new_edit['building_version'] == current['building_version'] == 1
    assert old_edit['event_id'] == new_edit['event_id']  # Actual reset event-ID reuse.
    assert current['content_hash'] == old_snapshot['content_hash']
    assert current['closed'] != old_snapshot['closed']
    current_id = journey.state_id(current)
    assert current_id != old_id
    path = '/api/tours/' + old['tour_id']
    assert journey.get(path) == old  # No manual client replan after reset/new edit.

    instruction = journey.tool('next_step', {})
    saved = journey.get(path)
    assert saved['building_version'] == instruction['building_version'] == 1
    assert journey.state_id(saved) == current_id
    assert saved['revision'] > old['revision']
    assert saved['start']['space_id'] == position['space_id']
    assert saved['start']['point'] == position['point']
    assert_preserved(old, saved)
    assert saved['status'] != 'completed'
    if old_blocked:
        assert instruction['ok'] and not instruction['result'].get('complete', False), instruction
        assert saved['status'] == 'active' and not saved['unreachable_stops']
        assert saved['order'] == pending_ids
        if destination == 'end':
            assert instruction['result']['stop_id'] == 'end'
            assert saved['order'] == [] and saved['legs'][0]['reachable']
    else:
        assert not instruction['ok'] and instruction['error']['code'] == 'no_route', instruction
        assert saved['status'] == 'blocked' and saved['unreachable_stops']
        assert saved['order'] == []
        assert saved['unreachable_stops'][0]['stop_id'] == ('end' if destination == 'end' else pending_ids[0])


def test_state_identity_is_stable_for_reads_and_app_restart(journey):
    initial = journey.snapshot()
    initial_id = journey.state_id(initial)
    tour = journey.plan()
    assert journey.state_id(tour) == initial_id
    journey.close_target(journey.stairs)
    snapshot = journey.snapshot()
    state_id = journey.state_id(snapshot)
    assert state_id != initial_id
    tour = journey.replan(tour)
    assert journey.state_id(tour) == state_id
    found = journey.tool('find', {'query': journey.cnc['name']})
    assert found['ok'] and found['result']['id'] == journey.cnc['id']
    assert journey.snapshot() == snapshot
    stored = journey.get('/api/tours/' + tour['tour_id'])
    journey.restart()  # New app/service instances rebuild from the same persisted SQLite state.
    assert journey.snapshot() == snapshot
    assert journey.state_id(journey.snapshot()) == state_id
    assert journey.get('/api/tours/' + tour['tour_id']) == stored


def test_legacy_tour_without_state_identity_is_lazily_refreshed_once(journey):
    tour = journey.plan()
    state_id = journey.state_id(journey.snapshot())
    # Simulate a pre-C9 persisted JSON record, without weakening the public schema.
    store = journey.client.app.state.store
    legacy = store.get_tour(tour['tour_id'])
    legacy.pop('building_state_id')
    saved_legacy = store.save_tour(journey.nav, legacy, expected_revision=legacy['revision'])
    path = '/api/tours/' + tour['tour_id']
    assert 'building_state_id' not in journey.get(path)
    assert journey.tool('next_step', {})['ok']
    refreshed = journey.get(path)
    assert journey.state_id(refreshed) == state_id
    assert_preserved(tour, refreshed)
    assert refreshed['building_version'] == saved_legacy['building_version'] == 0
    assert refreshed['revision'] > saved_legacy['revision']
    assert refreshed['navigation_index'] == 1
    assert journey.tool('next_step', {})['ok']
    second = journey.get(path)
    assert journey.state_id(second) == state_id
    assert second['navigation_index'] == 2
    # Advancing the next instruction saves once; a redundant replan would save again/reset its index.
    assert second['revision'] == refreshed['revision'] + 1
    assert_preserved(refreshed, second)
