"""Route and tour computations without saved navigation or building edits."""

from copy import deepcopy
from dataclasses import dataclass
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from . import core_adapter as adapter
from .errors import ServiceError
from .schemas import Constraints
from .service import PlatformService


EntityId = Annotated[str, StringConstraints(min_length=1, max_length=1000, strip_whitespace=True)]
QueryResponse = tuple[dict[str, Any], str, dict[str, Any]]


class QueryArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class RouteOptions(QueryArgs):
    start: EntityId | None = None
    step_free: bool | None = None
    min_door_width_m: float | None = Field(default=None, ge=0)
    closed: list[EntityId] = Field(default_factory=list)


class RouteQueryArgs(RouteOptions):
    destination: EntityId


class TourQueryArgs(RouteOptions):
    items: list[EntityId] = Field(min_length=1, max_length=100)
    keep_order: bool = False
    end: EntityId | None = None


def validate_query_args[Model: BaseModel](model: type[Model], args: Any) -> Model:
    try:
        return model.model_validate(args, strict=True)
    except ValidationError as exc:
        raise ServiceError(
            "invalid_args", "Check the query fields and argument types.",
            fields=[".".join(map(str, error["loc"])) for error in exc.errors()],
        ) from exc


@dataclass(frozen=True)
class RouteQueryContext:
    building: adapter.AdaptedBuilding
    start: dict[str, Any]
    constraints: dict[str, Any]
    metadata: dict[str, Any]


def require_route_target(building: adapter.AdaptedBuilding, entity_id: str) -> str:
    """Accept stable space and asset IDs, without resolving labels."""
    if entity_id not in building.kit.spaces and entity_id not in building.kit.assets:
        raise ServiceError("not_found", f"Unknown space or asset ID: {entity_id}", ids=[entity_id])
    adapter.position(building, entity_id)
    return entity_id


def prepare_route_query(service: PlatformService, session: dict, args: RouteOptions) -> RouteQueryContext:
    """Validate shared inputs before a caller computes any routes."""
    building = service.current(session["building_id"])
    metadata = {"building_id": building.id, "building_version": building.version,
                "building_state_id": service.building_state_id(building)}
    # Validate stored values before the constraint merge performs set/numeric operations.
    validate_query_args(Constraints, session.get("constraints", {}))
    base = validate_query_args(Constraints, service.constraints(session)).model_dump()
    overrides = args.model_dump(include={"step_free", "min_door_width_m", "closed"}, exclude_none=True)
    constraints = validate_query_args(Constraints, service.constraints(session, overrides)).model_dump()
    constraints["step_free"] = base["step_free"] or constraints["step_free"]
    constraints["min_door_width_m"] = max(base["min_door_width_m"], constraints["min_door_width_m"])
    constraints["closed"] = sorted(set(base["closed"]) | set(constraints["closed"]) | set(building.closed))
    allowed_closed = building.kit.spaces.keys() | building.kit.openings.keys() | building.kit.connectors.keys()
    unknown_closed = sorted(set(constraints["closed"]) - allowed_closed)
    if unknown_closed:
        raise ServiceError("not_found", "Unknown closed element IDs.", ids=unknown_closed)
    room_types = {space.get("room_type") for space in building.kit.spaces.values()}
    unknown_types = sorted(set(constraints["no_transit_room_types"]) - room_types)
    if unknown_types:
        raise ServiceError("invalid_args", "Unknown restricted room types.", room_types=unknown_types)
    start = args.start if args.start is not None else session.get("position")
    if start is None:
        raise ServiceError("invalid_args", "Provide a starting space or asset ID, or confirm your starting room first.")
    if isinstance(start, str):
        require_route_target(building, start)
    return RouteQueryContext(building, adapter.position(building, start), constraints, metadata)


class RouteQuery:
    """Use shared routing and stop grouping without writing session or tour state."""

    def __init__(self, service: PlatformService):
        self.service = service

    def route(self, session: dict, args: dict | RouteQueryArgs) -> QueryResponse:
        values = validate_query_args(RouteQueryArgs, args)
        context = prepare_route_query(self.service, session, values)
        destination = require_route_target(context.building, values.destination)
        result = adapter.route(context.building, context.start, destination, deepcopy(context.constraints))
        result = {**result, **context.metadata, "start": deepcopy(context.start),
                  "destination": destination, "constraints": deepcopy(context.constraints)}
        speech = (f"The route is about {result['length_m']:.0f} metres." if result["reachable"]
                  else "No route is available under the current constraints.")
        return result, speech, {"kind": "none"}

    def tour(self, session: dict, args: dict | TourQueryArgs) -> QueryResponse:
        values = validate_query_args(TourQueryArgs, args)
        context = prepare_route_query(self.service, session, values)
        items = [require_route_target(context.building, item) for item in values.items]
        end = require_route_target(context.building, values.end) if values.end is not None else None
        stops = self.service._stops(context.building, items)
        result = adapter.plan_tour(context.building, context.start, stops, deepcopy(context.constraints),
                                   keep_order=values.keep_order, end=end)
        result = {**result, **context.metadata, "start": deepcopy(context.start),
                  "constraints": deepcopy(context.constraints), "keep_order": values.keep_order,
                  "reachable": not result.get("unreachable_stops")}
        for leg in result.get("legs", []):
            leg["building_state_id"] = context.metadata["building_state_id"]
        blocked = len(result.get("unreachable_stops", []))
        speech = f"The tour visits {len(result['order'])} stops, about {result['length_m']:.0f} metres."
        if blocked:
            speech += f" {blocked} stops or final destinations are unreachable."
        return result, speech, {"kind": "none"}
