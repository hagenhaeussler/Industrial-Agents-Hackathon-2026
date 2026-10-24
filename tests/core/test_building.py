import copy
from core.building import load_building, content_hash

PATH = "data/dev/proc-factory-dev-003"


def test_hash_and_independent_materializations():
    first = load_building(PATH)
    original = copy.deepcopy(first.data)
    first.graph(False)
    second = load_building(PATH)
    assert second.content_hash == content_hash(original)
    assert second.version == 0
    first.closed.add(next(iter(first.spaces)))
    first.data["building"]["name"] = "Edited"
    assert not second.closed
    assert second.data == original


def test_exact_rendered_space_and_asset():
    b = load_building(PATH)
    s = next(iter(b.spaces.values()))
    assert b.resolve_space(f"{s['name']} ({b.floor_name(s['floor_id'])})") == s["id"]
    a = next(iter(b.assets.values()))
    assert b.resolve_space(a["id"]) == a["space_id"]
