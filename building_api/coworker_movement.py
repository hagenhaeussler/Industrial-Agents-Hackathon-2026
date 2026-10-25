"""A clock-based workday over real routes. Viewing or hiding people never runs a model."""

import itertools
import math
from dataclasses import dataclass

import networkx as nx
import numpy as np
from shapely.geometry import Point, Polygon

from building_api.coworker_models import Coworker, Journey, Position, TimedPoint
from building_tools.building import Building
from building_tools.network import Node, RouteConditions, RouteNetwork, space_node
from building_tools.walks import COVER_TOLERANCE_M, WALL_CLEARANCE_M, anchor, door_landing, visibility_matrix

WALK_METRES_PER_SECOND = 1.2
WORK_SECONDS = 65


@dataclass(frozen=True)
class Persona:
    id: str
    name: str
    role: str
    color: str
    room_types: tuple[str, ...]
    task: str


PERSONAS = (
    Persona(
        "maya", "Maya Chen", "Facility manager", "#b56843", ("office", "meeting_room"), "Reviewing building operations"
    ),
    Persona("jonas", "Jonas Weber", "Maintenance", "#397a91", ("technical_room", "makerspace"), "Checking equipment"),
    Persona("priya", "Priya Nair", "Safety officer", "#8568a6", ("lab", "corridor"), "Reviewing access and safety"),
    Persona("leo", "Leo Martin", "Visitor desk", "#b58c26", ("lobby", "meeting_room"), "Preparing visitor directions"),
)


@dataclass(frozen=True)
class WalkPoint:
    floor_id: str
    x: float
    y: float
    space_id: str


def inside_path(polygon: Polygon, start: tuple[float, float], end: tuple[float, float]) -> list[tuple[float, float]]:
    """Recover the visibility-graph path used by walking lengths, including concave corners.

    Unlike the route drawing's sparse points, these points cannot cut across a room's corners.
    An impossible geometric path is rejected rather than replaced with a straight line.
    """
    walkable = polygon.buffer(-WALL_CLEARANCE_M)
    if walkable.is_empty or walkable.geom_type != "Polygon":
        walkable = polygon
    nodes = [start, end, *[(x, y) for ring in [walkable.exterior, *walkable.interiors] for x, y in ring.coords]]
    matrix = visibility_matrix(walkable.buffer(COVER_TOLERANCE_M), nodes)
    graph = nx.Graph()
    graph.add_nodes_from(range(len(nodes)))
    for first, second in itertools.combinations(range(len(nodes)), 2):
        if np.isfinite(matrix[first, second]):
            graph.add_edge(first, second, weight=float(matrix[first, second]))
    return [nodes[index] for index in nx.shortest_path(graph, 0, 1, weight="weight")]


def node_point(network: RouteNetwork, node: Node, space_id: str) -> tuple[float, float]:
    return (
        network.openings[node[1]].position if node[0] == "opening" else anchor(network.building.polygon_by_id[space_id])
    )


def walking_points(network: RouteNetwork, nodes: list[Node]) -> list[WalkPoint]:
    result: list[WalkPoint] = []
    for first, second in itertools.pairwise(nodes):
        edge = network.cheapest(first, second)
        if edge.space_id is None:
            for node in (first, second):
                space = network.building.space(node[1])
                x, y = anchor(network.building.polygon_by_id[space.id])
                result.append(WalkPoint(space.floor_id, x, y, space.id))
            continue
        space = network.building.space(edge.space_id)
        polygon = network.building.polygon_by_id[space.id]
        start, end = node_point(network, first, space.id), node_point(network, second, space.id)
        landing_start = door_landing(polygon, start) if first[0] == "opening" else start
        landing_end = door_landing(polygon, end) if second[0] == "opening" else end
        points = [start, *inside_path(polygon, landing_start, landing_end), end]
        for x, y in points:
            point = WalkPoint(space.floor_id, x, y, space.id)
            if not result or point != result[-1]:
                result.append(point)
    return result


class Workday:
    """Prepared, bounded itineraries. A session start time is enough to recover its current state."""

    def __init__(self, building: Building):
        self.building = building
        self.paths: dict[str, list[WalkPoint]] = {}
        network = RouteNetwork(building, RouteConditions())
        spaces = sorted(building.document.spaces, key=lambda space: (space.floor_id, space.id))
        assigned: set[str] = set()
        for index, persona in enumerate(PERSONAS):
            ranked = sorted(spaces, key=lambda space: (space.room_type not in persona.room_types, space.type != "room"))
            if not ranked:
                continue
            start = next((space for space in ranked if space.id not in assigned), ranked[index % len(ranked)])
            x, y = anchor(building.polygon_by_id[start.id])
            self.paths[persona.id] = [WalkPoint(start.floor_id, x, y, start.id)]
            # Try the ranked destinations, including another floor where reachable. No entity ID is assumed.
            destinations = sorted(ranked, key=lambda space: space.id in assigned)
            for end in destinations:
                if end.id == start.id:
                    continue
                found = network.shortest_path(space_node(start.id), space_node(end.id))
                if found is None:
                    continue
                try:
                    path = walking_points(network, found[1])
                except nx.NetworkXNoPath:
                    continue
                if len(path) > 1:
                    self.paths[persona.id] = path
                    break
            assigned.update((start.id, self.paths[persona.id][-1].space_id))

    def state(self, started_at: float, now: float) -> list[Coworker]:
        return [
            self.member(persona, started_at, now, index)
            for index, persona in enumerate(PERSONAS)
            if persona.id in self.paths
        ]

    def member(self, persona: Persona, started_at: float, now: float, index: int) -> Coworker:
        path = self.paths[persona.id]
        durations = [
            max(math.dist((first.x, first.y), (second.x, second.y)) / WALK_METRES_PER_SECOND, 0.01)
            if first.floor_id == second.floor_id
            else 8.0
            for first, second in itertools.pairwise(path)
        ]
        travel = sum(durations)
        cycle = 2 * (travel + WORK_SECONDS)
        elapsed = ((now - started_at) / 1000 + index * 27) % cycle
        reverse = elapsed >= travel + WORK_SECONDS
        if reverse:
            elapsed -= travel + WORK_SECONDS
            path = list(reversed(path))
            durations = list(reversed(durations))
        journey = None
        point = path[-1]
        activity = persona.task
        if elapsed < travel:
            departure = now - elapsed * 1000
            times = [departure]
            for duration in durations:
                times.append(times[-1] + duration * 1000)
            journey = Journey(
                points=[
                    TimedPoint(floor_id=p.floor_id, x=p.x, y=p.y, at=at) for p, at in zip(path, times, strict=True)
                ],
                destination_name=self.building.space(path[-1].space_id).name,
                arrives_at=times[-1],
            )
            activity = f"Walking to {journey.destination_name}"
            for first, second, begin, end in zip(path, path[1:], times, times[1:]):
                if now <= end:
                    fraction = min(1.0, max(0.0, (now - begin) / (end - begin)))
                    point = first
                    if first.floor_id == second.floor_id:
                        x, y = first.x + (second.x - first.x) * fraction, first.y + (second.y - first.y) * fraction
                        space_id = next(
                            (
                                space.id
                                for space in self.building.spaces_on(first.floor_id)
                                if self.building.polygon_by_id[space.id].covers(Point(x, y))
                            ),
                            first.space_id,
                        )
                        point = WalkPoint(first.floor_id, x, y, space_id)
                    break
        space = self.building.space(point.space_id)
        return Coworker(
            id=persona.id,
            name=persona.name,
            role=persona.role,
            color=persona.color,
            position=Position(floor_id=point.floor_id, x=point.x, y=point.y, space_id=space.id, space_name=space.name),
            activity=activity,
            journey=journey,
        )
