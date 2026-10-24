"""User-supplied SVG distance calibration; no building lookup or guessed units."""

import math

from core.errors import CoreError


def calibration(scale):
    if not isinstance(scale, dict):
        raise CoreError("invalid_args", "Scale requires p1, p2 and length_m.")
    points = []
    for field in ("p1", "p2"):
        point = scale.get(field)
        if not isinstance(point, (list, tuple)) or len(point) != 2 or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in point):
            raise CoreError("invalid_args", f"Scale {field} must contain two finite SVG coordinates.")
        points.append(tuple(point))
    length = scale.get("length_m")
    if isinstance(length, bool) or not isinstance(length, (int, float)) or not math.isfinite(length) or length <= 0:
        raise CoreError("invalid_args", "Scale length_m must be positive and finite.")
    distance = math.dist(*points)
    if distance <= 1e-9:
        raise CoreError("invalid_args", "Scale points must be distinct.")
    return {"origin": list(points[0]), "metres_per_svg_unit": length / distance,
            "p1": list(points[0]), "p2": list(points[1]), "length_m": length}


def to_metres(point, calibrated):
    x, y = point
    ox, oy = calibrated["origin"]
    factor = calibrated["metres_per_svg_unit"]
    # SVG y points down, building y points up. p1 defines a local origin; a
    # scale segment supplies distance, not geographic heading or georeference.
    return [(x - ox) * factor, (oy - y) * factor]
