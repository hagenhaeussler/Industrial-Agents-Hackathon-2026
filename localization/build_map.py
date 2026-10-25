"""Build a localization map from one Stray Scanner capture.

The map uses the ARKit poses as fixed camera poses and triangulates SuperPoint points between them.
That keeps metric scale and gravity without a separate alignment step. Frames between the map
keyframes are kept as held-out queries with known poses for `evaluate`.

Run on the GPU machine:
    python -m localization.build_map --capture ~/data/raw/<capture> --out ~/data/maps/<capture>
"""

import argparse
import itertools
import json
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
import pycolmap
from hloc import extract_features, pairs_from_retrieval, triangulation

from .capture import Capture, Frame, load_capture, select_keyframes, turn_clockwise, upright_turns
from .localizer import GLOBAL_FEATURES, LOCAL_FEATURES, colmap_camera
from .matching import match_pairs
from .video import VideoFrame, probe, read_frames

SHARPNESS_WINDOW = 3  # frames on each side of a keyframe; 50 ms at 60 fps

logger = logging.getLogger(__name__)


def sharpness(gray: np.ndarray) -> float:
    small = cv2.resize(gray, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    return float(cv2.Laplacian(small, cv2.CV_64F).var())


def write_upright(path: Path, frame: VideoFrame, turns: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), np.rot90(frame.bgr(), k=-turns), [cv2.IMWRITE_JPEG_QUALITY, 95])


def write_frames(capture: Capture, targets: dict[str, tuple[int, int]], turns: int, image_dir: Path) -> dict[str, int]:
    """Save the sharpest frame within each target's window. Targets map name to (frame, window)."""
    windows = {name: range(max(0, i - w), min(len(capture.frames), i + w + 1)) for name, (i, w) in targets.items()}
    candidates = defaultdict(list)
    for name, window in windows.items():
        for j in window:
            candidates[j].append(name)

    best: dict[str, tuple[float, int, VideoFrame]] = {}
    chosen = {}
    # Color conversion and JPEG encoding release the GIL, so threads overlap them with decoding.
    with ThreadPoolExecutor(max_workers=3) as writer:
        writes = []

        def save(name: str) -> None:
            _, index, frame = best.pop(name)
            chosen[name] = index
            writes.append(writer.submit(write_upright, image_dir / name, frame, turns))

        for j, frame in read_frames(capture.video, candidates):
            score = sharpness(frame.luma)
            for name in candidates[j]:
                if name not in best or score > best[name][0]:
                    best[name] = (score, j, frame)
                if j == windows[name][-1]:
                    save(name)
        for name in list(best):
            save(name)
        for write in writes:
            write.result()  # raise write errors here
    return chosen


def write_reference_model(frames: dict[str, Frame], model_dir: Path) -> None:
    """Write fixed camera poses as a COLMAP text model without 3D points."""
    model_dir.mkdir(parents=True, exist_ok=True)
    cameras, images = [], []
    for image_id, (name, frame) in enumerate(sorted(frames.items()), start=1):
        camera = colmap_camera(frame.K, frame.width, frame.height)
        params = " ".join(f"{p:.6f}" for p in camera.params)
        cameras.append(f"{image_id} PINHOLE {frame.width} {frame.height} {params}")
        cam_from_world = np.linalg.inv(frame.world_from_cam)
        qx, qy, qz, qw = pycolmap.Rotation3d(cam_from_world[:3, :3]).quat
        tx, ty, tz = cam_from_world[:3, 3]
        # Each image needs a second line for its 2D points, empty here.
        images.append(f"{image_id} {qw} {qx} {qy} {qz} {tx} {ty} {tz} {image_id} {name}\n\n")
    (model_dir / "cameras.txt").write_text("\n".join(cameras) + "\n")
    (model_dir / "images.txt").write_text("".join(images))
    (model_dir / "points3D.txt").write_text("")


def pose_pairs(
    frames: dict[str, Frame], per_image: int, max_angle_deg: float = 60, max_distance_m: float = 8
) -> set[tuple[str, str]]:
    """Pair each keyframe with its nearest keyframes that look in a similar direction."""
    names = sorted(frames)
    centers = np.array([frames[n].center for n in names])
    directions = np.array([frames[n].view_direction for n in names])
    distances = np.linalg.norm(centers[:, None] - centers[None], axis=-1)
    valid = (directions @ directions.T >= np.cos(np.radians(max_angle_deg))) & (distances <= max_distance_m)
    np.fill_diagonal(valid, False)
    pairs = set()
    for i in range(len(names)):
        for j in [j for j in np.argsort(distances[i]) if valid[i, j]][:per_image]:
            pairs.add(tuple(sorted((names[i], names[j]))))
    return pairs


def triangulate(out: Path, image_dir: Path, pairs: Path, features: Path, matches: Path) -> None:
    """Triangulate matches between the fixed reference poses, as `hloc.triangulation.main` does.

    hloc stores verified pairs with an undefined geometry type, and pycolmap 4 skips those pairs.
    Marking them as calibrated restores the expected behavior.
    """
    reference = pycolmap.Reconstruction(out / "reference")
    database = out / "sfm" / "database.db"
    database.parent.mkdir(parents=True, exist_ok=True)
    image_ids = triangulation.create_db_from_model(reference, database)
    with pycolmap.Database.open(database) as db:
        triangulation.import_features(image_ids, db, features)
        triangulation.import_matches(image_ids, db, pairs, matches)
        triangulation.geometric_verification(image_ids, reference, db, features, pairs, matches)
        pair_ids, geometries = db.read_two_view_geometries()
        for pair_id, geometry in zip(pair_ids, geometries):
            geometry.config = pycolmap.TwoViewGeometryConfiguration.CALIBRATED
            db.update_two_view_geometry(*pycolmap.pair_id_to_image_pair(pair_id), geometry)
    model = triangulation.run_triangulation(out / "sfm", database, image_dir, reference)
    logger.info("Triangulated map:\n%s", model.summary())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--min-step-m", type=float, default=0.3)
    parser.add_argument("--min-turn-deg", type=float, default=12)
    parser.add_argument("--pose-pairs", type=int, default=15)
    parser.add_argument("--retrieval-pairs", type=int, default=10)
    parser.add_argument("--num-queries", type=int, default=200)
    parser.add_argument("--max-frames", type=int, help="use only the first frames, for quick tests")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    video = probe(args.capture / "rgb.mp4")
    capture = load_capture(args.capture, video.width, video.height)
    if args.max_frames:
        capture = Capture(capture.root, capture.frames[: args.max_frames])
    turns = upright_turns(capture.frames)

    keyframes = select_keyframes(capture.frames, args.min_step_m, args.min_turn_deg)
    between = [(a + b) // 2 for a, b in itertools.pairwise(keyframes) if b - a >= 2]
    step = max(1, len(between) // args.num_queries)
    queries = between[::step][: args.num_queries]
    logger.info(
        "%d frames, %d keyframes, %d queries, %d quarter turns",
        len(capture.frames),
        len(keyframes),
        len(queries),
        turns,
    )

    image_dir = args.out / "images"
    targets = {f"map/{i:06d}.jpg": (i, SHARPNESS_WINDOW) for i in keyframes}
    targets |= {f"query/{i:06d}.jpg": (i, 0) for i in queries}
    chosen = write_frames(capture, targets, turns, image_dir)
    frames = {name: turn_clockwise(capture.frames[i], turns) for name, i in chosen.items()}
    map_frames = {n: f for n, f in frames.items() if n.startswith("map/")}

    write_reference_model(map_frames, args.out / "reference")
    map_names = sorted(map_frames)
    features = args.out / "features.h5"
    extract_features.main(LOCAL_FEATURES, image_dir, image_list=map_names, feature_path=features)
    global_features = args.out / "global.h5"
    extract_features.main(GLOBAL_FEATURES, image_dir, image_list=map_names, feature_path=global_features)

    retrieval_path = args.out / "pairs-retrieval.txt"
    pairs_from_retrieval.main(global_features, retrieval_path, args.retrieval_pairs)
    pairs = pose_pairs(map_frames, args.pose_pairs)
    for line in retrieval_path.read_text().splitlines():
        pairs.add(tuple(sorted(line.split())))
    pairs_path = args.out / "pairs.txt"
    pairs = sorted(pairs)
    pairs_path.write_text("\n".join(" ".join(p) for p in pairs))
    logger.info("%d image pairs", len(pairs))

    matches = args.out / "matches.h5"
    match_pairs(pairs, features, matches)
    triangulate(args.out, image_dir, pairs_path, features, matches)

    def describe(name: str) -> dict:
        frame = frames[name]
        return {
            "name": name,
            "frame": chosen[name],
            "width": frame.width,
            "height": frame.height,
            "K": frame.K.tolist(),
            "world_from_cam": frame.world_from_cam.tolist(),
        }

    query_names = sorted(n for n in frames if n.startswith("query/"))
    (args.out / "queries.json").write_text(json.dumps([describe(n) for n in query_names]))
    (args.out / "map.json").write_text(
        json.dumps(
            {
                "capture": args.capture.name,
                "quarter_turns": turns,
                "keyframes": len(map_names),
                "settings": {k: v for k, v in vars(args).items() if k not in ("capture", "out")},
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
