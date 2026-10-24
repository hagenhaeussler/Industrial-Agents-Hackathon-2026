"""Isolated edit probes; importing this module never accesses persistent state."""

import networkx as nx

from .edits import _edited_copy, _entrance_distances, _resolve_id, resolve_edit
from .errors import EditError


def _floor(building, floor_id):
    if not isinstance(floor_id, str) or floor_id not in building.floors:
        raise EditError("invalid_args", "A valid floor_id is required for this probe.")
    return floor_id


def _space(building, reference):
    if isinstance(reference, dict):
        reference = reference.get("space_id")
    if isinstance(reference, str) and reference in building.assets:
        return building.assets[reference]["space_id"]
    return _resolve_id(building, reference, ("space",))


def what_if(building, edit, probe):
    """Return before/after effects without changing building data or closures.

    Route probes return full canonical RouteResults; exit probes use every open
    entrance as a source; reachability respects the same routing constraints.
    Unreachable distances are None, so the output always remains valid JSON.
    """
    if not isinstance(probe, dict):
        raise EditError("invalid_args", "A what-if probe must be an object.")
    resolved = resolve_edit(building, edit)
    after = _edited_copy(building, resolved)
    result = {"edit": resolved, "base_version": building.version, "persisted": False}
    kind = probe.get("kind")
    if kind == "route":
        from .routing import route
        before_route = route(building, probe.get("start"), probe.get("destination"), probe.get("constraints"))
        after_route = route(after, probe.get("start"), probe.get("destination"), probe.get("constraints"))
        result.update(kind=kind, before=before_route, after=after_route,
                      value=after_route.get("length_m") if after_route["reachable"] else None)
    elif kind == "exit_distances":
        floor_id = _floor(building, probe.get("floor_id"))
        before_distances, after_distances = _entrance_distances(building), _entrance_distances(after)
        ids = sorted(sid for sid, s in building.spaces.items() if s["floor_id"] == floor_id)
        before_values = {sid: before_distances.get(sid) for sid in ids}
        after_values = {sid: after_distances.get(sid) for sid in ids}
        improved = [sid for sid in ids if after_values[sid] is not None
                    and (before_values[sid] is None or before_values[sid] - after_values[sid] > 1.0)]
        result.update(kind=kind, floor_id=floor_id, before=before_values, after=after_values,
                      improved_space_ids=improved, value=len(improved),
                      newly_unreachable_space_ids=[sid for sid in ids
                                                   if before_values[sid] is not None and after_values[sid] is None])
    elif kind == "reachable_count":
        from .routing import constrained_graph
        floor_id = _floor(building, probe.get("floor_id"))
        start = _space(building, probe.get("start"))
        counts = []
        for candidate in (building, after):
            graph = constrained_graph(candidate, probe.get("constraints"), start_space=start)
            reachable = nx.node_connected_component(graph, start) if start in graph else set()
            counts.append(sorted(sid for sid in reachable if sid in candidate.spaces
                                 and candidate.spaces[sid]["floor_id"] == floor_id))
        result.update(kind=kind, before={"value": len(counts[0]), "space_ids": counts[0]},
                      after={"value": len(counts[1]), "space_ids": counts[1]}, value=len(counts[1]))
    else:
        raise EditError("invalid_args", "Unknown what-if probe; use route, exit_distances or reachable_count.")
    return result
