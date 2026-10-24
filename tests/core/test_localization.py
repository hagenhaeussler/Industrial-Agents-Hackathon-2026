"""Synthetic measurements test software semantics, never physical accuracy."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
from pathlib import Path

import pytest
from core.localization import estimate_position, normalize_readings, validate_calibration

NOW = 1792918800.0
STAMP = datetime.fromtimestamp(NOW, timezone.utc).isoformat()
APS = ['00:11:22:33:44:01', '00:11:22:33:44:02', '00:11:22:33:44:03', '00:11:22:33:44:04']


def readings(values):
    return [{'bssid': b, 'rssi_dbm': r} for b, r in zip(APS, values)]


def calibration():
    # Intentionally false ONLY to exercise real-mode code with fixture data.
    # Nothing in this fixture is a real Colab radio survey or deployed config.
    return {'schema_version': 1, 'building_id': 'synthetic-test-building', 'synthetic': False, 'fingerprints': [
        {'id': 'a', 'floor_id': 'f3', 'space_id': 'room-a', 'point': [1, 2], 'readings': readings([-45, -65, -75, -80])},
        {'id': 'b', 'floor_id': 'f4', 'space_id': 'room-b', 'point': [8, 9], 'readings': readings([-80, -75, -55, -45])},
    ]}


def scan(values=(-46, -64, -76, -79)):
    return {'observed_at': STAMP, 'readings': readings(values), 'synthetic': False}


def test_distinct_match_returns_low_confidence_survey_point_without_interpolation():
    result = estimate_position(scan(), calibration(), now=NOW)
    assert result['status'] == 'estimated'
    assert result['position']['point'] == [1., 2.]
    assert result['position']['confidence'] == 'low'
    assert result['uncertainty_kind'] == 'uncalibrated_heuristic'
    assert result['uncertainty_radius_m'] >= 3


@pytest.mark.parametrize('field', ['scan', 'calibration', 'reference'])
def test_synthetic_inputs_never_create_real_fix(field):
    s, c = scan(), calibration()
    {'scan': s, 'calibration': c, 'reference': c['fingerprints'][0]}[field]['synthetic'] = True
    result = estimate_position(s, c, now=NOW)
    assert result['status'] == 'uncertain' and result['synthetic']
    assert result['position'] is None


def test_identical_signals_on_different_floors_are_ambiguous():
    c = calibration()
    c['fingerprints'][1]['readings'] = deepcopy(c['fingerprints'][0]['readings'])
    result = estimate_position(scan(), c, now=NOW)
    assert result['status'] == 'uncertain'
    assert result['position'] is None


def test_far_ap_pattern_is_not_claimed_as_a_fix():
    result = estimate_position(scan((-110, -110, -110, -110)), calibration(), now=NOW)
    assert result['status'] == 'uncertain'
    assert result['position'] is None


def test_stale_recording_and_future_clock_are_rejected():
    assert estimate_position(scan(), calibration(), now=NOW+21)['status'] == 'stale'
    assert estimate_position(scan(), calibration(), now=NOW-10)['status'] == 'invalid'


def test_ap_age_added_to_transport_age_and_duplicate_bssids_not_counted():
    s = scan()
    for r in s['readings']:
        r['age_s'] = 15
    assert estimate_position(s, calibration(), now=NOW+10)['status'] == 'insufficient_data'
    s['readings'] = [deepcopy(s['readings'][0]) for _ in range(4)]
    assert estimate_position(s, calibration(), now=NOW)['status'] == 'insufficient_data'


def test_duplicate_median_and_normalization():
    assert normalize_readings([{'bssid': '00-11-22-33-44-AA', 'rssi_dbm': -50},
                               {'bssid': '00:11:22:33:44:aa', 'rssi_dbm': -70}]) == {'00:11:22:33:44:aa': -60.}


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), True, 'bad', -130, 1, 10**1000])
def test_malformed_rssi_never_returns_position(bad):
    s = scan(); s['readings'][0]['rssi_dbm'] = bad
    assert estimate_position(s, calibration(), now=NOW)['status'] == 'invalid'


def test_missing_calibration_small_survey_and_unknown_aps():
    assert estimate_position(scan(), None, now=NOW)['reason'] == 'calibration_missing'
    c = calibration(); c['fingerprints'] = c['fingerprints'][:1]
    assert estimate_position(scan(), c, now=NOW)['status'] == 'insufficient_data'
    s = scan()
    for r in s['readings']:
        r['bssid'] = r['bssid'].replace('00:11', '00:12')
    assert estimate_position(s, calibration(), now=NOW)['status'] == 'insufficient_data'


def test_invalid_schema_coordinate_and_wrong_building():
    c = calibration(); c['fingerprints'][0]['point'] = [float('nan'), 2]
    assert validate_calibration(c)
    assert estimate_position(scan(), c, now=NOW)['status'] == 'invalid'
    s = scan(); s['building_id'] = 'other'
    assert estimate_position(s, calibration(), now=NOW)['reason'] == 'building_mismatch'


def test_timezone_is_required():
    s = scan(); s['observed_at'] = '2026-10-25T10:00:00'
    assert estimate_position(s, calibration(), now=NOW)['status'] == 'invalid'


def collector():
    path = Path(__file__).resolve().parents[2] / 'scripts/colab_wifi_collector.py'
    spec = importlib.util.spec_from_file_location('colab_wifi_collector_test', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_termux_uses_microseconds_since_boot_and_discards_cached_results():
    mod = collector()
    rows = [{'bssid': APS[0], 'rssi': -50, 'timestamp': 99_000_000},
            {'bssid': APS[1], 'rssi': -60, 'timestamp': 1_000_000},
            {'bssid': APS[2], 'rssi': -65, 'timestamp': 101_000_000}]
    result = mod.termux_scan(rows, boottime_s=100, observed_at=STAMP)
    assert len(result['readings']) == 1
    assert result['readings'][0]['age_s'] == 1
    assert result['dropped_old_or_invalid'] == 2


def test_iw_parser_ignores_unknown_age_and_old_entries():
    mod = collector()
    result = mod.iw_scan('BSS 00:11:22:33:44:01(on wlan0)\n signal: -56.00 dBm\n last seen: 200 ms ago\n'
                         'BSS 00:11:22:33:44:02(on wlan0)\n signal: -80.00 dBm\n last seen: 30000 ms ago\n', observed_at=STAMP)
    assert result['readings'] == [{'bssid': APS[0], 'rssi_dbm': -56., 'age_s': .2}]


def test_collector_does_not_refresh_file_timestamp(tmp_path):
    import json
    mod = collector()
    path = tmp_path / 'recorded.json'
    saved = {**scan(), 'synthetic': True}
    path.write_text(json.dumps(saved))
    assert mod.capture('file', input_path=str(path)) == saved


def test_collector_rejects_remote_http_without_network():
    with pytest.raises(ValueError, match='HTTPS'):
        collector().send_scan('http://example.com/api', 'pairing-token', 'd', 'Device', scan())


def test_extreme_coordinates_are_rejected_before_distance_overflow():
    c = calibration(); c['fingerprints'][0]['point'] = [1e308, -1e308]
    assert estimate_position(scan(), c, now=NOW)['status'] == 'invalid'
