"""Check recovered dev warm-up routes against immutable kit references.

Usage: python -m core.check_geometry data/dev
Fallback walks remain explicitly reported; their drawing is not asserted to be
walkable or equal to the deliberately inflated kit cost.
"""

import argparse
import itertools
import json
from pathlib import Path
import time

from shapely.geometry import LineString

from .building import load_building
from .geometry import space_geometry
from .routing import route


def check(split):
    counts = {"buildings": 0, "routes": 0, "walks": 0, "fallback_walks": 0}
    failures, fallback_spaces = [], set()
    started = time.perf_counter()
    for path in sorted(Path(split).glob("*/questions_basic.jsonl")):
        b = load_building(path.parent)
        counts["buildings"] += 1
        for line in path.read_text().splitlines():
            question = json.loads(line)
            if question["kind"] not in {"route", "route_step_free", "route_with_closure", "tour"}:
                continue
            answer = question.get("answer", {})
            legs = answer.get("legs", [answer])
            if question["kind"] == "tour" and answer.get("reachable") is False:
                legs = [{"from_space_id": a, "to_space_id": z, "_no_length_reference": True}
                        for a, z in itertools.pairwise(answer["stops"])]
            leg_reachable = []
            constraints = {"step_free": question["kind"] == "route_step_free",
                           "closed": [answer["closed_element_id"]] if answer.get("closed_element_id") else []}
            for reference in legs:
                if not reference.get("from_space_id") or not reference.get("to_space_id"):
                    failures.append(f"{question['id']}: missing reference endpoints")
                    continue
                result = route(b, reference["from_space_id"], reference["to_space_id"], constraints)
                leg_reachable.append(result["reachable"])
                counts["routes"] += 1
                expected = reference.get("optimal_length_m")
                # Unreachable references use optimal_length_m: null.
                if expected is None and not reference.get("_no_length_reference"):
                    if result["reachable"]:
                        failures.append(f"{question['id']}: should be unreachable")
                    continue
                if not result["reachable"]:
                    if not reference.get("_no_length_reference"):
                        failures.append(f"{question['id']}: should be reachable")
                    continue
                if expected is not None and abs(result["length_m"] - expected) > 0.01000001:
                    failures.append(f"{question['id']}: route cost mismatch {result.get('length_m')} != {expected}")
                    continue
                for field in ("space_path", "element_path"):
                    if reference.get(field) is not None and result[field] != reference[field]:
                        failures.append(f"{question['id']}: {field} mismatch")
                for segment in result["segments"]:
                    if segment["kind"] != "walk":
                        continue
                    counts["walks"] += 1
                    sid = segment["space_id"]
                    if segment["fallback"]:
                        counts["fallback_walks"] += 1
                        fallback_spaces.add(sid)
                        continue
                    if abs(segment["geometry_length_m"] - segment["length_m"]) > 0.001000001:
                        failures.append(f"{question['id']}: geometry/rounded cost disagree in {sid}")
                    allowed = space_geometry(b, sid).allowed
                    points = segment["points"]
                    for index, (first, second) in enumerate(itertools.pairwise(points)):
                        is_stub = ((index == 0 and segment.get("from_node", "").startswith("door:")) or
                                   (index == len(points) - 2 and segment.get("to_node", "").startswith("door:")))
                        if not is_stub and not allowed.buffer(1e-8).covers(LineString([first, second])):
                            failures.append(f"{question['id']}: walk leaves allowed polygon in {sid}")
            if answer.get("reachable") is False and all(leg_reachable):
                failures.append(f"{question['id']}: tour should be unreachable")
    return {**counts, "fallback_space_ids": sorted(fallback_spaces), "failures": failures,
            "elapsed_s": round(time.perf_counter() - started, 3), "ok": not failures,
            "edge_rounding_tolerance_m": 0.001}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split", nargs="?", default="data/dev")
    args = parser.parse_args()
    result = check(args.split)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
