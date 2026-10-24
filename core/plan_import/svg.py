"""Conservative extraction of explicit vector room outlines and door marks.

This spike supports the kit's Matplotlib SVG convention. It never renders SVG,
loads linked resources, decodes fonts, or infers connectivity from wall contact.
"""

import math
import xml.etree.ElementTree as ET

from shapely.geometry import Point, Polygon
from svgelements import Close, Line, Matrix, Move, Path

from core.errors import CoreError


MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_ELEMENTS = 60000
MAX_PATH_BYTES = 2 * 1024 * 1024
DOOR_COLOURS = {"#8b4513": "door", "#9e9e9e": "opening", "#d32f2f": "entrance"}


def _style(element, inherited):
    result = dict(inherited)
    result.update({key: value for key, value in element.attrib.items() if key in {"fill", "stroke", "opacity"}})
    for rule in element.get("style", "").split(";"):
        if ":" in rule:
            key, value = rule.split(":", 1)
            result[key.strip()] = value.strip().lower()
    return result


def _path_points(element, matrix):
    data = element.get("d", "")
    if len(data) > MAX_PATH_BYTES:
        raise CoreError("invalid_args", "SVG path is too large.")
    path = Path(data)
    path *= matrix
    path.reify()
    points = []
    moves = 0
    closed = False
    for segment in path:
        if not isinstance(segment, (Move, Line, Close)):
            return [], False  # Curves and compound room outlines need correction.
        if isinstance(segment, Move):
            moves += 1
            if moves > 1:
                return [], False
        if isinstance(segment, Close):
            closed = True
        point = segment.end
        if point is not None:
            points.append([float(point.x), float(point.y)])
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()
    return points, closed


def extract_svg(file_bytes):
    if not isinstance(file_bytes, bytes) or not file_bytes or len(file_bytes) > MAX_FILE_BYTES:
        raise CoreError("invalid_args", "SVG must be non-empty bytes, at most 10 MiB.")
    if b"<!ENTITY" in file_bytes.upper():
        raise CoreError("invalid_args", "SVG entity declarations are not supported.")
    try:
        root = ET.fromstring(file_bytes)
    except (ET.ParseError, ValueError) as error:
        raise CoreError("invalid_args", "The file is not valid SVG XML.") from error
    if root.tag.split("}")[-1] != "svg":
        raise CoreError("invalid_args", "Expected an SVG document.")
    if sum(1 for _ in root.iter()) > MAX_ELEMENTS:
        raise CoreError("invalid_args", "SVG has too many elements.")
    rooms, markers, skipped = [], [], 0

    def walk(element, parent_matrix, inherited, depth=0):
        nonlocal skipped
        if depth > 128:
            raise CoreError("invalid_args", "SVG nesting exceeds the supported depth.")
        tag = element.tag.split("}")[-1]
        if tag in {"defs", "metadata", "clipPath", "script", "style", "image", "foreignObject", "symbol"}:
            return
        matrix = Matrix(element.get("transform", "")) * parent_matrix
        style = _style(element, inherited)
        fill, stroke = style.get("fill", "none"), style.get("stroke", "none")
        explicit_room = element.get("data-room") in {"true", "1"}
        if tag in {"path", "polygon"}:
            if tag == "path":
                points, closed = _path_points(element, matrix)
            else:
                import re
                values = [float(v) for v in re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", element.get("points", ""))]
                points = [[p.x, p.y] for p in (matrix.point_in_matrix_space(values[i:i+2]) for i in range(0, len(values) - 1, 2))]
                closed = True
            if closed and len(points) >= 3 and fill not in {"none", "#ffffff", "white"} and (stroke == "#333333" or explicit_room):
                polygon = Polygon(points)
                if polygon.is_valid and polygon.area > 1e-9 and all(math.isfinite(v) for point in points for v in point):
                    rooms.append({"polygon": points, "fill": fill, "source_element": element.get("id")})
                else:
                    skipped += 1
            elif not closed and len(points) == 1 and stroke in DOOR_COLOURS:
                if not all(math.isfinite(v) for v in points[0]):
                    raise CoreError("invalid_args", "SVG marker coordinates must be finite.")
                markers.append({"position": points[0], "kind": DOOR_COLOURS[stroke], "source": "explicit_svg_marker"})
        for child in element:
            walk(child, matrix, style, depth + 1)

    try:
        walk(root, Matrix(), {})
    except (ValueError, TypeError, OverflowError, ZeroDivisionError) as error:
        raise CoreError("invalid_args", "Unsupported or malformed SVG geometry.") from error
    if not rooms:
        raise CoreError("invalid_args", "No supported room outlines found; upload kit JSON or correct the SVG draft manually.")
    return {"rooms": rooms, "markers": markers, "viewbox": root.get("viewBox"), "skipped_polygons": skipped}


def associate_markers(rooms, markers, tolerance):
    """Use explicit marks only; ambiguous junctions remain for human correction."""
    shapes = [Polygon(room["polygon"]) for room in rooms]
    connected, unresolved = [], []
    for marker in markers:
        point = Point(marker["position"])
        adjacent = [i for i, shape in enumerate(shapes) if shape.boundary.distance(point) <= tolerance]
        expected = 1 if marker["kind"] == "entrance" else 2
        if len(adjacent) == expected:
            connected.append({**marker, "room_indices": adjacent})
        else:
            unresolved.append({**marker, "candidate_room_indices": adjacent})
    return connected, unresolved
