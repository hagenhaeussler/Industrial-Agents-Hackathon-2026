"""Validate untrusted building JSON before any routing object is constructed."""

import math

import networkx as nx
from shapely.geometry import Point, Polygon
from shapely.validation import explain_validity


def _number(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _point(value):
    return isinstance(value, (list, tuple)) and len(value) == 2 and all(_number(v) for v in value)


def validate_building(raw):
    """Return structured errors, geometry warnings and connectivity statistics.

    Unknown names, languages, IDs and additional fields are accepted as data.
    Disconnected rooms and imperfect source geometry are reported as warnings.
    Connectivity statistics need only the topology, so validation does not pay
    for construction of every door-to-door visibility graph.
    """
    errors, warnings = [], []
    stats = {"floors": 0, "spaces": 0, "openings": 0, "assets": 0,
             "vertical_connectors": 0, "entrances": 0, "unreachable_rooms": 0}

    def report(items, code, path, message):
        items.append({"code": code, "path": path, "message": message})

    def error(code, path, message):
        report(errors, code, path, message)

    def warning(code, path, message):
        report(warnings, code, path, message)

    def text(item, key, path):
        value = item.get(key)
        if not isinstance(value, str) or not value.strip():
            error("required_string", f"{path}.{key}", "Expected a non-empty string.")
            return False
        return True

    def numeric(item, key, path, positive=False):
        value = item.get(key)
        if not _number(value) or (positive and value <= 0):
            error("invalid_number", f"{path}.{key}", "Expected a positive finite number." if positive else "Expected a finite number.")
            return False
        return True

    def position(item, key, path):
        if not _point(item.get(key)):
            error("invalid_point", f"{path}.{key}", "Expected two finite coordinates in metres.")
            return False
        return True

    if not isinstance(raw, dict):
        error("invalid_object", "$", "The building JSON must be an object.")
        return {"ok": False, "errors": errors, "warnings": warnings, "stats": stats}
    metadata = raw.get("building")
    if not isinstance(metadata, dict):
        error("invalid_object", "building", "Building metadata must be an object.")
    else:
        for key in ("id", "name", "source"):
            text(metadata, key, "building")
        if metadata.get("units") != "m":
            error("invalid_units", "building.units", "Coordinates and lengths must use metres (units: m).")

    arrays = {}
    identifiers = {}
    all_ids = set()
    for key in ("floors", "spaces", "openings", "vertical_connectors", "assets"):
        value = raw.get(key)
        if not isinstance(value, list):
            error("invalid_array", key, "Expected an array.")
            arrays[key] = []
            identifiers[key] = {}
            continue
        stats[key] = len(value)
        arrays[key], identifiers[key] = [], {}
        for index, item in enumerate(value):
            path = f"{key}[{index}]"
            if not isinstance(item, dict):
                error("invalid_object", path, "Expected an object.")
                continue
            arrays[key].append((path, item))
            if text(item, "id", path):
                item_id = item["id"]
                if item_id == "outside":
                    error("reserved_id", path + ".id", "The ID outside is reserved for entrances.")
                if item_id in all_ids:
                    error("duplicate_id", path + ".id", f"Duplicate ID: {item_id}.")
                all_ids.add(item_id)
                identifiers[key][item_id] = item
    floors, spaces = identifiers["floors"], identifiers["spaces"]
    if not arrays["floors"]:
        error("empty_floors", "floors", "At least one floor is required.")
    if not arrays["spaces"]:
        error("empty_spaces", "spaces", "At least one space is required.")

    for path, floor in arrays["floors"]:
        text(floor, "name", path)
        if not isinstance(floor.get("level"), int) or isinstance(floor.get("level"), bool):
            error("invalid_level", path + ".level", "Floor level must be an integer.")
        numeric(floor, "elevation_m", path)
        numeric(floor, "height_m", path, positive=True)

    def floor_ref(item, path):
        value = item.get("floor_id")
        if not isinstance(value, str) or value not in floors:
            error("unknown_floor", path + ".floor_id", "The referenced floor does not exist.")

    polygons = {}
    for path, space in arrays["spaces"]:
        floor_ref(space, path)
        for key in ("type", "room_type", "name"):
            text(space, key, path)
        polygon = space.get("polygon")
        if not isinstance(polygon, list) or len(polygon) < 3 or not all(_point(p) for p in polygon):
            error("invalid_polygon", path + ".polygon", "A polygon needs at least three finite XY points.")
            continue
        shape = Polygon(polygon)
        if not shape.is_valid:
            repaired = shape.buffer(0)
            if repaired.is_empty or repaired.area <= 0:
                error("invalid_polygon", path + ".polygon", explain_validity(shape))
                continue
            warning("polygon_repaired", path + ".polygon", explain_validity(shape))
            shape = repaired
        if shape.is_empty or shape.area <= 0:
            error("degenerate_polygon", path + ".polygon", "A space must have a positive polygon area.")
        elif isinstance(space.get("id"), str):
            polygons[space["id"]] = shape

    topology = nx.Graph()
    topology.add_nodes_from(spaces)
    entrances = set()
    for path, opening in arrays["openings"]:
        floor_ref(opening, path)
        refs = opening.get("space_ids")
        valid_refs = isinstance(refs, list) and len(refs) == 2 and all(isinstance(s, str) for s in refs)
        if not valid_refs:
            error("invalid_opening_spaces", path + ".space_ids", "An opening must join exactly two space IDs.")
            refs = []
        elif len(set(refs)) != 2:
            error("invalid_opening_spaces", path + ".space_ids", "An opening must join distinct spaces.")
        for sid in refs:
            if sid != "outside" and sid not in spaces:
                error("unknown_space", path + ".space_ids", f"Unknown space ID: {sid}.")
            elif sid in spaces and spaces[sid].get("floor_id") != opening.get("floor_id"):
                error("opening_floor_mismatch", path + ".floor_id", "An opening must be on the same floor as its spaces.")
        if refs and all(s in spaces or s == "outside" for s in refs):
            topology.add_edge(*refs)
            if "outside" in refs:
                stats["entrances"] += 1
                entrances.update(s for s in refs if s != "outside")
        if opening.get("kind") not in ("door", "opening", "entrance"):
            error("invalid_opening_kind", path + ".kind", "Opening kind must be door, opening or entrance.")
        numeric(opening, "width_m", path, positive=True)
        if not isinstance(opening.get("step_free"), bool):
            error("invalid_boolean", path + ".step_free", "step_free must be a boolean.")
        if position(opening, "position", path):
            point = Point(opening["position"])
            for sid in refs:
                if sid in polygons and point.distance(polygons[sid].boundary) > 0.6 + 1e-9:
                    warning("door_off_boundary", path + ".position", f"Door is more than 0.6 m from the boundary of {sid}.")

    for path, connector in arrays["vertical_connectors"]:
        text(connector, "name", path)
        if connector.get("kind") not in ("stairs", "lift"):
            error("invalid_connector_kind", path + ".kind", "Connector kind must be stairs or lift.")
        if not isinstance(connector.get("step_free"), bool):
            error("invalid_boolean", path + ".step_free", "step_free must be a boolean.")
        floor_ids, space_ids = connector.get("floor_ids"), connector.get("space_ids")
        if not (isinstance(floor_ids, list) and isinstance(space_ids, list)
                and len(floor_ids) == len(space_ids) and len(floor_ids) >= 2
                and all(isinstance(s, str) for s in floor_ids + space_ids)):
            error("invalid_connector_stops", path, "A connector needs matching floor_ids and space_ids with at least two stops.")
            continue
        if len(set(floor_ids)) != len(floor_ids):
            error("duplicate_connector_floor", path + ".floor_ids", "A connector may have only one stop on a floor.")
        for fid, sid in zip(floor_ids, space_ids):
            if fid not in floors:
                error("unknown_floor", path + ".floor_ids", f"Unknown floor ID: {fid}.")
            if sid not in spaces:
                error("unknown_space", path + ".space_ids", f"Unknown space ID: {sid}.")
            elif spaces[sid].get("floor_id") != fid:
                error("connector_floor_mismatch", path + ".space_ids", f"Connector space {sid} is not on {fid}.")
        if all(s in spaces for s in space_ids):
            topology.add_edges_from(zip(space_ids, space_ids[1:]))

    for path, asset in arrays["assets"]:
        floor_ref(asset, path)
        for key in ("name", "type", "category", "source"):
            text(asset, key, path)
        sid = asset.get("space_id")
        if not isinstance(sid, str) or sid not in spaces:
            error("unknown_space", path + ".space_id", "The asset's space does not exist.")
        elif spaces[sid].get("floor_id") != asset.get("floor_id"):
            error("asset_floor_mismatch", path + ".floor_id", "The asset's floor must match its space.")
        if position(asset, "position", path) and isinstance(sid, str) and sid in polygons:
            if not polygons[sid].covers(Point(asset["position"])):
                warning("asset_outside_space", path + ".position", "The asset position is outside its space polygon.")
        footprint = asset.get("footprint")
        if not isinstance(footprint, dict):
            error("invalid_object", path + ".footprint", "An asset footprint must be an object.")
        else:
            numeric(footprint, "width_m", path + ".footprint", positive=True)
            numeric(footprint, "depth_m", path + ".footprint", positive=True)
            numeric(footprint, "rotation_deg", path + ".footprint")

    if not entrances:
        error("no_entrance", "openings", "At least one opening to outside is required for routing.")
        warning("display_only", "openings", "Geometry can be displayed, but entrance-based routing is unavailable.")
    reachable = nx.node_connected_component(topology, "outside") if "outside" in topology else set()
    unreachable = sorted(sid for sid, space in spaces.items()
                         if sid not in reachable and space.get("type") in {"room", "hall"})
    stats["unreachable_rooms"] = len(unreachable)
    if unreachable:
        warning("unreachable_rooms", "spaces", f"{len(unreachable)} rooms are disconnected from every entrance.")
        warnings[-1]["space_ids"] = unreachable
    return {"ok": not errors, "errors": errors, "warnings": warnings, "stats": stats}
