"""Offline solver checks with prediction separated from reference scoring.

The reference template parser is a temporary adapter until Lenard publishes
bench.templates. It is loaded by exact file path and never placed on sys.path.
"""

import argparse
import importlib.util
import json
import time
from collections import defaultdict
from pathlib import Path

from benchmark.score import score_reply
from .profiles import current_profile
from .spatial import SpatialCore


def _template_parser():
    try:
        from bench.templates import parse_question
        return parse_question, "bench.templates"
    except ModuleNotFoundError as error:
        if error.name not in {"bench", "bench.templates"}:
            raise
    reference = Path(__file__).resolve().parents[1] / "research/sibling-repo-2026-10-24/core/questions.py"
    spec = importlib.util.spec_from_file_location("_tyb_reference_template_adapter", reference)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.parse_question, str(reference.relative_to(Path(__file__).resolve().parents[1]))


def evaluate(directory: Path, output: Path, check="text") -> dict:
    """Validate public train/dev inputs or public question text, without API calls."""
    directory, output = Path(directory), Path(output)
    started = time.perf_counter()
    rows = []
    parser, parser_source = _template_parser() if check == "text" else (None, None)
    buildings = 0
    for path in sorted(directory.glob("*/questions.jsonl")):
        buildings += 1
        building = SpatialCore.load(path.parent)
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            question = json.loads(line)
            row = {"id": question["id"], "kind": question["kind"], "profile": building.profile,
                   "content_hash": building.content_hash, "check": check}
            tick = time.perf_counter()
            try:
                if check == "text":
                    kind, inputs = parser(building, question["question"])
                else:
                    # Structured mode is explicitly a tool-level regression
                    # oracle. These fields never enter submitted inference.
                    kind, inputs = question["kind"], question["inputs"]
                result = building.solve(kind, inputs)
                reply = building.format_answer(result)
                row.update(parsed_kind=kind, parsed_inputs=inputs, result=result, reply=reply)
            except Exception as error:
                row.update(error=f"{type(error).__name__}: {error}", reply="")
            row["duration_ms"] = (time.perf_counter() - tick) * 1000
            # Do not move reference-answer reads into the prediction block.
            row["correct"] = score_reply(question["answer"], row["reply"]) if "answer" in question else None
            if check == "text" and "inputs" in question:
                row["parse_matches_inputs"] = (row.get("parsed_kind") == question["kind"] and
                                                 row.get("parsed_inputs") == question["inputs"])
            rows.append(row)
    if not rows:
        raise ValueError(f"No benchmark questions found in {directory}")
    by_kind = defaultdict(lambda: {"total": 0, "correct": 0, "scored": 0, "errors": 0, "parse_mismatches": 0})
    for row in rows:
        stat = by_kind[row["kind"]]
        stat["total"] += 1
        stat["correct"] += row["correct"] is True
        stat["scored"] += row["correct"] is not None
        stat["errors"] += "error" in row
        stat["parse_mismatches"] += row.get("parse_matches_inputs") is False
    summary = {"split": directory.name, "buildings": buildings, "total": len(rows), "check": check,
               "profile": current_profile(), "parser": parser_source,
               "correct": sum(row["correct"] is True for row in rows),
               "scored": sum(row["correct"] is not None for row in rows),
               "seconds": time.perf_counter() - started, "by_kind": dict(sorted(by_kind.items()))}
    output.mkdir(parents=True, exist_ok=True)
    stem = f"{directory.name}-{check}"
    (output / f"{stem}.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    (output / f"{stem}-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, default=Path("agent_output/reports/core"))
    parser.add_argument("--check", choices=("structured", "text"), default="text")
    args = parser.parse_args()
    failed = False
    for directory in args.directories:
        summary = evaluate(directory, args.output, args.check)
        print(f"{summary['split']} {summary['check']} · {summary['profile']}")
        print(f"{'kind':30} {'correct / total':>17} {'errors':>8}")
        for kind, stats in summary["by_kind"].items():
            print(f"{kind:30} {stats['correct']:6} / {stats['total']:<6} {stats['errors']:8}")
        print(f"{'all':30} {summary['correct']:6} / {summary['total']:<6} ({summary['seconds']:.2f}s)")
        failed |= summary["correct"] < summary["scored"] or any(stats["errors"] for stats in summary["by_kind"].values())
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
