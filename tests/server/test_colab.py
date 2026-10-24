"""Real HTTP contracts: shared demo state, collector admission and truthful fixes."""
from copy import deepcopy
from datetime import datetime, timezone
import json

from fastapi.testclient import TestClient
import pytest
from shapely.geometry import Point
from starter_agent.building_map import outline

from server.app import create_app
from server.config import REPO_ROOT, Settings


@pytest.fixture
def colab(tmp_path):
    raw = json.loads((REPO_ROOT / 'data/dev/proc-factory-dev-003/building.json').read_text())
    raw['building']['id'] = 'colab-contract-fixture'
    for index, floor in enumerate(raw['floors']):
        floor['level'] = index + 3
    # A known generous room gives the furniture animation a valid short move.
    room = max(raw['spaces'], key=lambda r: outline(r['polygon']).area)
    point = outline(room['polygon']).representative_point()
    raw['assets'].insert(0, {'id': 'demo-coffee', 'name': 'Demo coffee machine',
        'category': 'equipment', 'type': 'coffee_machine', 'space_id': room['id'],
        'floor_id': room['floor_id'], 'position': [point.x, point.y], 'source': 'generated',
        'footprint': {'width_m': .6, 'depth_m': .6, 'rotation_deg': 0}})
    model_dir = tmp_path / 'colab'
    model_dir.mkdir()
    (model_dir / 'building.json').write_text(json.dumps(raw))
    (model_dir / 'metadata.json').write_text(json.dumps({'description': 'Synthetic HTTP fixture',
        'walk_path': [{'floor_id': room['floor_id'], 'space_id': room['id'], 'x': point.x, 'y': point.y},
                      {'floor_id': room['floor_id'], 'space_id': room['id'], 'x': point.x + .5, 'y': point.y}]}))
    settings = Settings(state_dir=tmp_path / 'state', hero_dir=tmp_path / 'hero',
                        colab_dir=model_dir, admin_token='test-admin-code')
    application = create_app(settings)
    clock = [1_792_881_000.0]
    application.state.colab.clock = lambda: clock[0]
    with TestClient(application) as client:
        yield client, application.state.colab, clock, raw, settings


def refs(raw):
    rooms = sorted(raw['spaces'], key=lambda r: outline(r['polygon']).area, reverse=True)[:2]
    points = []
    for index, room in enumerate(rooms):
        point = outline(room['polygon']).representative_point()
        points.append({'id': f'reference-{index}', 'floor_id': room['floor_id'],
            'space_id': room['id'], 'point': [point.x, point.y], 'synthetic': False,
            'readings': [{'bssid': f'10:20:30:40:50:0{i}', 'rssi_dbm': n + index * 25}
                         for i, n in enumerate((-75, -65, -55), 1)]})
    return {'schema_version': 1, 'building_id': raw['building']['id'],
            'synthetic': False, 'fingerprints': points}


def scan(clock, readings):
    return {'observed_at': datetime.fromtimestamp(clock[0], timezone.utc).isoformat(),
            'readings': deepcopy(readings), 'synthetic': False}


def pairing(client, device='android-test'):
    response = client.post('/api/colab/pair', json={'device_id': device},
                           headers={'X-Admin-Token': 'test-admin-code'})
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    return {'X-Colab-Token': response.json()['token']}


def test_model_appears_in_regular_catalog_and_metadata_stays_sidecar(colab):
    client, runtime, clock, raw, settings = colab
    model = client.get('/api/colab/model').json()
    assert model['building'] == raw
    assert model['metadata']['description'] == 'Synthetic HTTP fixture'
    assert client.get('/api/buildings/' + raw['building']['id']).status_code == 200
    listed = client.get('/api/buildings').json()
    assert sum(b['id'] == raw['building']['id'] for b in listed) == 1


def test_browsers_share_occasional_valid_asset_motion_and_no_fake_location(colab):
    client, runtime, clock, raw, settings = colab
    before = client.get('/api/colab/state').json()
    assert before['positions'] == []
    assert before['movements'] == []
    clock[0] += 36
    first = client.get('/api/colab/state').json()
    second = client.get('/api/colab/state').json()
    assert first == second
    assert len(first['movements']) == 1
    move = first['movements'][0]
    asset = next(a for a in raw['assets'] if a['id'] == move['asset_id'])
    room = next(r for r in raw['spaces'] if r['id'] == asset['space_id'])
    assert outline(room['polygon']).covers(Point(move['to']))
    clock[0] += 8
    after = client.get('/api/colab/state').json()
    assert after['movements'] == []
    assert next(a for a in after['assets'] if a['asset_id'] == move['asset_id'])['position'] == move['to']
    assert client.get('/api/buildings/' + raw['building']['id']).json()['building_version'] == 0
    # Core geometry and kit data are unaffected by this visual-only overlay.
    assert client.get('/api/colab/model').json()['building'] == raw


def test_demo_pause_and_walk_are_explicit_shared_simulations(colab):
    client, runtime, clock, raw, settings = colab
    assert client.post('/api/colab/demo', json={'running': False}).json()['demo_running'] is False
    clock[0] += 150
    assert client.get('/api/colab/state').json()['movements'] == []
    walking = client.post('/api/colab/demo/walk', json={'running': True}).json()
    assert walking['positions'][0]['source'] == 'simulated'
    stopped = client.post('/api/colab/demo/walk', json={'running': False}).json()
    assert stopped['positions'] == []


def test_manual_position_is_validated_and_cannot_claim_wifi(colab):
    client, runtime, clock, raw, settings = colab
    ref = refs(raw)['fingerprints'][0]
    body = {'device_id': 'manual-test', 'label': 'Manually confirmed visitor',
            'floor_id': ref['floor_id'], 'x': ref['point'][0], 'y': ref['point'][1], 'source': 'manual'}
    assert client.post('/api/colab/positions', json=body).json()['source'] == 'manual'
    assert client.post('/api/colab/positions', json={**body, 'source': 'wifi_fingerprint'}).status_code == 422
    assert client.post('/api/colab/positions', json={**body, 'x': 1e8}).status_code == 422
    clock[0] += 121
    assert client.get('/api/colab/state').json()['positions'][0]['stale'] is True


def test_wifi_requires_admin_pairing_and_token_bound_to_device(colab):
    client, runtime, clock, raw, settings = colab
    assert client.post('/api/colab/pair', json={}).status_code == 403
    headers = pairing(client)
    body = {'device_id': 'android-test', 'scan': scan(clock, refs(raw)['fingerprints'][0]['readings'])}
    assert client.post('/api/colab/wifi/scans', json=body).status_code == 403
    assert client.post('/api/colab/wifi/scans', json={**body, 'device_id': 'different-device'}, headers=headers).status_code == 403
    result = client.post('/api/colab/wifi/scans', json=body, headers=headers).json()
    assert result['status'] == 'insufficient_data'
    assert result['reason'] == 'calibration_missing'
    assert client.get('/api/colab/state').json()['positions'] == []


def test_real_fingerprint_admission_staleness_and_no_radio_data_in_public_state(colab):
    client, runtime, clock, raw, settings = colab
    calibration = refs(raw)
    assert client.post('/api/colab/wifi/calibration', json=calibration).status_code == 403
    saved = client.post('/api/colab/wifi/calibration', json=calibration,
                        headers={'X-Admin-Token': 'test-admin-code'})
    assert saved.json()['ready'] is True
    body = {'device_id': 'android-test', 'label': 'Survey Android',
            'scan': scan(clock, calibration['fingerprints'][0]['readings'])}
    headers = pairing(client)
    result = client.post('/api/colab/wifi/scans', json=body, headers=headers).json()
    assert result['status'] == 'estimated'
    state = client.get('/api/colab/state').json()
    assert state['positions'][0]['source'] == 'wifi_fingerprint'
    assert state['positions'][0]['confidence'] == 'low'
    assert 'bssid' not in json.dumps(state)
    assert 'test-admin-code' not in json.dumps(state)
    clock[0] += 21
    assert client.get('/api/colab/state').json()['positions'][0]['stale'] is True
    assert client.post('/api/colab/wifi/scans', json=body, headers=headers).json()['status'] == 'stale'
    retained = client.get('/api/colab/state').json()['positions']
    assert len(retained) == 1 and retained[0]['stale'] is True
    assert retained[0]['updated_at'] == state['positions'][0]['updated_at']


def test_synthetic_radio_data_never_creates_real_fix_and_survey_points_are_inside_model(colab):
    client, runtime, clock, raw, settings = colab
    calibration = refs(raw)
    admin = {'X-Admin-Token': 'test-admin-code'}
    bad = deepcopy(calibration)
    bad['fingerprints'][0]['point'] = [1e9, 1e9]
    assert client.post('/api/colab/wifi/calibration', json=bad, headers=admin).status_code == 422
    calibration['synthetic'] = True
    assert client.post('/api/colab/wifi/calibration', json=calibration, headers=admin).json()['ready'] is False
    body = {'device_id': 'android-test', 'scan': scan(clock, calibration['fingerprints'][0]['readings'])}
    result = client.post('/api/colab/wifi/scans', json=body, headers=pairing(client)).json()
    assert result['status'] == 'uncertain'
    assert client.get('/api/colab/state').json()['positions'] == []


def test_capture_needs_fresh_native_scan_and_restart_keeps_survey(colab):
    client, runtime, clock, raw, settings = colab
    reference = refs(raw)['fingerprints'][0]
    body = {'device_id': 'android-test', 'floor_id': reference['floor_id'],
            'x': reference['point'][0], 'y': reference['point'][1], 'label': 'Known point'}
    admin = {'X-Admin-Token': 'test-admin-code'}
    assert client.post('/api/colab/wifi/capture', json=body, headers=admin).status_code == 422
    payload = {'device_id': 'android-test', 'scan': scan(clock, reference['readings'])}
    client.post('/api/colab/wifi/scans', json=payload, headers=pairing(client))
    assert client.post('/api/colab/wifi/capture', json=body, headers=admin).json()['calibration_points'] == 1
    clock[0] += 21
    assert client.post('/api/colab/wifi/capture', json=body, headers=admin).status_code == 422
    from server.colab import ColabRuntime
    restarted = ColabRuntime(settings.colab_dir, settings.state_dir, clock=lambda: clock[0])
    restarted.initialize()
    assert restarted.wifi_status()['calibration_points'] == 1


def test_replacement_calibration_invalidates_old_fix(colab):
    client, runtime, clock, raw, settings = colab
    calibration = refs(raw)
    admin = {'X-Admin-Token': 'test-admin-code'}
    client.post('/api/colab/wifi/calibration', json=calibration, headers=admin)
    body = {'device_id': 'android-test', 'scan': scan(clock, calibration['fingerprints'][0]['readings'])}
    client.post('/api/colab/wifi/scans', json=body, headers=pairing(client))
    assert client.get('/api/colab/state').json()['positions']
    client.post('/api/colab/wifi/calibration', json=calibration, headers=admin)
    assert client.get('/api/colab/state').json()['positions'] == []


def test_delayed_scan_does_not_replace_a_newer_fingerprint_fix(colab):
    client, runtime, clock, raw, settings = colab
    calibration = refs(raw)
    admin = {'X-Admin-Token': 'test-admin-code'}
    assert client.post('/api/colab/wifi/calibration', json=calibration, headers=admin).status_code == 200
    headers = pairing(client)
    earlier = {'device_id': 'android-test', 'scan': scan(clock, calibration['fingerprints'][0]['readings'])}
    assert client.post('/api/colab/wifi/scans', json=earlier, headers=headers).json()['status'] == 'estimated'
    clock[0] += 2
    newer = {'device_id': 'android-test', 'scan': scan(clock, calibration['fingerprints'][1]['readings'])}
    assert client.post('/api/colab/wifi/scans', json=newer, headers=headers).json()['status'] == 'estimated'
    latest_position = client.get('/api/colab/state').json()['positions'][0]
    assert latest_position['space_id'] == calibration['fingerprints'][1]['space_id']

    # The previous packet is still under the global 20-second age limit, but
    # must not roll the device back when requests arrive out of order.
    client.post('/api/colab/wifi/scans', json=earlier, headers=headers)
    assert client.get('/api/colab/state').json()['positions'] == [latest_position]


def test_stale_older_packet_does_not_delete_a_fresh_fix(colab):
    client, runtime, clock, raw, settings = colab
    calibration = refs(raw)
    admin = {'X-Admin-Token': 'test-admin-code'}
    client.post('/api/colab/wifi/calibration', json=calibration, headers=admin)
    headers = pairing(client)
    expired = {'device_id': 'android-test', 'scan': scan([clock[0] - 30], calibration['fingerprints'][0]['readings'])}
    current = {'device_id': 'android-test', 'scan': scan(clock, calibration['fingerprints'][1]['readings'])}
    assert client.post('/api/colab/wifi/scans', json=current, headers=headers).json()['status'] == 'estimated'
    latest_position = client.get('/api/colab/state').json()['positions'][0]
    client.post('/api/colab/wifi/scans', json=expired, headers=headers)
    assert client.get('/api/colab/state').json()['positions'] == [latest_position]
    assert latest_position['stale'] is False


def test_same_id_changed_geometry_invalidates_persisted_survey_fix_and_overlay(colab):
    client, runtime, clock, raw, settings = colab
    client.get('/api/colab/state')
    clock[0] += 36
    started = client.get('/api/colab/state').json()['movements']
    assert started
    moved_id = started[0]['asset_id']
    clock[0] += 8
    moved_state = client.get('/api/colab/state').json()
    old_sequence = moved_state['sequence']
    old_revision = moved_state['model_revision']
    assert next(a for a in moved_state['assets'] if a['asset_id'] == moved_id)['position'] == started[0]['to']

    calibration = refs(raw)
    client.post('/api/colab/wifi/calibration', json=calibration,
                headers={'X-Admin-Token': 'test-admin-code'})
    payload = {'device_id': 'android-test', 'scan': scan(clock, calibration['fingerprints'][0]['readings'])}
    assert client.post('/api/colab/wifi/scans', json=payload, headers=pairing(client)).json()['status'] == 'estimated'
    assert client.get('/api/colab/state').json()['positions']

    # A valid rigid translation keeps the public building/room IDs, but changes
    # the coordinate frame. Old survey points can still lie inside the large
    # room, so membership validation alone cannot catch this mismatch.
    changed = deepcopy(raw)
    for room in changed['spaces']:
        room['polygon'] = [[x + 1, y] for x, y in room['polygon']]
    for opening in changed['openings']:
        opening['position'][0] += 1
    for asset in changed['assets']:
        asset['position'][0] += 1
    (settings.colab_dir / 'building.json').write_text(json.dumps(changed))
    from server.colab import ColabRuntime
    restarted = ColabRuntime(settings.colab_dir, settings.state_dir, clock=lambda: clock[0])
    restarted.initialize()
    assert restarted.model()['building']['building']['id'] == raw['building']['id']
    assert restarted.wifi_status()['calibration_points'] == 0
    assert restarted.wifi_status()['ready'] is False
    state = restarted.state()
    assert state['sequence'] > old_sequence
    assert state['model_revision'] != old_revision
    assert state['positions'] == []
    assert state['movements'] == []
    expected_positions = {a['id']: a['position'] for a in changed['assets']}
    assert {a['asset_id']: a['position'] for a in state['assets']} == expected_positions


def test_capture_excludes_ap_readings_that_aged_out_since_observation(colab):
    client, runtime, clock, raw, settings = colab
    reference = refs(raw)['fingerprints'][0]
    readings = deepcopy(reference['readings'])
    readings.append({'bssid': '10:20:30:40:50:09', 'rssi_dbm': -68, 'age_s': 18})
    payload = {'device_id': 'android-test', 'scan': scan(clock, readings)}
    response = client.post('/api/colab/wifi/scans', json=payload, headers=pairing(client))
    assert response.json()['reason'] == 'calibration_missing'
    clock[0] += 4
    captured = client.post('/api/colab/wifi/capture', json={
        'device_id': 'android-test', 'floor_id': reference['floor_id'],
        'x': reference['point'][0], 'y': reference['point'][1], 'label': 'Fresh vectors only',
    }, headers={'X-Admin-Token': 'test-admin-code'})
    assert captured.status_code == 200
    with runtime.db() as db:
        saved = runtime.read(db, 'calibration')['fingerprints'][0]['readings']
    assert {entry['bssid'] for entry in saved} == {entry['bssid'] for entry in reference['readings']}
