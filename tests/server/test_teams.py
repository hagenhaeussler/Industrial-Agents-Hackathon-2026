"""Shared catalog groups and real two-file import, without paid providers."""
import copy
import csv
import io
import json

from fastapi.testclient import TestClient
import pytest

from server.app import create_app
from server.config import REPO_ROOT, Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(state_dir=tmp_path / 'state', hero_dir=tmp_path / 'hero', static_dir=tmp_path / 'dist', admin_token='team-upload-test-code')


@pytest.fixture
def plan():
    return json.loads((REPO_ROOT / 'data/dev/proc-factory-dev-003/building.json').read_text())


def inventory(plan, count=2):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=['asset_id', 'name', 'type', 'space_id', 'x_m', 'y_m'])
    writer.writeheader()
    for asset in plan['assets'][:count]:
        writer.writerow({'asset_id': asset['id'], 'name': asset['name'], 'type': asset['type'], 'space_id': asset['space_id'], 'x_m': asset['position'][0], 'y_m': asset['position'][1]})
    return stream.getvalue()


def submit(client, plan, csv_text=None, team='engineering', code='team-upload-test-code'):
    return client.post(f'/api/teams/{team}/buildings', json={'floor_plan': plan, 'equipment_csv': inventory(plan) if csv_text is None else csv_text}, headers={'X-Admin-Token': code} if code else {})


def test_catalog_is_partitioned_once_and_invalid_team_is_not_an_empty_success(settings):
    with TestClient(create_app(settings)) as client:
        teams = client.get('/api/teams').json()
        assert len(teams) == 5
        all_ids = []
        for team in teams:
            buildings = client.get(f"/api/teams/{team['id']}/buildings").json()
            assert len(buildings) == team['building_count']
            all_ids += [item['id'] for item in buildings]
        assert len(all_ids) == len(set(all_ids)) == len(client.get('/api/buildings').json())
        assert client.get('/api/teams/not-a-team/buildings').status_code == 404


def test_two_file_upload_persists_in_selected_team_and_tools_use_uploaded_inventory(settings, plan):
    original_id = plan['building']['id']
    with TestClient(create_app(settings)) as client:
        response = submit(client, plan)
        assert response.status_code == 200, response.text
        result = response.json(); bid = result['building_id']
        assert bid != original_id and result['team_id'] == 'engineering'
        assert result['validation']['ok'] and result['validation']['stats']['assets'] == 2
        saved = client.get('/api/buildings/' + bid).json()
        assert saved['building']['spaces'] == plan['spaces']
        assert [asset['id'] for asset in saved['building']['assets']] == [asset['id'] for asset in plan['assets'][:2]]
        sid = client.post('/api/sessions', json={'building_id': bid, 'device': 'desk', 'role': 'navigator'}).json()['session_id']
        found = client.post('/api/tools/find', json={'session_id': sid, 'args': {'query': plan['assets'][0]['id']}})
        assert found.status_code == 200 and found.json()['ok']
        start = plan['assets'][0]['space_id']
        assert client.patch('/api/sessions/' + sid, json={'position': {'space_id': start, 'source': 'desk'}}).status_code == 200
        tour = client.post('/api/tours', json={'session_id': sid, 'items': [plan['assets'][1]['id']]})
        assert tour.status_code == 200 and tour.json()['legs'][0]['reachable'], tour.text
        assert client.get('/api/buildings/' + original_id).json()['building']['assets'] == plan['assets']
    with TestClient(create_app(settings)) as restarted:
        members = restarted.get('/api/teams/engineering/buildings').json()
        assert any(item['id'] == bid for item in members)
        assert not any(item['id'] == bid for item in restarted.get('/api/teams/production/buildings').json())


@pytest.mark.parametrize('code', ['', 'wrong'])
def test_import_requires_existing_admin_authority(settings, plan, code):
    with TestClient(create_app(settings)) as client:
        before = len(client.get('/api/buildings').json())
        assert submit(client, plan, code=code).status_code == 403
        assert len(client.get('/api/buildings').json()) == before
        assert not list((settings.state_dir / 'uploads').glob('*.json'))


@pytest.mark.parametrize('change', ['unknown_room', 'duplicate_id', 'nonfinite', 'missing_column', 'out_of_room', 'empty', 'bad_plan'])
def test_bad_files_never_create_partial_buildings(settings, plan, change):
    text = inventory(plan)
    if change == 'unknown_room': text = text.replace(plan['assets'][0]['space_id'], 'not-a-room')
    if change == 'duplicate_id': text = text.replace(plan['assets'][1]['id'], plan['assets'][0]['id'])
    if change == 'nonfinite': text = text.replace(str(plan['assets'][0]['position'][0]), 'nan')
    if change == 'missing_column': text = 'name,type\nPrinter,printer\n'
    if change == 'out_of_room': text = text.replace(str(plan['assets'][0]['position'][0]), '9999999')
    if change == 'empty': text = 'asset_id,name,type,space_id,x_m,y_m\n'
    if change == 'bad_plan': plan = copy.deepcopy(plan); plan['spaces'] = 'not rooms'
    with TestClient(create_app(settings)) as client:
        response = submit(client, plan, text)
        assert response.status_code == 422, response.text
        assert not list((settings.state_dir / 'uploads').glob('*.json'))
        with client.app.state.store.connect() as db:
            assert db.execute('SELECT count(*) FROM building_teams').fetchone()[0] == 0
