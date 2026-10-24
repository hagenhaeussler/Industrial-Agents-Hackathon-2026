"""Pure, deterministic building edit resolution, previews and event replay.

Storage, proposal expiry, admin permissions and idempotent *commits* belong to
the server.  This module never writes to disk or changes a caller's building.
"""

import copy
import math

import networkx as nx
from shapely.geometry import Point

from .building import Building, content_hash, load_building
from .errors import CoreError, EditError


ROOM_TYPES = frozenset({
    "bedroom", "living_room", "kitchen", "bathroom", "toilet", "storage",
    "corridor", "balcony", "stairwell", "lift", "office", "meeting_room",
    "seminar_room", "lecture_hall", "lab", "makerspace", "library",
    "server_room", "technical_room", "lobby", "canteen", "shop", "print_room",
    "locker_room", "production_zone", "additive_zone", "assembly_zone",
    "warehouse_zone", "logistics_zone", "quality_lab", "generic_room",
})
EDIT_ACTIONS = frozenset({"close", "open", "add_door", "move_asset", "set_room_type"})


def _error(message, code="invalid_args", candidates=None):
    raise EditError(code, message, candidates)


def _resolve_id(building, reference, kinds):
    """Use the shared resolver, retaining the candidates needed by the UI."""
    if not isinstance(reference, str) or not reference.strip():
        _error("An edit target must be a non-empty ID or name.")
    collections = {
        "space": building.spaces, "asset": building.assets,
        "opening": building.openings, "connector": building.connectors,
    }
    if any(reference in collections[kind] for kind in kinds):
        return reference
    from .resolve import resolve
    candidates, suggestions = [], []
    for kind in kinds:
        result = resolve(building, reference, kind)
        if result.get("status") in {"unique", "ambiguous"}:
            candidates.extend(result.get("candidates", []))
        else:
            suggestions.extend(result.get("candidates", []))
    # An exact candidate in one namespace must beat a fuzzy candidate in another.
    candidates = list({(c["kind"], c["id"]): c for c in candidates}.values())
    priority = {"exact ID": 3, "exact name/ref": 2, "normalized": 1, "fuzzy": 0}
    rank = lambda c: (priority.get(c.get("why"), 0), c.get("score", 0))
    best = max((rank(c) for c in candidates), default=(-1, -1))
    winners = [c for c in candidates if rank(c) == best]
    if len(winners) == 1:
        return winners[0]["id"]
    if winners:
        _error(f"Several edit targets match {reference!r}.", "ambiguous", winners)
    _error(f"No edit target matches {reference!r}.", "not_found", suggestions)


def _point(value):
    if isinstance(value, str):
        value = value.split(",")
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        _error("A position must contain two finite coordinates in metres.")
    if any(isinstance(v, bool) for v in value):
        _error("A position must contain two finite coordinates in metres.")
    try:
        point = tuple(float(v) for v in value)
    except (TypeError, ValueError, OverflowError):
        _error("A position must contain two finite coordinates in metres.")
    if not all(math.isfinite(v) for v in point):
        _error("A position must contain two finite coordinates in metres.")
    return point


def resolve_edit(building, edit):
    """Validate an intention and return its canonical IDs and numeric values."""
    if not isinstance(edit, dict):
        _error("An edit must be an object.")
    action = edit.get("action", edit.get("kind"))
    if not isinstance(action, str) or action not in EDIT_ACTIONS:
        _error("Unknown edit action. Use close, open, add_door, move_asset or set_room_type.")
    target_kinds = ("asset",) if action == "move_asset" else (
        ("connector", "opening", "space") if action in {"close", "open"} else ("space",)
    )
    result = {"action": action, "target": _resolve_id(building, edit.get("target"), target_kinds)}
    if action == "open" and result["target"] not in building.closed:
        _error("This element is already open.")
    if action == "add_door":
        second = _resolve_id(building, edit.get("second_target"), ("space",))
        from .spatial import shared_wall_midpoint
        try:
            position = shared_wall_midpoint(building, result["target"], second)
        except CoreError as error:
            raise EditError(error.code, error.message, error.candidates) from error
        width = edit.get("width_m", edit.get("value", 0.9))
        if width is None or width == "":
            width = 0.9
        if isinstance(width, bool):
            _error("Door width must be a positive finite number in metres.")
        try:
            width = float(width)
        except (ValueError, TypeError, OverflowError):
            _error("Door width must be a positive finite number in metres.")
        if not math.isfinite(width) or width <= 0:
            _error("Door width must be a positive finite number in metres.")
        result.update(second_target=second, position=list(position), width_m=width, value=width)
    elif action == "move_asset":
        second = _resolve_id(building, edit.get("second_target"), ("space",))
        supplied = edit.get("position", edit.get("value"))
        point = building.anchor(second) if supplied is None or supplied == "" else _point(supplied)
        if not building.polygons[second].covers(Point(point)):
            _error("The supplied asset position must be inside its target space.")
        result.update(second_target=second, position=list(point))
    elif action == "set_room_type":
        value = edit.get("value", edit.get("room_type"))
        if not isinstance(value, str) or value not in ROOM_TYPES:
            _error("Choose a room_type from the kit room-type list.")
        result["value"] = value
    return result


def _materialize(building, edit, version):
    """Apply one canonical edit to an owned copy; keep closures outside raw data."""
    action, target = edit["action"], edit["target"]
    if action == "close":
        building.closed.add(target)
    elif action == "open":
        building.closed.discard(target)
    elif action == "add_door":
        opening = building.add_door(target, edit["second_target"], position=edit["position"])
        old_id = opening["id"]
        opening["id"] = f"{opening['floor_id']}-O-evt{version}"
        if opening["id"] in building.openings:
            _error("The generated door ID is already present in the building.")
        opening["width_m"] = edit["width_m"]
        del building.openings[old_id]
        building.openings[opening["id"]] = opening
    elif action == "move_asset":
        asset = building.assets[target]
        asset.update(space_id=edit["second_target"],
                     floor_id=building.spaces[edit["second_target"]]["floor_id"],
                     position=list(edit["position"]))
    elif action == "set_room_type":
        building.spaces[target]["room_type"] = edit["value"]
    building.version = version
    building.content_hash = content_hash(building.data)
    building._walk_cache_key = (building.content_hash, version, building.profile)
    return building


def _edited_copy(building, edit):
    materialized = load_building(building)
    return _materialize(materialized, resolve_edit(materialized, edit), building.version + 1)


def apply_events(base, events):
    """Replay a complete event log, cancelling the selected edits on undo.

    Duplicate event IDs are accepted only when the record is identical. They
    never apply twice. The returned version is the supplied log's length, as
    required by the materialisation contract; servers store unique event IDs.
    """
    if not isinstance(events, list):
        _error("Events must be a list.")
    records, undone = {}, set()
    for index, event in enumerate(events, 1):
        if not isinstance(event, dict):
            _error("Every event must be an object.")
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            _error("Every event must have a non-empty event_id.")
        if event_id in records:
            if records[event_id][1] != event:
                _error(f"Conflicting records for event {event_id}.")
            continue
        payload = event.get("edit") or {}
        if not isinstance(payload, dict):
            _error("A building edit event needs an edit object.")
        kind = event.get("kind", payload.get("action"))
        if kind == "undo":
            edit = event.get("edit") or {}
            target = event.get("undoes") or edit.get("event_id") or edit.get("target")
            if not isinstance(target, str) or target not in records:
                _error("Cannot undo an unknown event.")
            original = records[target][1]
            if original.get("kind") == "undo":
                _error("An undo event cannot itself be undone.")
            if target in undone:
                _error("This event has already been undone.")
            undone.add(target)
        elif not isinstance(kind, str) or kind not in EDIT_ACTIONS:
            _error(f"Unknown event kind: {kind!r}.")
        records[event_id] = (index, copy.deepcopy(event))
    result = load_building(base)
    removed_openings = set()
    for event_id in undone:
        index, original = records[event_id]
        original_edit = original.get("edit", {})
        if (original.get("kind") == "add_door" and isinstance(original_edit.get("target"), str)
                and original_edit["target"] in result.spaces):
            floor_id = result.spaces[original_edit["target"]]["floor_id"]
            removed_openings.add(f"{floor_id}-O-evt{index}")
    for event_id, (index, event) in records.items():
        if event_id in undone or event.get("kind") == "undo":
            continue
        edit = event.get("edit")
        if not isinstance(edit, dict):
            _error("A building edit event needs an edit object.")
        edit = dict(edit, action=event.get("kind", edit.get("action")))
        # Closing a door, then undoing its creation, must still materialise a
        # valid building. That closure has no remaining element to affect.
        if (edit["action"] in {"close", "open"} and isinstance(edit.get("target"), str)
                and edit["target"] in removed_openings):
            continue
        # Reopening an element whose closing event was undone is harmless at
        # replay time, even though proposing an already-open element is invalid.
        if edit["action"] == "open":
            target = _resolve_id(result, edit.get("target"), ("connector", "opening", "space"))
            resolved = {"action": "open", "target": target}
        else:
            resolved = resolve_edit(result, edit)
        _materialize(result, resolved, index)
    result.version = len(events)
    result.content_hash = content_hash(result.data)
    result._walk_cache_key = (result.content_hash, result.version, result.profile)
    return result


def _entrance_distances(building):
    graph = building.graph(step_free=False)
    sources = ["door:" + opening["id"] for opening in building.openings.values()
               if "outside" in opening["space_ids"] and opening["id"] not in building.closed
               and "door:" + opening["id"] in graph]
    return nx.multi_source_dijkstra_path_length(graph, sources, weight="weight") if sources else {}


def _summary(building, edit):
    target = edit["target"]
    element = (building.spaces.get(target) or building.assets.get(target)
               or building.connectors.get(target) or building.openings.get(target))
    label = element.get("name", target)
    if edit["action"] in {"close", "open"}:
        return f"{edit['action'].capitalize()} {label}."
    if edit["action"] == "add_door":
        return f"Add a door between {label} and {building.spaces[edit['second_target']]['name']}."
    if edit["action"] == "move_asset":
        return f"Move {label} to {building.spaces[edit['second_target']]['name']}."
    return f"Set {label} to {edit['value'].replace('_', ' ')}."


def preview_edit(building, edit, active_tours=None):
    """Compute a proposal's effects on isolated state, without persisting it."""
    resolved = resolve_edit(building, edit)
    after = _edited_copy(building, resolved)
    before_reachable = set(_entrance_distances(building)) & building.spaces.keys()
    after_reachable = set(_entrance_distances(after)) & after.spaces.keys()
    tours, affected = [], 0
    for tour in active_tours or []:
        from .tour import replan
        replanned = replan(after, copy.deepcopy(tour), tour.get("start"))
        reachable = not replanned.get("unreachable_stops") and replanned.get("status") != "unreachable"
        after_length = replanned.get("length_m") if reachable else None
        tours.append({"tour_id": tour.get("tour_id"), "before_m": tour.get("length_m"),
                      "after_m": after_length, "reachable_after": reachable})
        def route_signature(value):
            return (value.get("order"),
                    [(leg.get("space_path"), leg.get("element_path")) for leg in value.get("legs", [])],
                    [(stop.get("stop_id"), stop.get("space_id"), stop.get("asset_ids"))
                     for stop in value.get("stops", [])])
        if (after_length != tour.get("length_m") or not reachable
                or route_signature(tour) != route_signature(replanned)):
            affected += 1
    return {"edit": resolved, "summary": _summary(building, resolved), "base_version": building.version,
            "effects": {"active_tours_affected": affected, "tours": tours,
                        "newly_unreachable_spaces": len(before_reachable - after_reachable)}}
