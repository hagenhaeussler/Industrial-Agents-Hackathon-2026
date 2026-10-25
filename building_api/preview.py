"""Isometric exterior view of a building as SVG, for previews.

Each floor's outline is the union of its spaces, extruded from the floor's elevation by its height. Floors are
stacked without gaps, so the drawing reads as one solid building. It is a picture only: no tool or route uses it.
"""

import itertools
import math
from dataclasses import dataclass

from shapely import Point, Polygon, affinity, unary_union
from shapely.geometry.polygon import orient

from building_db.source import BuildingDocument, Floor

# Rooms in building.json are separated by wall gaps. Growing and shrinking by this closes them.
WALL_GAP_M = 0.3
MIN_COURTYARD_M2 = 30
COS = math.cos(math.pi / 6)
SIN = math.sin(math.pi / 6)
# The viewer looks along +x+y from above, so walls whose outward normal points along -x-y face the viewer.
# Light comes from the viewer's left.
LIGHT = (-0.86, -0.51)

WALL_LIT = (247, 245, 239)
WALL_SHADE = (184, 190, 172)
GLASS_LIT = (92, 109, 86)
GLASS_SHADE = (38, 47, 35)
ROOF = "#e2e6d6"
ENTRANCE = "#dcff58"
INK = "#191c16"

Point2 = tuple[float, float]


@dataclass(frozen=True)
class Slab:
    """One floor's outline, lifted to its place in the stack."""

    shape: Polygon
    bottom: float
    height: float


def isometric_svg(document: BuildingDocument) -> str:
    """The building's exterior as a standalone SVG with a transparent background."""
    floors = _shown_floors(document.floors)
    base = min((floor.elevation_m for floor in floors), default=0.0)
    slabs = [
        Slab(shape, floor.elevation_m - base, floor.height_m)
        for floor in floors
        for shape in _outline(document, floor.id)
    ]
    if not slabs:
        return _svg("0 0 1 1", [])
    entrances = [
        (opening.position, opening.width_m, slab)
        for opening in document.openings
        if opening.kind == "entrance"
        for slab in slabs
        if slab.bottom == 0 and slab.shape.distance(Point(opening.position)) < 1.5
    ]

    parts = [_shadow(slabs)]

    # Lower floors first, and within a floor the farthest outline first: nearer things are painted over farther ones.
    for slab in sorted(slabs, key=lambda s: (s.bottom, -_depth(s.shape.centroid.coords[0]))):
        parts.extend(_walls(slab, [(p, w) for p, w, s in entrances if s is slab]))
        parts.append(_roof(slab))

    points = [
        _project(point, slab.bottom + z)
        for slab in slabs
        for point in slab.shape.exterior.coords
        for z in (0, slab.height)
    ]
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    pad = max(max(xs) - min(xs), max(ys) - min(ys)) * 0.04
    view_box = (
        f"{min(xs) - pad:.2f} {min(ys) - pad:.2f} {max(xs) - min(xs) + 2 * pad:.2f} {max(ys) - min(ys) + 2 * pad:.2f}"
    )
    return _svg(view_box, parts)


def _shadow(slabs: list[Slab]) -> str:
    """A soft shadow on the ground, cast to the right, away from the light: the footprint swept along the offset."""
    reach = max(slab.bottom + slab.height for slab in slabs) * 0.4
    ground = unary_union([slab.shape for slab in slabs])
    sweep: list[Polygon] = [ground, affinity.translate(ground, reach, -reach)]
    for polygon in getattr(ground, "geoms", [ground]):
        for a, b in itertools.pairwise(polygon.exterior.coords):
            sweep.append(Polygon([a, b, (b[0] + reach, b[1] - reach), (a[0] + reach, a[1] - reach)]).buffer(0))
    cast = unary_union(sweep)
    d = "".join(
        _ring([_project(point, 0) for point in polygon.exterior.coords]) for polygon in getattr(cast, "geoms", [cast])
    )
    return f'<path d="{d}" fill="{INK}" fill-opacity="0.08" stroke="none"/>'


def _shown_floors(floors: list[Floor]) -> list[Floor]:
    """Floors above ground. Basements are hidden from the outside unless the building has nothing else."""
    above = [floor for floor in floors if floor.level >= 0]
    return sorted(above or floors, key=lambda floor: floor.elevation_m)


def _outline(document: BuildingDocument, floor_id: str) -> list[Polygon]:
    """The floor's outline as separate polygons, exterior counter-clockwise and holes clockwise."""
    shapes = [
        Polygon(space.polygon).buffer(0)
        for space in document.spaces
        if space.floor_id == floor_id and space.type != "outdoor"
    ]
    if not shapes:
        return []
    merged = (
        unary_union([shape.buffer(WALL_GAP_M, join_style="mitre") for shape in shapes])
        .buffer(-WALL_GAP_M, join_style="mitre")
        .simplify(0.05)
    )
    polygons = [polygon for polygon in getattr(merged, "geoms", [merged]) if isinstance(polygon, Polygon)]
    return [orient(_close_shafts(polygon)) for polygon in polygons if polygon.area > 1]


def _close_shafts(polygon: Polygon) -> Polygon:
    """Keep courtyards open but close small holes such as light wells, which read as noise from outside."""
    holes = [ring for ring in polygon.interiors if Polygon(ring).area >= MIN_COURTYARD_M2]
    return Polygon(polygon.exterior, holes)


def _walls(slab: Slab, entrances: list[tuple[Point2, float]]) -> list[str]:
    """The walls that face the viewer, farthest first, each with a window band and any entrance on it."""
    edges: list[tuple[Point2, Point2]] = []
    for ring in [slab.shape.exterior, *slab.shape.interiors]:
        coords = list(ring.coords)
        edges.extend(itertools.pairwise(coords))

    parts: list[str] = []
    top = slab.bottom + slab.height
    for a, b in sorted(edges, key=lambda edge: -_depth(_mid(*edge))):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if length < 0.05:
            continue
        normal = (dy / length, -dx / length)
        if normal[0] + normal[1] >= 0:
            continue
        light = max(0.0, normal[0] * LIGHT[0] + normal[1] * LIGHT[1])
        corners = [_project(a, slab.bottom), _project(b, slab.bottom), _project(b, top), _project(a, top)]
        parts.append(_path(corners, f'fill="{_mix(WALL_SHADE, WALL_LIT, light)}"'))
        if length > 1.2:
            inset = 0.4 / length
            low, high = slab.bottom + slab.height * 0.32, slab.bottom + slab.height * 0.74
            p, q = _along(a, b, inset), _along(a, b, 1 - inset)
            band = [_project(p, low), _project(q, low), _project(q, high), _project(p, high)]
            parts.append(_path(band, f'fill="{_mix(GLASS_SHADE, GLASS_LIT, light)}" stroke="none"'))
        for position, width in entrances:
            door = _door(a, b, length, position, width, slab)
            if door:
                parts.append(_path(door, f'fill="{ENTRANCE}"'))
    return parts


def _door(a: Point2, b: Point2, length: float, position: Point2, width: float, slab: Slab) -> list[Point2] | None:
    """An entrance drawn on the wall from `a` to `b`, if the entrance lies on that wall."""
    t = ((position[0] - a[0]) * (b[0] - a[0]) + (position[1] - a[1]) * (b[1] - a[1])) / (length * length)
    foot = _along(a, b, min(1.0, max(0.0, t)))
    if math.dist(foot, position) > 1.0:
        return None
    half = min(width, length) / 2 / length
    start, end = max(0.0, t - half), min(1.0, t + half)
    p, q = _along(a, b, start), _along(a, b, end)
    height = slab.bottom + min(2.4, slab.height * 0.8)
    return [_project(p, slab.bottom), _project(q, slab.bottom), _project(q, height), _project(p, height)]


def _roof(slab: Slab) -> str:
    """The slab's top face. Holes such as courtyards stay open so their walls show through."""
    top = slab.bottom + slab.height
    rings = [slab.shape.exterior, *slab.shape.interiors]
    d = "".join(_ring([_project(point, top) for point in ring.coords]) for ring in rings)
    return f'<path d="{d}" fill="{ROOF}" fill-rule="evenodd" stroke-opacity="0.55"/>'


def _project(point: Point2 | tuple[float, ...], z: float) -> Point2:
    x, y = point[0], point[1]
    return ((x - y) * COS, -(x + y) * SIN - z)


def _depth(point: Point2 | tuple[float, ...]) -> float:
    return point[0] + point[1]


def _mid(a: Point2, b: Point2) -> Point2:
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def _along(a: Point2, b: Point2, t: float) -> Point2:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def _mix(low: tuple[int, int, int], high: tuple[int, int, int], t: float) -> str:
    return "#" + "".join(f"{round(lo + (hi - lo) * t):02x}" for lo, hi in zip(low, high, strict=True))


def _ring(points: list[Point2]) -> str:
    return "M" + "L".join(f"{x:.2f} {y:.2f}" for x, y in points) + "Z"


def _path(points: list[Point2], paint: str) -> str:
    return f'<path d="{_ring(points)}" {paint}/>'


def _svg(view_box: str, parts: list[str]) -> str:
    style = (
        f"path{{stroke:{INK};stroke-opacity:.6;stroke-width:.7;stroke-linejoin:round;vector-effect:non-scaling-stroke}}"
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}"><style>{style}</style>'
        + "".join(parts)
        + "</svg>"
    )
