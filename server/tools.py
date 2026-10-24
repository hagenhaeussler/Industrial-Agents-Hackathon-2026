"""One typed tool registry shared by HTTP, text chat and ElevenLabs."""

from dataclasses import dataclass
import logging
import time

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Literal

from . import core_adapter as adapter
from .errors import ServiceError
from .state import encode, identifier, now
from .public import public_payload

logger = logging.getLogger(__name__)


class Args(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class FindArgs(Args):
    query: str = Field(min_length=1, max_length=1000)


class TourArgs(Args):
    items: str = Field(min_length=1, max_length=4000)
    keep_order: bool = False
    step_free: bool | None = None


class RouteArgs(Args):
    destination: str = Field(min_length=1, max_length=1000)
    step_free: bool | None = None
    min_door_width_m: float | None = Field(default=None, ge=0)


class SpatialArgs(Args):
    kind: Literal["largest_room", "floor_area_total", "errand", "wide_delivery_count", "step_free_reachable_count", "room_stacked", "shared_walls_count", "straight_line_3d", "what_if_door"]
    target: str | None = None
    second_target: str | None = Field(default=None, description="For step_free_reachable_count, an optional additional connector, door or room to close. With no current or requested closures, count the unmodified building. For other kinds, the second comparison target.")
    floor: str | None = None
    room_type: str | None = None
    asset_type: str | None = None
    direction: Literal["above", "below"] | None = None
    min_width_m: float | None = Field(default=None, ge=0)


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
    Tool("find", "Find a named item or place; ask once if ambiguous.", FindArgs, "_find"),
    Tool("plan_tour", "Plan a tour from the session position through comma-separated items.", TourArgs, "_tour"),
    Tool("route", "Compute a route from the session position, respecting mobility constraints.", RouteArgs, "_route"),
    Tool("next_step", "Return the next instruction of the active tour, including final destination directions and an explicit arrival confirmation.", Args, "_next_step"),
    Tool("spatial_query", "Answer a spatial question through the deterministic core.", SpatialArgs, "_spatial"),
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
        if notify is not None:
            self.service.notify = notify

    def json_schemas(self):
        return [{"name": t.name, "description": t.description, "input_schema": t.json_schema} for t in REGISTRY.values()]

    def call(self, name, session_id, args=None):
        request_id = identifier("req")
        version = 0
        building_id = None
        started = time.perf_counter()
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
            building = self.service.current(building_id)
            source = result.get("_adapter", building.adapter) if isinstance(result, dict) else building.adapter
            return public_payload({"ok": True, "tool": name, "request_id": request_id,
                    "building_id": building_id, "building_version": version,
                    "result": result, "speech": speech, "display": display,
                    "trace": [{"fn": name, "args": values, "ms": round((time.perf_counter() - started) * 1000, 2), "_adapter": source}]})
        except ServiceError as exc:
            error = exc.payload()
            if isinstance(error.get("candidates"), list):
                error["candidates"] = [{**candidate, "name": candidate.get("name") or candidate.get("label") or candidate.get("id")}
                                       if isinstance(candidate, dict) else candidate for candidate in error["candidates"]]
            return public_payload({"ok": False, "tool": name, "request_id": request_id, "building_id": building_id,
                    "building_version": version, "error": error, "speech": exc.message,
                    "trace": [{"fn": name, "args": {}, "ms": round((time.perf_counter() - started) * 1000, 2)}]})
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
        store = self.service.store
        with store.connect(write=True) as db:
            current = store._session(db.execute("SELECT * FROM sessions WHERE session_id=?", (session["session_id"],)).fetchone())
            constraints = dict(current["constraints"])
            profile = current["profile"]
            if args.get("step_free") is True:
                constraints["step_free"] = True
                if profile == "walk":
                    profile = "wheelchair"
            if "min_door_width_m" in args:
                constraints["min_door_width_m"] = args["min_door_width_m"]
            if profile != current["profile"] or constraints != current["constraints"]:
                db.execute("UPDATE sessions SET profile=?,constraints_json=?,updated_at=? WHERE session_id=?", (
                    profile, encode(constraints), now(), current["session_id"]))
                return store._session(db.execute("SELECT * FROM sessions WHERE session_id=?", (current["session_id"],)).fetchone())
            return current

    def _route(self, session, args):
        if not session["position"]:
            raise ServiceError("invalid_args", "Where are you starting? Confirm your room first.")
        building = self.service.current(session["building_id"])
        destination = adapter.require_id(building, args.pop("destination"))
        adapter.position(building, destination)
        adapter.position(building, session["position"])
        session = self._persist_mobility(session, args)
        result = adapter.route(building, session["position"], destination, self.service.constraints(session, args))
        if not result["reachable"]:
            raise ServiceError("no_route", "No route is available under your current mobility constraints.", reason=result["reason"], route=result)
        return result, f"The route is about {result['length_m']:.0f} metres.", {"kind": "route", "route": result}

    def _tour(self, session, args):
        items = [item.strip() for item in args["items"].split(",") if item.strip()]
        if not items:
            raise ServiceError("invalid_args", "Choose at least one item or place.")
        if not session["position"]:
            raise ServiceError("invalid_args", "Where are you starting? Confirm your room first.")
        building = self.service.current(session["building_id"])
        items = [adapter.require_id(building, item) for item in items]
        for item in items:
            adapter.position(building, item)
        adapter.position(building, session["position"])
        session = self._persist_mobility(session, args)
        overrides = {"step_free": args["step_free"]} if "step_free" in args else None
        result = self.service.create_tour(session["session_id"], items, keep_order=args["keep_order"], constraints=overrides)
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
        if kind == "step_free_reachable_count":
            closed = set(building.closed) | set(session["constraints"].get("closed", []))
            if args.get("second_target", "").strip():
                closed.add(adapter.require_id(building, args["second_target"]))
            known = building.kit.spaces.keys() | building.kit.openings.keys() | building.kit.connectors.keys()
            if closed - known:
                raise ServiceError("invalid_args", "Closed elements must be connectors, doors or rooms in this building.")
            inputs["closed"] = sorted(closed)
        result = adapter._call(solve, building.core, kind, inputs)
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

    def json_schemas(self):
        return [{"name": t.name, "description": t.description, "input_schema": t.json_schema} for t in REGISTRY.values()]


registry = _RegistryProxy()
