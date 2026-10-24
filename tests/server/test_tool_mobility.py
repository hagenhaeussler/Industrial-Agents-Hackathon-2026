"""Shared-session mobility and explicit spatial closure transport (CR-L-1/2)."""
import json

import pytest

from server.buildings import BuildingCatalog
from server.config import REPO_ROOT, Settings
from server.service import PlatformService
from server.state import StateStore
from server.tools import ToolRegistry


@pytest.fixture
def platform(tmp_path):
    settings = Settings(state_dir=tmp_path / 'state', hero_dir=tmp_path / 'hero')
    store = StateStore(settings.state_dir)
    store.initialize()
    service = PlatformService(BuildingCatalog(settings), store)
    raw = json.loads((REPO_ROOT / 'data/dev/proc-factory-dev-003/building.json').read_text())
    lift = next(item for item in raw['vertical_connectors'] if item['kind'] == 'lift')
    stairs = next(item for item in raw['vertical_connectors'] if item['kind'] == 'stairs')
    session = store.create_session(raw['building']['id'], 'desk', 'navigator')
    sid = session['session_id']
    store.update_session(sid, {'position': {'space_id': lift['space_ids'][0], 'source': 'desk'}})
    return service, ToolRegistry(service), sid, lift, stairs, raw


@pytest.mark.parametrize('name', ['route', 'plan_tour'])
def test_affirmative_mobility_survives_next_tool_and_phone_handoff(platform, name):
    service, tools, sid, lift, stairs, raw = platform
    args = {'destination': lift['space_ids'][1]} if name == 'route' else {'items': lift['space_ids'][1]}
    response = tools.call(name, sid, {**args, 'step_free': True})
    assert response['ok'], response
    session = service.store.get_session(sid)
    assert session['profile'] == 'wheelchair'
    assert session['constraints']['step_free'] is True
    second = tools.call('route', sid, {'destination': lift['space_ids'][1]})
    assert second['ok'] and second['result']['constraints']['step_free'] is True
    tour = service.create_tour(sid, [lift['space_ids'][1]])
    assert tour['mobility_profile'] == 'wheelchair'
    assert tour['constraints']['step_free'] is True


def test_explicit_route_width_persists_without_erasing_other_constraints(platform):
    service, tools, sid, lift, stairs, raw = platform
    service.store.update_session(sid, {'constraints': {'closed': [stairs['id']]}})
    response = tools.call('route', sid, {'destination': lift['space_ids'][1], 'min_door_width_m': 0.8})
    assert response['ok'], response
    stored = service.store.get_session(sid)
    assert stored['constraints']['min_door_width_m'] == 0.8
    assert stored['constraints']['closed'] == [stairs['id']]
    next_route = tools.call('route', sid, {'destination': lift['space_ids'][1]})
    assert next_route['result']['constraints']['min_door_width_m'] == 0.8


@pytest.mark.parametrize('profile', ['wheelchair', 'pram', 'trolley'])
def test_negative_argument_never_downgrades_existing_mobility(platform, profile):
    service, tools, sid, lift, stairs, raw = platform
    service.store.update_session(sid, {'profile': profile, 'constraints': {'step_free': True}})
    response = tools.call('route', sid, {'destination': lift['space_ids'][1], 'step_free': False})
    assert response['ok'], response
    stored = service.store.get_session(sid)
    assert stored['profile'] == profile and stored['constraints']['step_free'] is True
    assert response['result']['constraints']['step_free'] is True


@pytest.mark.parametrize('name,args', [
    ('route', {'destination': 'Definitely absent place', 'step_free': True}),
    ('route', {'destination': 'missing', 'step_free': True, 'min_door_width_m': -1}),
    ('plan_tour', {'items': 'Definitely absent place', 'step_free': True}),
    ('plan_tour', {'items': ', ,', 'step_free': True}),
])
def test_invalid_intentions_do_not_change_session(platform, name, args):
    service, tools, sid, *_ = platform
    before = service.store.get_session(sid)
    response = tools.call(name, sid, args)
    assert response['ok'] is False
    assert service.store.get_session(sid) == before


def test_ambiguous_tour_item_does_not_persist_mobility(platform):
    service, tools, sid, lift, stairs, raw = platform
    from collections import Counter
    types = Counter(asset['type'] for asset in raw['assets'])
    repeated = next(kind.replace('_', ' ') for kind, count in types.items() if count > 1)
    before = service.store.get_session(sid)
    response = tools.call('plan_tour', sid, {'items': repeated, 'step_free': True})
    assert not response['ok'] and response['error']['code'] == 'ambiguous'
    assert service.store.get_session(sid) == before


def test_valid_but_unreachable_request_keeps_affirmative_mobility(platform):
    service, tools, sid, lift, stairs, raw = platform
    service.store.update_session(sid, {'constraints': {'closed': [lift['id']]}})
    response = tools.call('route', sid, {'destination': lift['space_ids'][1], 'step_free': True})
    assert not response['ok'] and response['error']['code'] == 'no_route'
    stored = service.store.get_session(sid)
    assert stored['profile'] == 'wheelchair' and stored['constraints']['step_free'] is True


def spatial_args(lift, closure=None):
    args = {'kind': 'step_free_reachable_count', 'target': lift['space_ids'][0], 'floor': lift['floor_ids'][1]}
    if closure is not None:
        args['second_target'] = closure
    return args


def test_empty_closure_counts_with_no_artificial_clarification(platform):
    service, tools, sid, lift, *_ = platform
    response = tools.call('spatial_query', sid, spatial_args(lift))
    assert response['ok'] and response['result']['value'] > 0, response
    assert service.current(service.store.get_session(sid)['building_id']).core.closed == set()


def test_single_closure_uses_existing_session_constraint(platform):
    service, tools, sid, lift, stairs, raw = platform
    service.store.update_session(sid, {'constraints': {'closed': [lift['id']]}})
    response = tools.call('spatial_query', sid, spatial_args(lift))
    assert response['ok'], response
    assert response['result']['value'] == 0
    assert service.current(raw['building']['id']).core.closed == set()


def test_multiple_closures_apply_without_mutating_the_live_building(platform):
    service, tools, sid, lift, stairs, raw = platform
    service.store.update_session(sid, {'constraints': {'closed': [stairs['id']]}})
    stairs_only = tools.call('spatial_query', sid, spatial_args(lift))
    assert stairs_only['ok'] and stairs_only['result']['value'] > 0
    service.store.update_session(sid, {'constraints': {'closed': [stairs['id'], lift['id']]}})
    both = tools.call('spatial_query', sid, spatial_args(lift))
    assert both['ok'], both
    assert both['result']['value'] == 0
    assert service.current(raw['building']['id']).core.closed == set()
    assert service.current(raw['building']['id']).closed == set()


def test_explicit_closure_name_unions_with_session_and_does_not_persist(platform):
    service, tools, sid, lift, stairs, raw = platform
    service.store.update_session(sid, {'constraints': {'closed': [stairs['id']]}})
    before = service.store.get_session(sid)
    response = tools.call('spatial_query', sid, spatial_args(lift, lift['name']))
    assert response['ok'] and response['result']['value'] == 0, response
    assert service.store.get_session(sid) == before
    assert service.current(raw['building']['id']).core.closed == set()


def test_building_closures_preserved_but_session_closures_never_leak(platform):
    service, tools, sid, lift, stairs, raw = platform
    admin = service.store.create_session(raw['building']['id'], 'desk', 'admin')['session_id']
    preview = service.propose_edit(admin, {'action': 'close', 'target': stairs['id']})
    service.commit_edit(admin, preview['proposal_id'])
    service.store.update_session(sid, {'constraints': {'closed': [lift['id']]}})
    response = tools.call('spatial_query', sid, spatial_args(lift))
    assert response['ok'] and response['result']['value'] == 0, response
    current = service.current(raw['building']['id'])
    assert current.core.closed == {stairs['id']}
    assert current.closed == {stairs['id']}


@pytest.mark.parametrize('source', ['explicit', 'session'])
def test_unknown_closure_ids_are_domain_failures_with_no_state_leak(platform, source):
    service, tools, sid, lift, stairs, raw = platform
    args = spatial_args(lift)
    if source == 'explicit':
        args['second_target'] = 'not-a-real-connector-9999'
    else:
        service.store.update_session(sid, {'constraints': {'closed': ['not-a-real-connector-9999']}})
    before = service.store.get_session(sid)
    response = tools.call('spatial_query', sid, args)
    assert not response['ok'] and response['error']['code'] in {'not_found', 'invalid_args'}
    assert service.store.get_session(sid) == before
    assert service.current(raw['building']['id']).core.closed == set()


@pytest.mark.parametrize('name,args', [
    ('route', {'destination': 'unused', 'step_free': True}),
    ('plan_tour', {'items': 'unused', 'step_free': True}),
])
def test_missing_start_position_does_not_persist_mobility(platform, name, args):
    service, tools, sid, *_ = platform
    service.store.update_session(sid, {'position': None})
    before = service.store.get_session(sid)
    response = tools.call(name, sid, args)
    assert not response['ok'] and response['error']['code'] == 'invalid_args'
    assert service.store.get_session(sid) == before


def test_empty_optional_closure_uses_the_zero_closure_count(platform):
    service, tools, sid, lift, *_ = platform
    response = tools.call('spatial_query', sid, spatial_args(lift, '  '))
    assert response['ok'] and response['result']['value'] > 0, response


def test_ambiguous_spare_drill_candidates_include_full_display_name(platform, tmp_path):
    service, tools, sid, lift, stairs, raw = platform
    import copy
    fixture = copy.deepcopy(raw)
    fixture['building']['id'] = 'tool-ambiguity-test'
    first = fixture['assets'][0]
    second = next(asset for asset in fixture['assets'] if asset['floor_id'] != first['floor_id'])
    first['name'] = second['name'] = 'Spare drill'
    (service.store.directory / 'uploads' / 'ambiguity.json').write_text(json.dumps(fixture))
    sid = service.store.create_session(fixture['building']['id'], 'desk', 'navigator')['session_id']
    service.store.update_session(sid, {'position': {'space_id': first['space_id'], 'source': 'desk'}})
    before = service.store.get_session(sid)
    response = tools.call('plan_tour', sid, {'items': 'Spare drill', 'step_free': True})
    assert not response['ok'] and response['error']['code'] == 'ambiguous'
    candidates = response['error']['candidates']
    assert len(candidates) == 2
    assert all(candidate['name'] == candidate['label'] and '(' in candidate['name'] for candidate in candidates)
    assert {candidate['id'] for candidate in candidates} == {first['id'], second['id']}
    assert service.store.get_session(sid) == before


@pytest.mark.parametrize('second_args', [{'min_door_width_m': 0.8}, {'step_free': False}])
def test_simultaneous_tools_merge_mobility_against_latest_session(platform, monkeypatch, second_args):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    service, tools, sid, lift, *_ = platform
    original = tools._persist_mobility
    old_snapshot_loaded = threading.Event()
    step_free_saved = threading.Event()

    def ordered(session, args):
        if args.get('step_free') is not True:
            old_snapshot_loaded.set()
            assert step_free_saved.wait(10)
        result = original(session, args)
        if args.get('step_free') is True:
            step_free_saved.set()
        return result

    monkeypatch.setattr(tools, '_persist_mobility', ordered)
    with ThreadPoolExecutor(max_workers=2) as pool:
        second = pool.submit(tools.call, 'route', sid, {'destination': lift['space_ids'][1], **second_args})
        assert old_snapshot_loaded.wait(10)
        affirmative = pool.submit(tools.call, 'route', sid, {'destination': lift['space_ids'][1], 'step_free': True})
        affirmative_result, second_result = affirmative.result(), second.result()
    assert affirmative_result['ok'] and second_result['ok']
    assert second_result['result']['constraints']['step_free'] is True
    stored = service.store.get_session(sid)
    assert stored['profile'] == 'wheelchair'
    assert stored['constraints']['step_free'] is True
    if 'min_door_width_m' in second_args:
        assert stored['constraints']['min_door_width_m'] == 0.8


@pytest.mark.parametrize('closure_count', [0, 1, 2])
def test_spatial_transport_passes_the_complete_closure_list(platform, monkeypatch, closure_count):
    from server import core_adapter
    service, tools, sid, lift, stairs, raw = platform
    closures = [stairs['id'], lift['id']][:closure_count]
    service.store.update_session(sid, {'constraints': {'closed': closures}})
    original_lookup = core_adapter.core_function
    real_solve = original_lookup('spatial', 'solve')
    received = []

    def solve(building, kind, inputs):
        received.append(inputs['closed'])
        return real_solve(building, kind, inputs)

    def lookup(module, name):
        return solve if (module, name) == ('spatial', 'solve') else original_lookup(module, name)

    monkeypatch.setattr(core_adapter, 'core_function', lookup)
    response = tools.call('spatial_query', sid, spatial_args(lift))
    assert response['ok'], response
    assert received == [sorted(closures)]
    assert service.current(raw['building']['id']).core.closed == set()
