"""Collection tours with explicit exact/heuristic policies and stable stop identity."""

import copy
import math
import networkx as nx

from .errors import CoreError
from .routing import route, constrained_graph, normalize_constraints, _endpoint


def _position(b, value):
    sid, point = _endpoint(b, value)
    return {"space_id": sid, "floor_id": b.spaces[sid]["floor_id"],
            "point": point or list(b.anchor(sid)),
            "source": value.get("source", "desk") if isinstance(value, dict) else "desk"}


def _group_stops(b, stops):
    if not isinstance(stops, list):
        raise CoreError("invalid_args", "Stops must be a list of asset/space IDs or target objects.")
    groups = {}
    for raw in stops:
        item = raw if isinstance(raw, dict) else {"target": raw}
        target = item.get("target", item.get("space_id", item.get("id")))
        sid, _ = _endpoint(b, target)
        assets = [target] if target in b.assets else list(item.get("asset_ids", []))
        if any(a not in b.assets or b.assets[a]["space_id"] != sid for a in assets):
            raise CoreError("invalid_args", "A stop's assets must exist in its target room.")
        key = (sid, item.get("stop_id")) if item.get("_preserve_identity") else sid
        if key not in groups:
            groups[key] = {"stop_id": item.get("stop_id", f"s{len(groups)+1}"),
                           "space_id": sid, "asset_ids": [], "label": item.get("label", b.spaces[sid]["name"]),
                           "status": item.get("status", "pending")}
        group = groups[key]
        for aid in assets:
            if aid not in group["asset_ids"]:
                group["asset_ids"].append(aid)
        if group["asset_ids"] and not item.get("label"):
            group["label"] = ", ".join(b.assets[a]["name"] for a in group["asset_ids"]) + " · " + b.spaces[sid]["name"]
    if len({s["stop_id"] for s in groups.values()}) != len(groups):
        raise CoreError("invalid_args", "Stop IDs must be unique.")
    return list(groups.values())


def optimal_order(matrix, end_costs=None):
    """Held-Karp open path: matrix[0] is start; indices 1..n are stops."""
    n = len(matrix) - 1
    if not n:
        return [], 0.0
    state = {(1 << j, j): (matrix[0][j+1], (j,)) for j in range(n)}
    for mask in range(1, 1 << n):
        for last in range(n):
            if (mask, last) not in state:
                continue
            cost, path = state[(mask, last)]
            for nxt in range(n):
                if mask & (1 << nxt):
                    continue
                key = (mask | (1 << nxt), nxt)
                candidate = (cost + matrix[last+1][nxt+1], path + (nxt,))
                if key not in state or candidate < state[key]:
                    state[key] = candidate
    full = (1 << n) - 1
    choices = [(state[(full, j)][0] + (end_costs[j] if end_costs else 0), state[(full, j)][1]) for j in range(n)]
    cost, path = min(choices)
    return list(path), cost


def _heuristic_order(matrix, end_costs=None):
    n = len(matrix)-1
    todo, order, last = set(range(n)), [], 0
    while todo:
        nxt = min(todo, key=lambda j: (matrix[last][j+1], j))
        order.append(nxt)
        todo.remove(nxt)
        last = nxt+1
    def cost(seq):
        return matrix[0][seq[0]+1] + sum(matrix[a+1][z+1] for a,z in zip(seq,seq[1:])) + (end_costs[seq[-1]] if end_costs else 0)
    improved = True
    while improved:
        improved = False
        best = cost(order)
        for a in range(n):
            for z in range(a+2,n+1):
                candidate = order[:a] + list(reversed(order[a:z])) + order[z:]
                if cost(candidate) + 1e-9 < best:
                    order, improved = candidate, True
                    break
            if improved:
                break
    return order, cost(order)


def plan_tour(b, start, stops, constraints=None, keep_order=False, end=None):
    """Plan all reachable pending stops; server assigns the opaque tour_id."""
    start_pos = _position(b, start)
    end_pos = _position(b, end) if end is not None else None
    c = normalize_constraints(b, constraints)
    view = copy.copy(b)
    view.closed = set()
    requested = normalize_constraints(view, constraints)
    grouped = _group_stops(b, stops)
    pending = [s for s in grouped if s["status"] != "collected"]
    unreachable = []
    feasible = []
    first_routes = {}
    for stop in pending:
        leg = route(b, start, stop["space_id"], c)
        first_routes[stop["space_id"]] = leg
        if not leg["reachable"]:
            unreachable.append({"stop_id": stop["stop_id"], "space_id": stop["space_id"], "reason": leg["reason"]})
        else:
            feasible.append(stop)
    order = list(range(len(feasible)))
    policy = "fixed" if keep_order else "optimized_exact" if len(feasible)<=12 else "optimized_heuristic"
    if feasible and not keep_order:
        ids = [start_pos["space_id"]] + [s["space_id"] for s in feasible]
        matrix = [[0.0]*len(ids) for _ in ids]
        graph = constrained_graph(b, c)
        for i, source in enumerate(ids):
            lengths = nx.single_source_dijkstra_path_length(graph, source, weight="weight") if source in graph else {}
            for j,target in enumerate(ids):
                if i == 0 and j:
                    matrix[i][j] = first_routes[target]["length_m_exact"]
                elif c["no_transit_room_types"] and i!=j:
                    result = route(b,source,target,c)
                    matrix[i][j] = result.get("length_m_exact", math.inf)
                else:
                    matrix[i][j] = lengths.get(target,math.inf)
        end_costs = None
        if end_pos:
            end_costs = [route(b,s["space_id"],end,c).get("length_m_exact", math.inf) for s in feasible]
        order,_ = optimal_order(matrix,end_costs) if len(feasible)<=12 else _heuristic_order(matrix,end_costs)
    legs, current = [], start
    ordered = []
    for index in order:
        stop = feasible[index]
        leg = route(b,current,stop["space_id"],c)
        if not leg["reachable"]:
            unreachable.append({"stop_id":stop["stop_id"],"space_id":stop["space_id"],"reason":leg["reason"]})
            continue
        legs.append(leg)
        current = stop["space_id"]
        ordered.append(stop["stop_id"])
    end_route = route(b,current,end,c) if end_pos else None
    if end_route and end_route["reachable"]:
        legs.append(end_route)
    elif end_route:
        unreachable.append({"stop_id":"end", "space_id":end_pos["space_id"],"reason":end_route["reason"]})
    exact = math.fsum(leg["length_m_exact"] for leg in legs)
    return {"tour_id": None,"revision":1,"status":"blocked" if unreachable and not ordered else "active" if ordered else "completed",
            "building_id":b.id,"building_version":b.version,"content_hash":b.content_hash,
            "profile":b.profile,"constraints":requested,"building_closed":sorted(b.closed),"order_policy":policy,
            "start":start_pos,"end":end_pos,"stops":grouped,"order":ordered,"legs":legs,
            "length_m":round(exact,2),"length_m_exact":exact,"unreachable_stops":unreachable,
            "changed_because":None,"reachable":not unreachable}


def replan(b, tour, from_position, reason_event=None):
    """Recompute pending work without losing collected stops or stable stop IDs."""
    old = copy.deepcopy(tour)
    pending = []
    next_id = max((int(s["stop_id"][1:]) for s in old.get("stops",[])
                   if s.get("stop_id", "").startswith("s") and s["stop_id"][1:].isdigit()), default=0)+1
    for original in old.get("stops",[]):
        if original.get("status") == "collected":
            continue
        assets = original.get("asset_ids", [])
        locations = {}
        for aid in assets:
            if aid not in b.assets:
                raise CoreError("not_found", f"A pending part was removed: {aid}")
            locations.setdefault(b.assets[aid]["space_id"], []).append(aid)
        if not assets:
            locations[original["space_id"]] = []
        for i, (sid, asset_ids) in enumerate(locations.items()):
            stop = dict(original, space_id=sid, asset_ids=asset_ids, _preserve_identity=True)
            if i:
                stop["stop_id"] = f"s{next_id}"
                next_id += 1
            if asset_ids:
                stop["label"] = ", ".join(b.assets[a]["name"] for a in asset_ids) + " · " + b.spaces[sid]["name"]
            pending.append(stop)
    by_id = {s["stop_id"]:s for s in pending}
    if old.get("order_policy")=="fixed":
        pending = [by_id[sid] for sid in old.get("order",[]) if sid in by_id] + [s for s in pending if s["stop_id"] not in old.get("order",[])]
    result = plan_tour(b,from_position,pending,old.get("constraints"),old.get("order_policy")=="fixed",old.get("end"))
    result["stops"] = [s for s in old.get("stops",[]) if s.get("status")=="collected"] + result["stops"]
    result["tour_id"] = old.get("tour_id")
    result["revision"] = old.get("revision",0)+1
    result["changed_because"] = reason_event
    return result
