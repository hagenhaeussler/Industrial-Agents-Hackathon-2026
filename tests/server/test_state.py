from concurrent.futures import ThreadPoolExecutor

import pytest

from server.errors import ServiceError
from server.state import StateStore


@pytest.fixture
def store(tmp_path):
    state = StateStore(tmp_path)
    state.initialize()
    return state


def admin(store):
    return store.create_session('test-building', 'desk', 'admin')['session_id']


def proposal(store, sid, version=0):
    return store.propose(sid, {'action': 'close', 'target': 'lift'}, version, 'Close lift', {})['proposal_id']


def test_parallel_double_commit_and_restart(store):
    sid = admin(store)
    pid = proposal(store, sid)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: store.commit(sid, pid, op_id='stable-operation'), range(4)))
    assert sum(created for _, created in results) == 1
    assert len({event['event_id'] for event, _ in results}) == 1
    reopened = StateStore(store.directory)
    reopened.initialize()
    assert len(reopened.events('test-building')) == 1
    assert reopened.get_session(sid)['role'] == 'admin'
    assert reopened.commit(sid, pid)[0] == results[0][0]


def test_stale_preview_undo_and_roles(store):
    sid = admin(store)
    first, stale = proposal(store, sid), proposal(store, sid)
    event, _ = store.commit(sid, first)
    with pytest.raises(ServiceError, match='fresh preview') as exc:
        store.commit(sid, stale)
    assert exc.value.code == 'version_conflict'
    undone, created = store.undo(sid, event['event_id'], op_id='undo-once')
    assert created and undone['undoes'] == event['event_id']
    assert store.undo(sid, op_id='undo-once') == (undone, False)
    with pytest.raises(ServiceError, match='already been undone'):
        store.undo(sid, event['event_id'])
    navigator = store.create_session('test-building', 'phone', 'navigator')['session_id']
    with pytest.raises(ServiceError) as exc:
        store.commit(navigator, first)
    assert exc.value.code == 'forbidden'
    with pytest.raises(ServiceError, match='Unsupported session fields'):
        store.update_session(navigator, {'role': 'admin'})


def test_tour_revisions_and_compare_and_swap(store):
    sid = admin(store)
    first = store.save_tour(sid, {'stops': [{'stop_id': 's1', 'status': 'pending'}]})
    second = store.save_tour(sid, {**first, 'stops': [{'stop_id': 's1', 'status': 'collected'}]}, expected_revision=1)
    assert second['revision'] == 2
    with pytest.raises(ServiceError) as exc:
        store.save_tour(sid, first, expected_revision=1)
    assert exc.value.code == 'version_conflict'
    reopened = StateStore(store.directory)
    assert reopened.get_tour(first['tour_id'])['stops'][0]['status'] == 'collected'


def test_reset_archives_and_operation_id_cannot_target_another_proposal(store):
    sid = admin(store)
    event, _ = store.commit(sid, proposal(store, sid), op_id='one')
    with pytest.raises(ServiceError, match='different proposal'):
        store.commit(sid, proposal(store, sid, 1), op_id='one')
    store.reset('test-building')
    assert store.version('test-building') == 0
    assert store.events('test-building') == []
    new_event, _ = store.commit(sid, proposal(store, sid), op_id='two')
    assert new_event['building_version'] == 1
    assert new_event['event_id'] == event['event_id'] == 'evt-1'


def test_parallel_preview_retry_is_idempotent_and_rejects_different_payload(store):
    sid = admin(store)
    edit = {'action': 'close', 'target': 'lift'}
    with ThreadPoolExecutor(max_workers=4) as pool:
        previews = list(pool.map(lambda _: store.propose(sid, edit, 0, 'Close lift', {}, op_id='preview-once'), range(4)))
    assert len({preview['proposal_id'] for preview in previews}) == 1
    with pytest.raises(ServiceError, match='different preview'):
        store.propose(sid, {'action': 'open', 'target': 'lift'}, 0, 'Open lift', {}, op_id='preview-once')
    other_admin = admin(store)
    with pytest.raises(ServiceError, match='different preview'):
        store.propose(other_admin, edit, 0, 'Close lift', {}, op_id='preview-once')
    assert store.events('test-building') == []


def test_expired_preview_cannot_commit_or_be_reused(store, monkeypatch):
    from datetime import datetime, timezone
    import server.state as state_module

    sid = admin(store)
    preview = store.propose(sid, {'action': 'close', 'target': 'lift'}, 0, 'Close lift', {}, op_id='expired-preview')
    expiry = '2026-10-24T20:00:00+00:00'
    with store.connect(write=True) as db:
        db.execute('UPDATE proposals SET expires_at=? WHERE proposal_id=?', (expiry, preview['proposal_id']))

    class ExpirationInstant(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 24, 20, tzinfo=timezone.utc)

    monkeypatch.setattr(state_module, 'datetime', ExpirationInstant)
    with pytest.raises(ServiceError, match='expired') as exc:
        store.commit(sid, preview['proposal_id'])
    assert exc.value.code == 'version_conflict'
    with pytest.raises(ServiceError, match='expired'):
        store.propose(sid, preview['edit'], 0, 'Close lift', {}, op_id='expired-preview')
    assert store.version('test-building') == 0
    assert store.events('test-building') == []


def test_parallel_tour_updates_allow_only_one_expected_revision(store):
    sid = admin(store)
    first = store.save_tour(sid, {'stops': []})

    def save(_):
        try:
            return store.save_tour(sid, first, expected_revision=1)
        except ServiceError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(save, range(4)))
    assert sum(isinstance(result, dict) for result in results) == 1
    assert results.count('version_conflict') == 3
    assert store.get_tour(first['tour_id'])['revision'] == 2


def test_tours_and_markers_cannot_move_to_another_building(store):
    sid = admin(store)
    other_sid = store.create_session('other-building', 'phone', 'navigator')['session_id']
    tour = store.save_tour(sid, {'stops': []})
    with pytest.raises(ServiceError, match='different building'):
        store.save_tour(other_sid, tour, expected_revision=1)
    assert store.get_tour(tour['tour_id'])['building_id'] == 'test-building'
    assert store.get_tour(tour['tour_id'])['revision'] == 1
    marker = {'marker_id': 'fixed-marker', 'building_id': 'test-building', 'label': 'Entry'}
    store.put_marker(marker)
    with pytest.raises(ServiceError, match='different building'):
        store.put_marker({**marker, 'building_id': 'other-building'})
    assert store.markers('test-building') == [marker]
    assert store.markers('other-building') == []
    assert store.get_marker(marker['marker_id']) == marker


def test_reset_invalidates_previews_but_preserves_archived_history_and_sessions(store):
    sid = admin(store)
    event, _ = store.commit(sid, proposal(store, sid), op_id='before-reset')
    stale = proposal(store, sid, 1)
    store.reset('test-building')
    with pytest.raises(ServiceError, match='Proposal not found'):
        store.commit(sid, stale)
    assert store.get_session(sid)['building_id'] == 'test-building'
    assert store.version('test-building') == 0
    with store.connect() as db:
        archived = db.execute('SELECT archived FROM events WHERE event_id=?', (event['event_id'],)).fetchone()[0]
    assert archived == 1
    next_proposal = proposal(store, sid)
    with pytest.raises(ServiceError, match='different proposal'):
        store.commit(sid, next_proposal, op_id='before-reset')
    next_event, created = store.commit(sid, next_proposal, op_id='after-reset')
    assert created and next_event['building_version'] == 1
    assert store.events('test-building') == [next_event]


def test_server_fixtures_use_real_geometry_without_question_labels(tmp_path, monkeypatch):
    import importlib.util
    import json
    from pathlib import Path

    from shapely.geometry import Point
    from starter_agent.building_map import BuildingMap, outline

    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location('server_fixture_generator', root / 'scripts/generate_server_fixtures.py')
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    original_read_text = Path.read_text

    def no_questions(path, *args, **kwargs):
        assert not path.name.startswith('questions'), 'Fixtures must not read question labels.'
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'read_text', no_questions)
    building_path = root / 'data/dev/proc-factory-dev-003'
    payloads = generator.generate(building_path, tmp_path)
    building = BuildingMap.load(building_path)
    session = payloads['session.json']
    space = building.spaces[session['position']['space_id']]
    assert session['position']['floor_id'] == space['floor_id']
    assert outline(space['polygon']).covers(Point(session['position']['point']))
    event = payloads['events_close_lift.json']['events'][0]
    assert building.connectors[event['edit']['target']]['kind'] == 'lift'
    building.set_closed(event['edit']['target'], True)
    assert event['edit']['target'] in building.closed
    for name, body in payloads.items():
        assert body['_fixture']['contract'] == 'C2'
        assert 'not live server state' in body['_fixture']['kind']
        assert json.loads((tmp_path / name).read_text()) == body


def test_generated_identifier_formats_follow_c1():
    import re
    import uuid
    from server.state import identifier

    formats = {'session': r'[a-f0-9]{32}', 'tour': r'[a-z2-7]{10}',
               'req': r'req_[a-z2-7]{12}', 'proposal': r'prp_[a-z2-7]{12}', 'marker': r'mk_[a-z2-7]{8}'}
    for kind, pattern in formats.items():
        samples = {identifier(kind) for _ in range(25)}
        assert len(samples) == 25
        assert all(re.fullmatch(pattern, sample) for sample in samples)
    assert uuid.UUID(identifier('session')).version == 4
    assert uuid.UUID(identifier('op')).version == 4


def test_public_event_ids_are_scoped_to_building_and_reset_generation(store):
    first_sid = admin(store)
    other_sid = store.create_session('other-building', 'desk', 'admin')['session_id']
    first, _ = store.commit(first_sid, proposal(store, first_sid))
    other, _ = store.commit(other_sid, proposal(store, other_sid))
    assert first['event_id'] == other['event_id'] == 'evt-1'
    first_undo, _ = store.undo(first_sid, op_id='first-building-undo')
    other_undo, _ = store.undo(other_sid)
    assert first_undo['event_id'] == other_undo['event_id'] == 'evt-2'
    assert other_undo['building_id'] == 'other-building'
    assert other_undo['undoes'] == other['event_id']
    with pytest.raises(ServiceError, match='different or archived'):
        store.undo(other_sid, op_id='first-building-undo')
    store.reset('test-building')
    replacement, _ = store.commit(first_sid, proposal(store, first_sid))
    assert replacement['event_id'] == 'evt-1'
    assert 'row_id' not in replacement
    with store.connect() as db:
        rows = list(db.execute('SELECT event_id, archived FROM events WHERE building_id=? ORDER BY row_id', ('test-building',)))
    assert [(row['event_id'], row['archived']) for row in rows] == [('evt-1', 1), ('evt-2', 1), ('evt-1', 0)]


def test_schema_v1_migration_preserves_history_and_restart_idempotence(tmp_path):
    import sqlite3

    path = tmp_path / 'tyb.sqlite3'
    with sqlite3.connect(path) as db:
        db.executescript('''
            CREATE TABLE schema_version(version INTEGER PRIMARY KEY);
            INSERT INTO schema_version VALUES(1);
            CREATE TABLE events(
                building_id TEXT NOT NULL, building_version INTEGER NOT NULL,
                event_id TEXT PRIMARY KEY, kind TEXT NOT NULL, edit_json TEXT NOT NULL,
                undoes TEXT, op_id TEXT UNIQUE, proposal_id TEXT UNIQUE, session_id TEXT NOT NULL,
                author_role TEXT NOT NULL, summary TEXT NOT NULL, created_at TEXT NOT NULL,
                archived INTEGER NOT NULL DEFAULT 0);
        ''')
        db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                   ('test-building', 1, 'legacy-event', 'close', '{"action":"close","target":"lift"}', None,
                    'legacy-operation', 'legacy-proposal', 'legacy-session', 'admin', 'Close lift', '2026-10-24T20:00:00Z', 0))
    migrated = StateStore(tmp_path)
    migrated.initialize()
    assert migrated.events('test-building')[0]['event_id'] == 'legacy-event'
    sid = admin(migrated)
    undo, created = migrated.undo(sid, event_id='legacy-event', op_id='migration-undo')
    assert created and undo['event_id'] == 'evt-2'
    assert undo['undoes'] == 'legacy-event'
    reopened = StateStore(tmp_path)
    reopened.initialize()
    assert reopened.undo(sid, op_id='migration-undo') == (undo, False)
    with reopened.connect() as db:
        assert [row[0] for row in db.execute('SELECT version FROM schema_version')] == [2]
        assert 'row_id' in {row['name'] for row in db.execute('PRAGMA table_info(events)')}
    reopened.reset('test-building')
    new, _ = reopened.commit(sid, proposal(reopened, sid))
    assert new['event_id'] == 'evt-1'
