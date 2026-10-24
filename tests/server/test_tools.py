"""Shared tool integration: edits are durable once; mobility survives reroutes."""

import json

import pytest

from server import core_adapter as adapter
from server.buildings import BuildingCatalog
from server.config import Settings
from server.service import PlatformService
from server.errors import ServiceError
from server.state import StateStore
from server.tools import REGISTRY, ToolRegistry, registry


def fixture_building():
    def space(sid, floor, x, name):
        return {"id": sid, "floor_id": floor, "name": name, "ref": sid, "type": "room", "room_type": "office", "polygon": [[x, 0], [x+4, 0], [x+4, 4], [x, 4]]}
    return {
        "building": {"id": "server-test", "name": "Test works", "source": "test", "split": None, "units": "m"},
        "floors": [{"id": "ground", "name": "Ground floor", "level": 0, "elevation_m": 0, "height_m": 3}, {"id": "upper", "name": "First floor", "level": 1, "elevation_m": 3, "height_m": 3}],
        "spaces": [space("start", "ground", 0, "Welcome desk"), space("shaft0", "ground", 4, "Lift lobby"), space("shaft1", "upper", 4, "Upper lobby"), space("store", "upper", 8, "Tool store")],
        "openings": [{"id": "door0", "floor_id": "ground", "space_ids": ["start", "shaft0"], "kind": "door", "position": [4, 2], "width_m": 1, "step_free": True}, {"id": "door1", "floor_id": "upper", "space_ids": ["shaft1", "store"], "kind": "door", "position": [8, 2], "width_m": 1, "step_free": True}],
        "vertical_connectors": [{"id": "lift", "kind": "lift", "name": "East lift", "floor_ids": ["ground", "upper"], "space_ids": ["shaft0", "shaft1"], "step_free": True}, {"id": "stairs", "kind": "stairs", "name": "West stairs", "floor_ids": ["ground", "upper"], "space_ids": ["shaft0", "shaft1"], "step_free": False}],
        "assets": [{"id": "asset4", "name": "Press 4", "type": "machine", "space_id": "start", "floor_id": "ground", "position": [1, 1]}, {"id": "asset14", "name": "Press 14", "type": "machine", "space_id": "store", "floor_id": "upper", "position": [9, 1]}, {"id": "wrench", "name": "Torque wrench", "type": "tool", "space_id": "store", "floor_id": "upper", "position": [10, 1]}, {"id": "duplicate1", "name": "Spare drill", "type": "tool", "space_id": "start", "floor_id": "ground", "position": [2, 1]}, {"id": "duplicate2", "name": "Spare drill", "type": "tool", "space_id": "store", "floor_id": "upper", "position": [9, 2]}],
    }


@pytest.fixture
def platform(tmp_path, monkeypatch):
    # Explicitly prove the declared kit fallback, even once H01 is installed.
    monkeypatch.setattr(adapter, "core_function", lambda module, name: None)
    store = StateStore(tmp_path / "state")
    store.initialize()
    (store.directory / "uploads" / "fixture.json").write_text(json.dumps(fixture_building()))
    settings = Settings(data_dir=tmp_path / "none", state_dir=store.directory, hero_dir=tmp_path / "hero")
    messages = []
    service = PlatformService(BuildingCatalog(settings), store, notify=lambda building, message: messages.append((building, message)))
    admin = store.create_session("server-test", "desk", "admin")
    nav = store.create_session("server-test", "phone", "navigator", "wheelchair")
    for session in (admin, nav):
        store.update_session(session["session_id"], {"position": {"space_id": "start", "floor_id": "ground", "point": [2, 2], "source": "desk"}})
    return service, ToolRegistry(service), admin["session_id"], nav["session_id"], messages


def test_registry_exposes_structured_discovery_and_navigation(platform):
    service, tools, *_ = platform
    schemas = tools.json_schemas()
    assert {schema["name"] for schema in schemas} == set(REGISTRY)
    assert {"building_info", "search_entities", "get_entities", "compare_routes", "route", "plan_tour"} <= {schema["name"] for schema in schemas}
    assert next(s for s in schemas if s["name"] == "find")["input_schema"]["required"] == ["query"]
    registry.configure(service)
    assert registry.call("find", platform[3], {"query": "Press 4"})["ok"] is True


def test_find_never_confuses_numbers_and_ambiguity_changes_nothing(platform):
    service, tools, admin, nav, messages = platform
    response = tools.call("find", nav, {"query": "Press 4"})
    assert response["ok"] is True
    assert response["result"]["id"] == "asset4"
    assert response["display"]["asset_ids"] == ["asset4"]
    assert response["display"]["floor_id"] == "ground"
    assert response["trace"] == []
    response = tools.call("find", nav, {"query": "Press 5"})
    assert response["ok"] is False
    assert response["error"]["code"] == "not_found"
    assert response["trace"] == []
    response = tools.call("find", nav, {"query": "Spare drill"})
    assert response["ok"] is False
    assert response["error"]["code"] == "ambiguous"
    assert len(response["error"]["candidates"]) == 2
    assert service.store.version("server-test") == 0


def test_tour_merges_same_room_and_keeps_collected_ids_after_replan(platform):
    service, tools, admin, nav, messages = platform
    result = tools.call("plan_tour", nav, {"items": "Press 4, Press 14, Torque wrench"})
    assert result["ok"], result
    tour = result["result"]
    assert len(tour["stops"]) == 2
    assert tour["constraints"]["step_free"] is True
    assert tour["mobility_profile"] == "wheelchair"
    assert tour["geometry"] == "provisional"
    assert any("lift" in leg["element_path"] for leg in tour["legs"])
    first = tour["order"][0]
    progressed = service.progress_tour(tour["tour_id"], first, "collected")
    assert progressed["revision"] == 2
    assert service.store.get_session(nav)["position"]["space_id"] == next(s["space_id"] for s in tour["stops"] if s["stop_id"] == first)
    replanned = service.replan_tour(tour["tour_id"], nav, {"space_id": "start"}, "manual")
    assert replanned["revision"] == 3
    assert next(s["status"] for s in replanned["stops"] if s["stop_id"] == first) == "collected"
    assert first not in replanned["order"]
    assert {s["stop_id"] for s in replanned["stops"]} == {s["stop_id"] for s in tour["stops"]}
    assert service.store.get_tour(tour["tour_id"])["revision"] == 3


def test_preview_commit_repeat_undo_and_stale_preview(platform):
    service, tools, admin, nav, messages = platform
    before = tools.call("route", nav, {"destination": "Tool store"})
    assert before["ok"]
    assert "lift" in before["result"]["element_path"]
    preview = tools.call("propose_edit", admin, {"action": "close", "target": "East lift"})
    assert preview["ok"], preview
    assert service.store.version("server-test") == 0
    stale = tools.call("propose_edit", admin, {"action": "close", "target": "West stairs"})
    args = {"proposal_id": preview["result"]["proposal_id"], "op_id": "stable-commit"}
    first = tools.call("commit_edit", admin, args)
    second = tools.call("commit_edit", admin, args)
    assert first["ok"] is True
    assert first["result"]["event_id"] == second["result"]["event_id"]
    assert len(service.store.events("server-test")) == 1
    assert len([m for _, m in messages if m["type"] == "building_changed"]) == 1
    stale_response = tools.call("commit_edit", admin, {"proposal_id": stale["result"]["proposal_id"]})
    assert stale_response["error"]["code"] == "version_conflict"
    assert service.snapshot("server-test").closed == ["lift"]
    after = tools.call("route", nav, {"destination": "Tool store", "step_free": False})
    assert after["error"]["code"] == "no_route"
    assert after["error"]["route"]["reachable"] is False
    restored = tools.call("undo", admin, {"op_id": "stable-undo"})
    assert restored["ok"]
    assert service.snapshot("server-test").closed == []
    assert service.snapshot("server-test", version=1).closed == ["lift"]
    assert tools.call("route", nav, {"destination": "Tool store"})["ok"] is True


def test_admin_role_is_taken_from_session_and_errors_are_truthful(platform):
    service, tools, admin, nav, messages = platform
    for tool, args in [("propose_edit", {"action": "close", "target": "lift"}), ("commit_edit", {"proposal_id": "fake"}), ("undo", {}), ("generate_markers", {})]:
        response = tools.call(tool, nav, args)
        assert response["ok"] is False
        assert response["error"]["code"] == "forbidden"
    assert tools.call("find", nav, {})["error"]["code"] == "invalid_args"
    assert tools.call("nonexistent", nav, {})["error"]["code"] == "invalid_args"
    assert tools.call("set_scale", admin, {"reference": "wall", "length_m": 2})["error"]["code"] == "not_available"
    assert tools.call("spatial_query", nav, {"kind": "largest_room"})["error"]["code"] == "not_available"
    assert tools.call("route", nav, {"destination": "Tool store", "min_door_width_m": 1.1})["error"]["code"] == "no_route"
    assert service.store.version("server-test") == 0


def test_restart_resumes_sessions_tours_and_event_replay(platform):
    service, tools, admin, nav, messages = platform
    tour = service.create_tour(nav, ["Torque wrench"])
    preview = service.propose_edit(admin, {"action": "close", "target": "lift"})
    service.commit_edit(admin, preview["proposal_id"])
    reopened_store = StateStore(service.store.directory)
    reopened_store.initialize()
    reopened = PlatformService(service.catalog, reopened_store)
    assert reopened_store.get_session(nav)["active_tour_id"] == tour["tour_id"]
    assert reopened_store.get_tour(tour["tour_id"])["revision"] == 1
    assert reopened.snapshot("server-test").closed == ["lift"]
    replanned = reopened.replan_tour(tour["tour_id"], nav, {"space_id": "start"}, "reconnected")
    assert replanned["unreachable_stops"]
    assert replanned["changed_because"]["event_id"]
    assert replanned["constraints"]["step_free"] is True


def test_finishing_all_stops_and_what_if_never_persists(platform):
    service, tools, admin, nav, messages = platform
    result = tools.call("what_if", admin, {"action": "close", "target": "lift"})
    assert result["ok"], result
    assert service.store.events("server-test") == []
    tour = service.create_tour(nav, ["Torque wrench"])
    finished = service.progress_tour(tour["tour_id"], tour["stops"][0]["stop_id"], "collected")
    assert finished["status"] == "completed"
    assert finished["order"] == []
    assert finished["length_m"] == 0
    assert tools.call("next_step", nav, {})["result"]["complete"] is True


def test_next_step_does_not_call_blocked_pending_stops_collected(platform):
    service, tools, admin, nav, messages = platform
    tour = service.create_tour(nav, ["Torque wrench"])
    preview = service.propose_edit(admin, {"action": "close", "target": "lift"})
    service.commit_edit(admin, preview["proposal_id"])
    blocked = service.replan_tour(tour["tour_id"], nav, {"space_id": "start"})
    assert not blocked["order"]
    response = tools.call("next_step", nav, {})
    assert response["ok"] is False
    assert response["error"]["code"] == "no_route"


def test_progress_updates_phone_caller_after_desk_handoff(platform):
    service, tools, admin, nav, messages = platform
    tour = service.create_tour(admin, ["Torque wrench"])
    service.store.update_session(nav, {"active_tour_id": tour["tour_id"]})
    result = service.progress_tour(tour["tour_id"], tour["stops"][0]["stop_id"], "collected", nav)
    assert result["session_id"] == nav
    assert service.store.get_session(nav)["position"]["space_id"] == "store"
    assert service.store.get_session(admin)["position"]["space_id"] == "start"


def test_derived_walk_cache_restores_without_recomputing_geometry(platform, monkeypatch):
    service, tools, admin, nav, messages = platform
    assert tools.call("route", nav, {"destination": "Tool store"})["ok"]
    with service.store.connect() as db:
        row = db.execute("SELECT key,blob FROM derived_cache").fetchone()
    assert row is not None
    assert json.loads(row["blob"])
    assert '"version":0' in row["key"]
    original = adapter.BuildingMap.space_walks
    def cached_only(kit, space_id):
        assert space_id in kit.walks, "Cold geometry should have been restored from SQLite"
        return original(kit, space_id)
    monkeypatch.setattr(adapter.BuildingMap, "space_walks", cached_only)
    restarted = PlatformService(service.catalog, StateStore(service.store.directory))
    result = ToolRegistry(restarted).call("route", nav, {"destination": "Tool store"})
    assert result["ok"], result


def test_invalid_positions_and_asset_move_never_persist(platform):
    service, tools, admin, nav, messages = platform
    for position in ({}, {"space_id": "start", "floor_id": "upper"}, {"space_id": "start", "point": [1000, 1000]}, {"space_id": "start", "point": [float('nan'), 1]}):
        with pytest.raises(ServiceError) as failure:
            service.create_tour(nav, ["Torque wrench"], start=position)
        assert getattr(failure.value, "code", None) == "invalid_args"
    response = tools.call("propose_edit", admin, {"action": "move_asset", "target": "wrench", "second_target": "start", "value": "1000,1000"})
    assert response["error"]["code"] == "invalid_args"
    assert not service.store.events("server-test")


def test_event_version_reuse_after_reset_does_not_hit_stale_materialization(platform):
    service, tools, admin, nav, messages = platform
    first = service.propose_edit(admin, {"action": "close", "target": "lift"})
    service.commit_edit(admin, first["proposal_id"])
    assert service.snapshot("server-test").closed == ["lift"]
    adapter.route(service.current("server-test"), "start", "store")
    service.store.reset("server-test")
    second = service.propose_edit(admin, {"action": "close", "target": "stairs"})
    service.commit_edit(admin, second["proposal_id"])
    assert service.snapshot("server-test").closed == ["stairs"]
    adapter.route(service.current("server-test"), "start", "store")
    with service.store.connect() as db:
        keys = [row[0] for row in db.execute("SELECT key FROM derived_cache")]
    assert len(keys) == 2
    assert all('"version":1' in key for key in keys)
    assert json.loads(keys[0].split("kit_walks:", 1)[1])["event_log"] != json.loads(keys[1].split("kit_walks:", 1)[1])["event_log"]


def test_new_door_uses_event_version_id_and_subsequent_edits_resolve_it(platform):
    service, tools, admin, nav, messages = platform
    preview = service.propose_edit(admin, {"action": "add_door", "target": "start", "second_target": "shaft0", "value": "1.2"})
    assert "Welcome desk" in preview["summary"]
    assert "Lift lobby" in preview["summary"]
    service.commit_edit(admin, preview["proposal_id"])
    snapshot = service.snapshot("server-test")
    assert snapshot.building["openings"][-1]["id"] == "ground-O-evt1"
    assert snapshot.building["openings"][-1]["width_m"] == 1.2
    second = service.propose_edit(admin, {"action": "close", "target": "ground-O-evt1"})
    service.commit_edit(admin, second["proposal_id"])
    assert "ground-O-evt1" in service.snapshot("server-test").closed
    service.undo(admin)
    service.undo(admin)
    assert not any(o["id"] == "ground-O-evt1" for o in service.snapshot("server-test").building["openings"])


def test_undo_new_door_with_later_close_rejects_without_changing_state(platform):
    service, tools, admin, nav, messages = platform
    door_preview = service.propose_edit(admin, {"action": "add_door", "target": "start", "second_target": "shaft0"})
    door_event = service.commit_edit(admin, door_preview["proposal_id"])
    closure_preview = service.propose_edit(admin, {"action": "close", "target": "ground-O-evt1"})
    service.commit_edit(admin, closure_preview["proposal_id"])
    before = service.snapshot("server-test").model_dump()
    response = tools.call("undo", admin, {"event_id": door_event["event_id"], "op_id": "undo-dependent-door"})
    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_args"
    assert response["error"]["message"] == "Undo later changes first."
    assert service.store.version("server-test") == 2
    assert service.snapshot("server-test").model_dump() == before
    assert len([message for _, message in messages if message["type"] == "building_changed"]) == 2
    # Reverse the dependent closure first, then the newly created door.
    closure_undo = service.undo(admin, op_id="undo-closure")
    service.undo(admin, door_event["event_id"], op_id="undo-dependent-door")
    assert service.store.version("server-test") == 4
    assert not any(o["id"] == "ground-O-evt1" for o in service.snapshot("server-test").building["openings"])
    # An idempotent retry returns the original undo before simulating new state.
    duplicate = service.undo(admin, op_id="undo-closure")
    assert duplicate["event_id"] == closure_undo["event_id"]
    assert service.store.version("server-test") == 4
