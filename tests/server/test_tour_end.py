"""HTTP recovery when the optional final destination becomes unreachable."""
import json

from fastapi.testclient import TestClient
import pytest

from server.app import create_app
from server.config import REPO_ROOT, Settings


@pytest.mark.parametrize('adapter_name', ['core', 'kit'])
def test_collected_tour_with_closed_optional_end_is_blocked(tmp_path, monkeypatch, adapter_name):
    if adapter_name == 'kit':
        from server import core_adapter
        monkeypatch.setattr(core_adapter, 'core_function', lambda module, name: None)
    raw = json.loads((REPO_ROOT / 'data/dev/proc-factory-dev-003/building.json').read_text())
    building_id = raw['building']['id']
    start, end = (space['id'] for space in raw['spaces'][:2])
    settings = Settings(state_dir=tmp_path / 'state', hero_dir=tmp_path / 'hero', static_dir=tmp_path / 'dist')
    with TestClient(create_app(settings)) as client:
        def session(role):
            response = client.post('/api/sessions', json={'building_id': building_id, 'role': role})
            assert response.status_code == 200, response.text
            return response.json()['session_id']

        nav, admin = session('navigator'), session('admin')
        response = client.patch('/api/sessions/' + nav, json={'position': {'space_id': start}})
        assert response.status_code == 200, response.text
        response = client.post('/api/tours', json={'session_id': nav, 'items': [start], 'end': end})
        assert response.status_code == 200, response.text
        tour = response.json()
        assert not tour['unreachable_stops']
        assert tour['legs'][-1]['reachable']
        response = client.post(f"/api/tours/{tour['tour_id']}/progress",
                               json={'stop_id': tour['stops'][0]['stop_id'], 'status': 'collected'},
                               headers={'X-Session-ID': nav})
        assert response.status_code == 200, response.text
        collected_id = response.json()['stops'][0]['stop_id']
        response = client.post('/api/tools/propose_edit', json={
            'session_id': admin, 'args': {'action': 'close', 'target': end}})
        assert response.status_code == 200 and response.json()['ok'], response.text
        proposal_id = response.json()['result']['proposal_id']
        response = client.post('/api/tools/commit_edit', json={
            'session_id': admin, 'args': {'proposal_id': proposal_id}})
        assert response.status_code == 200 and response.json()['ok'], response.text
        response = client.post(f"/api/tours/{tour['tour_id']}/replan", json={
            'session_id': nav, 'from': {'space_id': start}, 'reason': 'The final destination closed.'})
        assert response.status_code == 200, response.text
        revised = response.json()
        assert revised['stops'][0]['stop_id'] == collected_id
        assert revised['stops'][0]['status'] == 'collected'
        assert revised['unreachable_stops'][0]['stop_id'] == 'end'
        assert revised['unreachable_stops'][0]['reason'] == 'blocked_by_closure'
        assert revised['status'] == 'blocked'
        assert client.get('/api/tours/' + tour['tour_id']).json()['status'] == 'blocked'
        assert not revised['legs']  # An unreachable final leg is reported, never drawn as a route.
        response = client.post('/api/tools/propose_edit', json={
            'session_id': admin, 'args': {'action': 'open', 'target': end}})
        assert response.status_code == 200 and response.json()['ok'], response.text
        response = client.post('/api/tools/commit_edit', json={
            'session_id': admin, 'args': {'proposal_id': response.json()['result']['proposal_id']}})
        assert response.status_code == 200 and response.json()['ok'], response.text
        response = client.post(f"/api/tours/{tour['tour_id']}/replan", json={
            'session_id': nav, 'from': {'space_id': start}, 'reason': 'The final destination reopened.'})
        assert response.status_code == 200, response.text
        recovered = response.json()
        assert recovered['status'] == 'completed'
        assert recovered['unreachable_stops'] == []
        assert recovered['legs'][-1]['reachable']
        assert recovered['stops'][0]['stop_id'] == collected_id
        assert recovered['stops'][0]['status'] == 'collected'
