"""Prepared GEOS state is shared per space, so its native helpers must not race."""

from concurrent.futures import ThreadPoolExecutor
import math
from threading import Barrier, Event, Lock, RLock

import core.geometry as geometry
from core.building import load_building
from core.routing import route


def building(identifier):
    return load_building({
        "building": {"id": identifier},
        "floors": [{"id": "f", "level": 0, "elevation_m": 0, "name": "Ground"}],
        "spaces": [{"id": "a", "floor_id": "f", "room_type": "office", "name": "A",
                    "polygon": [[0,0],[4,0],[4,4],[0,4]]},
                   {"id": "b", "floor_id": "f", "room_type": "office", "name": "B",
                    "polygon": [[4,0],[8,0],[8,4],[4,4]]}],
        "openings": [{"id": "door", "floor_id": "f", "space_ids": ["a","b"],
                      "kind": "door", "position": [4,2], "width_m": 1, "step_free": True}],
        "assets": [], "vertical_connectors": [],
    })


def test_same_cached_space_serializes_native_geometry_calls(monkeypatch):
    b = building("same-space-native-lock")
    shared = geometry.space_geometry(b, "a")
    native_entered, release_native, second_lock_attempt = Event(), Event(), Event()
    state_lock = Lock()
    calls = 0
    native = geometry.visibility_matrix

    class ObservedRLock:
        def __init__(self):
            self.actual = RLock()
            self.attempts = 0

        def __enter__(self):
            with state_lock:
                self.attempts += 1
                if self.attempts == 2:
                    second_lock_attempt.set()
            self.actual.acquire()
            return self

        def __exit__(self, *args):
            self.actual.release()

    monkeypatch.setattr(shared, "lock", ObservedRLock())

    def observed_native(allowed, nodes):
        nonlocal calls
        assert allowed is shared.allowed
        with state_lock:
            calls += 1
            first = calls == 1
        if first:
            native_entered.set()
            assert release_native.wait(5), "Test did not release the first native call."
        return native(allowed, nodes)

    monkeypatch.setattr(geometry, "visibility_matrix", observed_native)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(geometry.walk_polyline, b, "a", "a", "a", start_point=[1,1], end_point=[3,3])
        try:
            assert native_entered.wait(5)
            second = pool.submit(geometry.walk_polyline, b, "a", "a", "a", start_point=[1,2], end_point=[3,2])
            # The second caller has tried acquiring the same per-space lock;
            # this observation avoids sleeps or scheduler-dependent timing tests.
            assert second_lock_attempt.wait(5)
            with state_lock:
                assert calls == 1
        finally:
            release_native.set()
        assert first.result(timeout=5)["length_m"] > 0
        assert second.result(timeout=5)["length_m"] == 2
    assert calls == 2


def test_unrelated_spaces_can_use_native_helpers_concurrently(monkeypatch):
    b = building("different-space-native-locks")
    geometry.space_geometry(b, "a")
    geometry.space_geometry(b, "b")
    native = geometry.visibility_matrix
    both_entered = Barrier(2)

    def overlapping_native(allowed, nodes):
        both_entered.wait(timeout=5)
        return native(allowed, nodes)

    monkeypatch.setattr(geometry, "visibility_matrix", overlapping_native)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(geometry.walk_polyline, b, "a", "a", "a", start_point=[1,1], end_point=[3,3])
        second = pool.submit(geometry.walk_polyline, b, "b", "b", "b", start_point=[5,1], end_point=[7,3])
        assert first.result(timeout=10)["length_m"] > 0
        assert second.result(timeout=10)["length_m"] > 0


def test_real_concurrent_point_routes_keep_positions_and_finite_costs():
    b = building("concurrent-point-routes")
    b.graph(False)
    geometry.space_geometry(b, "a")
    geometry.space_geometry(b, "b")

    def compute(index):
        point = [1 + index / 1000, 2]
        result = route(b, {"space_id": "a", "point": point}, {"space_id": "b", "point": [6,2]})
        assert result["reachable"]
        assert result["segments"][0]["points"][0] == point
        assert result["segments"][-1]["points"][-1] == [6,2]
        assert math.isfinite(result["length_m_exact"])
        assert result["element_path"] == ["door"]
        return result["length_m_exact"]

    with ThreadPoolExecutor(max_workers=4) as pool:
        lengths = list(pool.map(compute, range(40)))
    assert len(lengths) == 40
    assert lengths[0] > lengths[-1]
