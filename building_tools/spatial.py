"""Spatial tools from the README definitions: stacking between floors, shared walls and 3D distance."""

import math
from typing import Literal

from building_tools.building import Building, FloorSummary, SpaceSummary, SpaceType, ToolInputError, ToolResult

MIN_OVERLAP_M2 = 0.01
"""Smaller overlaps are floating-point contact along an edge, not stacking."""


class Overlap(ToolResult):
    space: SpaceSummary
    overlap_m2: float
    share_of_start: float
    """Part of the start space's area that this space covers, from 0 to 1."""
    share_of_other: float
    """Part of this space's own area that lies over or under the start space, from 0 to 1."""


class StackedSpaces(ToolResult):
    start: SpaceSummary
    target_floor: FloorSummary
    overlaps: list[Overlap]
    """Largest overlap first. The README's "directly above/below" is the first entry."""


def stacked_spaces(
    building: Building, space_id: str, direction: Literal["above", "below"], floors: int = 1
) -> StackedSpaces:
    """Spaces on the floor `floors` steps above or below whose outline overlaps the start space's outline.

    Ask for the target floor directly. Two steps of one floor can give a different space than one step of two
    floors, because the space in between can be larger or offset.
    """
    if floors < 1:
        raise ToolInputError("floors must be 1 or more; use direction to choose above or below")
    start = building.space(space_id)
    index = building.floors.index(building.floor_by_id[start.floor_id]) + (floors if direction == "above" else -floors)
    if not 0 <= index < len(building.floors):
        raise ToolInputError(
            f"there is no floor {floors} step(s) {direction} {building.floor_by_id[start.floor_id].name}"
        )
    target = building.floors[index]

    outline = building.polygon_by_id[start.id]
    overlaps = []
    for other in building.spaces_on(target.id):
        area = outline.intersection(building.polygon_by_id[other.id]).area
        if area >= MIN_OVERLAP_M2:
            overlaps.append(
                Overlap(
                    space=building.space_summary(other),
                    overlap_m2=round(area, 2),
                    share_of_start=round(area / outline.area, 3),
                    share_of_other=round(area / building.polygon_by_id[other.id].area, 3),
                )
            )
    return StackedSpaces(
        start=building.space_summary(start),
        target_floor=building.floor_summary(target),
        overlaps=sorted(overlaps, key=lambda overlap: overlap.overlap_m2, reverse=True),
    )


class Neighbour(ToolResult):
    space: SpaceSummary
    shared_length_m: float


class SharedWalls(ToolResult):
    start: SpaceSummary
    count: int
    """Number of entries in `counted`. Spaces in `not_counted` are already left out."""
    counted: list[Neighbour]
    """Neighbours whose space type is in `count_types`, longest shared wall first."""
    not_counted: list[Neighbour]
    """Neighbours of other types, such as corridors, for context only."""


def shared_walls(
    building: Building,
    space_id: str,
    count_types: list[SpaceType] | None = None,
    min_length_m: float = 1.0,
    max_gap_m: float = 0.35,
) -> SharedWalls:
    """Spaces on the same floor that share a wall with the start space.

    Two outlines share a wall when at least `min_length_m` of one runs within `max_gap_m` of the other, because
    walls have thickness. A door between them does not matter. `count_types` defaults to rooms and halls.
    """
    counted_types = set(count_types or ["room", "hall"])
    start = building.space(space_id)
    outline = building.polygon_by_id[start.id]
    counted: list[Neighbour] = []
    not_counted: list[Neighbour] = []
    for other in building.spaces_on(start.floor_id):
        other_outline = building.polygon_by_id[other.id]
        if other.id == start.id or outline.distance(other_outline) > max_gap_m:
            continue
        length = max(
            outline.exterior.intersection(other_outline.exterior.buffer(max_gap_m)).length,
            other_outline.exterior.intersection(outline.exterior.buffer(max_gap_m)).length,
        )
        if length >= min_length_m:
            neighbour = Neighbour(space=building.space_summary(other), shared_length_m=round(length, 2))
            (counted if other.type in counted_types else not_counted).append(neighbour)
    for neighbours in (counted, not_counted):
        neighbours.sort(key=lambda neighbour: neighbour.shared_length_m, reverse=True)
    return SharedWalls(
        start=building.space_summary(start), count=len(counted), counted=counted, not_counted=not_counted
    )


class Centre(ToolResult):
    space: SpaceSummary
    point: tuple[float, float, float]
    """Polygon centroid x and y, and the floor's elevation as z, in metres."""


class Distance3D(ToolResult):
    first: Centre
    second: Centre
    distance_m: float
    horizontal_m: float
    vertical_m: float


def distance_3d(building: Building, first_space_id: str, second_space_id: str) -> Distance3D:
    """Straight-line distance between two space centres: the polygon centroid at the floor's elevation."""
    centres = []
    for space_id in (first_space_id, second_space_id):
        space = building.space(space_id)
        centroid = building.polygon_by_id[space.id].centroid
        elevation = building.floor_by_id[space.floor_id].elevation_m
        point = (round(centroid.x, 3), round(centroid.y, 3), round(elevation, 3))
        centres.append(Centre(space=building.space_summary(space), point=point))
    (x1, y1, z1), (x2, y2, z2) = centres[0].point, centres[1].point
    horizontal = math.hypot(x2 - x1, y2 - y1)
    return Distance3D(
        first=centres[0],
        second=centres[1],
        distance_m=round(math.hypot(horizontal, z2 - z1), 3),
        horizontal_m=round(horizontal, 3),
        vertical_m=round(abs(z2 - z1), 3),
    )
