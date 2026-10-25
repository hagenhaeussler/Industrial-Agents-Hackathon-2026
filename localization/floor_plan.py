"""Draw a clean floor plan and a first building.json from the LiDAR depth of one capture.

1. Back-project the depth of the map keyframes into 5 cm voxels in the map frame.
2. Find the floor height. Turn the plan so that most walls run along the x and y axes.
3. Mark walls (points 1.0 to 2.2 m above the floor) and free space (camera rays and seen floor).
4. Snap the outline to the strongest wall lines, see `outline.rectilinear_outline`.
5. Write one floor with one space. `source_ref` holds the transform from the map frame, so
   localization results can be shown in the plan.

The scan cannot tell names, room types or furniture. They come from a small annotations file:

    {"name": "Office 3rd floor",
     "space": {"name": "Office", "type": "room", "room_type": "office"},
     "assets": [{"name": "Table 1", "category": "furniture", "type": "table", "near": [3.0, 4.0]}]}

`near` is an approximate position in the plan frame. The asset footprint is taken from the points at
table height around it.

Run on the GPU machine:
    python -m localization.floor_plan --capture ~/data/raw/<capture> --map <map name> \
        --annotations annotations.json --out ~/data/buildings/<capture>
"""

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from shapely.geometry import Polygon

from .alignment import apply
from .capture import Capture, load_capture, select_keyframes
from .outline import rectilinear_outline, wall_angle
from .point_cloud import depth_views, voxel_counts
from .video import probe

WALL_BAND_M = (1.0, 2.2)  # above desks and below door headers and ceiling fittings
TABLE_BAND_M = (0.6, 1.3)  # desks and standing tables
MIN_POINTS = 2  # voxels with fewer points are often noise

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Scan:
    voxels: np.ndarray  # N x 3 voxel centres, map frame
    counts: np.ndarray  # depth points per voxel
    centers: np.ndarray  # camera centre per view
    samples: list[np.ndarray]  # a few depth points per view, for free-space rays


@dataclass(frozen=True)
class Grid:
    lo: np.ndarray  # plan position of the lower-left corner
    cell_m: float
    shape: tuple[int, int]  # rows (y), columns (x)

    def index(self, xy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        cells = np.floor((xy - self.lo) / self.cell_m).astype(int)
        return np.clip(cells[:, 1], 0, self.shape[0] - 1), np.clip(cells[:, 0], 0, self.shape[1] - 1)

    def count(self, xy: np.ndarray) -> np.ndarray:
        grid = np.zeros(self.shape, np.float32)
        np.add.at(grid, self.index(xy), 1)
        return grid


def scan_points(capture: Capture, indices: list[int], cell_m: float) -> Scan:
    keys, counts, centers, samples = [], [], [], []
    for view in depth_views(capture, indices):
        k, c = voxel_counts(view.points, cell_m)
        keys.append(k)
        counts.append(c)
        centers.append(view.center)
        samples.append(view.points[::25])
    k, inverse = np.unique(np.concatenate(keys), axis=0, return_inverse=True)
    c = np.bincount(inverse.ravel(), weights=np.concatenate(counts))
    return Scan((k + 0.5) * cell_m, c, np.array(centers), samples)


def floor_height(scan: Scan, cell_m: float) -> float:
    """Map-frame height of the floor: the most common point height well below the camera."""
    y = scan.voxels[:, 1]
    low = (y < np.median(scan.centers[:, 1]) - 0.8) & (scan.counts >= MIN_POINTS)
    bins = np.arange(y[low].min(), y[low].max() + cell_m, cell_m)
    hist, edges = np.histogram(y[low], bins=bins, weights=np.minimum(scan.counts[low], 50))
    return float(edges[np.argmax(hist)] + cell_m / 2)


def building_from_map(angle: float, floor_y: float, origin: np.ndarray) -> np.ndarray:
    """4 x 4 transform from the map frame (ARKit: y up) to the plan frame (x right, y up, z height).

    Seen from above, the map's x and -z axes are the plan's x and y before the turn by `angle`.
    """
    c, s = np.cos(angle), np.sin(angle)
    return np.array(
        [[c, 0, s, -origin[0]], [s, 0, -c, -origin[1]], [0, 1, 0, -floor_y], [0, 0, 0, 1]], float
    )


def disk(radius_m: float, cell_m: float) -> np.ndarray:
    r = max(1, int(round(radius_m / cell_m)))
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def fill_holes(mask: np.ndarray) -> np.ndarray:
    outside = np.pad(mask, 1).astype(np.uint8)
    cv2.floodFill(outside, None, (0, 0), 2)
    return outside[1:-1, 1:-1] != 2


def interior_mask(
    wall: np.ndarray, free: np.ndarray, floor_seen: np.ndarray, path: tuple[np.ndarray, np.ndarray], cell_m: float
) -> np.ndarray:
    """Space inside the building that the scan saw, connected to the camera path.

    Free space reaches through windows, so it is cut to the hull of the walls. Closing with a 1.5 m disk
    bridges doors and glass walls, but not the gaps between separate wings.
    """
    hull = fill_holes(cv2.morphologyEx(wall.astype(np.uint8), cv2.MORPH_CLOSE, disk(1.5, cell_m)) > 0)
    seen = ((free >= 2) | floor_seen) & hull
    seen = fill_holes(cv2.morphologyEx(seen.astype(np.uint8), cv2.MORPH_CLOSE, disk(0.3, cell_m)) > 0) & hull
    _, labels = cv2.connectedComponents(seen.astype(np.uint8))
    visited = np.unique(labels[path])
    return np.isin(labels, visited[visited > 0])


def free_space(scan: Scan, transform: np.ndarray, grid: Grid) -> np.ndarray:
    """How many views saw each cell as empty: a ray from the camera to a depth point crosses it."""
    free = np.zeros(grid.shape, np.uint16)
    for samples, center in zip(scan.samples, scan.centers):
        points = apply(transform, samples)
        points = points[(points[:, 2] >= 0.3) & (points[:, 2] < WALL_BAND_M[1])]
        if not len(points):
            continue
        rows, cols = grid.index(points[:, :2])
        crow, ccol = grid.index(apply(transform, center[None])[:, :2])
        rays = np.zeros(grid.shape, np.uint8)
        for row, col in zip(rows, cols):
            cv2.line(rays, (int(ccol[0]), int(crow[0])), (int(col), int(row)), 1)
        free += rays
    return free


def ceiling_height(heights: np.ndarray, counts: np.ndarray) -> float:
    """Most common point height between 1.9 and 4 m above the floor."""
    sel = (heights > 1.9) & (heights < 4.0) & (counts >= MIN_POINTS)
    hist, edges = np.histogram(heights[sel], bins=np.arange(1.9, 4.0, 0.05), weights=np.minimum(counts[sel], 50))
    return round(float(edges[np.argmax(hist)] + 0.025), 2)


def asset_footprint(table: np.ndarray, near: np.ndarray, grid: Grid) -> dict | None:
    """Axis-aligned box of the largest blob of table-height points within 1 m of `near`.

    Opening the mask drops chair backs and people next to the table, which would join the blob.
    """
    mask = cv2.morphologyEx((table >= MIN_POINTS).astype(np.uint8), cv2.MORPH_OPEN, disk(0.1, grid.cell_m))
    _, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    row, col = (int(v[0]) for v in grid.index(near[None]))
    r = int(round(1.0 / grid.cell_m))
    candidates = [
        label for label in np.unique(labels[max(0, row - r) : row + r + 1, max(0, col - r) : col + r + 1])
        if label > 0
    ]
    if not candidates:
        return None
    label = max(candidates, key=lambda label: stats[label, cv2.CC_STAT_AREA])
    x, y, w, h = (int(stats[label, i]) for i in (cv2.CC_STAT_LEFT, cv2.CC_STAT_TOP, cv2.CC_STAT_WIDTH, cv2.CC_STAT_HEIGHT))
    lo = grid.lo + np.array([x, y]) * grid.cell_m
    size = np.array([w, h]) * grid.cell_m
    center = lo + size / 2
    return {"position": [round(float(center[0]), 3), round(float(center[1]), 3)],
            "footprint": {"width_m": round(float(size[0]), 2), "depth_m": round(float(size[1]), 2), "rotation_deg": 0.0}}


def write_preview(path: Path, wall: np.ndarray, grid: Grid, outline: Polygon, path_xy: np.ndarray,
                  assets: list[dict]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    hi = grid.lo + np.array(grid.shape[::-1]) * grid.cell_m
    fig, ax = plt.subplots(figsize=(20, 12))
    ax.imshow(np.clip(wall / 6, 0, 1), cmap="Greys", origin="lower", extent=[grid.lo[0], hi[0], grid.lo[1], hi[1]])
    ax.fill(*outline.exterior.xy, color="#1f77b4", alpha=0.12)
    ax.plot(*outline.exterior.xy, color="#1f77b4", lw=2.5, label="Outline")
    ax.plot(path_xy[:, 0], path_xy[:, 1], color="#d62728", lw=0.7, alpha=0.7, label="Scan path")
    for asset in assets:
        (x, y), fp = asset["position"], asset.get("footprint")
        if fp:
            ax.add_patch(Rectangle((x - fp["width_m"] / 2, y - fp["depth_m"] / 2), fp["width_m"], fp["depth_m"],
                                   fill=False, ec="#2ca02c", lw=2))
        ax.annotate(asset["name"], (x, y), color="#2ca02c", ha="center", va="center", fontsize=9)
    minx, miny, maxx, maxy = outline.bounds
    ax.set_xlim(minx - 2, maxx + 2)
    ax.set_ylim(miny - 2, maxy + 2)
    ax.set_xticks(np.arange(np.floor(minx / 5) * 5, maxx + 5, 5))
    ax.set_yticks(np.arange(np.floor(miny / 5) * 5, maxy + 5, 5))
    ax.grid(alpha=0.35)
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.legend(loc="upper right")
    ax.set_title(f"Floor plan from the scan: {outline.area:.0f} m²")
    fig.tight_layout()
    fig.savefig(path, dpi=90)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--map", required=True, help="name of the localization map built from this capture")
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cell-m", type=float, default=0.05)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    cell = args.cell_m
    annotations = json.loads(args.annotations.read_text())

    video = probe(args.capture / "rgb.mp4")
    capture = load_capture(args.capture, video.width, video.height)
    keyframes = select_keyframes(capture.frames, 0.3, 12)  # the map's keyframes
    scan = scan_points(capture, keyframes, cell)
    floor_y = floor_height(scan, cell)
    solid = scan.counts >= MIN_POINTS

    unturned = apply(building_from_map(0.0, floor_y, np.zeros(2)), scan.voxels)
    in_wall_band = (unturned[:, 2] >= WALL_BAND_M[0]) & (unturned[:, 2] < WALL_BAND_M[1]) & solid
    angle = wall_angle(unturned[in_wall_band, :2], cell)
    turned = building_from_map(angle, floor_y, np.zeros(2))
    points = apply(turned, scan.voxels)
    logger.info("%d voxels from %d views, floor at map y %.2f, walls turned by %.2f°",
                len(points), len(keyframes), floor_y, np.degrees(angle))

    lo = points[:, :2].min(0) - 1.0
    shape = tuple(np.ceil((points[:, :2].max(0) + 1.0 - lo) / cell).astype(int)[::-1])
    grid = Grid(lo, cell, shape)
    height = points[:, 2]
    wall = grid.count(points[in_wall_band, :2])
    table = grid.count(points[(height >= TABLE_BAND_M[0]) & (height < TABLE_BAND_M[1]) & solid, :2])
    floor_seen = grid.count(points[(np.abs(height) < 0.1) & solid, :2]) > 0
    free = free_space(scan, turned, grid)
    path_xy = apply(turned, scan.centers)[:, :2]
    interior = interior_mask(wall >= 3, free, floor_seen, grid.index(path_xy), cell)
    outline = rectilinear_outline(interior, wall >= 3, lo, cell)

    # Put the plan origin at the lower-left corner of the outline.
    origin = np.array(outline.bounds[:2])
    transform = building_from_map(angle, floor_y, origin)
    grid = Grid(lo - origin, cell, shape)
    outline = Polygon(np.asarray(outline.exterior.coords)[:-1] - origin)
    path_xy -= origin

    building_id = f"scan-{args.capture.name}"
    floor_id = f"{building_id}-F0"
    space_id = f"{floor_id}-S001"
    space = annotations.get("space", {})
    assets = []
    for number, note in enumerate(annotations.get("assets", []), start=1):
        found = asset_footprint(table, np.array(note["near"], float), grid)
        if found is None:
            logger.warning("No points at table height near %s, using the annotated position", note["name"])
            found = {"position": note["near"]}
        assets.append({
            "id": f"{building_id}-A{number:03d}", "name": note["name"], "category": note["category"],
            "type": note["type"], "space_id": space_id, "floor_id": floor_id, **found, "source": "dataset",
        })

    building = {
        "building": {
            "id": building_id,
            "name": annotations.get("name", building_id),
            "source": "scan",
            "source_ref": {
                "capture": args.capture.name,
                "map": args.map,
                "generator": "localization.floor_plan",
                "building_from_map": np.round(transform, 6).tolist(),
                "wall_angle_deg": round(float(np.degrees(angle)), 2),
                "cell_m": cell,
                "annotations": annotations,
            },
            "license": "private",
            "attribution": "Phone scan",
            "split": "scan",
            "units": "m",
        },
        "floors": [{
            "id": floor_id, "level": 0, "name": "Ground floor", "elevation_m": 0.0,
            "height_m": ceiling_height(height, scan.counts),
        }],
        "spaces": [{
            "id": space_id, "floor_id": floor_id, "type": space.get("type", "room"),
            "room_type": space.get("room_type"), "name": space.get("name", "Room"), "ref": None,
            "polygon": [[round(float(x), 3), round(float(y), 3)] for x, y in outline.exterior.coords[:-1]],
            "synthetic": False,
        }],
        "openings": [],
        "vertical_connectors": [],
        "assets": assets,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "building.json").write_text(json.dumps(building, indent=2, ensure_ascii=False))
    write_preview(args.out / "plan.png", wall, grid, outline, path_xy, assets)
    logger.info("Outline %.0f m² with %d corners, %d assets, written to %s",
                outline.area, len(outline.exterior.coords) - 1, len(assets), args.out)


if __name__ == "__main__":
    main()
