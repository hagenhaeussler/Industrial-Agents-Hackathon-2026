"""Measure localization error and server time on the held-out query frames of a map.

Each query is downscaled and JPEG-encoded the way the web client would send it. The reported time is
server time from JPEG bytes to pose. It excludes the network.

Held-out frames come from the same walk as the map, so the result is optimistic. `evaluate_capture`
gives a realistic test with a separate recording.

Run on the GPU machine:
    python -m localization.evaluate --map ~/data/maps/<capture> --long-side 1024
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from .capture import rotation_angle_deg
from .localizer import Localization, Localizer, colmap_camera, resize_long_side

WARMUP_QUERIES = 3
DISTANCE_THRESHOLDS_M = (0.25, 0.5, 1.0)


def percentile(values: list[float], q: float) -> float | None:
    return round(float(np.percentile(values, q)), 3) if values else None


def localize_as_client(
    localizer: Localizer, image: np.ndarray, K: np.ndarray, long_side: int, jpeg_quality: int
) -> tuple[Localization, dict]:
    """Downscale and JPEG-encode an upright image like the web client, then localize it."""
    image, scale = resize_long_side(image, long_side)
    K = K.copy()
    K[:2] *= scale
    K[:2, 2] += 0.5 * scale - 0.5
    camera = colmap_camera(K, image.shape[1], image.shape[0])
    _, jpeg = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
    result = localizer.localize_jpeg(jpeg.tobytes(), camera)
    row = {
        "num_inliers": result.num_inliers,
        "num_matches": result.num_matches,
        "jpeg_kb": round(len(jpeg) / 1024, 1),
        "timings_ms": result.timings_ms,
    }
    return result, row


def summarize(rows: list[dict]) -> dict:
    """Rows need `timings_ms`, `jpeg_kb` and, when localized, `position_error_m`. The first rows warm up."""
    measured = rows[WARMUP_QUERIES:] or rows
    errors = [r["position_error_m"] for r in rows if "position_error_m" in r]
    rotation = [r["rotation_error_deg"] for r in rows if "rotation_error_deg" in r]
    totals = [sum(r["timings_ms"].values()) for r in measured]
    stages = list(measured[0]["timings_ms"]) if measured else []
    return {
        "queries": len(rows),
        "localized": len(errors),
        "position_error_m": {"median": percentile(errors, 50), "p90": percentile(errors, 90)},
        "rotation_error_deg_median": percentile(rotation, 50),
        "within_m": {str(t): round(sum(e <= t for e in errors) / len(rows), 3) for t in DISTANCE_THRESHOLDS_M},
        "server_ms": {
            "median": percentile(totals, 50),
            "p90": percentile(totals, 90),
            "stages_median": {s: percentile([r["timings_ms"][s] for r in measured], 50) for s in stages},
        },
        "jpeg_kb_median": percentile([r["jpeg_kb"] for r in rows], 50),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--map", type=Path, required=True)
    parser.add_argument("--long-side", type=int, default=1024, help="query size sent by the client")
    parser.add_argument("--jpeg-quality", type=int, default=85)
    parser.add_argument("--num-retrieved", type=int, default=5)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    queries = json.loads((args.map / "queries.json").read_text())[: args.limit]
    localizer = Localizer(args.map, num_retrieved=args.num_retrieved)

    rows = []
    for query in queries:
        image = cv2.imread(str(args.map / "images" / query["name"]))
        result, row = localize_as_client(localizer, image, np.array(query["K"]), args.long_side, args.jpeg_quality)
        row["name"] = query["name"]
        truth = np.array(query["world_from_cam"])
        if result.world_from_cam is not None:
            row["position_error_m"] = float(np.linalg.norm(result.world_from_cam[:3, 3] - truth[:3, 3]))
            row["rotation_error_deg"] = rotation_angle_deg(result.world_from_cam[:3, :3], truth[:3, :3])
        rows.append(row)

    summary = summarize(rows) | {"settings": {k: v for k, v in vars(args).items() if k != "map"}}
    report = args.map / f"eval-long{args.long_side}-k{args.num_retrieved}.json"
    report.write_text(json.dumps({"summary": summary, "queries": rows}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
