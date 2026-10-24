"""Deterministic spatial tools. No question files, answer keys or LLM dependencies."""

import copy
import math
import re
from itertools import groupby
from dataclasses import dataclass

import networkx as nx
from shapely.geometry import LineString
from shapely.ops import linemerge, nearest_points

from starter_agent.building_map import DOOR_PREFIX, MapError, OUTSIDE
from .building import Building
from .errors import CoreError


@dataclass(frozen=True)
class Constraints:
    step_free: bool = False
    min_width: float = 0.0
    closed: frozenset[str] = frozenset()
    no_transit_room_types: frozenset[str] = frozenset()

    def __post_init__(self):
        if isinstance(self.min_width, bool) or not isinstance(self.min_width, (int, float)) or not math.isfinite(self.min_width) or self.min_width < 0:
            raise CoreError("invalid_args", "Minimum width must be a finite nonnegative number.")
        if not isinstance(self.step_free, bool):
            raise CoreError("invalid_args", "step_free must be a boolean.")
        for key in ("closed", "no_transit_room_types"):
            value = getattr(self, key)
            if not isinstance(value, (set, frozenset, list, tuple)) or not all(isinstance(item, str) and item for item in value):
                raise CoreError("invalid_args", f"{key} must be a collection of nonempty strings.")
            object.__setattr__(self, key, frozenset(value))


def normalise_constraints(constraints=None):
    if constraints is None:
        return Constraints()
    if isinstance(constraints, Constraints):
        return constraints
    if not isinstance(constraints, dict):
        raise CoreError("invalid_args", "Constraints must be an object.")
    unknown = constraints.keys() - {"step_free", "min_width", "min_door_width_m", "closed", "no_transit_room_types"}
    if unknown:
        raise CoreError("invalid_args", f"Unknown constraints: {sorted(unknown)}")
    if "min_width" in constraints and "min_door_width_m" in constraints and constraints["min_width"] != constraints["min_door_width_m"]:
        raise CoreError("invalid_args", "Conflicting minimum door widths.")
    return Constraints(constraints.get("step_free", False), constraints.get("min_door_width_m", constraints.get("min_width", 0.0)),
                       constraints.get("closed", frozenset()), constraints.get("no_transit_room_types", frozenset()))


def constrained_graph(building, constraints=None):
    """Fresh kit graph with closures, width limits and forbidden transit spaces.

    A space is represented by its walking edges as well as its anchor node;
    deleting only the node would still permit a door-to-door transit shortcut.
    Routing may exempt a forbidden start/end type before calling this helper.
    """
    constraints = normalise_constraints(constraints)
    closed = constraints.closed | building.closed
    known = building.spaces.keys() | building.openings.keys() | building.connectors.keys()
    if closed - known:
        raise CoreError("not_found", f"Unknown closed elements: {sorted(closed - known)}")
    graph = building.graph(constraints.step_free)
    forbidden = {sid for sid, space in building.spaces.items() if sid in closed or space["room_type"] in constraints.no_transit_room_types}
    graph.remove_nodes_from(sid for sid in closed if sid in building.spaces)
    graph.remove_nodes_from(DOOR_PREFIX + oid for oid, opening in building.openings.items()
                            if opening["width_m"] < constraints.min_width or oid in closed)
    graph.remove_edges_from([(a, b, key) for a, b, key, data in graph.edges(keys=True, data=True)
                             if data.get("via") in closed or data.get("space") in forbidden])
    return graph


class SpatialCore(Building):
    """Starter-compatible map with read-only spatial queries.

    Persistent edits/closures still use the inherited map API. Query constraints
    add to those closures; hypothetical doors never modify either state.
    """

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
        return constrained_graph(self, constraints)

    def constrained_route(self, start: str, destination: str, constraints: Constraints = Constraints()) -> dict:
        start, destination = self.resolve_space(start), self.resolve_space(destination)
        graph = self.constrained_graph(constraints)
        try:
            length, nodes = nx.single_source_dijkstra(graph, start, destination, weight="weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound) as error:
            raise MapError("No route under these constraints.") from error
        elements = []
        for a, b in zip(nodes, nodes[1:]):
            edge = self.cheapest(graph, a, b)
            if "via" in edge:
                elements.append(edge["via"])
            if b.startswith(DOOR_PREFIX):
                elements.append(b.removeprefix(DOOR_PREFIX))
        return {"length_m": length, "space_path": self.spaces_passed(graph, nodes),
                "node_path": nodes, "element_path": elements}

    def reachable_rooms(self, start: str, floor_id: str, constraints: Constraints) -> list[str]:
        """Count from a supplied interior space, after the assumed arrival through an entrance.

        Like the benchmark, this does not validate the prior arrival. Kit 1.1
        has no outside shortcut between separate entrances.
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

    def shared_wall_midpoint(self, first: str, second: str) -> tuple[float, float]:
        """Middle of the longest straight shared wall, centred between faces."""
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
        longest = max(straight, key=lambda line: line.length)
        position = longest.interpolate(0.5, normalized=True)
        # Centre the doorway between the two wall faces, independent of argument order.
        other = nearest_points(position, self.polygons[second].boundary)[1]
        point = ((position.x + other.x) / 2, (position.y + other.y) / 2)
        return point

    def compare_exit_distances_with_door(self, first: str, second: str, floor_id: str) -> dict:
        first, second = self.resolve_space(first), self.resolve_space(second)
        point = self.shared_wall_midpoint(first, second)
        graph = self.constrained_graph()
        entrances = [DOOR_PREFIX + oid for oid, opening in self.openings.items()
                     if OUTSIDE in opening["space_ids"] and DOOR_PREFIX + oid in graph]
        if not entrances:
            raise MapError("Building has no entrance.")
        before = nx.multi_source_dijkstra_path_length(graph, entrances, weight="weight")
        for sid in (first, second):
            if sid not in graph:
                raise MapError("Cannot connect a closed space.")
        hypothetical = type(self)(copy.deepcopy(self.data), version=self.version)
        hypothetical.walks = dict(self.walks)
        hypothetical.closed = set(self.closed)
        # The inherited mutation is confined to this fresh instance. Invalidate
        # both room walks and let the profile price the new portal normally.
        hypothetical.add_door(first, second, position=point)
        materialised = type(self)(hypothetical.data, version=self.version)
        materialised.walks = dict(hypothetical.walks)
        materialised.closed = set(hypothetical.closed)
        hypothetical = materialised
        after = nx.multi_source_dijkstra_path_length(hypothetical.constrained_graph(), entrances, weight="weight")
        improved = [s["id"] for s in self.floor_rooms(floor_id)
                    if s["id"] in after and (s["id"] not in before or before[s["id"]] - after[s["id"]] > 1.0)]
        return {"count": len(improved), "improved_space_ids": improved,
                "door_position": list(point)}

    def solve(self, kind: str, inputs: dict) -> dict:
        """Typed dispatch, usable directly by an agent without any benchmark metadata."""
        if not isinstance(kind, str) or not kind:
            raise CoreError("invalid_args", "kind must be a nonempty string.")
        if kind in {"locate", "count", "route", "route_step_free", "route_with_closure", "tour"}:
            return self._solve_warmup(kind, inputs)
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

    def _solve_warmup(self, kind: str, inputs: dict) -> dict:
        if not isinstance(inputs, dict):
            raise CoreError("invalid_args", "Inputs must be an object.")
        required = {"locate": {"asset"}, "count": {"asset_type", "floor_id"},
                    "route": {"start", "destination"}, "route_step_free": {"start", "destination"},
                    "route_with_closure": {"start", "destination"}, "tour": {"stops", "keep_order"}}[kind]
        optional = {"step_free", "closed"} if kind.startswith("route") else set()
        missing, extra = required - inputs.keys(), inputs.keys() - required - optional
        if missing or extra:
            raise CoreError("invalid_args", f"Invalid inputs: missing {sorted(missing)}, unexpected {sorted(extra)}")
        if kind == "locate":
            aid = inputs["asset"]
            if not isinstance(aid, str):
                raise CoreError("invalid_args", "asset must be an asset ID.")
            if aid not in self.assets:
                raise CoreError("not_found", f"Unknown asset: {aid}")
            asset = self.assets[aid]
            return {"asset_id": aid, "space_id": asset["space_id"],
                    "floor_level": self.floors[asset["floor_id"]]["level"], "position": list(asset["position"])}
        if kind == "count":
            if not all(isinstance(inputs[key], str) and inputs[key] for key in required):
                raise CoreError("invalid_args", "asset_type and floor_id must be nonempty strings.")
            if inputs["floor_id"] not in self.floors:
                raise CoreError("not_found", f"Unknown floor: {inputs['floor_id']}")
            return {"value": sum(a["type"] == inputs["asset_type"] and a["floor_id"] == inputs["floor_id"] for a in self.assets.values())}
        if kind == "tour":
            stops = inputs["stops"]
            if not isinstance(stops, list) or len(stops) < 2 or any(not isinstance(stop, str) or not stop for stop in stops):
                raise CoreError("invalid_args", "A fixed tour needs at least two nonempty stop IDs.")
            if inputs["keep_order"] is not True:
                raise CoreError("invalid_args", "The warm-up tour requires keep_order: true.")
            from .tour import plan_tour
            result = plan_tour(self, stops[0], [{"stop_id": f"s{index}", "target": stop} for index, stop in enumerate(stops[1:], 1)], keep_order=True)
            return {"reachable": not result.get("unreachable_stops"), **result}
        if "step_free" in inputs and not isinstance(inputs["step_free"], bool):
            raise CoreError("invalid_args", "step_free must be a boolean.")
        closed = inputs.get("closed", [])
        if not isinstance(closed, list) or any(not isinstance(item, str) or not item for item in closed):
            raise CoreError("invalid_args", "closed must be a list of element IDs.")
        from .routing import route
        result = route(self, inputs["start"], inputs["destination"],
                       {"step_free": kind == "route_step_free" or inputs.get("step_free", False), "closed": closed})
        return {"route": result, "reachable": result["reachable"]}

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


def _as_spatial(building):
    if isinstance(building, SpatialCore):
        return building
    if not isinstance(building, Building):
        raise CoreError("invalid_args", "Expected a core.building.Building instance.")
    result = SpatialCore(building.data, version=building.version)
    result.closed = set(building.closed)
    # Construction may already have reused completed walks from another fresh
    # materialisation. An unchanged caller with no local walks must not erase
    # that cache. Locally present walks retain precedence.
    result.walks.update(building.walks)
    return result


def shared_wall_midpoint(building, first, second):
    try:
        return _as_spatial(building).shared_wall_midpoint(first, second)
    except CoreError:
        raise
    except MapError as error:
        raise CoreError("invalid_args", str(error)) from error


def solve(building, kind: str, inputs: dict) -> dict:
    """Public pure solver interface shared by app, agents and benchmark."""
    try:
        # Warm-up dispatch uses only the Building read API and the pure routing
        # and tour functions. Avoid copying every polygon and asset merely to
        # count or locate an item in a large building.
        if isinstance(building, Building) and isinstance(kind, str) and kind in {"locate", "count", "route", "route_step_free", "route_with_closure", "tour"}:
            return SpatialCore._solve_warmup(building, kind, inputs)
        return _as_spatial(building).solve(kind, inputs)
    except CoreError:
        raise
    except MapError as error:
        raise CoreError("invalid_args", str(error)) from error
