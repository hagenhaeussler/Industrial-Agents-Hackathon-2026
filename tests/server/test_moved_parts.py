"""HTTP regressions for asset moves during a durable collection tour (CR-H-2)."""
from collections import defaultdict
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
    grouped = defaultdict(list)
    for asset in raw['assets']:
        grouped[asset['space_id']].append(asset['id'])
    source = next(sid for sid, assets in grouped.items() if len(assets) >= 2)
    other_rooms = [sid for sid in grouped if sid != source]
    assets = grouped[source][:2]
    collector_room, destination = other_rooms[:2]
    collector = grouped[collector_room][0]
    # Trusted in-process fixture; admin authentication is covered separately.
    settings = Settings(state_dir=tmp_path / 'state', hero_dir=tmp_path / 'hero', static_dir=tmp_path / 'dist', admin_requires_code=False)
    with TestClient(create_app(settings)) as client:
        def session(role):
            response = client.post('/api/sessions', json={'building_id': raw['building']['id'], 'role': role})
            assert response.status_code == 200, response.text
            return response.json()['session_id']
        nav, admin = session('navigator'), session('admin')
        response = client.patch('/api/sessions/' + nav, json={'position': {'space_id': source, 'source': 'desk'}})
        assert response.status_code == 200, response.text
        yield client, nav, admin, source, assets, collector_room, collector, destination


def tool(client, session_id, name, args):
    response = client.post('/api/tools/' + name, json={'session_id': session_id, 'args': args})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['ok'], body
    return body['result']


def move(client, admin, asset_id, destination):
    preview = tool(client, admin, 'propose_edit', {'action': 'move_asset', 'target': asset_id, 'second_target': destination})
    return tool(client, admin, 'commit_edit', {'proposal_id': preview['proposal_id']})


def create(client, nav, items):
    response = client.post('/api/tours', json={'session_id': nav, 'items': items, 'keep_order': True})
    assert response.status_code == 200, response.text
    return response.json()


def progress(client, nav, tour_id, stop_id):
    response = client.post(f'/api/tours/{tour_id}/progress', json={'stop_id': stop_id, 'status': 'collected'}, headers={'X-Session-ID': nav})
    assert response.status_code == 200, response.text
    return response.json()


def replan(client, nav, tour_id, source):
    response = client.post(f'/api/tours/{tour_id}/replan', json={'session_id': nav, 'from': {'space_id': source, 'source': 'manual'}, 'reason': 'A pending part moved.'})
    assert response.status_code == 200, response.text
    return response.json()


def test_replan_splits_a_moved_group_and_preserves_collected_identity(journey):
    client, nav, admin, source, assets, collector_room, collector, destination = journey
    tour = create(client, nav, [*assets, collector])
    old_pending = next(stop for stop in tour['stops'] if assets[0] in stop['asset_ids'])
    old_collected = next(stop for stop in tour['stops'] if collector in stop['asset_ids'])
    progress(client, nav, tour['tour_id'], old_collected['stop_id'])
    move(client, admin, assets[0], destination)
    revised = replan(client, nav, tour['tour_id'], collector_room)
    by_asset = {asset: stop for stop in revised['stops'] for asset in stop['asset_ids']}
    assert by_asset[collector]['status'] == 'collected'
    assert by_asset[collector]['stop_id'] == old_collected['stop_id']
    assert by_asset[collector]['space_id'] == collector_room
    assert by_asset[assets[0]]['space_id'] == destination
    assert by_asset[assets[0]]['stop_id'] == old_pending['stop_id']
    assert by_asset[assets[1]]['space_id'] == source
    assert by_asset[assets[1]]['stop_id'] != old_pending['stop_id']
    assert len({stop['stop_id'] for stop in revised['stops']}) == 3
    assert old_collected['stop_id'] not in revised['order']
    assert all(stop.get('target', stop['space_id']) == stop['space_id'] for stop in revised['stops'])
    assert client.get('/api/tours/' + tour['tour_id']).json()['stops'] == revised['stops']
    # A repeated replan keeps the newly allocated split identity as well.
    again = replan(client, nav, tour['tour_id'], collector_room)
    assert {stop['stop_id'] for stop in again['stops']} == {stop['stop_id'] for stop in revised['stops']}


def test_progress_retargets_other_pending_parts_after_a_move(journey):
    client, nav, admin, source, assets, collector_room, collector, destination = journey
    tour = create(client, nav, [assets[0], collector])
    moved_stop = next(stop for stop in tour['stops'] if assets[0] in stop['asset_ids'])
    collecting_stop = next(stop for stop in tour['stops'] if collector in stop['asset_ids'])
    move(client, admin, assets[0], destination)
    revised = progress(client, nav, tour['tour_id'], collecting_stop['stop_id'])
    pending = next(stop for stop in revised['stops'] if assets[0] in stop['asset_ids'])
    assert pending['status'] == 'pending'
    assert pending['space_id'] == destination
    assert pending['stop_id'] == moved_stop['stop_id']
    assert collecting_stop['stop_id'] not in revised['order']
    assert revised['revision'] == tour['revision'] + 1


def test_distinct_stop_ids_survive_two_parts_converging_in_one_room(journey):
    client, nav, admin, source, assets, collector_room, collector, destination = journey
    tour = create(client, nav, [assets[0], collector])
    original_ids = {stop['stop_id'] for stop in tour['stops']}
    move(client, admin, assets[0], collector_room)
    revised = replan(client, nav, tour['tour_id'], source)
    assert len(revised['stops']) == 2
    assert {stop['space_id'] for stop in revised['stops']} == {collector_room}
    assert {stop['stop_id'] for stop in revised['stops']} == original_ids
    assert len(revised['order']) == 2 and len(set(revised['order'])) == 2


def test_moved_unreachable_stop_remains_listed(journey):
    client, nav, admin, source, assets, collector_room, collector, destination = journey
    tour = create(client, nav, [assets[0]])
    stop_id = tour['stops'][0]['stop_id']
    move(client, admin, assets[0], destination)
    preview = tool(client, admin, 'propose_edit', {'action': 'close', 'target': destination})
    tool(client, admin, 'commit_edit', {'proposal_id': preview['proposal_id']})
    revised = replan(client, nav, tour['tour_id'], source)
    assert revised['stops'][0]['stop_id'] == stop_id
    assert revised['stops'][0]['space_id'] == destination
    assert revised['stops'][0]['status'] == 'pending'
    assert revised['unreachable_stops'][0]['stop_id'] == stop_id
    assert stop_id not in revised['order']
