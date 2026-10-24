"""Focused regressions for kit 1.1 spatial solvers and pure hypothetical edits."""

import copy
import math

import networkx as nx
import pytest

from core.building import Building, load_building
from core.errors import CoreError
from core.spatial import Constraints, SpatialCore, constrained_graph, shared_wall_midpoint, solve
from starter_agent.building_map import MapError


def fixture():
    def room(sid, floor, x, y, type="room", room_type="office"):
        return {"id": sid, "floor_id": floor, "type": type, "room_type": room_type,
                "name": sid, "ref": sid, "polygon": [[x, y], [x + 4, y], [x + 4, y + 4], [x, y + 4]]}

    def door(oid, floor, a, b, position, width=1.2):
        return {"id": oid, "floor_id": floor, "space_ids": [a, b], "position": position,
                "width_m": width, "step_free": True, "kind": "door"}

    return {"building": {"id": "unit", "name": "Unit building", "source": "procedural"},
            "floors": [{"id": "f0", "level": 0, "name": "Ground floor", "elevation_m": 0},
                       {"id": "f1", "level": 1, "name": "Floor 1", "elevation_m": 3},
                       {"id": "f3", "level": 3, "name": "Floor 3", "elevation_m": 10}],
            "spaces": [room("a", "f0", 0, 0), room("b", "f0", 4.2, 0),
                       room("h", "f0", 0, 4, "hall", "lobby"), room("l0", "f0", 4.2, 4, "lift", "lift"),
                       room("c", "f1", 0, 0), room("l1", "f1", 4.2, 4, "lift", "lift"),
                       room("d", "f3", 0, 0), room("l3", "f3", 4.2, 4, "lift", "lift")],
            "openings": [door("entrance", "f0", "outside", "a", [0, 2]), door("ab", "f0", "a", "b", [4.1, 2], .9),
                         door("ah", "f0", "a", "h", [2, 4]), door("hl", "f0", "h", "l0", [4.1, 6], 1.1),
                         door("lc", "f1", "l1", "c", [4, 4]), door("ld", "f3", "l3", "d", [4, 4])],
            "vertical_connectors": [{"id": "stairs", "name": "Stairs", "kind": "stairs", "step_free": False,
                                     "floor_ids": ["f3", "f0", "f1"], "space_ids": ["l3", "l0", "l1"]},
                                    {"id": "lift", "name": "Lift", "kind": "lift", "step_free": True,
                                     "floor_ids": ["f0", "f1", "f3"], "space_ids": ["l0", "l1", "l3"]}],
            "assets": [{"id": "desk1", "type": "desk", "name": "Desk", "floor_id": "f0", "space_id": "b", "position": [6, 2]}]}


def test_area_shared_wall_centroid_and_skipped_level():
    core = SpatialCore(fixture())
    assert set(core.shared_wall_neighbors("a")) == {"b", "h"}
    assert core.floor_area_total("f0", "lobby") == 16
    assert core.largest_room("f0", "lobby")["space_id"] == "h"
    assert core.distance_3d("a", "d") == 10
    assert core.stacked_room("c", "above")["space_id"] == "d"
    assert core.stacked_room("d", "below")["space_id"] == "c"
    raw = fixture()
    raw["spaces"][0]["polygon"] = [[0, 0], [4, 0], [4, 1], [1, 1], [1, 4], [0, 4]]
    assert SpatialCore(raw).distance_3d("a", "c") == pytest.approx(math.sqrt(2 * (2 - 19 / 14) ** 2 + 9))


def test_parallel_connectors_kit_1_1_costs_and_closures():
    core = SpatialCore(fixture())
    graph = core.constrained_graph()
    assert len(graph["l0"]["l1"]) == 2
    assert nx.shortest_path_length(graph, "l0", "l1", weight="weight") == 6
    graph = core.constrained_graph(Constraints(step_free=True))
    assert nx.shortest_path_length(graph, "l0", "l1", weight="weight") == 18
    # Every pair of lift stops gets a direct edge: one fixed boarding cost.
    assert nx.shortest_path_length(graph, "l0", "l3", weight="weight") == 25
    assert nx.shortest_path_length(graph, "l1", "l3", weight="weight") == 22
    graph = core.constrained_graph(Constraints(step_free=True, closed={"lift"}))
    assert not nx.has_path(graph, "a", "c")
    core.closed.add("lift")
    assert core.reachable_rooms("a", "f1", Constraints(True)) == []


def test_reachable_count_accepts_single_and_live_list_closures():
    b = load_building(fixture())
    args = {"start":"a", "floor_id":"f1"}
    assert solve(b,"step_free_reachable_count",{**args,"closed":[]})['value']==1
    single = solve(b,"step_free_reachable_count",{**args,"closed":"lift"})
    assert single == solve(b,"step_free_reachable_count",{**args,"closed":["lift"]})
    assert solve(b,"step_free_reachable_count",{**args,"closed":["lift","ab"]})['value']==0
    with pytest.raises(CoreError):
        solve(b,"step_free_reachable_count",{**args,"closed":[3]})


def test_width_threshold_closures_and_no_transit_edges():
    core = SpatialCore(fixture())
    assert set(core.reachable_rooms("a", "f0", Constraints(True, .9))) == {"a", "b"}
    assert core.reachable_rooms("a", "f0", Constraints(True, 1)) == ["a"]
    for closed in ("ab", "b"):
        assert "b" not in core.reachable_rooms("a", "f0", Constraints(closed={closed}))
    graph = constrained_graph(core, {"no_transit_room_types": ["lobby"]})
    assert not nx.has_path(graph, "a", "c")
    assert all(edge.get("space") != "h" for *_, edge in graph.edges(data=True))


def test_element_paths_include_each_stair_flight_and_both_doors():
    core = SpatialCore(fixture())
    result = core.constrained_route("a", "d")
    assert result["element_path"] == ["ah", "hl", "stairs", "stairs", "ld"]
    assert result["space_path"] == ["a", "h", "l0", "l1", "l3", "d"]
    assert core.constrained_route("a", "desk1")["element_path"] == ["ab"]


def test_two_doors_between_rooms_stay_distinct():
    raw = fixture()
    raw["openings"].append({**raw["openings"][1], "id": "ab2", "position": [4.1, 3]})
    core = SpatialCore(raw)
    assert {"door:ab", "door:ab2"} <= core.constrained_graph().nodes
    closed = core.constrained_route("a", "b", Constraints(closed={"ab"}))
    assert closed["element_path"] == ["ab2"]


def test_errand_pickup_uses_route_distance_and_allows_stairs():
    core = SpatialCore(fixture())
    result = core.errand("a", "desk", "f1", "office")
    assert (result["via"], result["target"]) == ("b", "c")
    expected = core.constrained_route("a", "b")["length_m"] + core.constrained_route("b", "c")["length_m"]
    assert result["length_m"] == expected
    for closed in ("a", "c"):
        core = SpatialCore(fixture())
        core.closed.add(closed)
        with pytest.raises(MapError, match="closed"):
            core.errand("a", "desk", "f1", "office")


def test_whatif_is_pure_symmetric_and_does_not_pollute_base_walk_cache():
    raw = fixture()
    raw["openings"] = [opening for opening in raw["openings"] if opening["id"] != "ab"]
    core = SpatialCore(raw)
    pristine = copy.deepcopy(core.data)
    result = core.compare_exit_distances_with_door("a", "b", "f0")
    assert result["improved_space_ids"] == ["b"]
    assert core.compare_exit_distances_with_door("b", "a", "f0") == result
    assert core.data == pristine
    assert core.closed == set()
    # A newly loaded base must still see b as disconnected after a what-if.
    fresh = SpatialCore(raw)
    assert not nx.has_path(fresh.constrained_graph(), "a", "b")


def test_wall_midpoint_is_order_and_ring_start_independent():
    raw = fixture()
    raw["spaces"][0]["polygon"] = [[4, 1], [4, 4], [0, 4], [0, 0], [4, 0]]
    core = SpatialCore(raw)
    assert shared_wall_midpoint(core, "a", "b") == pytest.approx((4.1, 2))
    assert shared_wall_midpoint(core, "b", "a") == pytest.approx((4.1, 2))
    with pytest.raises(CoreError, match="same floor"):
        shared_wall_midpoint(core, "a", "c")


@pytest.mark.parametrize("inputs", [{}, {"floor_id": "f0", "room_type": ["office"]}, {"floor_id": "f0", "room_type": "office", "typo": "x"}])
def test_public_solve_validates_inputs(inputs):
    with pytest.raises(CoreError):
        solve(load_building(fixture()), "largest_room", inputs)


@pytest.mark.parametrize("width", [-1, math.inf, math.nan, True, "1"])
def test_bad_widths(width):
    with pytest.raises(CoreError):
        Constraints(min_width=width)


def test_plain_building_solve_keeps_metadata_and_caller_state():
    raw = fixture()
    building = Building(raw, version=4)
    before = copy.deepcopy(building.data)
    assert solve(building, "largest_room", {"floor_id": "f0", "room_type": "office"})["area_m2"] == 16
    assert building.version == 4
    assert building.data == before
    assert building.last_route is None
    assert building.located_asset_ids == []
    with pytest.raises(CoreError):
        solve(building, "what_if_door", {"first": "a", "second": "b", "floor_id": "f1", "door_floor_id": "f1"})


def test_plain_building_spatial_solves_reuse_walk_cache(monkeypatch):
    import starter_agent.building_map as kit
    raw = fixture()
    raw["building"]["id"] = "cache-reuse-unit"
    building = load_building(raw)
    original = kit.walking_lengths
    computations = []

    def counted(*args, **kwargs):
        computations.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(kit, "walking_lengths", counted)
    inputs = {"start": "a", "asset_type": "desk", "floor_id": "f1", "room_type": "office"}
    first = solve(building, "errand", inputs)
    assert computations
    computations.clear()
    assert solve(building, "errand", inputs) == first
    assert computations == []
    assert building.walks == {}


def test_shared_solver_preserves_saved_width_for_reachable_counts():
    building = load_building(fixture())
    inputs = {'start': 'a', 'floor_id': 'f0', 'min_width': 0.1}
    assert solve(building, 'wide_delivery_count', inputs)['value'] == 2
    assert solve(building, 'wide_delivery_count', inputs,
                 constraints={'min_door_width_m': 1.0})['value'] == 1


def test_shared_solver_preserves_closures_for_errands():
    building = load_building(fixture())
    inputs = {'start': 'a', 'asset_type': 'desk', 'floor_id': 'f0', 'room_type': 'office'}
    assert solve(building, 'errand', inputs)['via'] == 'b'
    with pytest.raises(CoreError, match='No reachable desk'):
        solve(building, 'errand', inputs, constraints={'closed': ['ab']})
    assert building.closed == set()


def test_shared_solver_uses_no_transit_restrictions_for_reachability():
    building = load_building(fixture())
    inputs = {'start': 'a', 'floor_id': 'f1', 'closed': []}
    assert solve(building, 'step_free_reachable_count', inputs)['value'] == 1
    assert solve(building, 'step_free_reachable_count', inputs,
                 constraints={'no_transit_room_types': ['lobby']})['value'] == 0


def test_hypothetical_door_preserves_saved_width_and_source_data():
    building = load_building(fixture())
    before = copy.deepcopy(building.data)
    result = solve(building, 'what_if_door', {'first': 'a', 'second': 'b', 'floor_id': 'f0'},
                   constraints={'min_door_width_m': 1.0})
    assert result['value'] == 0  # The proposed 0.9 m door cannot admit this load.
    assert building.data == before


@pytest.mark.parametrize('start', ['a', 'h'])
def test_restricted_room_types_remain_valid_reachability_endpoints(start):
    building = load_building(fixture())
    result = solve(building, 'step_free_reachable_count',
                   {'start': start, 'floor_id': 'f1', 'closed': []},
                   constraints={'no_transit_room_types': ['office']})
    assert result['space_ids'] == ['c']


def test_reachability_does_not_use_other_restricted_destinations_for_transit():
    building = load_building(fixture())
    result = solve(building, 'step_free_reachable_count',
                   {'start': 'h', 'floor_id': 'f0', 'closed': []},
                   constraints={'no_transit_room_types': ['office']})
    assert result['space_ids'] == ['a']  # Reaching b would require transit through a.


def test_errand_allows_restricted_start_pickup_and_target():
    raw = fixture()
    raw['assets'][0].update(space_id='c', floor_id='f1', position=[2, 2])
    building = load_building(raw)
    inputs = {'start': 'a', 'asset_type': 'desk', 'floor_id': 'f3', 'room_type': 'office'}
    result = solve(building, 'errand', inputs, constraints={'no_transit_room_types': ['office']})
    assert (result['via'], result['target']) == ('c', 'd')
    assert result['length_m'] == solve(building, 'errand', inputs)['length_m']


def test_errand_keeps_restricted_transit_blocked_on_second_leg():
    building = load_building(fixture())
    with pytest.raises(CoreError, match='unreachable from pickup'):
        solve(building, 'errand', {'start': 'a', 'asset_type': 'desk', 'floor_id': 'f1', 'room_type': 'office'},
              constraints={'no_transit_room_types': ['office']})


def test_hypothetical_door_allows_restricted_entrance_and_destination():
    raw = fixture()
    raw['openings'] = [opening for opening in raw['openings'] if opening['id'] != 'ab']
    result = solve(load_building(raw), 'what_if_door', {'first': 'a', 'second': 'b', 'floor_id': 'f0'},
                   constraints={'no_transit_room_types': ['office']})
    assert result['improved_space_ids'] == ['b']


def test_restricted_connector_spaces_cannot_be_used_for_vertical_transit():
    raw = fixture()
    for space in raw['spaces']:
        if space['id'] == 'l1':
            space['room_type'] = 'restricted'
    raw['vertical_connectors'] = [connector for connector in raw['vertical_connectors'] if connector['kind'] == 'stairs']
    core = SpatialCore(raw)
    constraints = Constraints(no_transit_room_types={'restricted'})
    assert core.constrained_route('a', 'l1', constraints)['length_m'] > 0
    with pytest.raises(MapError, match='No route'):
        core.constrained_route('a', 'd', constraints)
