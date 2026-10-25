"""Localize frames of a separate recording in a map and measure the error.

The second recording has its own ARKit frame. After localizing its frames, a robust fit turns and
shifts its ARKit trajectory onto the map. The error is the distance between each localized position
and the aligned ARKit position. ARKit drift in the second recording adds to this error, so it is an
upper bound for walks of a few minutes.

Run on the GPU machine:
    python -m localization.evaluate_capture --map ~/data/maps/<map> --capture ~/data/raw/<other>
"""

import argparse
import json
from pathlib import Path

import numpy as np

from .alignment import apply, ransac_yaw_translation
from .capture import load_capture, rotation_angle_deg, turn_clockwise, upright_turns
from .evaluate import localize_as_client, summarize
from .localizer import Localizer
from .video import probe, read_frames

ALIGNMENT_THRESHOLD_M = 1.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--map", type=Path, required=True)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--every", type=int, default=30, help="use every n-th video frame")
    parser.add_argument("--long-side", type=int, default=1024)
    parser.add_argument("--jpeg-quality", type=int, default=85)
    parser.add_argument("--num-retrieved", type=int, default=5)
    args = parser.parse_args()

    video = probe(args.capture / "rgb.mp4")
    capture = load_capture(args.capture, video.width, video.height)
    turns = upright_turns(capture.frames)
    localizer = Localizer(args.map, num_retrieved=args.num_retrieved)

    rows, estimates, recorded = [], [], []
    for index, video_frame in read_frames(capture.video, range(0, len(capture.frames), args.every)):
        frame = turn_clockwise(capture.frames[index], turns)
        image = np.ascontiguousarray(np.rot90(video_frame.bgr(), k=-turns))
        result, row = localize_as_client(localizer, image, frame.K, args.long_side, args.jpeg_quality)
        row["frame"] = index
        rows.append(row)
        if result.world_from_cam is not None:
            estimates.append(result.world_from_cam)
            recorded.append(frame.world_from_cam)
            row["localized"] = True

    estimated_centers = np.array([e[:3, 3] for e in estimates])
    recorded_centers = np.array([r[:3, 3] for r in recorded])
    map_from_capture, inliers = ransac_yaw_translation(
        recorded_centers, estimated_centers, ALIGNMENT_THRESHOLD_M
    )
    aligned = apply(map_from_capture, recorded_centers)
    localized_rows = [r for r in rows if r.get("localized")]
    for row, estimate, truth, center in zip(localized_rows, estimates, recorded, aligned):
        row["position_error_m"] = float(np.linalg.norm(estimate[:3, 3] - center))
        row["rotation_error_deg"] = rotation_angle_deg(
            estimate[:3, :3], map_from_capture[:3, :3] @ truth[:3, :3]
        )

    summary = summarize(rows) | {
        "capture": args.capture.name,
        "quarter_turns": turns,
        "alignment_inliers": int(inliers.sum()),
        "settings": {k: v for k, v in vars(args).items() if k not in ("map", "capture")},
    }
    report = args.map / f"eval-capture-{args.capture.name}-long{args.long_side}.json"
    report.write_text(json.dumps({"summary": summary, "frames": rows}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
