"""Conservative Wi-Fi fingerprint matching; no radio access, persistence or AP ranging.

Coordinates are *surveyed calibration points* in building metres, not a claim of
continuous positioning. The server must validate those points against its building,
authenticate the collector, and expire displayed fixes. RSSI is not a distance.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
import re
from statistics import median
import time
from typing import Any

BSSID = re.compile(r"^(?:[0-9a-f]{2}:){5}[0-9a-f]{2}$")
MAX_READINGS = 512
MAX_FINGERPRINTS = 2000
MIN_COMMON_BSSIDS = 3


def _finite(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _timestamp(value: Any) -> float:
    if not isinstance(value, str):
        raise ValueError('observed_at must be an ISO 8601 timestamp with timezone')
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('observed_at is not a valid ISO 8601 timestamp') from exc
    if stamp.tzinfo is None:
        raise ValueError('observed_at needs a timezone')
    return stamp.timestamp()


def normalize_readings(readings: Any, *, max_reading_age_s: float | None = None) -> dict[str, float]:
    """Validate vectors, median duplicate BSSIDs and optionally omit old AP entries.

    BSSID identifies an AP radio, not necessarily a separate physical access point.
    No SSID, device MAC or user identity is needed by the estimator.
    """
    if not isinstance(readings, list) or len(readings) > MAX_READINGS:
        raise ValueError(f'readings must be a list with at most {MAX_READINGS} entries')
    buckets: dict[str, list[float]] = {}
    for entry in readings:
        if not isinstance(entry, dict):
            raise ValueError('each reading must be an object')
        bssid = entry.get('bssid')
        if not isinstance(bssid, str):
            raise ValueError('each reading needs a BSSID')
        bssid = bssid.lower().replace('-', ':')
        if not BSSID.fullmatch(bssid) or bssid in {'00:00:00:00:00:00', 'ff:ff:ff:ff:ff:ff', '02:00:00:00:00:00'}:
            raise ValueError('invalid or redacted BSSID')
        if int(bssid[:2], 16) & 1:
            raise ValueError('BSSID must be unicast')
        rssi = entry.get('rssi_dbm')
        if not _finite(rssi) or not -120 <= rssi <= 0:
            raise ValueError('rssi_dbm must be a finite number in [-120, 0]')
        age = entry.get('age_s', 0)
        if not _finite(age) or age < 0:
            raise ValueError('age_s must be a non-negative finite number')
        if max_reading_age_s is not None and age > max_reading_age_s:
            continue
        buckets.setdefault(bssid, []).append(float(rssi))
    return {key: float(median(values)) for key, values in buckets.items()}


def validate_calibration(calibration: Any) -> list[str]:
    """Return schema errors, without asserting survey accuracy or building membership."""
    if not isinstance(calibration, dict):
        return ['calibration must be an object']
    errors: list[str] = []
    if calibration.get('schema_version') != 1 or isinstance(calibration.get('schema_version'), bool):
        errors.append('schema_version must be 1')
    if not isinstance(calibration.get('building_id'), str) or not calibration['building_id'].strip():
        errors.append('building_id is required')
    if not isinstance(calibration.get('synthetic', False), bool):
        errors.append('synthetic must be boolean')
    refs = calibration.get('fingerprints')
    if not isinstance(refs, list) or len(refs) > MAX_FINGERPRINTS:
        return errors + [f'fingerprints must be a list with at most {MAX_FINGERPRINTS} entries']
    ids: set[str] = set()
    for index, ref in enumerate(refs):
        prefix = f'fingerprints[{index}]'
        if not isinstance(ref, dict):
            errors.append(f'{prefix} must be an object')
            continue
        for key in ('id', 'floor_id', 'space_id'):
            if not isinstance(ref.get(key), str) or not ref[key].strip():
                errors.append(f'{prefix}.{key} is required')
        ident = ref.get('id')
        if isinstance(ident, str):
            if ident in ids:
                errors.append(f'{prefix}.id must be unique')
            ids.add(ident)
        point = ref.get('point')
        if not isinstance(point, (list, tuple)) or len(point) != 2 or not all(_finite(v) and abs(v) <= 1_000_000 for v in point):
            errors.append(f'{prefix}.point must be two finite metre coordinates within +/-1000000')
        if not isinstance(ref.get('synthetic', False), bool):
            errors.append(f'{prefix}.synthetic must be boolean')
        try:
            if len(normalize_readings(ref.get('readings'))) < MIN_COMMON_BSSIDS:
                errors.append(f'{prefix} needs at least {MIN_COMMON_BSSIDS} distinct BSSIDs')
        except ValueError as exc:
            errors.append(f'{prefix}: {exc}')
    return errors


def _result(status: str, reason: str, **extra: Any) -> dict:
    return {'status': status, 'position': None, 'reason': reason,
            'uncertainty_radius_m': None, 'uncertainty_kind': 'uncalibrated_heuristic',
            'synthetic': False, 'diagnostics': {}, **extra}


def estimate_position(scan: Any, calibration: Any, *, now: float | None = None,
                      max_age_s: float = 20.0) -> dict:
    """Match a fresh RSSI vector to a surveyed reference, or explicitly decline.

    status: estimated | uncertain | insufficient_data | stale | invalid.
    Even estimated is LOW confidence: position is the nearest calibration point;
    the radius is a conservative display heuristic, never a 95% accuracy claim.
    Calibration/provider admission and authorization belong to the server.
    """
    now = time.time() if now is None else now
    if not _finite(now) or not _finite(max_age_s) or max_age_s <= 0:
        return _result('invalid', 'invalid_time_configuration')
    if not isinstance(scan, dict):
        return _result('invalid', 'scan_must_be_object')
    if not isinstance(scan.get('synthetic', False), bool):
        return _result('invalid', 'synthetic_must_be_boolean')
    try:
        observed = _timestamp(scan.get('observed_at'))
        age = now - observed
        if age < -5:
            return _result('invalid', 'scan_timestamp_in_future')
        if age > max_age_s:
            return _result('stale', 'scan_too_old', diagnostics={'age_s': round(age, 3)})
        vector = normalize_readings(scan.get('readings'), max_reading_age_s=max_age_s - max(0, age))
    except ValueError as exc:
        return _result('invalid', str(exc))
    if len(vector) < MIN_COMMON_BSSIDS:
        return _result('insufficient_data', 'need_three_fresh_distinct_bssids',
                       diagnostics={'usable_bssids': len(vector)})
    if calibration is None:
        return _result('insufficient_data', 'calibration_missing')
    errors = validate_calibration(calibration)
    if errors:
        return _result('invalid', 'invalid_calibration', diagnostics={'errors': errors[:20]})
    if scan.get('building_id') not in (None, calibration['building_id']):
        return _result('invalid', 'building_mismatch')
    refs = calibration['fingerprints']
    positions = {(r['floor_id'], r['space_id'], tuple(r['point'])) for r in refs}
    if len(positions) < 2:
        return _result('insufficient_data', 'need_two_distinct_surveyed_reference_points')
    synthetic = scan.get('synthetic', False) or calibration.get('synthetic', False) or any(r.get('synthetic', False) for r in refs)
    if synthetic:
        return _result('uncertain', 'synthetic_data_not_a_real_fix', synthetic=True)

    candidates = []
    for ref in refs:
        reference = normalize_readings(ref['readings'])
        common = vector.keys() & reference.keys()
        overlap = len(common) / len(vector.keys() | reference.keys())
        if len(common) < MIN_COMMON_BSSIDS or overlap < .35:
            continue
        differences = [vector[key] - reference[key] for key in sorted(common)]
        # Small receiver offsets are tolerated, but absolute attenuation still
        # contributes to score; an arbitrary global offset must not erase distance.
        offset = max(-3., min(3., median(differences)))
        rmse = math.sqrt(sum((d - offset) ** 2 for d in differences) / len(differences))
        score = rmse + .25 * abs(offset) + 6. * (1. - overlap)
        candidates.append({'ref': ref, 'score': score, 'common': len(common), 'overlap': overlap})
    candidates.sort(key=lambda c: (c['score'], c['ref']['id']))
    if not candidates:
        return _result('insufficient_data', 'not_enough_matching_bssids')
    best = candidates[0]
    diag = {'usable_bssids': len(vector), 'matched_bssids': best['common'],
            'score_db': round(best['score'], 3), 'overlap_ratio': round(best['overlap'], 3),
            'reference_id': best['ref']['id'], 'age_s': round(max(0., age), 3),
            'candidate_count': len(candidates), 'position_method': 'nearest_surveyed_reference_point'}
    if best['score'] > 12:
        return _result('uncertain', 'signal_pattern_outside_calibrated_range', diagnostics=diag)
    point = best['ref']['point']
    nearby = []
    for other in candidates[1:]:
        ref = other['ref']
        distance = math.dist(point, ref['point'])
        if other['score'] - best['score'] <= 2 and (
                ref['floor_id'] != best['ref']['floor_id'] or
                ref['space_id'] != best['ref']['space_id'] or distance > 3):
            return _result('uncertain', 'ambiguous_floor_or_reference_point', diagnostics=diag)
        if ref['floor_id'] == best['ref']['floor_id'] and other['score'] <= best['score'] + 6:
            nearby.append(distance)
    # Three metres is deliberately a floor, not measured radio accuracy. Sparse
    # coverage remains a limitation regardless of an exact RSSI vector match.
    radius = max(3., max(nearby, default=0.), best['score'] / 2)
    position = {'building_id': calibration['building_id'], 'floor_id': best['ref']['floor_id'],
                'space_id': best['ref']['space_id'], 'point': [float(v) for v in point],
                'source': 'wifi_fingerprint', 'confidence': 'low',
                'updated_at': datetime.fromtimestamp(observed, timezone.utc).isoformat().replace('+00:00', 'Z')}
    return _result('estimated', 'nearest_surveyed_reference_point', position=position,
                   uncertainty_radius_m=round(radius, 2), diagnostics=diag)
