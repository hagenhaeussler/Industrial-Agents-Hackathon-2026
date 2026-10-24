import copy

import pytest

from core.building import load_building
from core.errors import CoreError
from core.routing import route


def simple_building():
    floors = [{"id": "f0", "level": 0, "elevation_m": 0, "name": "Ground"},
              {"id": "f1", "level": 1, "elevation_m": 3, "name": "First floor"}]
    spaces = [{"id": "a", "name": "Start", "room_type": "office", "floor_id": "f0", "polygon": [[0,0],[2,0],[2,3],[0,3]]},
              {"id": "c", "name": "Hall", "room_type": "hall", "floor_id": "f0", "polygon": [[2,0],[4,0],[4,3],[2,3]]},
              {"id": "b", "name": "End", "room_type": "office", "floor_id": "f0", "polygon": [[4,0],[6,0],[6,3],[4,3]]},
              {"id": "up", "name": "Upper", "room_type": "office", "floor_id": "f1", "polygon": [[2,0],[4,0],[4,3],[2,3]]}]
    openings = [{"id": "narrow", "floor_id": "f0", "space_ids": ["a", "c"], "position": [2,1.5], "width_m": .8, "step_free": True, "kind": "door"},
                {"id": "wide", "floor_id": "f0", "space_ids": ["a", "c"], "position": [2,2.5], "width_m": 1.2, "step_free": True, "kind": "door"},
                {"id": "last", "floor_id": "f0", "space_ids": ["c", "b"], "position": [4,1.5], "width_m": 1.2, "step_free": True, "kind": "door"}]
    connectors = [{"id": "stairs", "kind": "stairs", "name": "Main stairs", "space_ids": ["c","up"], "floor_ids": ["f0","f1"], "step_free": False},
                  {"id": "lift", "kind": "lift", "name": "Main lift", "space_ids": ["c","up"], "floor_ids": ["f0","f1"], "step_free": True}]
    return load_building({"building": {"id": "test"}, "floors": floors, "spaces": spaces,
                         "openings": openings, "vertical_connectors": connectors, "assets": []})


def test_parallel_doors_keep_selected_opening_and_width_equality():
    b = simple_building()
    ordinary = route(b, "a", "b")
    wide = route(b, "a", "b", {"min_door_width_m": 1.2})
    assert ordinary["element_path"] == ["narrow", "last"]
    assert wide["element_path"] == ["wide", "last"]
    assert ordinary["space_path"] == ["a", "c", "b"]
    assert ordinary["length_m"] < wide["length_m"]
    assert not route(b, "a", "b", {"min_door_width_m": 1.21})["reachable"]


def test_lift_stairs_and_closure_reasons_never_fall_back_to_stairs():
    b = simple_building()
    assert route(b, "c", "up")["element_path"] == ["stairs"]
    assert route(b, "c", "up", {"step_free": True})["element_path"] == ["lift"]
    closed = route(b, "c", "up", {"step_free": True, "closed": ["lift"]})
    assert not closed["reachable"]
    assert closed["reason"] == "blocked_by_closure"
    assert closed["blocking_ids"] == ["lift"]
    b.closed.add("lift")
    assert route(b, "c", "up")["element_path"] == ["stairs"]
    assert b.closed == {"lift"}


def test_no_transit_spaces_cannot_be_used_but_can_be_endpoints():
    b = simple_building()
    c = {"no_transit_room_types": ["hall"]}
    assert not route(b, "a", "b", c)["reachable"]
    assert route(b, "a", "c", c)["reachable"]


def test_actual_position_changes_geometry_and_cost():
    b = simple_building()
    r = route(b, {"space_id": "a", "point": [1.9, 1.5]}, "b")
    assert r["start_position"] == [1.9, 1.5]
    assert r["segments"][0]["points"][0] == [1.9, 1.5]
    assert r["length_m"] < route(b, "a", "b")["length_m"]
    same = route(b, {"space_id": "a", "point": [.5, 1.5]}, {"space_id": "a", "point": [1.5, 1.5]})
    assert same["length_m"] == 1
    assert same["segments"][0]["points"] == [[.5, 1.5], [1.5, 1.5]]
    with pytest.raises(CoreError):
        route(b, {"space_id": "a", "point": [20, 20]}, "b")


def test_maneuver_costs_and_lengths_match_and_building_stays_immutable():
    b = simple_building()
    raw = copy.deepcopy(b.data)
    result = route(b, "a", "up")
    assert result["maneuvers"][0]["kind"] == "depart"
    assert result["maneuvers"][-1]["kind"] == "arrive"
    assert any(m["kind"] == "take_stairs" for m in result["maneuvers"])
    assert all(len(m["text"]) <= 90 for m in result["maneuvers"])
    assert abs(sum(s["length_m"] for s in result["segments"]) - result["length_m_exact"]) < 1e-9
    assert b.data == raw
