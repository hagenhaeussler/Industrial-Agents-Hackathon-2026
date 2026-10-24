"""A temporarily blocked stop must return to its prescribed collection position."""
import json

from fastapi.testclient import TestClient
import pytest

from server.app import create_app
from server.config import REPO_ROOT, Settings


@pytest.mark.parametrize('adapter_name', ['core', 'kit'])
@pytest.mark.parametrize('blocked_index', [0, 1], ids=['first-pending', 'middle-pending'])
def test_fixed_order_returns_after_reopening_a_stop(tmp_path, monkeypatch, adapter_name, blocked_index):
    if adapter_name == 'kit':
        from server import core_adapter
        monkeypatch.setattr(core_adapter, 'core_function', lambda module, name: None)
    raw = json.loads((REPO_ROOT / 'data/dev/proc-factory-dev-003/building.json').read_text())
    room_ids = [space['id'] for space in raw['spaces'][:4]]
    start = room_ids[0]
    settings = Settings(state_dir=tmp_path / 'state', hero_dir=tmp_path / 'hero', static_dir=tmp_path / 'dist', admin_token='server-test-admin-code')
    with TestClient(create_app(settings)) as client:
        def session(role):
            response = client.post('/api/sessions', json={'building_id': raw['building']['id'], 'role': role},
                                   headers={'X-Admin-Token': settings.admin_token} if role == 'admin' else {})
            assert response.status_code == 200, response.text
            return response.json()['session_id']

        def edit(action, target):
            response = client.post('/api/tools/propose_edit', json={
                'session_id': admin, 'args': {'action': action, 'target': target}})
            assert response.status_code == 200 and response.json()['ok'], response.text
            response = client.post('/api/tools/commit_edit', json={
                'session_id': admin, 'args': {'proposal_id': response.json()['result']['proposal_id']}})
            assert response.status_code == 200 and response.json()['ok'], response.text

        def replan(tour_id):
            response = client.post(f'/api/tours/{tour_id}/replan', json={
                'session_id': nav, 'from': {'space_id': start}, 'reason': 'A collection room changed.'})
            assert response.status_code == 200, response.text
            return response.json()

        nav, admin = session('navigator'), session('admin')
        response = client.patch('/api/sessions/' + nav, json={'position': {'space_id': start}})
        assert response.status_code == 200, response.text
        response = client.post('/api/tours', json={
            'session_id': nav, 'items': room_ids, 'keep_order': True})
        assert response.status_code == 200, response.text
        tour = response.json()
        collected_id = tour['order'][0]
        response = client.post(f"/api/tours/{tour['tour_id']}/progress", json={
            'stop_id': collected_id, 'status': 'collected'}, headers={'X-Session-ID': nav})
        assert response.status_code == 200, response.text
        prescribed = response.json()['order']
        assert len(prescribed) == 3
        blocked_id = prescribed[blocked_index]
        blocked_room = next(stop['space_id'] for stop in tour['stops'] if stop['stop_id'] == blocked_id)
        edit('close', blocked_room)
        blocked = replan(tour['tour_id'])
        assert blocked['order'] == [stop_id for stop_id in prescribed if stop_id != blocked_id]
        assert next(stop for stop in blocked['stops'] if stop['stop_id'] == blocked_id)['status'] == 'pending'
        assert any(stop['stop_id'] == blocked_id for stop in blocked['unreachable_stops'])
        edit('open', blocked_room)
        restored = replan(tour['tour_id'])
        assert restored['order_policy'] == 'fixed'
        assert restored['order'] == prescribed
        assert restored['unreachable_stops'] == []
        assert next(stop for stop in restored['stops'] if stop['stop_id'] == collected_id)['status'] == 'collected'
        assert collected_id not in restored['order']
        assert client.get('/api/tours/' + tour['tour_id']).json()['order'] == prescribed
