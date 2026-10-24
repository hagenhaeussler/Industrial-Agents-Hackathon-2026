"""Structured, read-only building queries for agent tools.

Search pages use ID order and substring text matching. Cursors bind the filters
and materialised state; callers may change the page size between requests.
Route comparisons use room destinations, as defined by the routing contract.
"""

import base64
import binascii
from copy import deepcopy
import hashlib
import json
from typing import Any, Literal

from pydantic import Field, ValidationError

from . import core_adapter as adapter
from .errors import ServiceError
from .route_queries import (
    EntityId, QueryArgs as _Args, QueryResponse, RouteOptions,
    prepare_route_query, require_route_target, validate_query_args as _validated,
)
from .service import PlatformService


EntityKind = Literal["asset", "space", "floor", "connector", "opening"]


class InfoArgs(_Args):
    pass


class SearchArgs(_Args):
    kind: EntityKind = "asset"
    query: str | None = Field(default=None, max_length=1000)
    type: EntityId | None = Field(default=None, description="Exact asset type or room type, for asset or space searches.")
    floor_id: EntityId | None = None
    space_id: EntityId | None = None
    limit: int = Field(default=25, ge=1, le=100)
    cursor: str | None = Field(default=None, min_length=1, max_length=4096)


class GetEntitiesArgs(_Args):
    ids: list[EntityId] = Field(min_length=1, max_length=100)


class CompareRoutesArgs(RouteOptions):
    destination_ids: list[EntityId] = Field(min_length=1, max_length=100)


class _Cursor(_Args):
    building_state_id: str
    fingerprint: str
    offset: int = Field(gt=0)


def _sources(building: adapter.AdaptedBuilding) -> dict[str, dict]:
    kit = building.kit
    return {"asset": kit.assets, "space": kit.spaces, "floor": kit.floors,
            "connector": kit.connectors, "opening": kit.openings}


def _require_exact(building: adapter.AdaptedBuilding, entity_id: str, kind: str) -> str:
    sources = _sources(building)
    records = sources.values() if kind == "any" else [sources[kind]]
    if not any(entity_id in group for group in records):
        raise ServiceError("not_found", f"Unknown {kind} ID: {entity_id}", ids=[entity_id])
    return adapter.require_id(building, entity_id, kind)


def _locations(kind: str, record: dict) -> tuple[list[str], list[str]]:
    floors = [record["floor_id"]] if record.get("floor_id") else list(record.get("floor_ids", []))
    spaces = [record["space_id"]] if record.get("space_id") else list(record.get("space_ids", []))
    if kind == "floor":
        floors = [record["id"]]
    if kind == "space":
        spaces = [record["id"]]
    return floors, spaces


def _entity(building: adapter.AdaptedBuilding, kind: str, record: dict) -> dict[str, Any]:
    """Keep useful attributes and small positions, without polygons or meshes."""
    fields = ("id", "name", "ref", "type", "room_type", "floor_id", "space_id",
              "floor_ids", "space_ids", "position", "level", "elevation_m", "height_m",
              "width_m", "step_free")
    result = {key: deepcopy(record[key]) for key in fields if record.get(key) is not None}
    result["kind"] = kind
    if kind in {"opening", "connector"} and record.get("kind"):
        result["type"] = record["kind"]
    floors, spaces = _locations(kind, record)
    floor_names = [building.kit.floors[fid].get("name", fid) for fid in floors if fid in building.kit.floors]
    result["label"] = record.get("name") or record.get("ref") or record["id"]
    if floor_names and kind != "floor":
        result["label"] += f" ({', '.join(floor_names)})"
    if floor_names:
        result["floor_names"] = floor_names
    rooms = [building.kit.spaces[sid] for sid in spaces if sid in building.kit.spaces]
    if rooms:
        result["rooms"] = [{key: room[key] for key in ("id", "name", "ref", "room_type", "floor_id")
                            if room.get(key) is not None} for room in rooms]
    if kind == "space":
        result["position"] = adapter.position(building, record["id"])["point"]
    result["closed"] = record["id"] in building.closed
    return result


def _types(records: dict, field: str) -> list[str]:
    return sorted({record[field] for record in records.values() if record.get(field)})


def _validate_filters(building: adapter.AdaptedBuilding, args: SearchArgs) -> None:
    if args.floor_id is not None:
        _require_exact(building, args.floor_id, "floor")
    if args.space_id is not None:
        _require_exact(building, args.space_id, "space")
    if args.type is not None:
        if args.kind not in {"asset", "space"}:
            raise ServiceError("invalid_args", "Type filters apply only to assets or spaces.")
        field = "type" if args.kind == "asset" else "room_type"
        if args.type not in _types(_sources(building)[args.kind], field):
            raise ServiceError("invalid_args", f"Unknown {field}: {args.type}", fields=["type"])


def _matches(record: dict, args: SearchArgs) -> bool:
    floors, spaces = _locations(args.kind, record)
    if args.floor_id is not None and args.floor_id not in floors:
        return False
    if args.space_id is not None and args.space_id not in spaces:
        return False
    field = "room_type" if args.kind == "space" else "type"
    return args.type is None or record.get(field) == args.type


def _fingerprint(args: SearchArgs) -> str:
    filters = args.model_dump(exclude={"cursor", "limit"})
    return hashlib.sha256(json.dumps(filters, sort_keys=True).encode()).hexdigest()


def _page_offset(args: SearchArgs, state_id: str, total: int) -> int:
    if args.cursor is None:
        return 0
    try:
        decoded = base64.b64decode(args.cursor, altchars=b"-_", validate=True)
        cursor = _Cursor.model_validate_json(decoded)
    except (ValueError, binascii.Error, ValidationError) as exc:
        raise ServiceError("invalid_args", "Invalid search cursor.") from exc
    if cursor.building_state_id != state_id:
        raise ServiceError("version_conflict", "The building changed. Start a new search.", status=409,
                           reason="stale_cursor", building_state_id=state_id)
    if cursor.fingerprint != _fingerprint(args):
        raise ServiceError("invalid_args", "The cursor belongs to different search filters.")
    if cursor.offset >= total:
        raise ServiceError("invalid_args", "The cursor is outside these search results.")
    return cursor.offset


def _next_cursor(args: SearchArgs, state_id: str, offset: int) -> str:
    cursor = _Cursor(building_state_id=state_id, fingerprint=_fingerprint(args), offset=offset)
    return base64.urlsafe_b64encode(cursor.model_dump_json().encode()).decode()


class AgentQueries:
    """Return query results, short speech and display metadata without navigation writes."""

    def __init__(self, service: PlatformService):
        self.service = service

    def _metadata(self, building: adapter.AdaptedBuilding) -> dict[str, Any]:
        return {"building_id": building.id, "building_version": building.version,
                "building_state_id": self.service.building_state_id(building)}

    def building_info(self, session: dict, args: dict | InfoArgs) -> QueryResponse:
        _validated(InfoArgs, args)
        building = self.service.current(session["building_id"])
        sources = _sources(building)
        floors = []
        for floor in sorted(building.kit.floors.values(), key=lambda item: (item.get("level", 0), item["id"])):
            summary = _entity(building, "floor", floor)
            summary["counts"] = {kind: sum(floor["id"] in _locations(kind, record)[0]
                                          for record in records.values()) for kind, records in sources.items()}
            floors.append(summary)
        result = {**self._metadata(building), "name": building.raw["building"].get("name", building.id),
                  "floors": floors, "asset_types": _types(building.kit.assets, "type"),
                  "room_types": _types(building.kit.spaces, "room_type"),
                  "counts": {kind: len(records) for kind, records in sources.items()},
                  "constraints": deepcopy(self.service.constraints(session)),
                  "position": deepcopy(session.get("position")), "closed": sorted(building.closed)}
        return result, f"{result['name']} has {len(floors)} floors.", {"kind": "none"}

    def search_entities(self, session: dict, args: dict | SearchArgs) -> QueryResponse:
        values = _validated(SearchArgs, args)
        building = self.service.current(session["building_id"])
        _validate_filters(building, values)
        query = (values.query or "").strip().casefold()
        entities = []
        for entity_id, record in sorted(_sources(building)[values.kind].items()):
            if not _matches(record, values):
                continue
            entity = _entity(building, values.kind, record)
            text = " ".join(str(entity.get(field, "")) for field in ("id", "name", "ref", "label", "type", "room_type"))
            if not query or query in text.casefold():
                entities.append(entity)
        metadata = self._metadata(building)
        offset = _page_offset(values, metadata["building_state_id"], len(entities))
        end = offset + values.limit
        result = {**metadata, "entities": entities[offset:end], "total": len(entities),
                  "next_cursor": _next_cursor(values, metadata["building_state_id"], end) if end < len(entities) else None}
        speech = f"Returned {len(result['entities'])} of {result['total']} matching entities."
        return result, speech, {"kind": "none"}

    def get_entities(self, session: dict, args: dict | GetEntitiesArgs) -> QueryResponse:
        values = _validated(GetEntitiesArgs, args)
        building = self.service.current(session["building_id"])
        sources = _sources(building)
        missing = sorted(set(values.ids) - {entity_id for records in sources.values() for entity_id in records})
        if missing:
            raise ServiceError("not_found", "Some entity IDs are absent from this building.", ids=missing)
        entities = []
        for entity_id in values.ids:
            _require_exact(building, entity_id, "any")
            kind = next(kind for kind, records in sources.items() if entity_id in records)
            entities.append(_entity(building, kind, sources[kind][entity_id]))
        result = {**self._metadata(building), "entities": entities, "total": len(entities)}
        return result, f"Returned details for {len(entities)} entities.", {"kind": "none"}

    def compare_routes(self, session: dict, args: dict | CompareRoutesArgs) -> QueryResponse:
        values = _validated(CompareRoutesArgs, args)
        context = prepare_route_query(self.service, session, values)
        building, start, constraints = context.building, context.start, context.constraints
        destinations = sorted(set(values.destination_ids))
        for entity_id in destinations:
            require_route_target(building, entity_id)
        reachable, unreachable = [], []
        for entity_id in destinations:
            route = adapter.route(building, start, entity_id, deepcopy(constraints))
            kind = "asset" if entity_id in building.kit.assets else "space"
            candidate = _entity(building, kind, _sources(building)[kind][entity_id])
            summary = {key: deepcopy(route[key]) for key in (
                "reachable", "length_m", "length_m_exact", "reason", "blocking_ids",
                "from_space_id", "to_space_id", "profile", "geometry", "_adapter",
            ) if key in route}
            candidate["route"] = summary
            (reachable if route["reachable"] else unreachable).append(candidate)
        reachable.sort(key=lambda item: (item["route"].get("length_m_exact", item["route"]["length_m"]), item["id"]))
        result = {**self._metadata(building), "reachable": reachable, "unreachable": unreachable,
                  "nearest_id": reachable[0]["id"] if reachable else None,
                  "constraints": constraints, "start": deepcopy(start), "total": len(destinations)}
        speech = (f"The nearest reachable destination is {reachable[0]['label']}." if reachable
                  else "No candidate is reachable under the current constraints.")
        return result, speech, {"kind": "none"}
