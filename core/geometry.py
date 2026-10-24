"""Recover the kit's visibility-graph walks without changing its cost model."""

from collections import OrderedDict
from dataclasses import dataclass, field
import heapq
import math
from threading import RLock

import numpy as np
from shapely.geometry import Point
from shapely.ops import nearest_points

from starter_agent.building_map import (
    BLOCKED_DETOUR_FACTOR, COVER_TOLERANCE_M, DOOR_PREFIX,
    WALL_CLEARANCE_M, door_landing, visibility_matrix,
)
from .errors import CoreError


@dataclass
class SpaceGeometry:
    polygon: object
    allowed: object
    members: list
    nodes: list
    matrix: np.ndarray
    paths: dict = field(default_factory=dict)


_CACHE = OrderedDict()
_LOCK = RLock()
_MAX_CACHED_SPACES = 512


def space_geometry(b, space_id):
    """Cached node ordering is exactly BuildingMap.space_walks' ordering."""
    key = (b.content_hash, b.version, space_id)
    with _LOCK:
        cached = _CACHE.get(key)
        if cached is not None:
            _CACHE.move_to_end(key)
            return cached
    polygon = b.polygons[space_id]
    walkable = polygon.buffer(-WALL_CLEARANCE_M)
    if walkable.is_empty or walkable.geom_type != "Polygon":
        walkable = polygon
    allowed = walkable.buffer(COVER_TOLERANCE_M)
    members = [(space_id, b.anchor(space_id), None)]
    for opening in b.openings.values():
        if space_id in opening["space_ids"]:
            position = tuple(opening["position"][:2])
            members.append((DOOR_PREFIX + opening["id"], door_landing(polygon, position), position))
    corners = [tuple(p) for ring in [walkable.exterior, *walkable.interiors]
               for p in list(ring.coords)[:-1]]
    nodes = [tuple(m[1]) for m in members] + corners
    geometry = SpaceGeometry(polygon, allowed, members, nodes, visibility_matrix(allowed, nodes))
    with _LOCK:
        _CACHE[key] = geometry
        _CACHE.move_to_end(key)
        while len(_CACHE) > _MAX_CACHED_SPACES:
            _CACHE.popitem(last=False)
    return geometry


def _shortest_path(matrix, source, target):
    """Dense Dijkstra retaining predecessors, including zero-length edges."""
    distances = {source: 0.0}
    previous = {}
    queue = [(0.0, source)]
    while queue:
        distance, node = heapq.heappop(queue)
        if distance != distances.get(node):
            continue
        if node == target:
            path = [target]
            while path[-1] != source:
                path.append(previous[path[-1]])
            return distance, path[::-1]
        for neighbour in np.flatnonzero(np.isfinite(matrix[node])):
            neighbour = int(neighbour)
            candidate = distance + float(matrix[node, neighbour])
            if candidate < distances.get(neighbour, math.inf):
                distances[neighbour] = candidate
                previous[neighbour] = node
                heapq.heappush(queue, (candidate, neighbour))
    return math.inf, []


def polyline_length(points):
    return sum(math.dist(a, c) for a, c in zip(points, points[1:]))


def _deduplicate(points):
    result = []
    for point in points:
        point = [float(point[0]), float(point[1])]
        if not result or math.dist(result[-1], point) > 1e-12:
            result.append(point)
    return result


def walk_polyline(b, space_id, first_node, second_node, *, start_point=None, end_point=None):
    """A walk's drawable length and its authoritative kit cost are separate.

    Custom positions are connected through the same visibility geometry. Positions
    in the wall-clearance band receive an explicit short endpoint stub. A kit
    fallback keeps its inflated cost and is visibly flagged, never disguised as
    a valid shortest walk.
    """
    geometry = space_geometry(b, space_id)
    index = {member[0]: i for i, member in enumerate(geometry.members)}
    nodes = geometry.nodes
    matrix = geometry.matrix
    stubs = []
    for node, custom in ((first_node, start_point), (second_node, end_point)):
        if custom is None:
            if node not in index:
                raise CoreError("invalid_args", f"{node} is not a member of {space_id}.")
            i = index[node]
            stubs.append((i, geometry.members[i][2]))
            continue
        raw = tuple(float(v) for v in custom[:2])
        if not all(math.isfinite(v) for v in raw) or not geometry.polygon.buffer(0.02).covers(Point(raw)):
            raise CoreError("invalid_args", f"Position is outside space {space_id}.")
        landed = raw
        if not geometry.allowed.covers(Point(raw)):
            p = nearest_points(geometry.allowed, Point(raw))[0]
            landed = (p.x, p.y)
        nodes = list(nodes) + [landed]
        stubs.append((len(nodes) - 1, raw))
    if nodes is not geometry.nodes:
        matrix = visibility_matrix(geometry.allowed, nodes)
    first, second = stubs[0][0], stubs[1][0]
    cache_key = (first, second)
    if nodes is geometry.nodes and cache_key in geometry.paths:
        distance, path = geometry.paths[cache_key]
    else:
        distance, path = _shortest_path(matrix, first, second)
        if nodes is geometry.nodes:
            geometry.paths[cache_key] = distance, path
    fallback = not math.isfinite(distance)
    if fallback:
        distance = math.dist(nodes[first], nodes[second]) * BLOCKED_DETOUR_FACTOR
        path = [first, second]
    before, after = stubs[0][1], stubs[1][1]
    points = _deduplicate(([before] if before is not None else []) +
                          [nodes[i] for i in path] + ([after] if after is not None else []))
    cost = distance
    if before is not None:
        cost += math.dist(before, nodes[first])
    if after is not None:
        cost += math.dist(after, nodes[second])
    return {"points": points, "length_m": polyline_length(points), "kit_length_m": cost,
            "fallback": fallback, "endpoint_stubs": [p is not None for _, p in stubs]}
