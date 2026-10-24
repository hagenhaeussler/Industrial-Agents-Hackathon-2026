"""Edit invariants and effects on a small, independently authored floorplan."""

import copy
import json

import pytest

from core.building import load_building
from core.edits import apply_events, preview_edit, resolve_edit
from core.errors import EditError
from core.routing import route
from core.whatif import what_if


@pytest.fixture
def building():
    raw = {"building": {"id": "edit-test", "name": "Workshop", "source": "authored", "units": "m"},
           "floors": [{"id": "F0", "name": "Ground floor", "level": 0, "elevation_m": 0, "height_m": 3}],
           "spaces": [], "openings": [], "vertical_connectors": [], "assets": []}
    for index, label in enumerate(("Workshop 1", "Workshop 2", "Workshop 3")):
        x = index * 4
        raw["spaces"].append({"id": f"S{index}", "floor_id": "F0", "name": label,
                              "type": "room", "room_type": "lab", "ref": str(index + 1),
                              "polygon": [[x, 0], [x + 4, 0], [x + 4, 4], [x, 4]], "synthetic": False})
    for oid, spaces, point in (("E", ["outside", "S0"], [0, 2]),
                                ("AB", ["S0", "S1"], [4, 2]), ("BC", ["S1", "S2"], [8, 2])):
        raw["openings"].append({"id": oid, "floor_id": "F0", "space_ids": spaces,
                                "position": point, "kind": "door", "width_m": .9,
                                "step_free": True, "synthetic": False})
    raw["assets"].append({"id": "A", "name": "Torque wrench", "space_id": "S0", "floor_id": "F0",
                           "type": "tool", "category": "equipment", "source": "dataset", "position": [1, 1],
                           "footprint": {"width_m": .2, "depth_m": .1, "rotation_deg": 0}})
    return load_building(raw)


def event(index, action, target=None, **edit):
    return {"event_id": f"evt-{index}", "kind": action,
            "edit": {"action": action, "target": target, **edit}}


def test_close_undo_restores_route_and_preserves_source(building):
    raw_before = copy.deepcopy(building.data)
    before = route(building, "S0", "S2")
    close = event(1, "close", "BC")
    closed = apply_events(building, [close])
    assert not route(closed, "S0", "S2")["reachable"]
    restored = apply_events(building, [close, {"event_id": "evt-2", "kind": "undo", "undoes": "evt-1"}])
    assert route(restored, "S0", "S2")["length_m"] == before["length_m"]
    assert restored.content_hash == building.content_hash
    assert restored.version == 2
    assert building.data == raw_before and not building.closed
    # Closures are versioned overlay state, not additions to kit JSON.
    assert closed.content_hash == building.content_hash
    assert closed.closed == {"BC"}


def test_add_door_idempotent_replay_undo_and_cache_isolation(building):
    building.graph(False)
    cached = dict(building.walks)
    add = event(1, "add_door", "S0", second_target="S1", value=1.3)
    first = apply_events(building, [add])
    second = apply_events(building, [add])
    door = first.openings["F0-O-evt1"]
    assert door["position"] == [4, 2] and door["width_m"] == 1.3 and door["step_free"]
    assert first.content_hash == second.content_hash != building.content_hash
    assert first.data == second.data
    assert "S0" not in first.walks and "S1" not in first.walks
    assert first.walks["S2"] is cached["S2"]
    first.graph(False)
    assert building.walks == cached
    duplicate = apply_events(building, [add, add])
    assert len(duplicate.openings) == 4 and duplicate.version == 2
    undone = apply_events(building, [add, {"event_id": "evt-2", "kind": "undo", "undoes": "evt-1"}])
    assert undone.content_hash == building.content_hash
    assert "F0-O-evt1" not in undone.openings


def test_move_and_room_type_undo_restores_original_data(building):
    move = event(1, "move_asset", "A", second_target="S2")
    room = event(2, "set_room_type", "S0", value="office")
    changed = apply_events(building, [move, room])
    assert changed.assets["A"]["space_id"] == "S2"
    assert changed.assets["A"]["position"] == [10, 2]
    assert changed.spaces["S0"]["room_type"] == "office"
    undone = apply_events(building, [move, room,
                                   {"event_id": "evt-3", "kind": "undo", "undoes": "evt-1"},
                                   {"event_id": "evt-4", "kind": "undo", "undoes": "evt-2"}])
    assert undone.data == building.data


def test_undo_added_door_with_later_closure_does_not_leave_ghost_state(building):
    added = event(1, "add_door", "S0", second_target="S1")
    closed = event(2, "close", "F0-O-evt1")
    result = apply_events(building, [added, closed,
                                   {"event_id": "evt-3", "kind": "undo", "undoes": "evt-1"}])
    assert result.data == building.data
    assert not result.closed


def test_open_and_targeted_undo_keep_independent_events(building):
    close = event(1, "close", "BC")
    opened = event(2, "open", "BC")
    assert not apply_events(building, [close, opened]).closed
    assert apply_events(building, [close, opened,
                                  {"event_id": "evt-3", "kind": "undo", "undoes": "evt-2"}]).closed == {"BC"}
    # Cancelling an earlier close does not cancel the later independent close.
    assert apply_events(building, [close, event(2, "close", "BC"),
                                  {"event_id": "evt-3", "kind": "undo", "undoes": "evt-1"}]).closed == {"BC"}


@pytest.mark.parametrize("events", [
    [{"event_id": "evt-1", "kind": "undo", "undoes": "missing"}],
    [event(1, "close", "BC"), {"event_id": "evt-2", "kind": "undo", "undoes": "evt-1"},
     {"event_id": "evt-3", "kind": "undo", "undoes": "evt-1"}],
    [event(1, "close", "BC"), {"event_id": "evt-2", "kind": "undo", "undoes": "evt-1"},
     {"event_id": "evt-3", "kind": "undo", "undoes": "evt-2"}],
    [event(1, "close", "BC"), event(1, "close", "AB")],
])
def test_invalid_undo_and_event_id_reuse_rejected(building, events):
    with pytest.raises(EditError):
        apply_events(building, events)


@pytest.mark.parametrize("edit", [
    {"action": "add_door", "target": "S0", "second_target": "S2"},
    {"action": "add_door", "target": "S0", "second_target": "S1", "value": -1},
    {"action": "add_door", "target": "S0", "second_target": "S1", "value": float("nan")},
    {"action": "move_asset", "target": "A", "second_target": "S1", "value": "1,1"},
    {"action": "move_asset", "target": "A", "second_target": "S1", "value": "nan,2"},
    {"action": "set_room_type", "target": "S0", "value": "whatever the LLM invented"},
    {"action": "open", "target": "AB"},
    {"action": []},
])
def test_invalid_geometry_and_values_rejected(building, edit):
    with pytest.raises(EditError):
        resolve_edit(building, edit)


def test_names_resolved_and_missing_entities_never_invented(building):
    assert resolve_edit(building, {"action": "close", "target": "Workshop 2"})["target"] == "S1"
    with pytest.raises(EditError) as error:
        resolve_edit(building, {"action": "close", "target": "entirely unknown factory"})
    assert error.value.code == "not_found"


def test_preview_and_what_if_leave_source_unchanged(building):
    before = (copy.deepcopy(building.data), building.content_hash, building.version, set(building.closed))
    edit = {"action": "close", "target": "BC"}
    preview = preview_edit(building, edit, [])
    assert preview["base_version"] == 0
    assert preview["effects"]["newly_unreachable_spaces"] == 1
    probe = what_if(building, edit, {"kind": "route", "start": "S0", "destination": "S2"})
    assert probe["before"]["reachable"] and not probe["after"]["reachable"]
    assert probe["persisted"] is False
    reach = what_if(building, edit, {"kind": "reachable_count", "start": "S0", "floor_id": "F0"})
    assert reach["before"]["value"] == 3 and reach["after"]["value"] == 2
    exits = what_if(building, edit, {"kind": "exit_distances", "floor_id": "F0"})
    assert exits["after"]["S2"] is None
    json.dumps(exits, allow_nan=False)
    assert before == (building.data, building.content_hash, building.version, building.closed)


def test_preview_replans_active_tour_without_changing_it(building):
    from core.tour import plan_tour
    tour = plan_tour(building, "S0", [{"target": "S2"}])
    tour["tour_id"] = "tour-test"
    original = copy.deepcopy(tour)
    preview = preview_edit(building, {"action": "close", "target": "BC"}, [tour])
    effects = preview["effects"]
    assert effects["active_tours_affected"] == 1
    assert effects["tours"] == [{"tour_id": "tour-test", "before_m": tour["length_m"],
                                 "after_m": None, "reachable_after": False}]
    assert original == tour


def test_move_asset_preview_follows_pending_item_to_new_room(building):
    from core.tour import plan_tour
    tour = plan_tour(building, "S0", [{"target": "A"}])
    tour["tour_id"] = "move-test"
    original = copy.deepcopy(tour)
    preview = preview_edit(building, {"action": "move_asset", "target": "A", "second_target": "S2"}, [tour])
    assert preview["effects"]["active_tours_affected"] == 1
    assert preview["effects"]["tours"][0]["after_m"] > tour["length_m"]
    assert preview["effects"]["tours"][0]["reachable_after"]
    assert original == tour
