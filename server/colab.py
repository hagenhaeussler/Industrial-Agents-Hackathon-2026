"""Shared Colab demonstration state and opt-in native Wi-Fi ingestion.

Furniture animation is a separate, explicitly simulated overlay. It never writes
kit data, building events or navigation positions. Actual Wi-Fi estimates can
only enter through an authenticated collector and surveyed calibration vectors.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
import hashlib
import hmac
import json
import math
from pathlib import Path
import secrets
import sqlite3
import threading
import time
from uuid import uuid4

from fastapi import APIRouter, Header, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from shapely.geometry import Point
from starter_agent.building_map import outline

from core.localization import estimate_position, normalize_readings, validate_calibration
from .errors import ServiceError
from .config import REPO_ROOT


router = APIRouter(prefix='/api/colab', tags=['Colab demo'])


class Arguments(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class Switch(Arguments):
    running: bool


class ManualPosition(Arguments):
    device_id: str | None = Field(default=None, pattern=r'^[A-Za-z0-9_-]{1,64}$')
    label: str = Field(default='Demo visitor', min_length=1, max_length=60)
    floor_id: str = Field(min_length=1, max_length=100)
    x: float
    y: float
    source: Literal['manual', 'simulated'] = 'manual'


class Pair(Arguments):
    device_id: str | None = Field(default=None, pattern=r'^[A-Za-z0-9_-]{1,64}$')
    label: str = Field(default='Android visitor', min_length=1, max_length=60)


class WifiScan(Arguments):
    device_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    label: str = Field(default='Android visitor', min_length=1, max_length=60)
    scan: dict


class Capture(Arguments):
    device_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    floor_id: str = Field(min_length=1, max_length=100)
    x: float
    y: float
    label: str = Field(default='Survey point', min_length=1, max_length=100)


class ColabPosition(BaseModel):
    device_id: str
    label: str
    x: float
    y: float
    floor_id: str
    space_id: str
    source: Literal['wifi_fingerprint', 'manual', 'simulated']
    confidence: Literal['low', 'confirmed', 'simulated']
    accuracy_m: float | None
    updated_at: float
    stale: bool
    uncertainty_kind: str | None = None


class ColabMovement(BaseModel):
    asset_id: str
    floor_id: str
    from_: tuple[float, float] = Field(alias='from')
    to: tuple[float, float]
    started_at: float
    duration_s: float


class ColabAsset(BaseModel):
    asset_id: str
    position: tuple[float, float]
    floor_id: str
    space_id: str


class ColabState(BaseModel):
    model_revision: str = ''
    sequence: int
    server_time: float
    movements: list[ColabMovement]
    assets: list[ColabAsset]
    positions: list[ColabPosition]
    demo_running: bool
    walk_running: bool


class ColabModel(BaseModel):
    building: dict
    metadata: dict
    anchors: dict[str, tuple[float, float]]
    model_revision: str = ''


class WifiDevice(BaseModel):
    device_id: str
    label: str
    last_scan_at: float
    readings_count: int


class WifiStatus(BaseModel):
    calibration_points: int
    ready: bool
    synthetic: bool
    devices: list[WifiDevice]
    browser_scan_supported: bool
    method: str
    accuracy_validated: bool


class PairedCollector(BaseModel):
    token: str
    device_id: str
    expires_at: float
    scan_endpoint: str


def fail(message, *, status=422, code='invalid_args'):
    raise ServiceError(code, message, status=status)


class ColabRuntime:
    def __init__(self, model_dir: Path, state_dir: Path, *, clock=time.time):
        self.model_dir = model_dir
        self.path = state_dir / 'colab.sqlite3'
        self.clock = clock
        self.lock = threading.RLock()
        self._model = None

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS positions(device_id TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS scans(device_id TEXT PRIMARY KEY, label TEXT NOT NULL,
                    received_at REAL NOT NULL, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tokens(hash TEXT PRIMARY KEY, device_id TEXT NOT NULL,
                    expires_at REAL NOT NULL);
            ''')
            model_hash = self.model()['model_revision']
            if self.read(db, 'model_hash') != model_hash:
                # Calibration metres and furniture offsets belong to one exact
                # geometry revision, even when its public building ID is reused.
                sequence = self.read(db, 'sequence', 0) + 1
                db.execute('DELETE FROM metadata')
                db.execute('DELETE FROM positions')
                db.execute('DELETE FROM scans')
                self.write(db, 'model_hash', model_hash)
                self.write(db, 'sequence', sequence)

    @contextmanager
    def db(self):
        with self.lock:
            connection = sqlite3.connect(self.path, timeout=15)
            connection.row_factory = sqlite3.Row
            try:
                connection.execute('BEGIN IMMEDIATE')
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
            finally:
                connection.close()

    @staticmethod
    def read(db, key, default=None):
        row = db.execute('SELECT value FROM metadata WHERE key=?', (key,)).fetchone()
        return json.loads(row['value']) if row else deepcopy(default)

    @staticmethod
    def write(db, key, value):
        db.execute('INSERT OR REPLACE INTO metadata VALUES(?,?)', (key, json.dumps(value, allow_nan=False)))

    def model(self):
        with self.lock:
            if self._model is None:
                try:
                    building = json.loads((self.model_dir / 'building.json').read_text())
                    metadata = json.loads((self.model_dir / 'metadata.json').read_text())
                except (OSError, ValueError):
                    fail('The Colab demonstration model is unavailable.', status=503, code='not_available')
                anchors = {}
                for room in building['spaces']:
                    point = outline(room['polygon']).representative_point()
                    anchors[room['id']] = [point.x, point.y]
                revision = hashlib.sha256(json.dumps(building, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
                self._model = {'building': building, 'metadata': metadata, 'anchors': anchors, 'model_revision': revision}
            return deepcopy(self._model)

    def room_at(self, floor_id, x, y, *, space_id=None):
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (x, y)):
            fail('Position coordinates must be finite.')
        for room in self.model()['building']['spaces']:
            if room['floor_id'] == floor_id and (space_id is None or room['id'] == space_id):
                if outline(room['polygon']).buffer(.01).covers(Point(x, y)):
                    return room
        fail('Choose a position inside a room on the selected floor.')

    @staticmethod
    def bump(db):
        number = ColabRuntime.read(db, 'sequence', 0) + 1
        ColabRuntime.write(db, 'sequence', number)
        return number

    def _motion_choices(self):
        payload = self.model()
        model = payload['building']
        rooms = {r['id']: r for r in model['spaces']}
        floors = {f['id']: f['level'] for f in model['floors']}
        choices = []
        assets = {asset['id']: asset for asset in model['assets']}
        for move in payload['metadata'].get('movable_assets', [])[:3]:
            asset = assets.get(move.get('asset_id'))
            if asset and all(outline(rooms[asset['space_id']]['polygon']).covers(Point(p))
                             for p in (move['from'], move['to'])):
                choices.append({'asset': asset, 'from': move['from'], 'to': move['to']})
        if choices:
            default_level = payload['metadata'].get('default_floor_level', 3)
            return sorted(choices, key=lambda c: floors[c['asset']['floor_id']] != default_level)
        for asset in model['assets']:
            if floors.get(asset['floor_id']) not in (3, 4):
                continue
            if not any(term in (asset['name'] + ' ' + asset['type']).lower() for term in ('coffee', 'table', 'trolley', 'cart')):
                continue
            polygon = outline(rooms[asset['space_id']]['polygon']).buffer(-.35)
            start = asset['position']
            for dx, dy in ((1.6, 0), (0, 1.6), (-1.6, 0), (0, -1.6), (.7, .7)):
                end = [start[0] + dx, start[1] + dy]
                if polygon.covers(Point(end)):
                    choices.append({'asset': asset, 'from': start, 'to': end})
                    break
            if len(choices) == 3:
                break
        return choices

    def _advance(self, db, now):
        moves = self.read(db, 'movements', [])
        locations = self.read(db, 'asset_locations', {})
        active = []
        for move in moves:
            if now >= move['started_at'] + move['duration_s']:
                locations[move['asset_id']] = move['to']
            else:
                active.append(move)
        running = self.read(db, 'demo_running', True)
        next_at = self.read(db, 'next_motion_at')
        if next_at is None:
            self.write(db, 'next_motion_at', now + 35)
        elif running and now >= next_at and not active:
            choices = self._motion_choices()
            index = self.read(db, 'motion_index', 0)
            if choices:
                choice = choices[index % len(choices)]
                asset = choice['asset']
                start = locations.get(asset['id'], choice['from'])
                target = choice['from'] if start == choice['to'] else choice['to']
                active = [{'asset_id': asset['id'], 'from': start, 'to': target,
                           'floor_id': asset['floor_id'], 'started_at': now, 'duration_s': 7.0}]
                self.write(db, 'motion_index', index + 1)
                self.bump(db)
            self.write(db, 'next_motion_at', now + 80)
        self.write(db, 'movements', active)
        self.write(db, 'asset_locations', locations)
        return active, locations

    def _walker(self, db, now):
        if not self.read(db, 'walk_running', False):
            return None
        path = self.model()['metadata'].get('walk_path', [])
        if len(path) < 2:
            return None
        # Follow the model's validated path out and back, never teleport between
        # arbitrary room centres or floors. It remains explicitly simulated.
        started = self.read(db, 'walk_started_at', now)
        pairs = [(a, b, math.hypot(b['x'] - a['x'], b['y'] - a['y'])) for a, b in zip(path, path[1:])]
        length = sum(p[2] for p in pairs)
        if length <= 0:
            return None
        distance = max(0, now - started) * .65 % (2 * length)
        if distance > length:
            distance = 2 * length - distance
        a, b = path[0], path[1]
        t = 0.
        for a, b, segment_length in pairs:
            if distance <= segment_length:
                t = distance / segment_length if segment_length else 0.
                break
            distance -= segment_length
        x, y = a['x'] + (b['x'] - a['x']) * t, a['y'] + (b['y'] - a['y']) * t
        room = self.room_at(a['floor_id'], x, y)
        return {'device_id': 'simulated-visitor', 'label': 'Demo visitor',
                'x': x, 'y': y, 'floor_id': room['floor_id'],
                'space_id': room['id'], 'source': 'simulated', 'confidence': 'simulated',
                'accuracy_m': None, 'updated_at': now, 'stale': False}

    def state(self):
        now = self.clock()
        with self.db() as db:
            movements, overrides = self._advance(db, now)
            positions = [json.loads(row['body']) for row in db.execute('SELECT body FROM positions')]
            positions = [p for p in positions if now - p['updated_at'] < 1800]
            for position in positions:
                position['stale'] = now - position['updated_at'] > (20 if position['source'] == 'wifi_fingerprint' else 120)
            if walker := self._walker(db, now):
                positions.append(walker)
            assets = [{'asset_id': a['id'], 'position': overrides.get(a['id'], a['position']),
                       'floor_id': a['floor_id'], 'space_id': a['space_id']}
                      for a in self.model()['building']['assets']]
            return {'sequence': self.read(db, 'sequence', 0), 'server_time': now,
                    'model_revision': self.model()['model_revision'],
                    'movements': movements, 'assets': assets, 'positions': positions,
                    'demo_running': self.read(db, 'demo_running', True),
                    'walk_running': self.read(db, 'walk_running', False)}

    def switch(self, running, *, walk=False):
        now = self.clock()
        with self.db() as db:
            key = 'walk_running' if walk else 'demo_running'
            self.write(db, key, running)
            if walk and running:
                self.write(db, 'walk_started_at', now)
            elif not walk:
                moves = self.read(db, 'movements', [])
                overrides = self.read(db, 'asset_locations', {})
                for move in moves:
                    progress = min(1., max(0., (now - move['started_at']) / move['duration_s']))
                    overrides[move['asset_id']] = [a + (b - a) * progress for a, b in zip(move['from'], move['to'])]
                self.write(db, 'asset_locations', overrides)
                self.write(db, 'movements', [])
                self.write(db, 'next_motion_at', now + 35)
            self.bump(db)
        return self.state()

    def put_position(self, body):
        room = self.room_at(body.floor_id, body.x, body.y)
        device_id = body.device_id or 'manual-' + uuid4().hex[:12]
        position = {'device_id': device_id, 'label': body.label, 'floor_id': body.floor_id,
                    'space_id': room['id'], 'x': body.x, 'y': body.y, 'source': body.source,
                    'confidence': 'confirmed' if body.source == 'manual' else 'simulated',
                    'accuracy_m': None, 'updated_at': self.clock(), 'stale': False}
        with self.db() as db:
            existing = db.execute('SELECT body FROM positions WHERE device_id=?', (device_id,)).fetchone()
            if existing and json.loads(existing['body'])['source'] == 'wifi_fingerprint':
                fail('A manual marker cannot replace a paired Wi-Fi device.', status=409, code='version_conflict')
            if db.execute('SELECT count(*) FROM positions').fetchone()[0] >= 40 and not existing:
                fail('The demo has enough visitor markers. Reuse a marker.', status=429)
            db.execute('INSERT OR REPLACE INTO positions VALUES(?,?)', (device_id, json.dumps(position)))
            self.bump(db)
        return position

    def pair(self, body):
        token = secrets.token_urlsafe(32)
        device = body.device_id or 'android-' + uuid4().hex[:12]
        expires = self.clock() + 12 * 3600
        with self.db() as db:
            db.execute('DELETE FROM tokens WHERE expires_at<? OR device_id=?', (self.clock(), device))
            db.execute('INSERT INTO tokens VALUES(?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), device, expires))
        return {'token': token, 'device_id': device, 'expires_at': expires,
                'scan_endpoint': '/api/colab/wifi/scans'}

    def authenticate(self, token, device_id):
        if not isinstance(token, str) or not token:
            fail('Pair the native collector first.', status=403, code='forbidden')
        with self.db() as db:
            row = db.execute('SELECT device_id,expires_at FROM tokens WHERE hash=?',
                             (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
        if not row or row['expires_at'] < self.clock() or row['device_id'] != device_id:
            fail('Collector access has expired or belongs to another device.', status=403, code='forbidden')

    def validate_survey(self, calibration):
        errors = validate_calibration(calibration)
        if errors:
            fail('; '.join(errors[:4]))
        if calibration['building_id'] != self.model()['building']['building']['id']:
            fail('Calibration belongs to another building.')
        for ref in calibration['fingerprints']:
            self.room_at(ref['floor_id'], *ref['point'], space_id=ref['space_id'])

    def save_survey(self, calibration):
        self.validate_survey(calibration)
        with self.db() as db:
            self.write(db, 'calibration', calibration)
            # Prior fixes must be reacquired against the replacement survey.
            db.execute("DELETE FROM positions WHERE json_extract(body, '$.source')='wifi_fingerprint'")
            self.bump(db)
        return self.wifi_status()

    def ingest(self, body):
        if len(json.dumps(body.scan)) > 100_000:
            fail('The scan is too large.')
        try:
            normalize_readings(body.scan.get('readings'))
        except ValueError as exc:
            fail(str(exc))
        with self.db() as db:
            calibration = self.read(db, 'calibration')
            result = estimate_position(body.scan, calibration, now=self.clock())
            previous = db.execute('SELECT body FROM scans WHERE device_id=?', (body.device_id,)).fetchone()
            try:
                observed = datetime.fromisoformat(body.scan['observed_at'].replace('Z', '+00:00')).timestamp()
                previous_time = (datetime.fromisoformat(json.loads(previous['body'])['observed_at'].replace('Z', '+00:00')).timestamp()
                                 if previous else float('-inf'))
            except (ValueError, TypeError, KeyError, AttributeError):
                return result
            if observed < previous_time:
                return {**result, 'position': None, 'status': 'stale', 'reason': 'out_of_order_scan_ignored'}
            if result['status'] in ('invalid', 'stale'):
                return result
            if result['status'] not in ('invalid', 'stale') and not body.scan.get('synthetic', False):
                db.execute('INSERT OR REPLACE INTO scans VALUES(?,?,?,?)',
                           (body.device_id, body.label, self.clock(), json.dumps(body.scan)))
            if result['status'] == 'estimated' and result['position']:
                fix = result['position']
                self.room_at(fix['floor_id'], *fix['point'], space_id=fix['space_id'])
                position = {'device_id': body.device_id, 'label': body.label,
                            'x': fix['point'][0], 'y': fix['point'][1], 'floor_id': fix['floor_id'],
                            'space_id': fix['space_id'], 'source': 'wifi_fingerprint', 'confidence': 'low',
                            'accuracy_m': result['uncertainty_radius_m'],
                            'updated_at': datetime.fromisoformat(fix['updated_at'].replace('Z', '+00:00')).timestamp(),
                            'uncertainty_kind': 'uncalibrated_heuristic', 'stale': False}
                db.execute('INSERT OR REPLACE INTO positions VALUES(?,?)', (body.device_id, json.dumps(position)))
                self.bump(db)
            else:
                # Never leave the old marker looking like a current confident fix.
                db.execute("DELETE FROM positions WHERE device_id=? AND json_extract(body,'$.source')='wifi_fingerprint'", (body.device_id,))
        # No radio identifiers or raw measurements are exposed through public state.
        return result

    def capture(self, body):
        room = self.room_at(body.floor_id, body.x, body.y)
        with self.db() as db:
            row = db.execute('SELECT body FROM scans WHERE device_id=?', (body.device_id,)).fetchone()
            if not row:
                fail('No native Wi-Fi scan has arrived from this device yet.')
            scan = json.loads(row['body'])
            check = estimate_position(scan, None, now=self.clock())
            if check['status'] in ('invalid', 'stale') or check['reason'] != 'calibration_missing':
                fail('A fresh native scan with at least three access-point radios is required.')
            calibration = self.read(db, 'calibration', {'schema_version': 1,
                'building_id': self.model()['building']['building']['id'], 'synthetic': False, 'fingerprints': []})
            observed = datetime.fromisoformat(scan['observed_at'].replace('Z', '+00:00')).timestamp()
            fresh = normalize_readings(scan['readings'], max_reading_age_s=20 - max(0, self.clock() - observed))
            calibration['fingerprints'].append({'id': 'survey-' + uuid4().hex[:12],
                'label': body.label, 'floor_id': body.floor_id, 'space_id': room['id'],
                'point': [body.x, body.y], 'synthetic': False,
                'readings': [{'bssid': key, 'rssi_dbm': value} for key, value in fresh.items()]})
            self.validate_survey(calibration)
            self.write(db, 'calibration', calibration)
            self.bump(db)
        return self.wifi_status()

    def wifi_status(self):
        with self.db() as db:
            calibration = self.read(db, 'calibration')
            refs = calibration.get('fingerprints', []) if calibration else []
            points = {(r['floor_id'], r['space_id'], tuple(r['point'])) for r in refs}
            synthetic = bool(calibration and (calibration.get('synthetic') or any(r.get('synthetic') for r in refs)))
            devices = [{'device_id': r['device_id'], 'label': r['label'], 'last_scan_at': r['received_at'],
                        'readings_count': len(json.loads(r['body']).get('readings', []))}
                       for r in db.execute('SELECT * FROM scans WHERE received_at>?', (self.clock() - 1800,))]
        return {'calibration_points': len(refs), 'ready': len(points) >= 2 and not synthetic,
                'synthetic': synthetic, 'devices': devices, 'browser_scan_supported': False,
                'method': 'wifi_fingerprint', 'accuracy_validated': False}


def runtime(request):
    value = request.app.state.colab
    if value is None:
        fail('The Colab demo is not configured.', status=404, code='not_available')
    return value


def require_admin(request, code):
    configured = request.app.state.settings.admin_token
    if not configured or not isinstance(code, str) or not hmac.compare_digest(configured.encode(), code.encode()):
        fail('Enter the configured admin code to pair a collector or edit calibration.', status=403, code='forbidden')


@router.get('/model', response_model=ColabModel)
def model(request: Request):
    return runtime(request).model()


@router.get('/building.json', include_in_schema=False)
def download_building(request: Request):
    return FileResponse(runtime(request).model_dir / 'building.json',
                        filename='munich-urban-colab-building.json', media_type='application/json')


@router.get('/collector.py', include_in_schema=False)
def download_collector(request: Request):
    runtime(request)
    return FileResponse(REPO_ROOT / 'scripts' / 'colab_wifi_collector.py',
                        filename='colab_wifi_collector.py', media_type='text/x-python')


@router.get('/guide.md', include_in_schema=False)
def download_guide(request: Request):
    runtime(request)
    return FileResponse(REPO_ROOT / 'docs' / 'colab-demo.md',
                        filename='colab-setup.md', media_type='text/markdown')


@router.get('/state', response_model=ColabState)
def state(request: Request):
    return runtime(request).state()


@router.post('/demo', response_model=ColabState)
def demo(body: Switch, request: Request):
    return runtime(request).switch(body.running)


@router.post('/demo/walk', response_model=ColabState)
def demo_walk(body: Switch, request: Request):
    return runtime(request).switch(body.running, walk=True)


@router.post('/positions', response_model=ColabPosition)
def position(body: ManualPosition, request: Request):
    return runtime(request).put_position(body)


@router.post('/pair', response_model=PairedCollector)
def pair(body: Pair, request: Request, code: str | None = Header(default=None, alias='X-Admin-Token')):
    require_admin(request, code)
    result = runtime(request).pair(body)
    from fastapi.responses import JSONResponse
    return JSONResponse(result, headers={'Cache-Control': 'no-store'})


@router.get('/wifi/status', response_model=WifiStatus)
def wifi_status(request: Request):
    return runtime(request).wifi_status()


@router.post('/wifi/scans')
def wifi_scan(body: WifiScan, request: Request, token: str | None = Header(default=None, alias='X-Colab-Token')):
    service = runtime(request)
    service.authenticate(token, body.device_id)
    return service.ingest(body)


@router.post('/wifi/calibration', response_model=WifiStatus)
def calibration(body: dict, request: Request, code: str | None = Header(default=None, alias='X-Admin-Token')):
    require_admin(request, code)
    return runtime(request).save_survey(body)


@router.post('/wifi/capture', response_model=WifiStatus)
def capture(body: Capture, request: Request, code: str | None = Header(default=None, alias='X-Admin-Token')):
    require_admin(request, code)
    return runtime(request).capture(body)
