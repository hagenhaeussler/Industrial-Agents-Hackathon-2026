"""Deterministic spatial tools. No question files, answer keys or LLM dependencies."""

import math
import re
from itertools import groupby
from dataclasses import dataclass

import networkx as nx
from shapely.geometry import LineString, Polygon
from shapely.ops import linemerge, nearest_points

from starter_agent.building_map import BuildingMap, DOOR_PREFIX, MapError, OUTSIDE


@dataclass(frozen=True)
class Constraints:
    step_free: bool = False
    min_width: float = 0.0
    closed: frozenset[str] = frozenset()

    def __post_init__(self):
        if not math.isfinite(self.min_width) or self.min_width < 0:
            raise MapError("Minimum width must be a finite nonnegative number.")


class SpatialCore(BuildingMap):
    """Starter-compatible map with read-only spatial queries.

    Persistent edits/closures still use the inherited map API. Query constraints
    add to those closures; hypothetical doors never modify either state.
    """

    def __init__(self, building: dict):
        super().__init__(building)
        self.polygons = {sid: Polygon(s["polygon"]) for sid, s in self.spaces.items()}
        for sid, polygon in self.polygons.items():
            if polygon.is_empty or not polygon.is_valid or polygon.area <= 0:
                raise MapError(f"Invalid room polygon: {sid}")

    def anchor(self, space_id: str) -> tuple[float, float]:
        point = self.polygons[space_id].representative_point()
        return point.x, point.y

    def resolve_space(self, reference: str) -> str:
        # The starter's search fallback updates UI selection even on failed lookup.
        selection = self.located_asset_ids
        try:
            return super().resolve_space(reference)
        finally:
            self.located_asset_ids = selection

    def floor_rooms(self, floor_id: str, room_type: str | None = None) -> list[dict]:
        if floor_id not in self.floors:
            raise MapError(f"Unknown floor: {floor_id}")
        return [s for s in self.spaces.values() if s["floor_id"] == floor_id
                and s["type"] in {"room", "hall"} and (room_type is None or s["room_type"] == room_type)]

    def largest_room(self, floor_id: str, room_type: str) -> dict:
        rooms = self.floor_rooms(floor_id, room_type)
        if not rooms:
            raise MapError(f"No {room_type} rooms on {floor_id}")
        room = max(rooms, key=lambda s: (self.polygons[s["id"]].area, s["id"]))
        return {"space_id": room["id"], "area_m2": self.polygons[room["id"]].area}

    def floor_area_total(self, floor_id: str, room_type: str) -> float:
        return math.fsum(self.polygons[s["id"]].area for s in self.floor_rooms(floor_id, room_type))

    def shared_wall(self, first: str, second: str):
        a, b = self.spaces[first], self.spaces[second]
        if first == second or a["floor_id"] != b["floor_id"]:
            raise MapError("Shared walls require distinct spaces on the same floor.")
        return self.polygons[first].boundary.intersection(self.polygons[second].boundary.buffer(0.35))

    def shared_wall_neighbors(self, start: str) -> list[str]:
        start = self.resolve_space(start)
        return [s["id"] for s in self.floor_rooms(self.spaces[start]["floor_id"])
                if s["id"] != start and self.shared_wall(start, s["id"]).length >= 1.0]

    def stacked_room(self, start: str, direction: str) -> dict:
        start = self.resolve_space(start)
        if direction not in {"above", "below"}:
            raise MapError("Direction must be above or below.")
        floor = self.floors[self.spaces[start]["floor_id"]]
        candidates = [f for f in self.floors.values()
                      if (f["level"] > floor["level"] if direction == "above" else f["level"] < floor["level"])]
        if not candidates:
            raise MapError(f"No floor {direction} {floor['id']}")
        next_floor = min(candidates, key=lambda f: abs(f["level"] - floor["level"]))
        overlaps = [(self.polygons[start].intersection(self.polygons[s["id"]]).area, s["id"])
                    for s in self.floor_rooms(next_floor["id"])]
        if not overlaps or max(overlaps)[0] <= 0:
            raise MapError("No overlapping room on the adjacent floor.")
        area, sid = max(overlaps)
        return {"space_id": sid, "overlap_m2": area}

    def distance_3d(self, first: str, second: str) -> float:
        def position(reference):
            sid = self.resolve_space(reference)
            p = self.polygons[sid].centroid
            return p.x, p.y, self.floors[self.spaces[sid]["floor_id"]]["elevation_m"]
        return math.dist(position(first), position(second))

    def constrained_graph(self, constraints: Constraints = Constraints()) -> nx.MultiGraph:
        graph = super().graph(constraints.step_free)
        known = self.spaces.keys() | self.openings.keys() | self.connectors.keys()
        if constraints.closed - known:
            raise MapError(f"Unknown closed elements: {sorted(constraints.closed - known)}")
        graph.remove_nodes_from(sid for sid in constraints.closed if sid in self.spaces)
        graph.remove_nodes_from(DOOR_PREFIX + oid for oid, opening in self.openings.items()
                                if opening["width_m"] < constraints.min_width or oid in constraints.closed)
        graph.remove_edges_from([(a, b, key) for a, b, key, data in graph.edges(keys=True, data=True)
                                 if data["via"] in constraints.closed])
        return graph

    def constrained_route(self, start: str, destination: str, constraints: Constraints = Constraints()) -> dict:
        start, destination = self.resolve_space(start), self.resolve_space(destination)
        graph = self.constrained_graph(constraints)
        try:
            length, nodes = nx.single_source_dijkstra(graph, start, destination, weight="weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound) as error:
            raise MapError("No route under these constraints.") from error
        elements = [min(graph[a][b].values(), key=lambda e: e["weight"])["via"]
                    for a, b in zip(nodes, nodes[1:])]
        return {"length_m": length, "space_path": [n for n in nodes if n in self.spaces or n == OUTSIDE],
                "node_path": nodes, "element_path": [element for element, _ in groupby(elements)]}

    def reachable_rooms(self, start: str, floor_id: str, constraints: Constraints) -> list[str]:
        """Count from a supplied interior space, after the assumed arrival through an entrance.

        Like the benchmark, this does not validate that prior arrival or restrict
        the zero-cost outside node to a single entrance.
        """
        start = self.resolve_space(start)
        rooms = self.floor_rooms(floor_id)
        graph = self.constrained_graph(constraints)
        reachable = nx.node_connected_component(graph, start) if start in graph else set()
        # The delivery/reachability benchmark counts rooms, excluding hall circulation.
        return [s["id"] for s in rooms if s["type"] == "room" and s["id"] in reachable]

    def errand(self, start: str, asset_type: str, floor_id: str, room_type: str) -> dict:
        start = self.resolve_space(start)
        graph = self.constrained_graph()
        if start not in graph:
            raise MapError("Errand start space is closed.")
        lengths = nx.single_source_dijkstra_path_length(graph, start, weight="weight")
        candidates = {a["space_id"] for a in self.assets.values() if a["type"] == asset_type}
        reachable = candidates & lengths.keys()
        if not reachable:
            raise MapError(f"No reachable {asset_type}")
        via = min(reachable, key=lambda sid: (lengths[sid], sid))
        target = self.largest_room(floor_id, room_type)["space_id"]
        if target not in graph:
            raise MapError("Largest target room is closed.")
        try:
            second = nx.shortest_path_length(graph, via, target, weight="weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound) as error:
            raise MapError("Largest target room is unreachable from pickup.") from error
        return {"length_m": lengths[via] + second, "via": via, "target": target}

    def compare_exit_distances_with_door(self, first: str, second: str, floor_id: str) -> dict:
        first, second = self.resolve_space(first), self.resolve_space(second)
        first, second = sorted((first, second))
        wall = self.shared_wall(first, second)
        if wall.length < 1:
            raise MapError("No shared wall of at least one metre.")
        # Use the longest continuous shared segment, not an arbitrary nearest vertex.
        def lines(geometry):
            if geometry.geom_type in {"LineString", "LinearRing"}:
                return [geometry]
            return [line for part in getattr(geometry, "geoms", ()) for line in lines(part)]
        segments = lines(wall)
        if not segments:
            raise MapError("No shared wall segment.")
        merged = linemerge(segments)
        # Join fragments crossing a polygon ring's start vertex before choosing a wall.
        def collinear(a, b, c):
            u, v = (b[0] - a[0], b[1] - a[1]), (c[0] - b[0], c[1] - b[1])
            return abs(u[0] * v[1] - u[1] * v[0]) <= 1e-9 and u[0] * v[0] + u[1] * v[1] > 0

        straight = []
        for line in lines(merged):
            coords = [point for point, _ in groupby(line.coords)]
            if len(coords) < 2:
                continue
            runs = [[coords[0], coords[1]]]
            for point in coords[2:]:
                if collinear(*runs[-1][-2:], point):
                    runs[-1].append(point)
                else:
                    runs.append([runs[-1][-1], point])
            if len(runs) > 1 and coords[0] == coords[-1] and collinear(runs[-1][-2], coords[0], runs[0][1]):
                runs[0] = runs[-1][:-1] + runs[0]
                runs.pop()
            straight.extend(LineString(run) for run in runs)
        if not straight:
            raise MapError("No nonzero shared wall segment.")
        position = max(straight, key=lambda line: line.length).interpolate(0.5, normalized=True)
        # Centre the doorway between the two wall faces, independent of argument order.
        other = nearest_points(position, self.polygons[second].boundary)[1]
        point = ((position.x + other.x) / 2, (position.y + other.y) / 2)
        graph = self.constrained_graph()
        if OUTSIDE not in graph:
            raise MapError("Building has no entrance.")
        before = nx.single_source_dijkstra_path_length(graph, OUTSIDE, weight="weight")
        door_node = "what-if:door"
        for sid in (first, second):
            if sid not in graph:
                raise MapError("Cannot connect a closed space.")
            graph.add_edge(sid, door_node, weight=math.dist(self.anchor(sid), point),
                           via=door_node)
        after = nx.single_source_dijkstra_path_length(graph, OUTSIDE, weight="weight")
        improved = [s["id"] for s in self.floor_rooms(floor_id)
                    if s["id"] in after and (s["id"] not in before or before[s["id"]] - after[s["id"]] > 1.0)]
        return {"count": len(improved), "improved_space_ids": improved,
                "door_position": list(point)}

    def solve(self, kind: str, inputs: dict) -> dict:
        """Typed dispatch, usable directly by an agent without any benchmark metadata."""
        required = {
            "largest_room": {"floor_id", "room_type"},
            "floor_area_total": {"floor_id", "room_type"},
            "shared_walls_count": {"start"},
            "straight_line_3d": {"first", "second"},
            "room_stacked": {"start", "direction"},
            "errand": {"start", "asset_type", "floor_id", "room_type"},
            "wide_delivery_count": {"start", "floor_id", "min_width"},
            "step_free_reachable_count": {"start", "floor_id", "closed"},
            "what_if_door": {"first", "second", "floor_id"},
        }
        if kind not in required:
            raise MapError(f"Unsupported question kind: {kind}")
        if not isinstance(inputs, dict):
            raise MapError("Inputs must be an object.")
        missing = required[kind] - inputs.keys()
        extra = inputs.keys() - required[kind] - ({"door_floor_id"} if kind == "what_if_door" else set())
        if missing or extra:
            raise MapError(f"Invalid inputs: missing {sorted(missing)}, unexpected {sorted(extra)}")
        for key, value in inputs.items():
            if key == "min_width":
                if isinstance(value, bool) or not isinstance(value, (float, int)):
                    raise MapError("min_width must be a number in metres.")
            elif not isinstance(value, str) or not value:
                raise MapError(f"{key} must be a nonempty string.")
        if kind == "largest_room":
            return self.largest_room(inputs["floor_id"], inputs["room_type"])
        if kind == "floor_area_total":
            return {"value": self.floor_area_total(inputs["floor_id"], inputs["room_type"])}
        if kind == "shared_walls_count":
            neighbors = self.shared_wall_neighbors(inputs["start"])
            return {"value": len(neighbors), "space_ids": neighbors}
        if kind == "straight_line_3d":
            return {"value": self.distance_3d(inputs["first"], inputs["second"])}
        if kind == "room_stacked":
            return self.stacked_room(inputs["start"], inputs["direction"])
        if kind == "errand":
            result = self.errand(inputs["start"], inputs["asset_type"], inputs["floor_id"], inputs["room_type"])
            return {"value": result["length_m"], **result}
        if kind in {"wide_delivery_count", "step_free_reachable_count"}:
            constraints = Constraints(step_free=True, min_width=inputs.get("min_width", 0),
                                      closed=frozenset([inputs["closed"]]) if "closed" in inputs else frozenset())
            rooms = self.reachable_rooms(inputs["start"], inputs["floor_id"], constraints)
            return {"value": len(rooms), "space_ids": rooms}
        if kind == "what_if_door":
            if "door_floor_id" in inputs and self.spaces[self.resolve_space(inputs["first"])]["floor_id"] != inputs["door_floor_id"]:
                raise MapError("door_floor_id does not match the door's spaces.")
            result = self.compare_exit_distances_with_door(inputs["first"], inputs["second"], inputs["floor_id"])
            return {"value": result["count"], **result}
        raise AssertionError("Missing implementation for a validated question kind")

    def format_answer(self, result: dict) -> str:
        if "space_id" in result:
            room = self.spaces[result["space_id"]]
            # OSM may have a name without a room ref. The kit uses a stable level.index fallback.
            level = self.floors[room["floor_id"]]["level"]
            suffix = re.search(r"-S(\d+)$", room["id"])
            fallback = f"{level}.{int(suffix[1]):02d}" if suffix else room["name"]
            label = room.get("ref") or fallback
            text = f"{label}, {room['name']}"
            if "area_m2" in result:
                text += f", {result['area_m2']:.6f} m²"
        else:
            value = result["value"]
            text = str(value) if isinstance(value, int) else f"{value:.6f}"
        return "Answer: " + text
