"""Walking inside one space, as the README route model defines it.

A walk stays 15 cm off the walls and goes round corners: it is a shortest path through a visibility graph of
the start, the end and the corners of the shrunken outline. An opening lands 30 cm inside the space, and the
step from the opening to its landing is part of the walk.
"""

import itertools
import math
from dataclasses import dataclass

import numpy as np
import shapely
from shapely.geometry import Point, Polygon
from shapely.ops import nearest_points

WALL_CLEARANCE_M = 0.15
DOOR_LANDING_M = 0.30
NARROW_LANDING_M = 0.05
COVER_TOLERANCE_M = 0.02
BLOCKED_DETOUR_FACTOR = 1.5
"""Applied to the straight distance when no clear walk exists between two points of a space."""

Point2 = tuple[float, float]


@dataclass(frozen=True)
class Member:
    """A point a walk can start or end at: the space's centre (`opening_id` None) or one of its openings."""

    opening_id: str | None
    landing: Point2
    stub_m: float
    """Distance from the opening's position to its landing. Zero for the centre."""


@dataclass(frozen=True)
class Walk:
    first: Member
    second: Member
    length_m: float
    """Walk between the two landings plus both stubs, rounded to millimetres like every route edge."""


def anchor(polygon: Polygon) -> Point2:
    """The space's centre node: a point guaranteed inside the polygon."""
    point = polygon.representative_point()
    return (point.x, point.y)


def door_landing(polygon: Polygon, position: Point2) -> Point2:
    """Where an opening at `position` lands inside the space: 30 cm in from the walls."""
    inner = polygon.buffer(-DOOR_LANDING_M)
    if inner.is_empty:
        inner = polygon.buffer(-NARROW_LANDING_M)
    if inner.is_empty:
        return anchor(polygon)
    if inner.contains(Point(position)):
        return position
    landing = nearest_points(inner, Point(position))[0]
    return (landing.x, landing.y)


def visibility_matrix(allowed: Polygon, nodes: list[Point2]) -> np.ndarray:
    """Straight distances between nodes that see each other inside `allowed`; infinite where blocked."""
    coordinates = np.asarray(nodes, dtype=float)
    straight = np.hypot(*(coordinates[:, None, :] - coordinates[None, :, :]).transpose(2, 0, 1))
    first, second = np.triu_indices(len(nodes), k=1)
    shapely.prepare(allowed)
    segments = shapely.linestrings(np.stack([coordinates[first], coordinates[second]], axis=1))
    usable = shapely.covers(allowed, segments) | (straight[first, second] == 0)
    matrix = np.full(straight.shape, np.inf)
    np.fill_diagonal(matrix, 0.0)
    matrix[first[usable], second[usable]] = straight[first[usable], second[usable]]
    matrix[second[usable], first[usable]] = straight[first[usable], second[usable]]
    return matrix


def walking_lengths(polygon: Polygon, points: list[Point2]) -> np.ndarray:
    """Shortest walks between all pairs of `points` inside the space."""
    walkable = polygon.buffer(-WALL_CLEARANCE_M)
    if walkable.is_empty or walkable.geom_type != "Polygon":
        walkable = polygon
    allowed = walkable.buffer(COVER_TOLERANCE_M)
    corners: list[Point2] = [
        (x, y) for ring in [walkable.exterior, *walkable.interiors] for x, y in list(ring.coords)[:-1]
    ]
    matrix = visibility_matrix(allowed, [*points, *corners])
    for middle in range(len(matrix)):  # Floyd-Warshall
        matrix = np.minimum(matrix, matrix[:, middle, None] + matrix[None, middle, :])
    size = len(points)
    lengths = matrix[:size, :size]
    fallback = np.hypot(*(np.asarray(points)[:, None, :] - np.asarray(points)[None, :, :]).transpose(2, 0, 1))
    return np.where(np.isfinite(lengths), lengths, fallback * BLOCKED_DETOUR_FACTOR)


def space_walks(polygon: Polygon, openings: list[tuple[str, Point2]]) -> list[Walk]:
    """Walks between the centre and each opening, and between every two openings, of one space."""
    members = [Member(None, anchor(polygon), 0.0)]
    for opening_id, position in openings:
        landing = door_landing(polygon, position)
        members.append(Member(opening_id, landing, math.dist(landing, position)))
    lengths = walking_lengths(polygon, [member.landing for member in members])
    return [
        Walk(members[i], members[j], round(float(lengths[i, j]) + members[i].stub_m + members[j].stub_m, 3))
        for i, j in itertools.combinations(range(len(members)), 2)
    ]
