"""Evaluation only: compare SVG bytes with known floor geometry.

The gold JSON is read only in this module. Bounds provide an oracle calibration
for measurement, simulating a perfectly supplied user distance; import_plan
never receives the directory, filename, reference IDs or reference polygons.
"""

import argparse
import itertools
import json
from pathlib import Path

from shapely.affinity import translate
from shapely.geometry import Polygon
from shapely.ops import unary_union

from . import import_plan
from .svg import extract_svg


DEFAULT_FLOORS = [("proc-factory-dev-003", 0), ("proc-campus-dev-000", 0), ("osm-way27326387", 0)]


def measure_floor(directory, floor_level=0):
    directory = Path(directory)
    raw = json.loads((directory / "building.json").read_text())
    floor = next(f for f in raw["floors"] if f["level"] == floor_level)
    gold = [s for s in raw["spaces"] if s["floor_id"] == floor["id"]]
    file_bytes = (directory / f"floor_{floor_level}.svg").read_bytes()
    extracted = extract_svg(file_bytes)
    svg_bounds = unary_union([Polygon(r["polygon"]) for r in extracted["rooms"]]).bounds
    gold_bounds = unary_union([Polygon(s["polygon"]).buffer(0) for s in gold]).bounds
    sx0, sy0, sx1, sy1 = svg_bounds
    gx0, gy0, gx1, gy1 = gold_bounds
    scale = {"p1": [sx0, sy1], "p2": [sx1, sy1], "length_m": gx1-gx0}
    result = import_plan(file_bytes, "svg", floor_level, scale)
    draft = result["draft"]
    reference = {s["id"]: translate(Polygon(s["polygon"]).buffer(0), -gx0, -gy0) for s in gold}
    imported = {s["id"]: Polygon(s["polygon"]) for s in draft["spaces"]}
    candidates = []
    for imported_id, first in imported.items():
        for gold_id, second in reference.items():
            if not first.intersects(second):
                continue
            intersection = first.intersection(second).area
            union = first.union(second).area
            iou = intersection/union if union else 0
            if iou >= .5:
                candidates.append((iou, imported_id, gold_id))
    matches, used_gold, ious = {}, set(), []
    for iou, imported_id, gold_id in sorted(candidates, reverse=True):
        if imported_id not in matches and gold_id not in used_gold:
            matches[imported_id] = gold_id
            used_gold.add(gold_id)
            ious.append(iou)

    def pair(first, second):
        return tuple(sorted((first, second)))

    true_edges = {pair(*opening["space_ids"]) for opening in raw["openings"]
                  if opening["floor_id"] == floor["id"] and "outside" not in opening["space_ids"]}
    found_edges = set()
    for opening in draft["openings"]:
        if "outside" in opening["space_ids"]:
            continue
        first, second = opening["space_ids"]
        if first in matches and second in matches:
            found_edges.add(pair(matches[first], matches[second]))
    recovered_edges = true_edges & found_edges
    return {"building_id": raw["building"]["id"], "floor_level": floor_level,
            "gold_rooms": len(gold), "draft_rooms": len(imported), "matched_rooms": len(matches),
            "room_recall": round(len(matches)/len(gold), 6),
            "mean_matched_iou": round(sum(ious)/len(ious), 6) if ious else 0,
            "gold_door_adjacencies": len(true_edges), "draft_door_adjacencies": len(found_edges),
            "door_graph_recall": round(len(recovered_edges)/len(true_edges), 6) if true_edges else 1,
            "door_graph_precision": round(len(recovered_edges)/len(found_edges), 6) if found_edges else 0,
            "calibration_anisotropy_error": round(abs((sx1-sx0)/(sy1-sy0) - (gx1-gx0)/(gy1-gy0)), 9),
            "validation_ok": result["validation"]["ok"], "validation_errors": result["validation"]["errors"],
            "needs": result["needs"], "unresolved_markers": len(result["diagnostics"]["unresolved_markers"]),
            "calibration_source": "evaluation_only_gold_bounds", "vision_calls": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", default="data/dev")
    parser.add_argument("--output")
    args = parser.parse_args()
    results = [measure_floor(Path(args.split)/bid, level) for bid, level in DEFAULT_FLOORS]
    report = {"recommendation": "mention_only", "scope": "kit Matplotlib SVG drafts; not arbitrary floor plans",
              "calibration": "Oracle bounds in evaluation only; runtime requires two user points and known distance.",
              "results": results, "vision_calls": 0, "vision_cost": 0,
              "unmeasured": ["arbitrary architect SVG/PDF/PNG plans", "labels", "room semantic types", "door widths", "accessibility", "multi-floor alignment"]}
    output = json.dumps(report, indent=2)
    if args.output:
        Path(args.output).write_text(output + "\n")
    print(output)


if __name__ == "__main__":
    main()
