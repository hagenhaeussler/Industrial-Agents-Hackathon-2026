"""The walking network of a building under route conditions, following the README route model.

Nodes are space centres and openings. Walking inside a space joins its centre and its openings. Stairs and lifts
join space centres: stairs cost 2 m per metre climbed, a lift 15 m once per ride plus 1 m per metre climbed.
An entrance opening belongs to one space only, so a route can never go round the outside.
"""

import itertools
from dataclasses import dataclass
from typing import Literal

import networkx as nx
from pydantic import BaseModel, ConfigDict, Field
from shapely.geometry import LineString, Polygon
from shapely.ops import linemerge, nearest_points

from building_db.source import OUTSIDE, Opening
from building_tools.building import Building, ToolInputError, normalize
from building_tools.walks import Point2, Walk, space_walks

STAIRS_M_PER_RISE = 2.0
LIFT_FIXED_M = 15.0
LIFT_M_PER_RISE = 1.0
ADDED_DOOR_WIDTH_M = 0.9
SHARED_WALL_GAP_M = 0.35


class RouteConditions(BaseModel):
    """Rules a route must follow. The defaults allow every open door, stair and lift."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    step_free: bool = Field(default=False, description="No stairs and no openings with steps; lifts are fine")
    min_door_width_m: float = Field(default=0.0, ge=0, description="Every opening passed must be this wide")
    closed: list[str] = Field(default=[], description="IDs of closed spaces, openings, stairs or lifts")
    added_doors: list[tuple[str, str]] = Field(
        default=[], description="New doors, each between two space IDs that share a wall, placed mid-wall"
    )
    no_pass_through_room_types: list[str] = Field(
        default=[], description="Room types a route may start or end in but not pass through"
    )


Node = tuple[Literal["space", "opening"], str]


def space_node(space_id: str) -> Node:
    return ("space", space_id)


def opening_node(opening_id: str) -> Node:
    return ("opening", opening_id)


def shared_wall_midpoint(first: Polygon, second: Polygon) -> Point2:
    """The middle of the wall two outlines share: halfway along it, between both outlines."""
    wall = first.exterior.intersection(second.exterior.buffer(SHARED_WALL_GAP_M))
    lines = [piece for piece in getattr(wall, "geoms", [wall]) if isinstance(piece, LineString) and piece.length > 0]
    if not lines:
        raise ToolInputError("these spaces do not share a wall, so a door cannot join them")
    # The outline's start point can split one wall in two pieces; merge them so the start point does not matter.
    merged = linemerge(lines)
    pieces = [merged] if isinstance(merged, LineString) else list(merged.geoms)
    middle = max(pieces, key=lambda piece: piece.length).interpolate(0.5, normalized=True)
    opposite = nearest_points(second.exterior, middle)[0]
    return ((middle.x + opposite.x) / 2, (middle.y + opposite.y) / 2)


@dataclass(frozen=True)
class Edge:
    weight: float
    space_id: str | None = None
    """The space walked through, for walking edges."""
    connector_id: str | None = None
    """The stair or lift used, for vertical edges."""


class RouteNetwork:
    """The graph for one set of conditions. `leavable` lists spaces that may be left even if they cannot be
    passed through, such as the start of a route."""

    def __init__(self, building: Building, conditions: RouteConditions, leavable: frozenset[str] = frozenset()):
        self.building = building
        self.conditions = conditions
        self.openings = {opening.id: opening for opening in building.document.openings}
        self.added_openings = [
            self.added_door(first, second, index)
            for index, (first, second) in enumerate(conditions.added_doors, start=1)
        ]
        self.openings |= {opening.id: opening for opening in self.added_openings}
        self.check_closed()
        # Room types compare like everywhere else, so "production zone" matches "production_zone". Unknown types
        # are refused, so a typo cannot silently allow a route through a bay.
        no_pass_through = {building.room_type(room_type) for room_type in conditions.no_pass_through_room_types}
        self.pass_through = {
            space.id for space in building.document.spaces if normalize(space.room_type) not in no_pass_through
        }
        self.leavable = self.pass_through | leavable
        """Spaces whose centre a walk may leave again: all but no-pass-through spaces, unless they are a start."""
        self.graph = nx.MultiDiGraph()
        self.add_walking()
        self.add_connectors()

    def added_door(self, first_id: str, second_id: str, index: int) -> Opening:
        first, second = self.building.space(first_id), self.building.space(second_id)
        if first.floor_id != second.floor_id:
            raise ToolInputError("a door can only join two spaces on the same floor")
        position = shared_wall_midpoint(self.building.polygon_by_id[first.id], self.building.polygon_by_id[second.id])
        return Opening(
            id=f"added-door-{index}",
            floor_id=first.floor_id,
            space_ids=(first.id, second.id),
            kind="door",
            position=position,
            width_m=ADDED_DOOR_WIDTH_M,
            step_free=True,
            synthetic=True,
        )

    def check_closed(self) -> None:
        known = self.openings.keys() | self.building.space_by_id.keys() | self.building.connector_by_id.keys()
        unknown = [element for element in self.conditions.closed if element not in known]
        if unknown:
            raise ToolInputError(f"unknown closed element ids {unknown}; use space, opening, stair or lift ids")

    def usable_opening(self, opening: Opening) -> bool:
        return (
            opening.id not in self.conditions.closed
            and (opening.step_free or not self.conditions.step_free)
            and opening.width_m >= self.conditions.min_door_width_m
        )

    def walks(self, space_id: str) -> list[Walk]:
        """Walks of one space with all its openings. Cached on the building unless a door was added to the space."""
        openings = [opening for opening in self.openings.values() if space_id in opening.space_ids]
        has_added_door = any(opening in self.added_openings for opening in openings)
        if not has_added_door and space_id in self.building.walk_cache:
            return self.building.walk_cache[space_id]
        walks = space_walks(
            self.building.polygon_by_id[space_id], [(opening.id, opening.position) for opening in openings]
        )
        if not has_added_door:
            self.building.walk_cache[space_id] = walks
        return walks

    def add_walking(self) -> None:
        usable = {opening_id for opening_id, opening in self.openings.items() if self.usable_opening(opening)}
        for space in self.building.document.spaces:
            if space.id in self.conditions.closed:
                continue
            self.graph.add_node(space_node(space.id))
            for walk in self.walks(space.id):
                if walk.second.opening_id not in usable:
                    continue
                edge = Edge(walk.length_m, space_id=space.id)
                door = opening_node(walk.second.opening_id)
                if walk.first.opening_id is None:  # centre to opening
                    self.add_edge(door, space_node(space.id), edge)
                    if space.id in self.leavable:
                        self.add_edge(space_node(space.id), door, edge)
                elif walk.first.opening_id in usable and space.id in self.pass_through:  # opening to opening
                    self.add_edge(opening_node(walk.first.opening_id), door, edge)
                    self.add_edge(door, opening_node(walk.first.opening_id), edge)

    def add_connectors(self) -> None:
        levels = {floor.id: floor.level for floor in self.building.floors}
        elevations = {floor.id: floor.elevation_m for floor in self.building.floors}
        for connector in self.building.document.vertical_connectors:
            if connector.id in self.conditions.closed or (self.conditions.step_free and not connector.step_free):
                continue
            stops = sorted(zip(connector.floor_ids, connector.space_ids, strict=True), key=lambda s: levels[s[0]])
            # A lift ride pays the fixed cost once however many floors it passes; stairs go one flight at a time.
            is_lift = connector.kind == "lift"
            for (low_floor, low_space), (high_floor, high_space) in (
                itertools.combinations(stops, 2) if is_lift else itertools.pairwise(stops)
            ):
                low, high = space_node(low_space), space_node(high_space)
                if low not in self.graph or high not in self.graph:
                    continue
                rise = abs(elevations[high_floor] - elevations[low_floor])
                cost = LIFT_FIXED_M + LIFT_M_PER_RISE * rise if is_lift else STAIRS_M_PER_RISE * rise
                edge = Edge(round(cost, 3), connector_id=connector.id)
                if low_space in self.leavable:
                    self.add_edge(low, high, edge)
                if high_space in self.leavable:
                    self.add_edge(high, low, edge)

    def add_edge(self, source: Node, target: Node, edge: Edge) -> None:
        self.graph.add_edge(source, target, weight=edge.weight, edge=edge)

    def entrance_nodes(self) -> list[Node]:
        return [
            opening_node(opening.id)
            for opening in self.openings.values()
            if opening.kind == "entrance" and OUTSIDE in opening.space_ids and opening_node(opening.id) in self.graph
        ]

    def cheapest(self, source: Node, target: Node) -> Edge:
        return min((data["edge"] for data in self.graph[source][target].values()), key=lambda edge: edge.weight)

    def shortest_path(self, source: Node, target: Node) -> tuple[float, list[Node]] | None:
        try:
            length, nodes = nx.bidirectional_dijkstra(self.graph, source, target, weight="weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
        return float(length), list(nodes)

    def distances_from(self, source: Node) -> dict[Node, float]:
        if source not in self.graph:
            return {}
        return nx.single_source_dijkstra_path_length(self.graph, source, weight="weight")
