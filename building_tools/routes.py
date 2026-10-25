"""Route tools: routes with stops, reachable spaces and the effect of a change on walks out of the building."""

import itertools
from typing import Literal

import networkx as nx

from building_tools.building import Building, SpaceType, ToolInputError, ToolResult, normalize
from building_tools.network import Node, RouteConditions, RouteNetwork, space_node


class SpaceRef(ToolResult):
    id: str
    name: str
    floor_name: str


class ElementStep(ToolResult):
    id: str
    kind: Literal["door", "opening", "entrance", "stairs", "lift"]
    name: str | None = None
    width_m: float | None = None


class RouteLeg(ToolResult):
    start: SpaceRef
    end: SpaceRef
    reachable: bool
    length_m: float | None
    spaces: list[SpaceRef]
    """Every space passed, in order, including corridors crossed from door to door."""
    elements: list[ElementStep]
    """Openings, stairs and lifts used, in order. A stair appears once per flight."""
    blocked_by: list[str]
    """For an unreachable leg: the conditions that, each lifted alone, would make it reachable."""


class Route(ToolResult):
    reachable: bool
    length_m: float | None
    """Total walking length of all legs in m, or None if a leg is unreachable."""
    legs: list[RouteLeg]


def space_ref(building: Building, space_id: str) -> SpaceRef:
    space = building.space(space_id)
    return SpaceRef(id=space.id, name=space.name, floor_name=building.floor_by_id[space.floor_id].name)


def route(
    building: Building,
    stops: list[str],
    conditions: RouteConditions | None = None,
    leg_conditions: list[RouteConditions] | None = None,
) -> Route:
    """The shortest walk through `stops` in order. `leg_conditions`, if given, sets the conditions of each leg."""
    if len(stops) < 2:
        raise ToolInputError("a route needs at least two stops")
    for stop in stops:
        building.space(stop)
    pairs = list(itertools.pairwise(stops))
    if leg_conditions is not None and len(leg_conditions) != len(pairs):
        raise ToolInputError(f"leg_conditions needs one entry per leg: {len(pairs)}")
    legs = [
        shortest_leg(building, start, end, leg_conditions[index] if leg_conditions else conditions or RouteConditions())
        for index, (start, end) in enumerate(pairs)
    ]
    reachable = all(leg.reachable for leg in legs)
    total = round(sum(leg.length_m or 0.0 for leg in legs), 2) if reachable else None
    return Route(reachable=reachable, length_m=total, legs=legs)


def shortest_leg(building: Building, start: str, end: str, conditions: RouteConditions) -> RouteLeg:
    network = RouteNetwork(building, conditions, leavable=frozenset({start}))
    found = network.shortest_path(space_node(start), space_node(end))
    if found is None:
        return RouteLeg(
            start=space_ref(building, start),
            end=space_ref(building, end),
            reachable=False,
            length_m=None,
            spaces=[],
            elements=[],
            blocked_by=blocking_conditions(building, start, end, conditions),
        )
    length, nodes = found
    spaces: list[str] = []
    elements: list[ElementStep] = []
    for index, node in enumerate(nodes):
        edge = network.cheapest(nodes[index - 1], node) if index else None
        if edge is not None and edge.connector_id is not None:
            connector = building.connector_by_id[edge.connector_id]
            elements.append(ElementStep(id=connector.id, kind=connector.kind, name=connector.name))
        if node[0] == "opening":
            opening = network.openings[node[1]]
            elements.append(ElementStep(id=opening.id, kind=opening.kind, width_m=opening.width_m))
        for space_id in (edge.space_id if edge else None, node[1] if node[0] == "space" else None):
            if space_id is not None and (not spaces or spaces[-1] != space_id):
                spaces.append(space_id)
    return RouteLeg(
        start=space_ref(building, start),
        end=space_ref(building, end),
        reachable=True,
        length_m=round(length, 2),
        spaces=[space_ref(building, space_id) for space_id in spaces],
        elements=elements,
        blocked_by=[],
    )


def blocking_conditions(building: Building, start: str, end: str, conditions: RouteConditions) -> list[str]:
    """Which active conditions, each lifted alone, would let the leg through."""
    relaxed = {
        "closed": {"closed": []},
        "step_free": {"step_free": False},
        "min_door_width_m": {"min_door_width_m": 0.0},
        "no_pass_through_room_types": {"no_pass_through_room_types": []},
    }
    blocking = []
    for name, change in relaxed.items():
        if getattr(conditions, name) in ([], False, 0.0):
            continue
        network = RouteNetwork(building, conditions.model_copy(update=change), leavable=frozenset({start}))
        if network.shortest_path(space_node(start), space_node(end)) is not None:
            blocking.append(name)
    return blocking


class ReachableSpace(ToolResult):
    space: SpaceRef
    type: SpaceType
    room_type: str
    distance_m: float


class ReachableSpaces(ToolResult):
    count: int
    """Number of reachable spaces that pass the filters, also beyond `limit`."""
    spaces: list[ReachableSpace]
    """Nearest first, shortened to `limit`."""


def reachable_spaces(
    building: Building,
    start: str,
    conditions: RouteConditions | None = None,
    floor: str | None = None,
    space_types: list[SpaceType] | None = None,
    room_type: str | None = None,
    asset_type: str | None = None,
    limit: int = 50,
) -> ReachableSpaces:
    """Spaces a walk from `start` can reach under the conditions, nearest first, with walking distances.

    Filters combine: floor, space types, room type, and spaces that hold an asset of `asset_type`.
    The start space itself is included at distance 0 when it passes the filters.
    """
    building.space(start)
    floor_id = building.floor(floor).id if floor is not None else None
    holding = None
    if asset_type is not None:
        holding = {
            asset.space_id for asset in building.document.assets if normalize(asset.type) == normalize(asset_type)
        }
        if not holding:
            known = ", ".join(sorted({asset.type for asset in building.document.assets}))
            raise ToolInputError(f"no asset of type {asset_type!r} in this building; known types: {known}")
    network = RouteNetwork(building, conditions or RouteConditions(), leavable=frozenset({start}))
    distances = network.distances_from(space_node(start))
    matches = [
        ReachableSpace(
            space=space_ref(building, space.id),
            type=space.type,
            room_type=space.room_type,
            distance_m=round(distances[space_node(space.id)], 2),
        )
        for space in building.document.spaces
        if space_node(space.id) in distances
        and (floor_id is None or space.floor_id == floor_id)
        and (space_types is None or space.type in space_types)
        and (room_type is None or normalize(space.room_type) == normalize(room_type))
        and (holding is None or space.id in holding)
    ]
    matches.sort(key=lambda match: match.distance_m)
    return ReachableSpaces(count=len(matches), spaces=matches[: max(limit, 0)])


class ExitChange(ToolResult):
    space: SpaceRef
    before_m: float | None
    """Walk to the nearest entrance before the change, or None if there was no way out."""
    after_m: float | None


class ExitDistanceChange(ToolResult):
    shorter_count: int
    """Spaces whose walk out became shorter by more than `min_change_m`, including spaces that had no way out."""
    longer_count: int
    """Spaces whose walk out became longer by more than `min_change_m`, including spaces that lost their way out."""
    shorter: list[ExitChange]
    longer: list[ExitChange]


def exit_distance_change(
    building: Building,
    floor: str,
    change: RouteConditions,
    min_change_m: float = 1.0,
    space_types: list[SpaceType] | None = None,
) -> ExitDistanceChange:
    """How a change, such as an added door or a closure, alters each space's walk to its nearest entrance.

    Compares the building as it is with the building under `change`, for spaces on `floor`. `space_types`
    defaults to rooms.
    """
    if change.no_pass_through_room_types:
        raise ToolInputError("no_pass_through_room_types is not supported for walks out of the building")
    floor_id = building.floor(floor).id
    types = set(space_types or ["room"])
    before = exit_distances(RouteNetwork(building, RouteConditions(step_free=change.step_free)))
    after = exit_distances(RouteNetwork(building, change))
    shorter, longer = [], []
    for space in building.document.spaces:
        if space.floor_id != floor_id or space.type not in types:
            continue
        old, new = before.get(space_node(space.id)), after.get(space_node(space.id))
        entry = ExitChange(
            space=space_ref(building, space.id),
            before_m=round(old, 2) if old is not None else None,
            after_m=round(new, 2) if new is not None else None,
        )
        if new is not None and (old is None or old - new > min_change_m):
            shorter.append(entry)
        elif old is not None and (new is None or new - old > min_change_m):
            longer.append(entry)
    return ExitDistanceChange(shorter_count=len(shorter), longer_count=len(longer), shorter=shorter, longer=longer)


def exit_distances(network: RouteNetwork) -> dict[Node, float]:
    """Walking distance from every node to its nearest entrance."""
    entrances = network.entrance_nodes()
    if not entrances:
        return {}
    return nx.multi_source_dijkstra_path_length(network.graph.reverse(copy=False), entrances, weight="weight")
