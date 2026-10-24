"""A conflicting source flag must never turn physical stairs into a step-free route."""

import copy

import networkx as nx
import pytest

from core.building import load_building
from core.routing import route
from core.spatial import Constraints, SpatialCore, solve
from core.validate import validate_building
from starter_agent.building_map import MapError


def contradictory_stair_building():
    return {
        "building": {"id": "conflicting-stair", "name": "Conflicting source flag", "source": "test", "units": "m"},
        "floors": [{"id": "f0", "name": "Ground", "level": 0, "elevation_m": 0, "height_m": 3},
                   {"id": "f1", "name": "First", "level": 1, "elevation_m": 3, "height_m": 3}],
        "spaces": [{"id": sid, "floor_id": fid, "name": sid, "type": "room", "room_type": "office",
                    "polygon": [[0, 0], [4, 0], [4, 4], [0, 4]]}
                   for sid, fid in [("down", "f0"), ("up", "f1")]],
        "openings": [{"id": "entrance", "floor_id": "f0", "space_ids": ["outside", "down"],
                      "kind": "door", "position": [0, 2], "width_m": 1.2, "step_free": True}],
        "vertical_connectors": [{"id": kind, "name": kind, "kind": kind, "step_free": True,
                                 "floor_ids": ["f0", "f1"], "space_ids": ["down", "up"]}
                                for kind in ("stairs", "lift")],
        "assets": [],
    }


def test_core_graph_keeps_parallel_lift_but_excludes_flagged_stairs():
    raw = contradictory_stair_building()
    assert validate_building(raw)["ok"]
    building = load_building(raw)
    assert len(building.graph(False)["down"]["up"]) == 2
    edges = building.graph(True)["down"]["up"].values()
    assert [edge["via"] for edge in edges] == ["lift"]
    building.closed.add("lift")
    assert not nx.has_path(building.graph(True), "down", "up")
    # The inherited kit route is also constrained by the Building graph override.
    with pytest.raises(MapError, match="No step-free route"):
        building.route("down", "up", step_free=True)
    assert building.data == raw


def test_public_route_never_downgrades_to_flagged_stairs_after_lift_closure():
    building = load_building(contradictory_stair_building())
    pristine = copy.deepcopy(building.data)
    assert route(building, "down", "up")["element_path"] == ["stairs"]
    assert route(building, "down", "up", {"step_free": True})["element_path"] == ["lift"]
    result = route(building, "down", "up", {"step_free": True, "closed": ["lift"]})
    assert result["reachable"] is False
    assert result["reason"] == "blocked_by_closure"
    assert result["blocking_ids"] == ["lift"]
    building.closed.add("lift")
    assert not route(building, "down", "up", {"step_free": True})["reachable"]
    assert route(building, "down", "up")["element_path"] == ["stairs"]
    assert building.data == pristine


def test_spatial_graph_and_reachability_solvers_exclude_flagged_stairs():
    core = SpatialCore(contradictory_stair_building())
    assert [edge["via"] for edge in core.constrained_graph(Constraints(True))["down"]["up"].values()] == ["lift"]
    assert core.reachable_rooms("down", "f1", Constraints(True, closed={"lift"})) == []
    result = solve(core, "step_free_reachable_count", {"start": "down", "floor_id": "f1", "closed": "lift"})
    assert result == {"value": 0, "space_ids": []}
    core.closed.add("lift")
    result = solve(core, "wide_delivery_count", {"start": "down", "floor_id": "f1", "min_width": .9})
    assert result == {"value": 0, "space_ids": []}
    result = solve(core, "route_step_free", {"start": "down", "destination": "up"})
    assert result["reachable"] is False
