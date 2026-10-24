"""Completion includes the optional end; undoing progress preserves the plan."""

import copy

import pytest

from core.building import load_building
from core.edits import apply_events
from core.tour import plan_tour, replan


@pytest.fixture
def building():
    return load_building("data/dev/proc-factory-dev-003")


@pytest.mark.parametrize("collected", [False, True], ids=["empty", "all-collected"])
def test_remaining_end_leg_keeps_tour_active(building, collected):
    start, end = list(building.spaces)[:2]
    stops = [{"target": start, "status": "collected"}] if collected else []
    tour = plan_tour(building, start, stops, end=end)
    assert tour["status"] == "active"
    assert tour["reachable"] and not tour["order"]
    assert len(tour["legs"]) == 1 and tour["length_m_exact"] > 0


@pytest.mark.parametrize("collected", [False, True], ids=["empty", "all-collected"])
def test_arriving_at_end_completes_tour(building, collected):
    start = next(iter(building.spaces))
    stops = [{"target": start, "status": "collected"}] if collected else []
    tour = plan_tour(building, start, stops, end=start)
    assert tour["status"] == "completed"
    assert tour["reachable"] and tour["length_m_exact"] == 0


@pytest.mark.parametrize("collected", [False, True], ids=["empty", "all-collected"])
def test_unreachable_end_is_blocked(building, collected):
    start, end = list(building.spaces)[:2]
    building.closed.add(end)
    stops = [{"target": start, "status": "collected"}] if collected else []
    tour = plan_tour(building, start, stops, end=end)
    assert tour["status"] == "blocked"
    assert not tour["reachable"]
    assert tour["unreachable_stops"][0]["stop_id"] == "end"


def test_collect_then_restore_middle_stop_retains_fixed_sequence_and_snapshots(building):
    rooms = list(building.spaces)
    tour = plan_tour(building, rooms[0], rooms[1:4], keep_order=True)
    prescribed = tour["order"][:]
    tour["stops"][1]["status"] = "collected"
    original = copy.deepcopy(tour)
    collected = replan(building, tour, rooms[0])
    assert tour == original
    assert [s["stop_id"] for s in collected["stops"]] == prescribed
    assert collected["stops"][1] == original["stops"][1]
    collected["stops"][1]["status"] = "pending"
    restored = replan(building, collected, rooms[0])
    assert restored["order"] == prescribed


def test_moved_split_stays_adjacent_to_parent_and_collected_snapshot_stays_put(building):
    assets = list(building.assets.values())
    first = assets[0]
    second = next(a for a in assets[1:] if a["space_id"] == first["space_id"])
    others = [sid for sid in building.spaces if sid != first["space_id"]]
    tour = plan_tour(building, first["space_id"],
                     [first["id"], second["id"], others[0], others[1]], keep_order=True)
    tour["stops"][1]["status"] = "collected"
    snapshot = copy.deepcopy(tour["stops"][1])
    changed = apply_events(building, [{"event_id": "evt-1", "kind": "move_asset",
        "edit": {"action": "move_asset", "target": first["id"], "second_target": others[2]}}])
    split = replan(changed, tour, first["space_id"])
    ids = [s["stop_id"] for s in split["stops"]]
    assert ids == ["s1", "s4", "s2", "s3"]
    assert split["stops"][2] == snapshot
    again = replan(changed, split, first["space_id"])
    assert [s["stop_id"] for s in again["stops"]] == ids
    assert again["stops"][2] == snapshot
