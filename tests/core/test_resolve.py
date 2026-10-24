from core.building import load_building
from core.resolve import resolve


def test_exact_and_type_resolution_and_numeric_safety():
    b = load_building("data/dev/proc-factory-dev-003")
    a = next(iter(b.assets.values()))
    assert resolve(b, a["id"])["candidates"][0]["id"] == a["id"]
    assert resolve(b, a["type"], "asset_type")["status"] == "unique"
    raw = b.data
    raw["assets"] = [dict(a, id="a4", name="Press 4"), dict(a, id="a14", name="Press 14")]
    b = load_building(raw)
    assert resolve(b, "Press 4", "asset")["candidates"][0]["id"] == "a4"
    assert resolve(b, "Press 04", "asset")["candidates"][0]["id"] == "a4"
    assert resolve(b, "Press 44", "asset")["status"] == "none"
    assert resolve(b, "Press", "asset")["status"] == "ambiguous"
