"""Read-only route queries against a catalog and SQLite, with both adapters."""

from copy import deepcopy
import json

import pytest
from pydantic import ValidationError

from server import core_adapter as adapter
from server.buildings import BuildingCatalog
from server.config import Settings
from server.errors import ServiceError
from server.route_queries import RouteQuery, RouteQueryArgs, TourQueryArgs
from server.service import PlatformService
from server.state import StateStore


def route_building():
    def room(entity_id, floor_id, x):
        return {"id": entity_id, "name": entity_id.title(), "ref": entity_id,
                "floor_id": floor_id, "room_type": "office", "type": "room",
                "polygon": [[x, 0], [x + 4, 0], [x + 4, 4], [x, 4]]}

    return {
        "building": {"id": "route-test", "name": "Route test", "source": "test", "units": "m"},
        "floors": [{"id": "ground", "name": "Ground", "level": 0, "elevation_m": 0},
                   {"id": "upper", "name": "Upper", "level": 1, "elevation_m": 3}],
        "spaces": [room("start", "ground", 0), room("lobby", "ground", 4),
                   room("above", "upper", 4), room("far", "upper", 8)],
        "openings": [{"id": "door-ground", "kind": "door", "floor_id": "ground",
                      "space_ids": ["start", "lobby"], "position": [4, 2], "width_m": 1, "step_free": True},
                     {"id": "door-upper", "kind": "door", "floor_id": "upper",
                      "space_ids": ["above", "far"], "position": [8, 2], "width_m": 0.9, "step_free": True}],
        "vertical_connectors": [
            {"id": "stairs", "kind": "stairs", "name": "Stairs", "step_free": False,
             "floor_ids": ["ground", "upper"], "space_ids": ["lobby", "above"]},
            {"id": "lift", "kind": "lift", "name": "Lift", "step_free": True,
             "floor_ids": ["ground", "upper"], "space_ids": ["lobby", "above"]}],
        "assets": [{"id": "start-item", "name": "Start item", "type": "tool", "floor_id": "ground",
                    "space_id": "start", "position": [2, 2]},
                   {"id": "far-item", "name": "Far item", "type": "tool", "floor_id": "upper",
                    "space_id": "far", "position": [10, 2]},
                   {"id": "other-far-item", "name": "Other far item", "type": "tool", "floor_id": "upper",
                    "space_id": "far", "position": [10, 3]}],
    }


@pytest.fixture(params=["core", "kit"])
def platform(tmp_path, monkeypatch, request):
    if request.param == "kit":
        monkeypatch.setattr(adapter, "core_function", lambda module, name: None)
    store = StateStore(tmp_path / "state")
    store.initialize()
    (store.directory / "uploads" / "routes.json").write_text(json.dumps(route_building()))
    settings = Settings(data_dir=tmp_path / "none", hero_dir=tmp_path / "none", state_dir=store.directory)
    service = PlatformService(BuildingCatalog(settings), store)
    session = store.create_session("route-test", "desk", "navigator")
    return RouteQuery(service), session


def saved_state(service):
    tables = ("sessions", "tours", "events", "proposals", "markers", "buildings")
    with service.store.connect() as db:
        return {table: [tuple(row) for row in db.execute(f"SELECT * FROM {table} ORDER BY rowid")]
                for table in tables}


@pytest.mark.parametrize("start", ["start", "start-item"])
def test_explicit_start_without_session_position_uses_shared_route(platform, start):
    queries, session = platform
    result, speech, display = queries.route(session, RouteQueryArgs(start=start, destination="far-item"))
    expected = adapter.route(queries.service.current("route-test"), start, "far-item")
    assert (result["reachable"], result["length_m_exact"], result["element_path"]) == (
        True, expected["length_m_exact"], expected["element_path"])
    assert result["start"]["space_id"] == "start" and session["position"] is None
    assert speech and display == {"kind": "none"}


def test_temporary_stairs_closure_changes_route_then_reports_no_route(platform):
    queries, session = platform
    walking, _, _ = queries.route(session, {"start": "start", "destination": "far"})
    lift, _, _ = queries.route(session, {"start": "start", "destination": "far", "closed": ["stairs"]})
    blocked, speech, _ = queries.route(session, {
        "start": "start", "destination": "far", "closed": ["stairs", "lift"]})
    assert "stairs" in walking["element_path"] and "lift" in lift["element_path"]
    assert lift["length_m_exact"] > walking["length_m_exact"]
    assert blocked["reachable"] is False and blocked["reason"] == "blocked_by_closure" and speech
    assert queries.service.current("route-test").closed == set()


@pytest.mark.parametrize("closed", [["door-ground"], ["above"], ["stairs", "lift"]])
def test_all_supported_closure_kinds_apply(platform, closed):
    queries, session = platform
    result, _, _ = queries.route(session, {"start": "start", "destination": "far", "closed": closed})
    assert (result["reachable"], result["constraints"]["closed"]) == (False, sorted(closed))


def test_metadata_tracks_saved_building_closures(platform):
    queries, session = platform
    service = queries.service
    admin = service.store.create_session("route-test", "desk", "admin")
    proposal = service.propose_edit(admin["session_id"], {"action": "close", "target": "lift"})
    service.commit_edit(admin["session_id"], proposal["proposal_id"])
    result, _, _ = queries.route(session, {"start": "start", "destination": "far", "closed": ["stairs"]})
    assert (result["building_id"], result["building_version"], result["building_state_id"]) == (
        "route-test", 1, service.building_state_id(service.current("route-test")))
    assert result["constraints"]["closed"] == ["lift", "stairs"] and result["reachable"] is False


@pytest.mark.parametrize("method,args", [("route", {"destination": "far"}), ("tour", {"items": ["far"]})])
def test_missing_start_is_an_explicit_error(platform, method, args):
    queries, session = platform
    with pytest.raises(ServiceError, match="starting") as failure:
        getattr(queries, method)(session, args)
    assert failure.value.code == "invalid_args"


@pytest.mark.parametrize("method,args", [("route", {"destination": "far"}), ("tour", {"items": ["far"]})])
def test_session_position_fallback_and_explicit_override(platform, method, args):
    queries, session = platform
    session = queries.service.store.update_session(session["session_id"], {"position": {"space_id": "lobby"}})
    fallback, _, _ = getattr(queries, method)(session, args)
    explicit, _, _ = getattr(queries, method)(session, {**args, "start": "far-item"})
    assert (fallback["start"]["space_id"], explicit["start"]["space_id"]) == ("lobby", "far")


def test_tour_uses_shared_grouping_fixed_order_and_final_destination(platform):
    queries, session = platform
    result, speech, display = queries.tour(session, TourQueryArgs(
        start="start-item", items=["far-item", "other-far-item", "lobby"], keep_order=True, end="start"))
    ordered = {stop["stop_id"]: stop for stop in result["stops"]}
    assert [ordered[stop_id]["space_id"] for stop_id in result["order"]] == ["far", "lobby"]
    assert result["stops"][0]["asset_ids"] == ["far-item", "other-far-item"]
    assert result["end"]["space_id"] == result["legs"][-1]["to_space_id"] == "start"
    assert result["reachable"] and result["order_policy"] == "fixed" and speech and display == {"kind": "none"}
    assert all(leg["building_state_id"] == result["building_state_id"] for leg in result["legs"])


def test_tour_optimizes_order_through_shared_adapter(platform):
    queries, session = platform
    result, _, _ = queries.tour(session, {"start": "start", "items": ["far", "lobby", "above"]})
    expected = adapter.plan_tour(queries.service.current("route-test"), "start",
                                 queries.service._stops(queries.service.current("route-test"), ["far", "lobby", "above"]), {})
    assert (result["length_m"], result["order_policy"]) == (expected["length_m"], "optimized_exact")


@pytest.mark.parametrize("items,expected_rooms", [(["lobby", "far"], ["lobby"]), (["far"], [])])
def test_tour_reports_partial_or_fully_unreachable_stops(platform, items, expected_rooms):
    queries, session = platform
    result, speech, _ = queries.tour(session, {"start": "start", "items": items, "closed": ["stairs", "lift"]})
    stops = {stop["stop_id"]: stop for stop in result["stops"]}
    blocked = result["unreachable_stops"]
    assert [stops[stop_id]["space_id"] for stop_id in result["order"]] == expected_rooms
    assert len(blocked) == 1 and stops[blocked[0]["stop_id"]]["space_id"] == "far"
    assert result["reachable"] is False and "unreachable" in speech


def test_tour_reports_unreachable_final_destination(platform):
    queries, session = platform
    result, _, _ = queries.tour(session, {"start": "start", "items": ["lobby"], "end": "far",
                                        "closed": ["stairs", "lift"]})
    assert result["reachable"] is False and result["unreachable_stops"][0]["stop_id"] == "end"


@pytest.mark.parametrize("profile", ["walk", "wheelchair", "pram", "trolley"])
@pytest.mark.parametrize("method,args", [("route", {"destination": "far"}), ("tour", {"items": ["far"]})])
def test_query_cannot_weaken_saved_constraints(platform, profile, method, args):
    queries, session = platform
    session = queries.service.store.update_session(session["session_id"], {
        "profile": profile, "constraints": {"step_free": True, "min_door_width_m": 1.1,
                                            "closed": ["stairs"], "no_transit_room_types": ["office"]}})
    result, _, _ = getattr(queries, method)(session, {
        **args, "start": "start", "step_free": False, "min_door_width_m": 0.1, "closed": ["door-upper"]})
    assert result["constraints"] == {**session["constraints"], "closed": ["door-upper", "stairs"]}
    assert result["reachable"] is False


@pytest.mark.parametrize("profile", ["wheelchair", "pram", "trolley"])
def test_profile_alone_enforces_step_free_route(platform, profile):
    queries, session = platform
    session = queries.service.store.update_session(session["session_id"], {"profile": profile})
    result, _, _ = queries.route(session, {"start": "start", "destination": "far", "step_free": False})
    assert result["constraints"]["step_free"] is True and "lift" in result["element_path"]


@pytest.mark.parametrize("method,args", [("route", {"destination": "far"}), ("tour", {"items": ["far"]})])
def test_query_applies_minimum_door_width(platform, method, args):
    queries, session = platform
    result, _, _ = getattr(queries, method)(session, {**args, "start": "start", "min_door_width_m": 1.1})
    reason = result["reason"] if method == "route" else result["unreachable_stops"][0]["reason"]
    assert result["reachable"] is False and reason == "too_narrow"


@pytest.mark.parametrize("destination", ["Far", "unknown", "stairs", "door-upper", "upper"])
def test_route_rejects_labels_and_nonposition_ids(platform, monkeypatch, destination):
    queries, session = platform

    def unexpected(*args, **kwargs):
        pytest.fail("Validate the route destination before computing a route.")

    monkeypatch.setattr(adapter, "route", unexpected)
    with pytest.raises(ServiceError):
        queries.route(session, {"start": "start", "destination": destination})


def test_queries_preserve_existing_session_tour_and_event_rows(platform):
    queries, session = platform
    service = queries.service
    service.create_tour(session["session_id"], ["far"], start="start")
    session = service.store.get_session(session["session_id"])
    before, original = saved_state(service), deepcopy(session)
    queries.route(session, {"start": "lobby", "destination": "far", "step_free": True, "closed": ["stairs"]})
    queries.tour(session, {"start": "far", "items": ["lobby"], "step_free": True, "closed": ["stairs"]})
    with pytest.raises(ServiceError):
        queries.tour(session, {"start": "start", "items": ["far", "unknown"]})
    assert saved_state(service) == before and session == original


@pytest.mark.parametrize("method,args", [("route", {"destination": "far"}), ("tour", {"items": ["far"]})])
@pytest.mark.parametrize("patch", [
    {"start": "Start"}, {"start": "stairs"}, {"start": "unknown"},
    {"closed": ["unknown"]}, {"closed": ["Stairs"]}, {"closed": ["far-item"]},
    {"closed": "stairs"}, {"closed": [None]}, {"closed": [1]}, {"closed": [" "]},
])
def test_bad_ids_and_closures_fail_before_computation(platform, monkeypatch, method, args, patch):
    queries, session = platform
    before = saved_state(queries.service)

    def unexpected(*args, **kwargs):
        pytest.fail("No route or tour may be computed before all inputs are valid.")

    monkeypatch.setattr(adapter, "route", unexpected)
    monkeypatch.setattr(adapter, "plan_tour", unexpected)
    with pytest.raises(ServiceError):
        getattr(queries, method)(session, {**args, "start": "start", **patch})
    assert saved_state(queries.service) == before


@pytest.mark.parametrize("args", [
    {"items": ["far", "unknown"]}, {"items": ["far"], "end": "Unknown"},
    {"items": ["far"], "end": "stairs"}, {"items": ["far", "upper"]},
])
def test_every_tour_target_is_validated_before_planning(platform, monkeypatch, args):
    queries, session = platform

    def unexpected(*args, **kwargs):
        pytest.fail("Validate the last item and final destination before planning.")

    monkeypatch.setattr(adapter, "plan_tour", unexpected)
    with pytest.raises(ServiceError):
        queries.tour(session, {"start": "start", **args})


@pytest.mark.parametrize("model,args", [
    (RouteQueryArgs, {}), (RouteQueryArgs, {"destination": "far", "start": {"space_id": "start"}}),
    (RouteQueryArgs, {"destination": "far", "min_door_width_m": -1}),
    (RouteQueryArgs, {"destination": "far", "min_door_width_m": float("inf")}),
    (RouteQueryArgs, {"destination": "far", "min_door_width_m": float("nan")}),
    (RouteQueryArgs, {"destination": "far", "step_free": "false"}),
    (TourQueryArgs, {"items": []}), (TourQueryArgs, {"items": ["far"] * 101}),
    (TourQueryArgs, {"items": [None]}), (TourQueryArgs, {"items": [" "]}),
    (TourQueryArgs, {"items": "far"}), (TourQueryArgs, {"items": ["far"], "keep_order": "false"}),
    (TourQueryArgs, {"items": ["far"], "extra": 1}),
])
def test_argument_models_reject_malformed_values(model, args):
    with pytest.raises(ValidationError):
        model.model_validate(args)


@pytest.mark.parametrize("model", [RouteQueryArgs, TourQueryArgs])
def test_exported_schemas_forbid_extra_fields_and_accept_limits(model):
    args = {"destination": "far"} if model is RouteQueryArgs else {"items": ["far"] * 100}
    assert model.model_validate(args) and model.model_json_schema()["additionalProperties"] is False
