"""Localize a few random frames of another recording and draw them for a visual check.

Each figure shows:
- the photo as the web client would send it,
- the coloured LiDAR point cloud of the map, drawn from the estimated camera pose,
- both blended, so shifted edges stand out,
- the floor plan with the estimated position and viewing direction, and the reference position from the
  aligned ARKit path of the recording.

Run on the GPU machine after `evaluate_capture`, which stores the alignment of both recordings:
    python -m localization.compare --map ~/data/maps/<map> --map-capture ~/data/raw/<map capture> \
        --capture ~/data/raw/<other> --building ~/data/buildings/<capture>/building.json --out <dir>
"""

import argparse
import json
import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from shapely.geometry import Point, Polygon

from .alignment import apply
from .capture import load_capture, select_keyframes, turn_clockwise, upright_turns
from .evaluate import localize_as_client
from .localizer import Localizer, resize_long_side
from .point_cloud import colored_cloud, render
from .video import probe, read_frames

CLOUD_VOXEL_M = 0.03
LONG_SIDE = 1024
JPEG_QUALITY = 85

logger = logging.getLogger(__name__)


def load_cloud(map_dir: Path, map_capture: Path) -> tuple[np.ndarray, np.ndarray]:
    """Coloured cloud of the map keyframes, cached in the map folder because it takes minutes."""
    cache = map_dir / f"cloud-{round(CLOUD_VOXEL_M * 100)}cm.npz"
    if cache.exists():
        data = np.load(cache)
        return data["points"], data["colors"]
    settings = json.loads((map_dir / "map.json").read_text())["settings"]
    video = probe(map_capture / "rgb.mp4")
    capture = load_capture(map_capture, video.width, video.height)
    keyframes = select_keyframes(capture.frames, settings["min_step_m"], settings["min_turn_deg"])
    points, colors = colored_cloud(capture, keyframes, CLOUD_VOXEL_M)
    np.savez(cache, points=points.astype(np.float32), colors=colors)
    logger.info("Coloured cloud with %d points written to %s", len(points), cache)
    return points, colors


def plan_pose(building_from_map: np.ndarray, world_from_cam: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Plan position and unit viewing direction of a camera."""
    position = apply(building_from_map, world_from_cam[:3, 3][None])[0, :2]
    direction = (building_from_map[:3, :3] @ world_from_cam[:3, 2])[:2]
    return position, direction / (np.linalg.norm(direction) or 1)


def draw_plan(ax, building: dict, walls: np.ndarray) -> None:
    ax.scatter(walls[:, 0], walls[:, 1], s=0.05, c="#999999", rasterized=True)
    for space in building["spaces"]:
        outline = np.array(space["polygon"] + space["polygon"][:1])
        ax.plot(outline[:, 0], outline[:, 1], c="#1f77b4", lw=1.5)
    for asset in building["assets"]:
        (x, y), footprint = asset["position"], asset.get("footprint")
        if footprint:
            w, d = footprint["width_m"], footprint["depth_m"]
            ax.add_patch(Rectangle((x - w / 2, y - d / 2), w, d, fill=False, ec="#2ca02c"))
    ax.set_aspect("equal")
    ax.grid(alpha=0.3)
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--map", type=Path, required=True)
    parser.add_argument("--map-capture", type=Path, required=True)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--building", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    report = json.loads((args.map / f"eval-capture-{args.capture.name}-long{LONG_SIDE}.json").read_text())
    map_from_capture = np.array(report["summary"]["map_from_capture"])
    building = json.loads(args.building.read_text())
    building_from_map = np.array(building["building"]["source_ref"]["building_from_map"])
    spaces = [(space["name"], Polygon(space["polygon"])) for space in building["spaces"]]

    points, colors = load_cloud(args.map, args.map_capture)
    plan_points = apply(building_from_map, points)
    walls = plan_points[(plan_points[:, 2] > 1.0) & (plan_points[:, 2] < 2.2), :2][::20]

    video = probe(args.capture / "rgb.mp4")
    capture = load_capture(args.capture, video.width, video.height)
    turns = upright_turns(capture.frames)
    rng = np.random.default_rng(args.seed)
    chosen = sorted(int(i) for i in rng.choice(len(capture.frames), args.count, replace=False))
    localizer = Localizer(args.map)
    args.out.mkdir(parents=True, exist_ok=True)

    for index, video_frame in read_frames(capture.video, chosen):
        frame = turn_clockwise(capture.frames[index], turns)
        photo = np.ascontiguousarray(np.rot90(video_frame.bgr(), k=-turns))
        result, row = localize_as_client(localizer, photo, frame.K, LONG_SIDE, JPEG_QUALITY)
        small, scale = resize_long_side(photo, LONG_SIDE)
        reference = map_from_capture @ frame.world_from_cam
        ref_xy, ref_dir = plan_pose(building_from_map, reference)

        fig = plt.figure(figsize=(18, 13))
        grid = fig.add_gridspec(2, 3, height_ratios=[1, 1.15])
        panels = [fig.add_subplot(grid[0, i]) for i in range(3)]
        panels[0].imshow(small[:, :, ::-1])
        panels[0].set_title(f"Photo, frame {index}")
        lines = [f"Frame {index}: {result.num_inliers} inliers, {sum(result.timings_ms.values()):.0f} ms on the GPU"]
        plan = fig.add_subplot(grid[1, :])
        draw_plan(plan, building, walls)
        plan.plot(*ref_xy, "x", c="#2ca02c", ms=12, mew=3, label="Reference (ARKit path, aligned)")
        plan.arrow(*ref_xy, *(ref_dir * 1.5), color="#2ca02c", width=0.08)

        if result.world_from_cam is None:
            for ax in panels[1:]:
                ax.text(0.5, 0.5, "Not located", ha="center", va="center", transform=ax.transAxes)
            lines.append("Not located")
        else:
            K = frame.K.copy()
            K[:2] *= scale
            K[:2, 2] += 0.5 * scale - 0.5
            view = render(points, colors, K, result.world_from_cam, small.shape[1], small.shape[0])
            panels[1].imshow(view[:, :, ::-1])
            panels[1].set_title("Point cloud from the estimated pose")
            panels[2].imshow(((small.astype(np.float32) + view) / 2).astype(np.uint8)[:, :, ::-1])
            panels[2].set_title("Both blended")
            xy, direction = plan_pose(building_from_map, result.world_from_cam)
            height = apply(building_from_map, result.world_from_cam[:3, 3][None])[0, 2]
            space = next((name for name, polygon in spaces if polygon.contains(Point(xy))), "outside every space")
            error = float(np.linalg.norm(result.world_from_cam[:3, 3] - reference[:3, 3]))
            heading = np.degrees(np.arctan2(direction[1], direction[0]))
            plan.plot(*xy, "o", c="#d62728", ms=10, label="Estimated position")
            plan.arrow(*xy, *(direction * 1.5), color="#d62728", width=0.08)
            lines.append(
                f"Plan position ({xy[0]:.2f}, {xy[1]:.2f}) m in {space}, phone {height:.2f} m above the floor, "
                f"heading {heading:.0f}° from +x. Distance to reference {error:.2f} m"
            )
        for ax in panels:
            ax.axis("off")
        plan.legend(loc="upper right")
        plan.set_title(lines[-1], fontsize=11)
        fig.suptitle(lines[0], fontsize=13)
        fig.tight_layout()
        fig.savefig(args.out / f"compare-{index:06d}.png", dpi=80)
        plt.close(fig)
        print(" | ".join(lines))


if __name__ == "__main__":
    main()
