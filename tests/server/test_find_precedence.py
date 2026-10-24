"""Cross-kind find precedence: exact matches never tie with fuzzy scores."""
import copy
import json

import pytest

from server import core_adapter
from server.buildings import BuildingCatalog
from server.config import REPO_ROOT, Settings
from server.service import PlatformService
from server.state import StateStore
from server.tools import ToolRegistry


@pytest.fixture(params=['core', 'kit'])
def platform(tmp_path, request, monkeypatch):
    if request.param == 'kit':
        monkeypatch.setattr(core_adapter, 'core_function', lambda module, name: None)
    settings = Settings(state_dir=tmp_path / 'state', hero_dir=tmp_path / 'hero')
    store = StateStore(settings.state_dir)
    store.initialize()
    service = PlatformService(BuildingCatalog(settings), store)
    raw = json.loads((REPO_ROOT / 'data/dev/proc-factory-dev-003/building.json').read_text())
    sid = store.create_session(raw['building']['id'], 'desk', 'navigator')['session_id']
    return service, ToolRegistry(service), sid, raw, request.param


def custom_inventory(platform, mutate):
    service, tools, _, raw, _ = platform
    fixture = copy.deepcopy(raw)
    fixture['building']['id'] = 'find-stage-test'
    mutate(fixture)
    (service.store.directory / 'uploads' / 'find.json').write_text(json.dumps(fixture))
    sid = service.store.create_session(fixture['building']['id'], 'desk', 'navigator')['session_id']
    return sid, fixture


def test_real_cnc_name_beats_fuzzy_room_even_at_the_same_score(platform):
    service, tools, sid, raw, engine = platform
    asset = next(item for item in raw['assets'] if item['name'] == 'CNC mill H-A1-A')
    building = service.current(raw['building']['id'])
    if engine == 'core':
        exact = core_adapter.resolve(building, asset['name'], 'asset')['candidates'][0]
        fuzzy = core_adapter.resolve(building, asset['name'], 'space')['candidates'][0]
        assert exact['why'] == 'exact name/ref' and fuzzy['why'] == 'fuzzy'
        assert exact['score'] == fuzzy['score'] == 1.0  # the reported production collision
    before = service.store.get_session(sid)
    response = tools.call('find', sid, {'query': asset['name']})
    assert response['ok'], response
    assert response['result']['id'] == asset['id']
    assert response['display']['asset_ids'] == [asset['id']]
    assert service.store.get_session(sid) == before


def test_exact_asset_id_beats_another_kinds_equal_name(platform):
    service, tools, *_ = platform
    sid, fixture = custom_inventory(platform, lambda raw: raw['spaces'][1].update(name=raw['assets'][0]['id']))
    response = tools.call('find', sid, {'query': fixture['assets'][0]['id']})
    assert response['ok'], response
    assert response['result']['id'] == fixture['assets'][0]['id']
    assert response['result']['why'] == 'exact ID'


def test_exact_asset_ref_beats_fuzzy_space(platform):
    service, tools, *_ = platform
    def mutate(raw):
        raw['assets'][0]['ref'] = 'Distinct part 4'
        raw['spaces'][1]['name'] = 'Distinct part 4 assembly'
    sid, fixture = custom_inventory(platform, mutate)
    response = tools.call('find', sid, {'query': 'Distinct part 4'})
    assert response['ok'], response
    assert response['result']['id'] == fixture['assets'][0]['id']


def test_full_rendered_asset_label_is_an_exact_match(platform):
    service, tools, sid, raw, _ = platform
    asset = next(item for item in raw['assets'] if item['name'] == 'CNC mill H-A1-A')
    floor = next(item for item in raw['floors'] if item['id'] == asset['floor_id'])
    response = tools.call('find', sid, {'query': f"{asset['name']} ({floor['name']})"})
    assert response['ok'], response
    assert response['result']['id'] == asset['id']


def test_true_exact_ambiguity_across_kinds_remains_a_question(platform):
    service, tools, *_ = platform
    def mutate(raw):
        raw['assets'][0]['name'] = raw['spaces'][1]['name'] = 'Shared landmark'
    sid, fixture = custom_inventory(platform, mutate)
    response = tools.call('find', sid, {'query': 'Shared landmark'})
    assert not response['ok'] and response['error']['code'] == 'ambiguous'
    assert {candidate['id'] for candidate in response['error']['candidates']} == {fixture['assets'][0]['id'], fixture['spaces'][1]['id']}


def test_duplicate_exact_assets_remain_ambiguous(platform):
    service, tools, *_ = platform
    def mutate(raw):
        raw['assets'][0]['name'] = raw['assets'][1]['name'] = 'Spare drill'
    sid, fixture = custom_inventory(platform, mutate)
    response = tools.call('find', sid, {'query': 'Spare drill'})
    assert not response['ok'] and response['error']['code'] == 'ambiguous'
    assert len(response['error']['candidates']) == 2
    assert all(candidate['name'] == candidate['label'] for candidate in response['error']['candidates'])


def test_numeric_names_do_not_guess_between_press_numbers(platform):
    service, tools, *_ = platform
    def mutate(raw):
        raw['assets'] = [dict(raw['assets'][0], id='press-4', name='Press 4'), dict(raw['assets'][1], id='press-14', name='Press 14')]
    sid, fixture = custom_inventory(platform, mutate)
    exact = tools.call('find', sid, {'query': 'Press 4'})
    assert exact['ok'] and exact['result']['id'] == 'press-4'
    absent = tools.call('find', sid, {'query': 'Press 44'})
    assert not absent['ok'] and absent['error']['code'] == 'not_found'


def test_normalized_asset_match_beats_a_higher_scoring_fuzzy_room(platform):
    service, tools, *_ = platform
    def mutate(raw):
        raw['assets'][0]['name'] = 'Blue-widget'
        raw['spaces'][1]['name'] = 'Blue widget storage'
    sid, fixture = custom_inventory(platform, mutate)
    response = tools.call('find', sid, {'query': 'Blue widget'})
    assert response['ok'], response
    assert response['result']['id'] == fixture['assets'][0]['id']
    assert response['result']['why'] == 'normalized'
