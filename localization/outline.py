"""Turn a raster floor plan into a polygon with straight, axis-aligned walls.

Rasters use rows for y and columns for x. Row 0 and column 0 start at `lo`, the plan position of the
raster's lower-left corner.
"""

import itertools

import numpy as np
from shapely import box, unary_union
from shapely.geometry import MultiPolygon, Polygon

SIDE_M = 0.5  # how far beside a wall to look for interior


def wall_angle(xy: np.ndarray, cell_m: float = 0.05, step_deg: float = 0.25) -> float:
    """Rotation in radians, within ±45°, that turns most wall points onto lines parallel to the axes.

    Points of an axis-parallel wall fall into few histogram bins, so the sum of squared bin counts peaks
    at the right angle.
    """
    best_deg, best_score = 0.0, -1.0
    for deg in np.arange(-45, 45, step_deg):
        c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
        score = 0.0
        for values in (xy[:, 0] * c - xy[:, 1] * s, xy[:, 0] * s + xy[:, 1] * c):
            counts = np.bincount(np.floor((values - values.min()) / cell_m).astype(int))
            score += float(np.sum(counts.astype(np.float64) ** 2))
        if score > best_score:
            best_deg, best_score = deg, score
    return float(np.radians(best_deg))


def outer_walls(interior: np.ndarray, wall: np.ndarray, cell_m: float) -> tuple[np.ndarray, np.ndarray]:
    """Wall cells per column with interior only on their high side (left walls) or low side (right walls).

    Interior walls have interior on both sides, so they do not count. Transpose both rasters to get
    bottom and top walls per row.
    """
    k = max(1, round(SIDE_M / cell_m))
    padded = np.pad(interior, ((0, 0), (k, k)))
    before, after = padded[:, : -2 * k], padded[:, 2 * k :]
    return (wall & after & ~before).sum(axis=0), (wall & before & ~after).sum(axis=0)


def wall_lines(profile: np.ndarray, cell_m: float, min_length_m: float, merge_m: float, outward: int) -> list[float]:
    """Positions, in cells, of the outer walls on one side of the plan.

    A line needs `min_length_m` of wall. Lines closer than `merge_m` belong to one facade. Each facade
    becomes one straight line at its outermost line that holds at least half as much wall as its longest.
    `outward` is -1 for left or bottom walls and +1 for right or top walls.
    """
    smooth = np.convolve(profile, np.ones(3), mode="same") * cell_m
    peaks = [
        i for i in range(len(smooth)) if smooth[i] >= min_length_m and smooth[i] == smooth[max(0, i - 1) : i + 2].max()
    ]
    groups: list[list[int]] = []
    for i in peaks:
        if groups and (i - groups[-1][-1]) * cell_m < merge_m:
            groups[-1].append(i)
        else:
            groups.append([i])
    lines = []
    for group in groups:
        strong = [i for i in group if smooth[i] >= 0.5 * max(smooth[j] for j in group)]
        peak = max(strong) if outward > 0 else min(strong)
        peak += int(np.argmax(profile[peak - 1 : peak + 2])) - 1 if peak > 0 else 0  # undo the smoothing shift
        lines.append(peak + 0.5)  # middle of the wall cell
    return lines


def rectilinear_outline(
    interior: np.ndarray,
    wall: np.ndarray,
    lo: np.ndarray,
    cell_m: float,
    min_wall_m: float = 1.5,
    merge_m: float = 2.0,
    min_fill: float = 0.5,
) -> Polygon:
    """Outline of the interior, drawn along the outer walls.

    The outer wall lines cut the plan into cells. A cell belongs to the building when more than `min_fill`
    of it is interior. Space seen through glass or doors fills only part of a cell beyond the wall, so it
    drops out. Where the interior ends without a wall, the edge of the interior closes the outline. Holes
    are filled, because route tools expect one outline per space.
    """
    lines = []
    for raster_interior, raster_wall in ((interior, wall), (interior.T, wall.T)):  # x lines, then y lines
        low, high = outer_walls(raster_interior, raster_wall, cell_m)
        found = wall_lines(low, cell_m, min_wall_m, merge_m, -1) + wall_lines(high, cell_m, min_wall_m, merge_m, 1)
        used = np.nonzero(raster_interior.any(axis=0))[0]
        for edge in (float(used[0]), float(used[-1] + 1)):
            if all(abs(edge - line) * cell_m >= merge_m for line in found):
                found.append(edge)
        lines.append(sorted(found))
    xs, ys = lines

    cells = []
    for x0, x1 in itertools.pairwise(xs):
        for y0, y1 in itertools.pairwise(ys):
            part = interior[round(y0) : round(y1), round(x0) : round(x1)]
            if part.size and part.mean() > min_fill:
                cells.append(box(x0, y0, x1, y1))
    if not cells:
        raise ValueError("No interior cell is filled enough for an outline")

    shape = unary_union(cells)
    if isinstance(shape, MultiPolygon):
        shape = max(shape.geoms, key=lambda part: part.area)
    outline = Polygon(shape.exterior).simplify(1e-6)
    return Polygon((lo + np.asarray(outline.exterior.coords) * cell_m)[:-1])
