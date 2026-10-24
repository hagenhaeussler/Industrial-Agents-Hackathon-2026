"""Constrained routes with the kit's graph costs and recovered walk geometry."""

import itertools
import math
import networkx as nx

from starter_agent.building_map import DOOR_PREFIX, LENGTH_DECIMALS
from .errors import CoreError
from .geometry import walk_polyline
from .profiles import LIFT_FIXED_M, LIFT_M_PER_RISE, STAIRS_M_PER_RISE


def normalize_constraints(b, constraints=None):
    constraints = constraints or {}
    if not isinstance(constraints, dict):
        raise CoreError("invalid_args", "Constraints must be an object.")
    extra = set(constraints) - {"step_free", "min_door_width_m", "closed", "no_transit_room_types"}
    if extra:
        raise CoreError("invalid_args", f"Unknown constraint fields: {', '.join(sorted(extra))}")
    width = constraints.get("min_door_width_m", 0.0)
    if isinstance(width, bool) or not isinstance(width, (int, float)) or not math.isfinite(width) or width < 0:
        raise CoreError("invalid_args", "min_door_width_m must be a finite non-negative number.")
    step_free = constraints.get("step_free", False)
    if not isinstance(step_free, bool):
        raise CoreError("invalid_args", "step_free must be boolean.")
    closed = constraints.get("closed", [])
    no_transit = constraints.get("no_transit_room_types", [])
    if not isinstance(closed, (list, tuple, set)) or not all(isinstance(i, str) for i in closed):
        raise CoreError("invalid_args", "closed must contain element IDs.")
    if not isinstance(no_transit, (list, tuple, set)) or not all(isinstance(i, str) for i in no_transit):
        raise CoreError("invalid_args", "no_transit_room_types must contain room types.")
    unknown = set(closed) - (set(b.spaces) | set(b.openings) | set(b.connectors))
    if unknown:
        raise CoreError("not_found", f"Unknown closed elements: {', '.join(sorted(unknown))}")
    return {"step_free": step_free, "min_door_width_m": float(width),
            "closed": sorted(set(b.closed) | set(closed)),
            "no_transit_room_types": sorted(set(no_transit))}


def constrained_graph(b, constraints=None, start_space=None, destination_space=None):
    """Keep all parallel edges and permit restricted room types only at endpoints."""
    c = normalize_constraints(b, constraints)
    closed = set(c["closed"])
    graph = nx.MultiGraph()
    allowed_spaces = {sid for sid, s in b.spaces.items() if sid not in closed and
                      (s["room_type"] not in c["no_transit_room_types"] or sid in (start_space, destination_space))}
    doors = {DOOR_PREFIX + oid for oid, opening in b.openings.items()
             if oid not in closed and (not c["step_free"] or opening["step_free"])
             and opening.get("width_m", 0) >= c["min_door_width_m"]}
    graph.add_nodes_from(allowed_spaces)
    # Preserve kit insertion order for deterministic equal-cost path choices.
    for sid in b.spaces:
        if sid not in allowed_spaces:
            continue
        for first, second, length in b.space_walks(sid):
            if (first == sid or first in doors) and second in doors:
                graph.add_edge(first, second, weight=round(length, LENGTH_DECIMALS), space=sid)
    levels = {f: floor["level"] for f, floor in b.floors.items()}
    elevations = {f: floor["elevation_m"] for f, floor in b.floors.items()}
    for cid, connector in b.connectors.items():
        if cid in closed or (c["step_free"] and not connector["step_free"]):
            continue
        stops = sorted(zip(connector["floor_ids"], connector["space_ids"], strict=True), key=lambda s: levels[s[0]])
        pairs = itertools.combinations(stops, 2) if connector["kind"] == "lift" else itertools.pairwise(stops)
        for (fa, sa), (fb, sb) in pairs:
            if sa not in allowed_spaces or sb not in allowed_spaces:
                continue
            rise = abs(elevations[fa] - elevations[fb])
            cost = (LIFT_FIXED_M + LIFT_M_PER_RISE * rise if connector["kind"] == "lift"
                    else STAIRS_M_PER_RISE * rise)
            graph.add_edge(sa, sb, weight=round(cost, LENGTH_DECIMALS), via=cid)
    return graph


def _endpoint(b, value):
    if isinstance(value, dict):
        sid, point = value.get("space_id"), value.get("point")
    else:
        sid, point = value, None
    if not isinstance(sid, str):
        raise CoreError("invalid_args", "A space ID or asset ID is required.")
    if sid in b.assets:
        sid = b.assets[sid]["space_id"]
    if sid not in b.spaces:
        raise CoreError("not_found", f"Unknown space or asset ID: {sid}")
    if point is not None:
        if not isinstance(point, (list, tuple)) or len(point) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in point):
            raise CoreError("invalid_args", "Position point must contain two finite numbers.")
        point = [float(v) for v in point]
    return sid, point


def _position_node(b, graph, sid, point, label):
    if point is None:
        return sid
    node = "__position:" + label
    # Validate even if the space is closed and there can be no outgoing edges.
    walk_polyline(b, sid, sid, sid, start_point=point, end_point=point)
    if sid not in graph:
        return node
    graph.add_node(node)
    members = [sid] + [DOOR_PREFIX + oid for oid, o in b.openings.items()
                       if sid in o["space_ids"] and DOOR_PREFIX + oid in graph]
    for target in members:
        walk = walk_polyline(b, sid, sid, target, start_point=point)
        graph.add_edge(node, target, weight=round(walk["kit_length_m"], LENGTH_DECIMALS), space=sid)
    return node


def _find(b, start, destination, c, start_point=None, destination_point=None):
    graph = constrained_graph(b, c, start, destination)
    source = _position_node(b, graph, start, start_point, "start")
    target = _position_node(b, graph, destination, destination_point, "destination")
    if start == destination and start_point is not None and destination_point is not None and start in graph:
        direct = walk_polyline(b, start, start, destination, start_point=start_point, end_point=destination_point)
        graph.add_edge(source, target, weight=round(direct["kit_length_m"], LENGTH_DECIMALS), space=start)
    try:
        length, nodes = nx.single_source_dijkstra(graph, source, target, weight="weight")
        return graph, length, nodes
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return graph, None, []


def _unreachable(b, start, destination, c):
    # Check each restriction independently; closures retain priority when their
    # removal alone restores this requested mobility profile.
    variations = [("blocked_by_closure", {**c, "closed": []}),
                  ("no_step_free_path", {**c, "step_free": False}),
                  ("too_narrow", {**c, "min_door_width_m": 0.0})]
    for reason, relaxed in variations:
        if (reason == "blocked_by_closure" and not c["closed"]) or (reason == "no_step_free_path" and not c["step_free"]) or (reason == "too_narrow" and not c["min_door_width_m"]):
            continue
        # normalize_constraints merges b.closed; remove that merge for this
        # diagnostic through a shallow view, without mutating the building.
        import copy
        view = copy.copy(b)
        view.closed = set() if reason == "blocked_by_closure" else set(b.closed)
        graph, length, nodes = _find(view, start, destination, relaxed)
        if length is None:
            continue
        blocking = []
        if reason == "blocked_by_closure":
            used = set(nodes)
            used.update(n.removeprefix(DOOR_PREFIX) for n in nodes if n.startswith(DOOR_PREFIX))
            for a, z in itertools.pairwise(nodes):
                edge = b.cheapest(graph, a, z)
                used.add(edge.get("via"))
                used.add(edge.get("space"))
            blocking = sorted(set(c["closed"]) & used)
        return reason, blocking
    return "disconnected", []


def route(b, start, destination, constraints=None):
    """Return a JSON-ready C1 RouteResult. Free text must be resolved first."""
    start, start_point = _endpoint(b, start)
    destination, end_point = _endpoint(b, destination)
    c = normalize_constraints(b, constraints)
    common = {"from_space_id": start, "to_space_id": destination, "constraints": c,
              "profile": b.profile, "building_id": b.id, "building_version": b.version,
              "content_hash": b.content_hash}
    graph, length, nodes = _find(b, start, destination, c, start_point, end_point)
    if length is None:
        reason, blocking = _unreachable(b, start, destination, c)
        return {**common, "reachable": False, "reason": reason, "blocking_ids": blocking}
    segments, elements, spaces = [], [], [start]
    for first, second in itertools.pairwise(nodes):
        edge = b.cheapest(graph, first, second)
        if "via" in edge:
            connector = b.connectors[edge["via"]]
            elements.append(edge["via"])
            segments.append({"floor_id": b.spaces[first]["floor_id"], "kind": connector["kind"],
                             "element_id": edge["via"], "points": [list(b.anchor(first))],
                             "to_floor_id": b.spaces[second]["floor_id"], "length_m": edge["weight"],
                             "to_point": list(b.anchor(second))})
            if spaces[-1] != second:
                spaces.append(second)
            continue
        sid = edge["space"]
        if spaces[-1] != sid:
            spaces.append(sid)
        if second.startswith(DOOR_PREFIX):
            elements.append(second.removeprefix(DOOR_PREFIX))
        first_member = sid if first.startswith("__position:") else first
        second_member = sid if second.startswith("__position:") else second
        first_point = (start_point if first.endswith(":start") else end_point) if first.startswith("__position:") else None
        second_point = (start_point if second.endswith(":start") else end_point) if second.startswith("__position:") else None
        walk = walk_polyline(b, sid, first_member, second_member, start_point=first_point, end_point=second_point)
        segments.append({"floor_id": b.spaces[sid]["floor_id"], "kind": "walk", "space_id": sid,
                         "points": walk["points"], "length_m": edge["weight"],
                         "geometry_length_m": walk["length_m"], "fallback": walk["fallback"],
                         "from_node": first_member, "to_node": second_member,
                         "endpoint_stubs": walk["endpoint_stubs"]})
    if spaces[-1] != destination:
        spaces.append(destination)
    # Public node IDs remain kit IDs; explicit point positions live in metadata.
    public_nodes = [start if n == "__position:start" else destination if n == "__position:destination" else n for n in nodes]
    result = {**common, "reachable": True, "length_m": round(length, 2), "length_m_exact": length,
              "space_path": spaces, "node_path": public_nodes, "element_path": elements,
              "segments": segments, "start_position": start_point or list(b.anchor(start)),
              "destination_position": end_point or list(b.anchor(destination))}
    from .maneuvers import build_maneuvers
    result["maneuvers"] = build_maneuvers(b, result)
    return result
