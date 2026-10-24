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
    assert new_event['event_id'] != event['event_id']
