"""Structured queries against a small real catalog, store and routing graph."""

from copy import deepcopy
import json
import math

import pytest
from pydantic import ValidationError

from server import core_adapter as adapter
from server.agent_queries import AgentQueries, CompareRoutesArgs, GetEntitiesArgs, InfoArgs, SearchArgs
from server.buildings import BuildingCatalog
from server.config import Settings
from server.errors import ServiceError
from server.service import PlatformService
from server.state import StateStore


def query_building():
    def room(entity_id, floor, x):
        return {"id": entity_id, "name": entity_id.title(), "ref": entity_id,
                "floor_id": floor, "type": "room", "room_type": "office",
                "polygon": [[x, 0], [x + 4, 0], [x + 4, 4], [x, 4]]}

    return {
        "building": {"id": "query-test", "name": "Query test", "source": "test", "units": "m"},
        "floors": [{"id": "ground", "name": "Ground", "level": 0, "elevation_m": 0},
                   {"id": "upper", "name": "Upper", "level": 1, "elevation_m": 3}],
        "spaces": [room("start", "ground", 0), room("middle", "ground", 4),
                   room("far", "ground", 8), room("above", "upper", 0)],
        "openings": [{"id": "door-a", "kind": "door", "floor_id": "ground", "space_ids": ["start", "middle"],
                      "position": [4, 2], "width_m": 1, "step_free": True},
                     {"id": "door-b", "kind": "door", "floor_id": "ground", "space_ids": ["middle", "far"],
                      "position": [8, 2], "width_m": 0.9, "step_free": True}],
        "vertical_connectors": [{"id": "stairs", "kind": "stairs", "name": "Stairs", "step_free": False,
                                 "floor_ids": ["ground", "upper"], "space_ids": ["start", "above"]}],
        "assets": [{"id": "printer-above", "name": "Printer above", "type": "printer", "floor_id": "upper",
                    "space_id": "above", "position": [2, 2]},
                   {"id": "printer-far-a", "name": "Printer far A", "type": "printer", "floor_id": "ground",
                    "space_id": "far", "position": [10, 2]},
                   {"id": "printer-far-b", "name": "Printer far B", "type": "printer", "floor_id": "ground",
                    "space_id": "far", "position": [10, 3]},
                   {"id": "tool", "name": "Spanner", "type": "tool", "floor_id": "ground",
                    "space_id": "middle", "position": [6, 2]}],
    }


@pytest.fixture
def platform(tmp_path):
    store = StateStore(tmp_path / "state")
    store.initialize()
    raw = query_building()
    (store.directory / "uploads" / "query.json").write_text(json.dumps(raw))
    settings = Settings(data_dir=tmp_path / "none", hero_dir=tmp_path / "none", state_dir=store.directory)
    service = PlatformService(BuildingCatalog(settings), store)
    session = store.create_session(raw["building"]["id"], "desk", "navigator")
    session = store.update_session(session["session_id"], {"position": {"space_id": "start", "point": [2, 2]}})
    return AgentQueries(service), session, raw


def test_info_discovers_vocabulary_counts_and_session_context(platform):
    queries, session, _ = platform
    result, speech, display = queries.building_info(session, InfoArgs())
    assert result["asset_types"] == ["printer", "tool"]
    assert result["room_types"] == ["office"]
    assert result["counts"] == {"asset": 4, "space": 4, "floor": 2, "connector": 1, "opening": 2}
    assert result["floors"][0]["counts"]["asset"] == 3
    assert result["position"] == session["position"]
    assert result["constraints"] == queries.service.constraints(session)
    assert result["building_state_id"] == queries.service.building_state_id(queries.service.current("query-test"))
    assert result["building_version"] == 0 and speech and display == {"kind": "none"}


def test_search_pages_are_complete_beyond_one_hundred_results(platform):
    queries, session, raw = platform
    for index in range(103):
        raw["assets"].append({**raw["assets"][1], "id": f"extra-{index:03d}"})
    (queries.service.store.directory / "uploads" / "query.json").write_text(json.dumps(raw))
    first, _, _ = queries.search_entities(session, {})
    assert len(first["entities"]) == 25 and first["total"] == 107
    second, _, _ = queries.search_entities(session, {"cursor": first["next_cursor"], "limit": 100})
    ids = [entity["id"] for entity in first["entities"] + second["entities"]]
    assert ids == sorted(asset["id"] for asset in raw["assets"])
    assert second["next_cursor"] is None


@pytest.mark.parametrize("args,expected", [
    ({"type": "printer", "floor_id": "ground", "space_id": "far"}, ["printer-far-a", "printer-far-b"]),
    ({"kind": "space", "type": "office", "floor_id": "upper"}, ["above"]),
    ({"query": "FAR b"}, ["printer-far-b"]),
    ({"kind": "floor", "floor_id": "upper"}, ["upper"]),
    ({"kind": "connector", "floor_id": "upper", "space_id": "above"}, ["stairs"]),
    ({"kind": "opening", "space_id": "middle"}, ["door-a", "door-b"]),
    ({"type": "tool", "floor_id": "upper"}, []),
    ({"query": "Nothing has this name"}, []),
])
def test_search_filters_and_empty_results(platform, args, expected):
    queries, session, _ = platform
    result, _, _ = queries.search_entities(session, args)
    assert ([entity["id"] for entity in result["entities"]], result["total"], result["next_cursor"]) == (expected, len(expected), None)


@pytest.mark.parametrize("change", [{"query": "printer"}, {"type": "printer"}, {"floor_id": "ground"},
                                    {"space_id": "far"}, {"kind": "space"}])
def test_cursor_rejects_different_filters(platform, change):
    queries, session, _ = platform
    first, _, _ = queries.search_entities(session, {"limit": 1})
    with pytest.raises(ServiceError, match="different search filters"):
        queries.search_entities(session, {"cursor": first["next_cursor"], **change})


def test_cursor_rejects_changed_state_even_after_reset_reuses_version(platform):
    queries, session, _ = platform
    service = queries.service
    admin = service.store.create_session(session["building_id"], "desk", "admin")
    proposal = service.propose_edit(admin["session_id"], {"action": "close", "target": "door-a"})
    service.commit_edit(admin["session_id"], proposal["proposal_id"])
    first, _, _ = queries.search_entities(session, {"limit": 1})
    service.store.reset(session["building_id"])
    proposal = service.propose_edit(admin["session_id"], {"action": "close", "target": "door-b"})
    service.commit_edit(admin["session_id"], proposal["proposal_id"])
    assert service.current(session["building_id"]).version == first["building_version"] == 1
    with pytest.raises(ServiceError) as failure:
        queries.search_entities(session, {"cursor": first["next_cursor"]})
    assert failure.value.code == "version_conflict" and failure.value.extra["reason"] == "stale_cursor"


@pytest.mark.parametrize("cursor", ["not base64!", "e30=", "bnVsbA=="])
def test_malformed_cursors_raise_service_errors(platform, cursor):
    queries, session, _ = platform
    with pytest.raises(ServiceError) as failure:
        queries.search_entities(session, {"cursor": cursor})
    assert failure.value.code == "invalid_args"


@pytest.mark.parametrize("args", [{"floor_id": "Ground"}, {"space_id": "Start"}, {"type": "printers"},
                                 {"kind": "opening", "type": "door"}, {"floor": "ground"}])
def test_unknown_filters_are_errors(platform, args):
    queries, session, _ = platform
    with pytest.raises(ServiceError):
        queries.search_entities(session, args)


def test_get_entities_preserves_order_and_includes_each_kind_without_geometry(platform):
    queries, session, raw = platform
    ids = ["stairs", "printer-far-a", "above", "door-a", "upper"]
    result, _, _ = queries.get_entities(session, {"ids": ids})
    assert [entity["id"] for entity in result["entities"]] == ids
    assert result["total"] == len(ids)
    assert result["entities"][1]["position"] == raw["assets"][1]["position"]
    assert result["entities"][1]["rooms"][0]["room_type"] == "office"
    assert not any("polygon" in entity for entity in result["entities"])


def test_get_entities_reports_all_missing_ids_without_a_partial_result(platform):
    queries, session, _ = platform
    with pytest.raises(ServiceError) as failure:
        queries.get_entities(session, {"ids": ["tool", "Tool", "printer-far-c"]})
    assert failure.value.payload()["ids"] == ["Tool", "printer-far-c"]


def test_missing_optional_record_fields_do_not_break_details(platform):
    queries, session, raw = platform
    for field in ("name", "position", "floor_id", "type"):
        raw["assets"][0].pop(field)
    (queries.service.store.directory / "uploads" / "query.json").write_text(json.dumps(raw))
    result, _, _ = queries.get_entities(session, {"ids": ["printer-above"]})
    entity = result["entities"][0]
    assert entity["label"] == "printer-above" and "position" not in entity


def test_step_free_comparison_uses_routes_and_ranks_only_reachable_printers(platform):
    queries, session, raw = platform
    destinations = ["printer-far-b", "printer-above", "printer-far-a"]
    # The upper printer is 3 m away in 3D. The ground printer is 8 m away.
    assert math.dist([2, 2, 0], [*raw["assets"][0]["position"], 3]) < 8
    walking, _, _ = queries.compare_routes(session, {"destination_ids": destinations})
    assert walking["nearest_id"] == "printer-above"
    result, _, display = queries.compare_routes(session, {"destination_ids": destinations, "step_free": True})
    assert result["nearest_id"] == "printer-far-a"
    assert [candidate["id"] for candidate in result["reachable"]] == ["printer-far-a", "printer-far-b"]
    assert result["unreachable"][0]["id"] == "printer-above"
    assert result["unreachable"][0]["route"]["reason"] == "no_step_free_path"
    route = adapter.route(queries.service.current(session["building_id"]), session["position"], "printer-far-a", {"step_free": True})
    assert result["reachable"][0]["route"]["length_m_exact"] == route["length_m_exact"]
    assert "segments" not in result["reachable"][0]["route"] and display == {"kind": "none"}


@pytest.mark.parametrize("profile", ["walk", "wheelchair", "pram", "trolley"])
def test_comparison_preserves_constraints_and_does_not_write_navigation(platform, profile):
    queries, session, _ = platform
    session = queries.service.store.update_session(session["session_id"], {
        "profile": profile, "constraints": {"step_free": True, "closed": ["door-b"],
                                            "min_door_width_m": 0.8, "no_transit_room_types": ["office"]},
    })
    before = deepcopy(session)
    result, _, _ = queries.compare_routes(session, {"destination_ids": ["printer-far-a", "printer-above"],
                                                   "step_free": False, "min_door_width_m": 0.1})
    assert result["nearest_id"] is None and len(result["unreachable"]) == 2
    assert result["constraints"] == before["constraints"]
    assert session == before == queries.service.store.get_session(session["session_id"])
    assert queries.service.store.active_tours(session["building_id"]) == []


def test_comparison_enforces_door_width(platform):
    queries, session, _ = platform
    result, _, _ = queries.compare_routes(session, {"destination_ids": ["printer-far-a"], "min_door_width_m": 1.1})
    assert result["nearest_id"] is None and result["unreachable"][0]["route"]["reason"] == "too_narrow"


@pytest.mark.parametrize("start", ["start", "tool"])
def test_comparison_accepts_explicit_start_without_session_position(platform, start):
    queries, session, _ = platform
    session = queries.service.store.update_session(session["session_id"], {"position": None})
    result, _, _ = queries.compare_routes(session, {"start": start, "destination_ids": ["printer-far-a"]})
    assert result["start"]["space_id"] == ("middle" if start == "tool" else "start")
    assert result["nearest_id"] == "printer-far-a" and session["position"] is None


def test_comparison_unions_temporary_closures_without_navigation_writes(platform):
    queries, session, _ = platform
    session = queries.service.store.update_session(session["session_id"], {"constraints": {"closed": ["door-b"]}})
    before = deepcopy(session)
    result, _, _ = queries.compare_routes(session, {
        "start": "start", "destination_ids": ["printer-above", "printer-far-a"], "closed": ["stairs", "stairs"]})
    assert result["constraints"]["closed"] == ["door-b", "stairs"]
    assert result["nearest_id"] is None and len(result["unreachable"]) == 2
    assert queries.service.store.get_session(session["session_id"]) == session == before
    assert queries.service.store.events(session["building_id"]) == []


@pytest.mark.parametrize("patch", [
    {"start": "Start"}, {"start": "upper"}, {"closed": ["unknown"]},
    {"closed": ["printer-above"]}, {"closed": "stairs"}, {"closed": [None]}, {"closed": [""]},
])
def test_bad_comparison_start_and_closures_fail_before_routing(platform, monkeypatch, patch):
    queries, session, _ = platform

    def unexpected(*args, **kwargs):
        pytest.fail("Validate explicit starts and all closures before routing.")

    monkeypatch.setattr(adapter, "route", unexpected)
    with pytest.raises(ServiceError):
        queries.compare_routes(session, {"destination_ids": ["printer-far-a"], **patch})


@pytest.mark.parametrize("patch", [{"position": None}, {"position": {"space_id": "unknown"}},
    {"position": {"space_id": "start", "point": [float("nan"), 2]}},
    {"position": {"space_id": "start", "point": [200, 2]}},
    {"position": {"space_id": "start", "floor_id": "upper"}},
    {"constraints": {"closed": ["unknown"]}}, {"constraints": {"no_transit_room_types": ["unknown"]}},
    {"constraints": {"min_door_width_m": float("inf")}},
])
def test_all_comparison_inputs_are_validated_before_routing(platform, monkeypatch, patch):
    queries, session, _ = platform
    def unexpected_route(*args, **kwargs):
        pytest.fail("Routing must not start before input validation is complete.")
    monkeypatch.setattr(adapter, "route", unexpected_route)
    with pytest.raises(ServiceError):
        queries.compare_routes({**session, **patch}, {"destination_ids": ["printer-far-a"]})


@pytest.mark.parametrize("destination", ["printer-far-c", "Printer far A", "upper", "stairs", "door-a"])
def test_all_destination_ids_are_validated_before_first_route(platform, monkeypatch, destination):
    queries, session, _ = platform
    def unexpected_route(*args, **kwargs):
        pytest.fail("A later invalid destination must prevent every route call.")
    monkeypatch.setattr(adapter, "route", unexpected_route)
    with pytest.raises(ServiceError):
        queries.compare_routes(session, {"destination_ids": ["printer-far-a", destination]})


@pytest.mark.parametrize("model,args", [
    (InfoArgs, {"extra": True}), (SearchArgs, {"limit": 101}), (SearchArgs, {"limit": 0}),
    (SearchArgs, {"limit": True}), (SearchArgs, {"kind": "unknown"}),
    (GetEntitiesArgs, {"ids": []}), (GetEntitiesArgs, {"ids": ["tool"] * 101}),
    (GetEntitiesArgs, {"ids": [1]}), (GetEntitiesArgs, {"ids": ["  "]}),
    (CompareRoutesArgs, {"destination_ids": []}), (CompareRoutesArgs, {"destination_ids": ["tool"] * 101}),
    (CompareRoutesArgs, {"destination_ids": ["tool"], "min_door_width_m": float("nan")}),
    (CompareRoutesArgs, {"destination_ids": ["tool"], "min_door_width_m": float("inf")}),
    (CompareRoutesArgs, {"destination_ids": ["tool"], "min_door_width_m": -1}),
    (CompareRoutesArgs, {"destination_ids": ["tool"], "step_free": "false"}),
])
def test_argument_models_reject_malformed_inputs(model, args):
    with pytest.raises(ValidationError):
        model.model_validate(args)


@pytest.mark.parametrize("model", [InfoArgs, SearchArgs, GetEntitiesArgs, CompareRoutesArgs])
def test_registry_schemas_forbid_extra_fields(model):
    assert model.model_json_schema()["additionalProperties"] is False


@pytest.mark.parametrize("method,args", [("building_info", {"unknown": 1}), ("search_entities", {"limit": 101}),
    ("get_entities", {"ids": [None]}), ("compare_routes", {"destination_ids": [None]})])
def test_public_methods_raise_service_error_for_invalid_args(platform, method, args):
    queries, session, _ = platform
    with pytest.raises(ServiceError) as failure:
        getattr(queries, method)(session, args)
    assert failure.value.code == "invalid_args"
