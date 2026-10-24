"""Contract bridge to independently published core functions.

The kit fallback is explicit in every tool trace and route. Its geometry is
provisional: it must never be presented as the H02 walk-polyline implementation.
"""

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import importlib
import itertools
import json
import logging
import math
import re
import threading

import networkx as nx
from rapidfuzz.fuzz import ratio
from shapely.geometry import Point
from starter_agent.building_map import BuildingMap, DOOR_PREFIX, outline

from .errors import ServiceError

logger = logging.getLogger(__name__)


def core_function(module, name):
    try:
        return getattr(importlib.import_module(f"core.{module}"), name)
    except ModuleNotFoundError as exc:
        if exc.name not in ("core", f"core.{module}"):
            raise
    except AttributeError:
        return None
    return None


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        if hasattr(exc, "code"):
            extra = {"candidates": exc.candidates} if getattr(exc, "candidates", None) else {}
            raise ServiceError(exc.code, str(exc), **extra) from exc
        raise


@dataclass
class AdaptedBuilding:
    raw: dict
    kit: BuildingMap
    core: object | None
    id: str
    content_hash: str
    version: int
    lock: object = field(default_factory=threading.RLock, repr=False)

    @property
    def closed(self):
        return self.kit.closed

    @property
    def adapter(self):
        return "core" if self.core is not None else "kit"


def materialize(raw, events):
    base = deepcopy(raw)
    content_hash = "sha256:" + hashlib.sha256(json.dumps(
        base, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode()).hexdigest()[:16]
    load = core_function("building", "load_building")
    apply_events = core_function("edits", "apply_events")
    core = _call(load, base) if load else None
    if core is not None and (not events or apply_events):
        if events:
            core = _call(apply_events, core, events)
        core_raw = getattr(core, "data", None) or getattr(core, "raw", None)
        if core_raw is None:
            core_map = getattr(core, "map", None) or getattr(core, "building_map", None)
            core_raw = getattr(core_map, "data", None)
        if core_raw is not None:
            base = deepcopy(core_raw)
            kit = BuildingMap(base)
            kit.closed = set(getattr(core, "closed", []))
            return AdaptedBuilding(base, kit, core, raw["building"]["id"], getattr(core, "content_hash", content_hash), len(events))
    # Replay from the immutable base; an undo removes its event from the active
    # semantic list while still occupying its own monotonic building version.
    undone = {event["undoes"] for event in events if event["kind"] == "undo"}
    kit = BuildingMap(base)
    for event in events:
        if event["kind"] != "undo" and event["event_id"] not in undone:
            apply_kit_edit(kit, event["edit"], event["building_version"])
    return AdaptedBuilding(base, kit, core if not events else None, raw["building"]["id"], content_hash, len(events))


def apply_kit_edit(kit, edit, version=1):
    action, target = edit["action"], edit["target"]
    if action in {"close", "open"}:
        kit.set_closed(target, action == "close")
    elif action == "move_asset":
        asset = kit.assets[target]
        space = kit.spaces[edit["second_target"]]
        point = edit.get("value")
        if isinstance(point, str):
            point = [float(v.strip()) for v in point.split(",")]
        asset.update(space_id=space["id"], floor_id=space["floor_id"], position=point or list(kit.anchor(space["id"])))
    elif action == "set_room_type":
        kit.spaces[target]["room_type"] = edit["value"]
    elif action == "add_door":
        first, second = kit.spaces[target], kit.spaces[edit["second_target"]]
        wall = outline(first["polygon"]).boundary.intersection(outline(second["polygon"]).boundary)
        lines = list(wall.geoms) if wall.geom_type == "MultiLineString" else [wall]
        lines = [line for line in lines if line.geom_type == "LineString"]
        if not lines or max(line.length for line in lines) < 1:
            raise ServiceError("invalid_args", "A door needs a shared wall at least one metre long.")
        longest = max(lines, key=lambda line: line.length)
        midpoint = longest.interpolate(0.5, normalized=True)
        opening = kit.add_door(target, edit["second_target"], position=(midpoint.x, midpoint.y))
        opening["width_m"] = float(edit.get("value") or 0.9)
        previous_id = opening["id"]
        opening["id"] = f"{first['floor_id']}-O-evt{version}"
        kit.openings.pop(previous_id)
        kit.openings[opening["id"]] = opening
    else:
        raise ServiceError("invalid_args", "Unknown edit action.")


def _normal(text):
    return " ".join(re.findall(r"[\w]+", str(text).casefold()))


def _numbers(text):
    return [int(n) for n in re.findall(r"\d+", str(text))]


def resolve(building, text, kind="any"):
    fn = core_function("resolve", "resolve")
    if building.core is not None and fn:
        return _call(fn, building.core, text, kind)
    kit = building.kit
    sources = {
        "space": kit.spaces, "asset": kit.assets, "floor": kit.floors,
        "connector": kit.connectors, "opening": kit.openings,
    }
    if kind in {"asset_type", "room_type"}:
        field, records = ("type", kit.assets) if kind == "asset_type" else ("room_type", kit.spaces)
        values = {item.get(field) for item in records.values()} - {None}
        sources = {kind: {v: {"id": v, "name": v} for v in values}}
    kinds = list(sources) if kind == "any" else [kind]
    candidates = []
    query = _normal(text)
    if not query:
        return {"status": "none", "candidates": []}
    for entity_kind in kinds:
        for entity_id, entity in sources.get(entity_kind, {}).items():
            floor = kit.floors.get(entity.get("floor_id"), {})
            name = entity.get("name") or entity.get("ref") or entity_id
            label = f"{name} ({floor['name']})" if floor else name
            variants = [name, label, entity.get("ref", "")]
            if str(text) == entity_id:
                score, why = 1.0, "exact ID"
            elif str(text).casefold() in {str(v).casefold() for v in variants if v}:
                score, why = 0.99, "exact name/ref/label"
            elif query in {_normal(v) for v in variants if v}:
                score, why = 0.98, "normalized"
            else:
                eligible = [v for v in variants if v and _numbers(v) == _numbers(text)]
                matches = [v for v in eligible if set(query.split()) <= set(_normal(v).split())]
                score = 0.9 if matches else max((ratio(query, _normal(v)) / 100 * 0.85 for v in eligible), default=0)
                why = "token match" if matches else "fuzzy"
                if score < 0.72:
                    continue
            candidates.append({"kind": entity_kind, "id": entity_id, "label": label, "score": score, "why": why})
    candidates.sort(key=lambda c: (-c["score"], c["label"], c["id"]))
    if not candidates:
        return {"status": "none", "candidates": []}
    best = [c for c in candidates if c["score"] == candidates[0]["score"]]
    return {"status": "unique" if len(best) == 1 else "ambiguous", "candidates": best}


def require_id(building, text, kind="any"):
    result = resolve(building, text, kind)
    if result["status"] == "none":
        raise ServiceError("not_found", f"No {kind if kind != 'any' else 'place or item'} matches '{text}'.")
    if result["status"] != "unique":
        raise ServiceError("ambiguous", "Which of these did you mean?", candidates=result["candidates"][:4])
    return result["candidates"][0]["id"]


def position(building, target):
    if isinstance(target, dict):
        space_id = target.get("space_id")
    elif isinstance(target, str):
        space_id = building.kit.assets.get(target, {}).get("space_id", target)
    else:
        raise ServiceError("invalid_args", "A position must name a room or item.")
    if not isinstance(space_id, str) or space_id not in building.kit.spaces:
        raise ServiceError("invalid_args", "Position does not name a space in this building.")
    space = building.kit.spaces[space_id]
    result = {"space_id": space_id, "point": list(building.kit.anchor(space_id)), "floor_id": space["floor_id"]}
    if isinstance(target, dict):
        if target.get("floor_id") not in (None, space["floor_id"]):
            raise ServiceError("invalid_args", "Position floor does not match its room.")
        point = target.get("point")
        if point is not None:
            if not isinstance(point, (tuple, list)) or len(point) != 2 or any(isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) for n in point):
                raise ServiceError("invalid_args", "Position must contain two finite coordinates.")
            if not outline(space["polygon"]).buffer(0.02).covers(Point(point)):
                raise ServiceError("invalid_args", "Position must lie inside its room.")
        result.update({k: v for k, v in target.items() if v is not None})
    return result


def _walk_cache_key(building, constraints):
    return "kit_walks:" + json.dumps({"version": building.version, "event_log": getattr(building, "event_fingerprint", ""), "profile": "kit_1_1_0", "constraints": constraints}, sort_keys=True, separators=(",", ":"))


def _load_walks(building, constraints):
    store = getattr(building, "cache_store", None)
    if not store:
        return
    key = _walk_cache_key(building, constraints)
    checked = getattr(building, "checked_walk_keys", set())
    if key in checked:
        return
    checked.add(key)
    building.checked_walk_keys = checked
    try:
        blob = store.cache_get(building.content_hash, key)
        if blob is None:
            return
        walks = json.loads(blob)
        allowed_nodes = set(building.kit.spaces) | {DOOR_PREFIX + oid for oid in building.kit.openings}
        if not isinstance(walks, dict) or not set(walks) <= set(building.kit.spaces):
            raise ValueError("Unknown cache space")
        for entries in walks.values():
            if not isinstance(entries, list):
                raise ValueError("Invalid cache entries")
            for entry in entries:
                if not isinstance(entry, list) or len(entry) != 3 or entry[0] not in allowed_nodes or entry[1] not in allowed_nodes or not isinstance(entry[2], (int, float)) or not math.isfinite(entry[2]) or entry[2] < 0:
                    raise ValueError("Invalid walk entry")
        building.kit.walks.update(walks)
    except Exception:
        logger.warning("Ignoring invalid/unavailable derived walk cache", exc_info=True)


def _save_walks(building, constraints):
    store = getattr(building, "cache_store", None)
    if not store:
        return
    key = _walk_cache_key(building, constraints)
    # Geometry caches depend on the immutable content, version, profile and the
    # complete request constraints. Keep cache failure separate from truth/state.
    encoded = json.dumps(building.kit.walks, separators=(",", ":"), allow_nan=False).encode()
    signature = hashlib.sha256(encoded).hexdigest()
    saved = getattr(building, "saved_walks", {})
    if saved.get(key) == signature:
        return
    try:
        store.cache_put(building.content_hash, key, encoded)
        saved[key] = signature
        building.saved_walks = saved
    except Exception:
        logger.warning("Could not persist derived walk cache", exc_info=True)


def route(building, start, destination, constraints=None):
    constraints = {"step_free": False, "min_door_width_m": 0.0, "closed": [], "no_transit_room_types": [], **(constraints or {})}
    first, last = position(building, start), position(building, destination)
    fn = core_function("routing", "route")
    if building.core is not None and fn:
        return _call(fn, building.core, first, last, constraints=constraints)
    kit = BuildingMap(deepcopy(building.raw))
    kit.closed = set(building.closed) | set(constraints["closed"])
    with building.lock:
        _load_walks(building, constraints)
        kit.walks = building.kit.walks
        graph = kit.graph(constraints["step_free"])
        _save_walks(building, constraints)
    minimum = constraints["min_door_width_m"]
    if minimum:
        graph.remove_nodes_from([DOOR_PREFIX + o["id"] for o in kit.openings.values() if o["width_m"] < minimum])
    prohibited = set(constraints["no_transit_room_types"])
    excluded = {sid for sid, s in kit.spaces.items() if s.get("room_type") in prohibited and sid not in {first["space_id"], last["space_id"]}}
    if excluded:
        graph.remove_nodes_from(excluded)
        graph.remove_edges_from([(u, v, k) for u, v, k, edge in graph.edges(keys=True, data=True) if edge.get("space") in excluded])
    metadata = {"from_space_id": first["space_id"], "to_space_id": last["space_id"], "constraints": constraints,
                "profile": "kit_1_1_0", "building_id": building.id, "building_version": building.version,
                "content_hash": building.content_hash, "_adapter": "kit", "geometry": "provisional"}
    try:
        distance, nodes = nx.single_source_dijkstra(graph, first["space_id"], last["space_id"], weight="weight")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        reason = "blocked_by_closure" if kit.closed else "no_step_free_path" if constraints["step_free"] else "too_narrow" if minimum else "disconnected"
        return {**metadata, "reachable": False, "reason": reason, "blocking_ids": sorted(kit.closed)}
    elements, segments = [], []
    for u, v in itertools.pairwise(nodes):
        edge = kit.cheapest(graph, u, v)
        floor, p1 = kit.node_point(u)
        to_floor, p2 = kit.node_point(v)
        if "via" in edge:
            element_id = edge["via"]
            elements.append(element_id)
            segments.append({"floor_id": floor, "to_floor_id": to_floor, "kind": kit.connectors[element_id]["kind"],
                             "element_id": element_id, "points": [list(p1)], "length_m": edge["weight"], "geometry": "provisional"})
        else:
            if v.startswith(DOOR_PREFIX):
                elements.append(v.removeprefix(DOOR_PREFIX))
            segments.append({"floor_id": floor, "space_id": edge.get("space"), "kind": "walk", "points": [list(p1), list(p2)],
                             "length_m": edge["weight"], "geometry": "provisional"})
    directions = kit.directions(graph, nodes)
    maneuvers = [{"i": i, "kind": "depart" if i == 0 else "arrive" if i == len(directions)-1 else "straight",
                  "floor_id": first["floor_id"] if i < len(directions)-1 else last["floor_id"],
                  "at": first["point"] if i < len(directions)-1 else last["point"], "distance_m": 0,
                  "text": text[:90], "landmark": None, "element_id": None} for i, text in enumerate(directions)]
    return {**metadata, "reachable": True, "length_m": round(distance, 2), "length_m_exact": distance,
            "space_path": kit.spaces_passed(graph, nodes), "node_path": nodes, "element_path": elements,
            "segments": segments, "maneuvers": maneuvers}


def resolve_edit(building, edit):
    fn = core_function("edits", "resolve_edit")
    if building.core is not None and fn:
        return _call(fn, building.core, edit)
    edit = dict(edit)
    action = edit.get("action")
    allowed = {"close", "open", "add_door", "move_asset", "set_room_type"}
    if action not in allowed:
        raise ServiceError("invalid_args", "Unknown edit action.")
    kind = "asset" if action == "move_asset" else "space" if action in {"add_door", "set_room_type"} else "any"
    edit["target"] = require_id(building, edit["target"], kind)
    if action in {"close", "open"} and edit["target"] not in building.kit.spaces | building.kit.openings | building.kit.connectors:
        raise ServiceError("invalid_args", "Only spaces, doors and connectors may be closed.")
    if action in {"add_door", "move_asset"}:
        if not edit.get("second_target"):
            raise ServiceError("invalid_args", "A destination space is required.")
        edit["second_target"] = require_id(building, edit["second_target"], "space")
    if action == "set_room_type":
        values = {s.get("room_type") for s in building.kit.spaces.values()}
        if edit.get("value") not in values:
            raise ServiceError("invalid_args", "Choose a room type already present in this building.")
    if action == "move_asset" and edit.get("value"):
        try:
            point = [float(v) for v in edit["value"].split(",")]
            if len(point) != 2 or not all(math.isfinite(n) for n in point):
                raise ValueError
        except (ValueError, AttributeError):
            raise ServiceError("invalid_args", "Asset position must be finite x,y coordinates.") from None
        position(building, {"space_id": edit["second_target"], "point": point})
    if action == "add_door":
        try:
            width = float(edit.get("value") or 0.9)
            if not math.isfinite(width) or width <= 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ServiceError("invalid_args", "Door width must be positive and finite.") from None
    # Validate without changing the live materialisation.
    copy = BuildingMap(deepcopy(building.raw))
    copy.closed = set(building.closed)
    apply_kit_edit(copy, edit, building.version + 1)
    return edit


def preview_edit(building, edit, active_tours):
    fn = core_function("edits", "preview_edit")
    if building.core is not None and fn:
        return _call(fn, building.core, edit, active_tours)
    kit = BuildingMap(deepcopy(building.raw))
    kit.closed = set(building.closed)
    apply_kit_edit(kit, edit, building.version + 1)
    proposed = AdaptedBuilding(kit.data, kit, None, building.id, building.content_hash, building.version)
    effects = []
    for tour in active_tours:
        start = tour["start"]
        length = 0
        reachable = True
        for stop_id in tour["order"]:
            stop = next(s for s in tour["stops"] if s["stop_id"] == stop_id)
            if stop["status"] == "collected":
                continue
            result = route(proposed, start, stop["space_id"], tour["constraints"])
            if not result["reachable"]:
                reachable = False
                break
            length += result["length_m"]
            start = stop["space_id"]
        effects.append({"tour_id": tour["tour_id"], "before_m": tour["length_m"], "after_m": round(length, 2) if reachable else None, "reachable_after": reachable})
    affected = [item for item in effects if item["after_m"] != item["before_m"]]
    # Reachability change is computed from each active tour's start, or the first
    # open space when no tour exists; this is explicitly the kit adapter.
    origins = [t["start"]["space_id"] for t in active_tours] or list(building.kit.spaces)[:1]
    before, after = building.kit.graph(False), kit.graph(False)
    lost = set()
    for origin in origins:
        before_nodes = nx.node_connected_component(before, origin) if origin in before else set()
        after_nodes = nx.node_connected_component(after, origin) if origin in after else set()
        lost.update((before_nodes - after_nodes) & set(kit.spaces))
    entities = building.kit.spaces | building.kit.assets | building.kit.connectors | building.kit.openings
    target = entities.get(edit["target"], {})
    label = target.get("name") or target.get("ref") or edit["target"]
    if edit["action"] == "move_asset":
        destination = building.kit.spaces[edit["second_target"]]["name"]
        summary = f"Move {label} to {destination}"
    elif edit["action"] == "add_door":
        destination = building.kit.spaces[edit["second_target"]]["name"]
        summary = f"Add a door between {label} and {destination}"
    elif edit["action"] == "set_room_type":
        summary = f"Set {label} room type to {edit['value']}"
    else:
        summary = f"{edit['action'].capitalize()} {label}"
    return {"summary": summary, "effects": {
        "active_tours_affected": len(affected), "tours": affected, "newly_unreachable_spaces": len(lost), "_adapter": "kit"}}


def replan_tour(building, tour, start):
    """Retarget pending inventory by identity before computing any new legs."""
    start = position(building, start)
    fn = core_function("tour", "replan")
    if building.core is not None and fn:
        result = _call(fn, building.core, tour, start)
    else:
        from .state import identifier
        pending = []
        collected = []
        used_ids = {stop["stop_id"] for stop in tour["stops"]}
        for original in tour["stops"]:
            if original["status"] == "collected":
                collected.append(deepcopy(original))
                continue
            locations = {}
            for asset_id in original["asset_ids"]:
                asset = building.kit.assets.get(asset_id)
                if asset is None:
                    raise ServiceError("not_found", f"A pending part was removed: {asset_id}")
                locations.setdefault(asset["space_id"], []).append(asset_id)
            if not original["asset_ids"]:
                locations[original["space_id"]] = []
            for index, (space_id, asset_ids) in enumerate(locations.items()):
                stop = {**original, "space_id": space_id, "target": space_id, "asset_ids": asset_ids}
                if index:
                    stop["stop_id"] = identifier("stop")
                    while stop["stop_id"] in used_ids:
                        stop["stop_id"] = identifier("stop")
                    used_ids.add(stop["stop_id"])
                space_name = building.kit.spaces[space_id]["name"]
                stop["label"] = (", ".join(building.kit.assets[aid]["name"] for aid in asset_ids) + " · " + space_name) if asset_ids else space_name
                pending.append(stop)
        if tour["order_policy"] == "fixed":
            by_id = {stop["stop_id"]: stop for stop in pending}
            pending = [by_id[sid] for sid in tour["order"] if sid in by_id] + [stop for stop in pending if stop["stop_id"] not in tour["order"]]
        result = plan_tour(building, start, pending, tour["constraints"], tour["order_policy"] == "fixed", tour.get("end"))
        result["stops"] = collected + result["stops"]
    # Target is additive server metadata. Keep it consistent with the canonical
    # retargeted stop, rather than restoring the previous revision's room.
    for stop in result["stops"]:
        stop["target"] = stop["space_id"]
    return result


def plan_tour(building, start, stops, constraints, keep_order=False, end=None):
    start = position(building, start)
    end = position(building, end) if end else None
    fn = core_function("tour", "plan_tour")
    if building.core is not None and fn:
        result = _call(fn, building.core, start, stops, constraints=constraints, keep_order=keep_order, end=end)
        return result
    start_position = position(building, start)
    end_position = position(building, end) if end else None
    n = len(stops)
    routes = {}
    def leg(first, second):
        key = (first, second)
        if key not in routes:
            a = start_position if first == -1 else stops[first]["space_id"]
            b = end_position if second == n else stops[second]["space_id"]
            routes[key] = route(building, a, b, constraints)
        return routes[key]
    def cost(first, second):
        r = leg(first, second)
        return r["length_m_exact"] if r["reachable"] else math.inf
    pending, unreachable = [], []
    for i in range(n):
        if leg(-1, i)["reachable"]:
            pending.append(i)
        else:
            unreachable.append({"stop_id": stops[i]["stop_id"], "reason": leg(-1, i)["reason"]})
    if keep_order:
        order = pending
        policy = "fixed"
    elif len(pending) <= 12:
        # Held-Karp over reachable pending stops. Fixed start and optional end.
        size = len(pending)
        dp = {(1 << j, j): (cost(-1, i), None) for j, i in enumerate(pending)}
        for mask in range(1, 1 << size):
            for last in range(size):
                if (mask, last) not in dp:
                    continue
                value = dp[mask, last][0]
                for nxt in range(size):
                    if mask & (1 << nxt):
                        continue
                    key = mask | (1 << nxt), nxt
                    candidate = value + cost(pending[last], pending[nxt])
                    if candidate < dp.get(key, (math.inf, None))[0]:
                        dp[key] = candidate, last
        order = []
        if size:
            mask = (1 << size) - 1
            last = min(range(size), key=lambda j: dp[mask, j][0] + (cost(pending[j], n) if end else 0))
            while mask:
                order.append(pending[last])
                previous = dp[mask, last][1]
                mask ^= 1 << last
                last = previous
            order.reverse()
        policy = "optimized_exact"
    else:
        # The fallback is honest about this heuristic. H02 replaces it.
        order, todo, previous = [], set(pending), -1
        while todo:
            nxt = min(todo, key=lambda i: (cost(previous, i), i))
            order.append(nxt)
            todo.remove(nxt)
            previous = nxt
        def total(candidate):
            path = [-1, *candidate, *([n] if end else [])]
            return sum(cost(a, b) for a, b in itertools.pairwise(path))
        improved = True
        while improved:
            improved = False
            current_cost = total(order)
            for a in range(len(order) - 1):
                for b in range(a + 2, len(order) + 1):
                    candidate = order[:a] + list(reversed(order[a:b])) + order[b:]
                    if total(candidate) < current_cost - 1e-9:
                        order = candidate
                        improved = True
                        break
                if improved:
                    break
        policy = "optimized_heuristic"
    legs, previous = [], -1
    for i in order:
        legs.append(leg(previous, i))
        previous = i
    if end:
        legs.append(leg(previous, n))
    return {
        "status": "blocked" if unreachable else "active" if stops else "completed", "building_id": building.id,
        "building_version": building.version, "content_hash": building.content_hash,
        "order_policy": policy, "start": start_position, "end": end_position,
        "stops": stops, "order": [stops[i]["stop_id"] for i in order], "legs": legs,
        "length_m": round(sum(r.get("length_m_exact", 0) for r in legs), 2), "unreachable_stops": unreachable,
        "changed_because": None, "profile": "kit_1_1_0", "constraints": constraints,
        "_adapter": "kit", "geometry": "provisional",
    }
