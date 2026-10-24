import math

import numpy as np

from shapely.geometry import LineString

from core.building import load_building
from core.geometry import space_geometry, walk_polyline
from starter_agent.building_map import walking_lengths


def test_l_shaped_room_walk_does_not_cut_through_wall():
    raw = {"building": {"id": "l-shape"}, "floors": [{"id": "f", "name": "Ground", "level": 0, "elevation_m": 0}],
           "spaces": [{"id": "l", "name": "L shaped room", "room_type": "hall", "floor_id": "f",
                       "polygon": [[0, 0], [4, 0], [4, 1], [1, 1], [1, 4], [0, 4]]}],
           "openings": [{"id": "a", "space_ids": ["l", "outside"], "floor_id": "f", "position": [4, .5], "width_m": 1, "step_free": True},
                        {"id": "b", "space_ids": ["l", "outside"], "floor_id": "f", "position": [.5, 4], "width_m": 1, "step_free": True}],
           "vertical_connectors": [], "assets": []}
    b = load_building(raw)
    walk = walk_polyline(b, "l", "door:a", "door:b")
    g = space_geometry(b, "l")
    assert not walk["fallback"]
    assert len(walk["points"]) > 4
    assert g.allowed.buffer(1e-8).covers(LineString(walk["points"][1:-1]))
    expected = next(cost for a, z, cost in b.space_walks("l") if (a, z) == ("door:a", "door:b"))
    assert math.isclose(walk["length_m"], expected, abs_tol=1e-8)
    reverse = walk_polyline(b, "l", "door:b", "door:a")
    assert math.isclose(reverse["length_m"], walk["length_m"], abs_tol=1e-8)


def test_repaired_polygon_anchor_has_zero_length_self_walk():
    raw = {"building": {"id": "islands"}, "floors": [{"id": "f", "name": "Ground", "level": 0, "elevation_m": 0}],
           "spaces": [{"id": "s", "name": "Bow tie", "room_type": "hall", "floor_id": "f",
                       "polygon": [[0, 0], [2, 2], [0, 2], [2, 0]]}], "openings": [], "vertical_connectors": [], "assets": []}
    b = load_building(raw)
    walk = walk_polyline(b, "s", "s", "s")
    assert not walk["fallback"]
    assert walk["length_m"] == 0


def test_visibility_reconstruction_agrees_with_kit_all_member_pairs():
    b = load_building("data/dev/proc-factory-dev-003")
    for sid in list(b.spaces)[:10]:
        for first, second, expected in b.space_walks(sid):
            walk = walk_polyline(b, sid, first, second)
            assert math.isclose(walk["kit_length_m"], expected, abs_tol=1e-8)


def test_fallback_retains_inflated_cost_and_explicit_warning(monkeypatch):
    import core.geometry as geometry

    def blocked(allowed, nodes):
        matrix = np.full((len(nodes), len(nodes)), math.inf)
        np.fill_diagonal(matrix, 0)
        return matrix

    monkeypatch.setattr(geometry, "visibility_matrix", blocked)
    raw = {"building": {"id": "blocked-visibility-test"},
           "floors": [{"id": "f", "name": "Ground", "level": 0, "elevation_m": 0}],
           "spaces": [{"id": "s", "name": "Room", "room_type": "office", "floor_id": "f",
                       "polygon": [[0,0],[5,0],[5,5],[0,5]]}],
           "openings": [{"id": "d", "floor_id": "f", "space_ids": ["s", "outside"],
                         "position": [5,2.5], "width_m": 1, "step_free": True}],
           "assets": [], "vertical_connectors": []}
    b = load_building(raw)
    result = geometry.walk_polyline(b, "s", "s", "door:d")
    assert result["fallback"]
    assert result["points"][0] == [2.5, 2.5]
    assert result["points"][-1] == [5, 2.5]
    assert result["kit_length_m"] > result["length_m"]
