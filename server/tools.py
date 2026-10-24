"""One typed tool registry shared by HTTP, text chat and ElevenLabs."""

from dataclasses import dataclass
import logging

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from typing import Literal

from . import core_adapter as adapter
from .errors import ServiceError
from .route_queries import RouteQuery, RouteQueryArgs, TourQueryArgs
from .state import identifier
from .public import public_payload
from .agent_queries import AgentQueries, InfoArgs, SearchArgs, GetEntitiesArgs, CompareRoutesArgs

logger = logging.getLogger(__name__)


class Args(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class FindArgs(Args):
    query: str = Field(min_length=1, max_length=1000)


class TourArgs(Args):
    items: list[str] = Field(min_length=1, max_length=100, description="Stable asset or space IDs to visit. The core chooses the route and stop order.")
    keep_order: bool = False
    step_free: bool | None = None
    min_door_width_m: float | None = Field(default=None, ge=0)
    end: str | None = None

    @field_validator("items", mode="before")
    @classmethod
    def legacy_items(cls, value):
        """Accept existing hosted voice configurations during their migration."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("items")
    @classmethod
    def nonempty_ids(cls, value):
        if any(not item.strip() or len(item) > 1000 for item in value):
            raise ValueError("Every destination must be a nonempty entity ID.")
        return value


class RouteArgs(Args):
    destination: str = Field(min_length=1, max_length=1000)
    step_free: bool | None = None
    min_door_width_m: float | None = Field(default=None, ge=0)


class SpatialArgs(Args):
    kind: Literal["largest_room", "floor_area_total", "errand", "wide_delivery_count", "step_free_reachable_count", "room_stacked", "shared_walls_count", "straight_line_3d", "what_if_door", "count", "locate"]
    target: str | None = None
    second_target: str | None = Field(default=None, description="For step_free_reachable_count, an optional additional connector, door or room to close. With no current or requested closures, count the unmodified building. For other kinds, the second comparison target.")
    floor: str | None = None
    room_type: str | None = None
    asset_type: str | None = None
    direction: Literal["above", "below"] | None = None
    min_width_m: float | None = Field(default=None, ge=0)
    step_free: bool | None = None
    closed: list[str] = Field(default_factory=list, max_length=100)


class EditArgs(Args):
    action: Literal["close", "open", "add_door", "move_asset", "set_room_type"]
    target: str = Field(min_length=1, max_length=1000)
    second_target: str | None = None
    value: str | None = None
    op_id: str | None = None


class CommitArgs(Args):
    proposal_id: str = Field(min_length=1)
    expected_version: int | None = Field(default=None, ge=0)
    op_id: str | None = None


class UndoArgs(Args):
    event_id: str | None = None
    op_id: str | None = None


class ScaleArgs(Args):
    reference: str
    length_m: float = Field(gt=0)


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    args_model: type[BaseModel]
    handler: str
    roles: frozenset[str] = frozenset({"navigator", "admin"})

    @property
    def json_schema(self):
        return self.args_model.model_json_schema()


_DEFINITIONS = [
    Tool("building_info", "Discover this building's floors, entity types, counts and current session constraints.", InfoArgs, "_building_info"),
    Tool("search_entities", "List and filter building objects with complete paginated results. Use real types and IDs from building_info.", SearchArgs, "_search_entities"),
    Tool("get_entities", "Fetch details for stable entity IDs. Unknown IDs fail explicitly.", GetEntitiesArgs, "_get_entities"),
    Tool("compare_routes", "Compare actual routes to candidate IDs under mobility constraints. Returns the nearest reachable destination and unreachable reasons without changing navigation.", CompareRoutesArgs, "_compare_routes"),
    Tool("query_route", "Calculate a route from an explicit start or session position, with temporary closures. Does not save navigation or mobility. Unreachable routes include reasons.", RouteQueryArgs, "_query_route"),
    Tool("query_tour", "Calculate a multi-stop tour without saving navigation. Accepts explicit start, final destination, stop order and temporary closures.", TourQueryArgs, "_query_tour"),
    Tool("find", "Find a named item or place; ask once if ambiguous.", FindArgs, "_find"),
    Tool("plan_tour", "Plan a tour through an array of entity IDs, with optional final destination and mobility constraints.", TourArgs, "_tour"),
    Tool("route", "Compute a route from the session position, respecting mobility constraints.", RouteArgs, "_route"),
    Tool("next_step", "Return the next instruction of the active tour, including final destination directions and an explicit arrival confirmation.", Args, "_next_step"),
    Tool("spatial_query", "Compute areas, counts, asset locations, adjacency, 3D distances, reachability or a hypothetical door. Use IDs and types from discovery. Temporary closures do not save edits.", SpatialArgs, "_spatial"),
    Tool("propose_edit", "Preview an edit without changing the building.", EditArgs, "_propose", frozenset({"admin"})),
    Tool("commit_edit", "Commit a confirmed proposal exactly once.", CommitArgs, "_commit", frozenset({"admin"})),
    Tool("undo", "Undo the last own change or a specified event.", UndoArgs, "_undo", frozenset({"admin"})),
    Tool("what_if", "Preview a hypothetical edit without saving it.", EditArgs, "_what_if", frozenset({"admin"})),
    Tool("set_scale", "Set the scale of an imported floor plan when import is available.", ScaleArgs, "_scale", frozenset({"admin"})),
    Tool("generate_markers", "Create position markers and return a printable sheet URL.", Args, "_markers", frozenset({"admin"})),
]
REGISTRY = {tool.name: tool for tool in _DEFINITIONS}


class ToolRegistry:
    REGISTRY = REGISTRY

    def __init__(self, service, notify=None):
        self.service = service
        self.queries = AgentQueries(service)
        self.route_queries = RouteQuery(service)
        if notify is not None:
            self.service.notify = notify

    def json_schemas(self, role=None):
        return [{"name": t.name, "description": t.description, "input_schema": t.json_schema}
                for t in REGISTRY.values() if role is None or role in t.roles]

    def _building_info(self, session, args):
        return self.queries.building_info(session, args)

    def _search_entities(self, session, args):
        return self.queries.search_entities(session, args)

    def _get_entities(self, session, args):
        return self.queries.get_entities(session, args)

    def _compare_routes(self, session, args):
        return self.queries.compare_routes(session, args)

    def _query_route(self, session, args):
        result, speech, display = self.route_queries.route(session, args)
        start = args.get("start") or result["start"]["space_id"]
        result["calculation"] = {"kind": "route", "inputs": {
            "start": start, "destination": args["destination"],
            **{key: result["constraints"][key] for key in ("step_free", "closed", "min_door_width_m")},
        }}
        return result, speech, display

    def _query_tour(self, session, args):
        result, speech, display = self.route_queries.tour(session, args)
        start = args.get("start") or result["start"]["space_id"]
        stops = [start, *args["items"], *([args["end"]] if args.get("end") else [])]
        result["calculation"] = {"kind": "tour", "inputs": {
            "stops": stops, "keep_order": args.get("keep_order", False),
        }}
        return result, speech, display

    def call(self, name, session_id, args=None):
        # Reserved envelope field stays empty: calculation explanations are disabled.
        request_id = identifier("req")
        version = 0
        building_id = None
        try:
            if name not in REGISTRY:
                raise ServiceError("invalid_args", "Unknown tool.")
            tool = REGISTRY[name]
            session = self.service.store.get_session(session_id)
            building_id = session["building_id"]
            version = self.service.store.version(building_id)
            if session["role"] not in tool.roles:
                raise ServiceError("forbidden", "Changes need the admin view.", status=403)
            try:
                values = tool.args_model.model_validate(args or {}).model_dump(exclude_none=True)
            except ValidationError as exc:
                raise ServiceError("invalid_args", "Check the tool's required fields and argument types.", fields=[".".join(map(str, e["loc"])) for e in exc.errors()]) from exc
            result, speech, display = getattr(self, tool.handler)(session, dict(values))
            version = self.service.store.version(building_id)
            return public_payload({"ok": True, "tool": name, "request_id": request_id,
                    "building_id": building_id, "building_version": version,
                    "result": result, "speech": speech, "display": display,
                    "trace": []})
        except ServiceError as exc:
            error = exc.payload()
            if isinstance(error.get("candidates"), list):
                error["candidates"] = [{**candidate, "name": candidate.get("name") or candidate.get("label") or candidate.get("id")}
                                       if isinstance(candidate, dict) else candidate for candidate in error["candidates"]]
            return public_payload({"ok": False, "tool": name, "request_id": request_id, "building_id": building_id,
                    "building_version": version, "error": error, "speech": exc.message,
                    "trace": []})
        except Exception:
            logger.exception("Tool failed request_id=%s tool=%s", request_id, name)
            return {"ok": False, "tool": name, "request_id": request_id, "building_id": building_id,
                    "building_version": version, "error": {"code": "internal", "message": "This request failed. Please try again."},
                    "speech": "This request failed. Please try again.", "trace": []}

    def _find(self, session, args):
        building = self.service.current(session["building_id"])
        candidates = []
        for kind in ("asset", "space"):
            candidates.extend(adapter.resolve(building, args["query"], kind)["candidates"])
        if not candidates:
            raise ServiceError("not_found", "No item or place matches that name.")
        # Scores are meaningful within a match stage: token-set fuzzy matches
        # can score 1.0, which must never outrank an exact result in another kind.
        stages = {"exact ID": 3, "exact name/ref": 2, "exact name/ref/label": 2,
                  "exact ref/name": 2, "exact ref": 2, "exact name": 2, "exact label": 2,
                  "normalized": 1}
        rank = lambda candidate: (stages.get(candidate.get("why"), 0), candidate["score"])
        best = max(map(rank, candidates))
        candidates = sorted((candidate for candidate in candidates if rank(candidate) == best), key=lambda candidate: candidate["id"])
        if len(candidates) > 1:
            raise ServiceError("ambiguous", "Which of these did you mean?", candidates=candidates[:4])
        candidate = candidates[0]
        position = adapter.position(building, candidate["id"])
        space = building.kit.spaces[position["space_id"]]
        floor = building.kit.floors[space["floor_id"]]
        result = {**candidate, **position}
        return result, f"{candidate['label']} is in {space['name']} on {floor['name']}.", {"kind": "highlight", "space_id": space["id"], "asset_id": candidate["id"] if candidate["kind"] == "asset" else None, "asset_ids": [candidate["id"]] if candidate["kind"] == "asset" else [], "floor_id": space["floor_id"]}

    def _persist_mobility(self, session, args):
        """Merge validated intent atomically with the latest shared session."""
        return self.service.store.merge_mobility(session["session_id"], args)

    def _route(self, session, args):
        if not session["position"]:
            raise ServiceError("invalid_args", "Where are you starting? Confirm your room first.")
        building = self.service.current(session["building_id"])
        destination = adapter.require_id(building, args.pop("destination"))
        adapter.position(building, destination)
        adapter.position(building, session["position"])
        session = self._persist_mobility(session, args)
        result = adapter.route(building, session["position"], destination, self.service.constraints(session, args))
        result["building_state_id"] = self.service.building_state_id(building)
        if not result["reachable"]:
            raise ServiceError("no_route", "No route is available under your current mobility constraints.", reason=result["reason"], route=result)
        return result, f"The route is about {result['length_m']:.0f} metres.", {"kind": "route", "route": result}

    def _tour(self, session, args):
        items = args["items"]
        if not items:
            raise ServiceError("invalid_args", "Choose at least one item or place.")
        if not session["position"]:
            raise ServiceError("invalid_args", "Where are you starting? Confirm your room first.")
        building = self.service.current(session["building_id"])
        items = [adapter.require_id(building, item) for item in items]
        for item in items:
            adapter.position(building, item)
        adapter.position(building, session["position"])
        if args.get("end") is not None:
            args["end"] = adapter.require_id(building, args["end"])
            adapter.position(building, args["end"])
        session = self._persist_mobility(session, args)
        overrides = {key: args[key] for key in ("step_free", "min_door_width_m") if key in args}
        result = self.service.create_tour(session["session_id"], items, keep_order=args["keep_order"], end=args.get("end"), constraints=overrides)
        blocked = result.get("unreachable_stops", [])
        speech = f"The tour has {len(result['stops'])} stops, about {result['length_m']:.0f} metres."
        if blocked:
            speech += f" {len(blocked)} stops cannot currently be reached."
        return result, speech, {"kind": "tour", "tour_id": result["tour_id"]}

    def _next_step(self, session, args):
        result = self.service.next_step(session["session_id"])
        return result, result["text"], {"kind": "instruction", "instruction": result}

    def _spatial(self, session, args):
        building = self.service.current(session["building_id"])
        solve = adapter.core_function("spatial", "solve")
        if building.core is None or solve is None:
            raise ServiceError("not_available", "Spatial question tools are waiting for the core integration.")
        kind = args["kind"]
        fields = {
            "locate": {"target": "asset"},
            "count": {"asset_type": "asset_type", "floor": "floor_id"},
            "largest_room": {"floor": "floor_id", "room_type": "room_type"},
            "floor_area_total": {"floor": "floor_id", "room_type": "room_type"},
            "errand": {"target": "start", "asset_type": "asset_type", "floor": "floor_id", "room_type": "room_type"},
            "wide_delivery_count": {"target": "start", "floor": "floor_id", "min_width_m": "min_width"},
            "step_free_reachable_count": {"target": "start", "floor": "floor_id"},
            "room_stacked": {"target": "start", "direction": "direction"},
            "shared_walls_count": {"target": "start"},
            "straight_line_3d": {"target": "first", "second_target": "second"},
            "what_if_door": {"target": "first", "second_target": "second", "floor": "floor_id"},
        }[kind]
        inputs = {}
        for source, target in fields.items():
            if source not in args:
                raise ServiceError("invalid_args", f"Please provide {source.replace('_', ' ')}.")
            value = args[source]
            if source in {"target", "second_target", "floor", "room_type", "asset_type"}:
                entity_kind = "floor" if source == "floor" else source if source in {"room_type", "asset_type"} else "any"
                value = adapter.require_id(building, value, entity_kind)
            inputs[target] = value
        constraints = self.service.constraints(session, {
            "step_free": args.get("step_free"), "min_door_width_m": args.get("min_width_m"),
            "closed": args.get("closed", []),
        })
        constraints["closed"] = sorted(set(constraints["closed"]) | building.kit.closed)
        if kind in {"step_free_reachable_count", "wide_delivery_count"}:
            constraints["step_free"] = True
        if kind == "step_free_reachable_count" and args.get("second_target", "").strip():
            constraints["closed"] = sorted(set(constraints["closed"]) | {adapter.require_id(building, args["second_target"])})
        known = building.kit.spaces.keys() | building.kit.openings.keys() | building.kit.connectors.keys()
        if set(constraints["closed"]) - known:
            raise ServiceError("invalid_args", "Closed elements must be connectors, doors or rooms in this building.")
        if kind == "locate" and inputs["asset"] not in building.kit.assets:
            raise ServiceError("invalid_args", "Location requires an asset ID.")
        if kind == "step_free_reachable_count":
            inputs["closed"] = constraints["closed"]
        result = adapter._call(solve, building.core, kind, inputs, constraints=constraints)
        result["calculation"] = {"kind": kind, "inputs": inputs}
        result["constraints"] = constraints
        result["building_state_id"] = self.service.building_state_id(building)
        value = result.get("value", result.get("area_m2", result.get("space_id")))
        return result, f"The computed result is {value}.", {"kind": "spatial_result", "result": result}

    def _propose(self, session, args):
        op_id = args.pop("op_id", None)
        result = self.service.propose_edit(session["session_id"], args, op_id)
        return result, result["summary"] + ". Shall I apply this change?", {"kind": "edit_preview", **result}

    def _commit(self, session, args):
        result = self.service.commit_edit(session["session_id"], **args)
        return result, result["summary"] + ". The change is saved.", {"kind": "edit_committed", "event": result}

    def _undo(self, session, args):
        result = self.service.undo(session["session_id"], **args)
        return result, result["summary"] + ".", {"kind": "edit_committed", "event": result}

    def _what_if(self, session, args):
        building = self.service.current(session["building_id"])
        args.pop("op_id", None)
        edit = adapter.resolve_edit(building, args)
        result = adapter.preview_edit(building, edit, self.service.store.active_tours(building.id))
        return result, result["summary"] + ". This is a preview; nothing has been changed.", {"kind": "what_if", **result}

    def _scale(self, session, args):
        raise ServiceError("not_available", "Plan scale editing is not available; upload a building JSON instead.")

    def _markers(self, session, args):
        if not self.service.marker_generator:
            raise ServiceError("not_available", "Marker generation is not connected yet.")
        result = self.service.marker_generator(session["session_id"])
        return result, "The position marker sheet is ready to print.", {"kind": "markers", **result}


class _RegistryProxy:
    """Configure once per application startup; importable before the service runs."""
    target = None

    def configure(self, service, notify=None):
        self.target = ToolRegistry(service, notify)
        return self.target

    def call(self, name, session_id, args=None):
        if self.target is None:
            raise ServiceError("not_available", "The platform service has not started.")
        return self.target.call(name, session_id, args)

    def json_schemas(self, role=None):
        return [{"name": t.name, "description": t.description, "input_schema": t.json_schema}
                for t in REGISTRY.values() if role is None or role in t.roles]


registry = _RegistryProxy()
