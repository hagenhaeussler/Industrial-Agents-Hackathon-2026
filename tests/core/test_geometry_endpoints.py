import math

import pytest

from core.building import load_building
from core.errors import CoreError
from core.geometry import walk_polyline
from core.routing import route


def building():
    return load_building({
        "building": {"id": "geometry-endpoints"},
        "floors": [{"id": "f", "level": 0, "elevation_m": 0, "name": "Ground"}],
        "spaces": [{"id": "a", "floor_id": "f", "room_type": "office", "name": "A",
                    "polygon": [[0,0],[4,0],[4,4],[0,4]]}],
        "openings": [], "assets": [], "vertical_connectors": [],
    })


@pytest.mark.parametrize("point", [[0,2], [.05,2], [2,2]])
def test_identical_valid_explicit_positions_need_no_movement(point):
    b = building()
    result = route(b, {"space_id": "a", "point": point}, {"space_id": "a", "point": point})
    assert result["reachable"]
    assert result["length_m_exact"] == result["length_m"] == 0
    assert result["segments"][0]["points"] == [point]
    assert not result["segments"][0]["fallback"]
    assert result["maneuvers"][0]["at"] == result["maneuvers"][-1]["at"] == point


def test_same_position_still_requires_valid_room_and_honors_closure():
    b = building()
    with pytest.raises(CoreError):
        walk_polyline(b, "a", "a", "a", start_point=[20,20], end_point=[20,20])
    b.closed.add("a")
    result = route(b, {"space_id": "a", "point": [0,2]}, {"space_id": "a", "point": [0,2]})
    assert not result["reachable"]
    assert result["reason"] == "blocked_by_closure"


def test_distinct_wall_band_positions_keep_clearance_walk_and_stubs():
    b = building()
    result = route(b, {"space_id": "a", "point": [0,1]}, {"space_id": "a", "point": [0,2]})
    assert result["reachable"]
    assert math.isclose(result["length_m_exact"], 1.26, abs_tol=1e-9)
    points = result["segments"][0]["points"]
    assert points[0] == [0,1] and points[-1] == [0,2]
    assert all(math.isclose(point[0], .13, abs_tol=1e-9) for point in points[1:-1])
