"""Validation of untrusted JSON and documented geometry warning behaviour."""

import copy

import pytest

from core.validate import validate_building


@pytest.fixture
def raw():
    return {"building": {"id": "new-未知", "name": "Factory <script>data</script>", "source": "upload", "units": "m"},
            "floors": [{"id": "F", "level": 0, "name": "Ground", "height_m": 3, "elevation_m": 0}],
            "spaces": [{"id": "A", "name": "未知", "floor_id": "F", "type": "room", "room_type": "special_lab",
                        "polygon": [[0, 0], [4, 0], [4, 4], [0, 4]]}],
            "openings": [{"id": "E", "floor_id": "F", "kind": "entrance", "space_ids": ["outside", "A"],
                          "position": [0, 2], "width_m": .9, "step_free": True}],
            "vertical_connectors": [], "assets": []}


def codes(report):
    return {item["code"] for item in report["errors"]}


def test_new_names_and_types_accepted_without_mutation(raw):
    before = copy.deepcopy(raw)
    report = validate_building(raw)
    assert report["ok"] and report["stats"]["entrances"] == 1
    assert raw == before


@pytest.mark.parametrize("value", [None, [], "not json", 12, {}, {"building": []},
                                    {"floors": [None, []], "spaces": [1], "assets": [False]}])
def test_malformed_top_level_always_returns_structured_errors(value):
    report = validate_building(value)
    assert not report["ok"]
    assert report["errors"] and all({"code", "path", "message"} <= e.keys() for e in report["errors"])


def test_missing_references_duplicate_ids_and_units(raw):
    raw["building"]["units"] = "ft"
    raw["spaces"].append(copy.deepcopy(raw["spaces"][0]))
    raw["openings"][0]["space_ids"][1] = "missing"
    raw["spaces"][0]["floor_id"] = "no floor"
    report = validate_building(raw)
    assert {"invalid_units", "duplicate_id", "unknown_space", "unknown_floor"} <= codes(report)


def test_degenerate_and_repairable_geometry(raw):
    raw["spaces"][0]["polygon"] = [[0, 0], [1, 1], [2, 2]]
    assert not validate_building(raw)["ok"]
    raw["spaces"][0]["polygon"] = [[0, 0], [4, 4], [0, 4], [4, 0]]
    report = validate_building(raw)
    assert report["ok"]
    assert "polygon_repaired" in {w["code"] for w in report["warnings"]}


def test_disconnected_rooms_and_boundary_mismatch_are_warnings(raw):
    raw["spaces"].append({**raw["spaces"][0], "id": "B", "polygon": [[10, 0], [14, 0], [14, 4], [10, 4]]})
    raw["openings"][0]["position"] = [2, 2]
    report = validate_building(raw)
    assert report["ok"] and report["stats"]["unreachable_rooms"] == 1
    assert {"unreachable_rooms", "door_off_boundary"} <= {w["code"] for w in report["warnings"]}


def test_no_entrance_errors_for_routing_but_has_display_warning(raw):
    raw["openings"] = []
    report = validate_building(raw)
    assert "no_entrance" in codes(report)
    assert "display_only" in {w["code"] for w in report["warnings"]}


@pytest.mark.parametrize("mutate", [
    lambda r: r["openings"][0].update(kind=[]),
    lambda r: r["openings"][0].update(space_ids=[{}, []]),
    lambda r: r["spaces"][0].update(polygon=[[0, 0], [float("nan"), 2], [3, 4]]),
    lambda r: r["floors"][0].update(height_m=True),
    lambda r: r["floors"][0].update(elevation_m=10 ** 1000),
    lambda r: r.update(vertical_connectors=[{"id": "V", "kind": {}, "name": "Lift", "floor_ids": [], "space_ids": [], "step_free": True}]),
])
def test_nested_malformed_values_do_not_raise(raw, mutate):
    mutate(raw)
    assert not validate_building(raw)["ok"]
