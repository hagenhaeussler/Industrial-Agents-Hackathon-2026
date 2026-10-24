"""Offline evaluation with strict separation of prediction and reference answers."""

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

from benchmark.score import score_reply
from core.questions import parse_question
from core.spatial import SpatialCore


def evaluate(directory: Path, output: Path) -> dict:
    started = time.perf_counter()
    rows = []
    buildings = 0
    for path in sorted(directory.glob("*/questions.jsonl")):
        buildings += 1
        core = SpatialCore.load(path.parent)
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            question = json.loads(line)
            row = {"id": question["id"], "kind": question["kind"]}
            tick = time.perf_counter()
            try:
                # Inference receives only the question text and building data.
                kind, inputs = parse_question(core, question["question"])
                result = core.solve(kind, inputs)
                reply = core.format_answer(result)
                row.update(parsed_kind=kind, parsed_inputs=inputs, result=result, reply=reply)
            except Exception as error:
                row.update(error=f"{type(error).__name__}: {error}", reply="")
            row["duration_ms"] = (time.perf_counter() - tick) * 1000
            # Answer keys are accessed only after the prediction is complete.
            row["correct"] = score_reply(question["answer"], row["reply"]) if "answer" in question else None
            row["parse_matches_inputs"] = (row.get("parsed_kind") == question["kind"] and
                                            row.get("parsed_inputs") == question.get("inputs")) if "inputs" in question else None
            # Separate tool-only validation using published structured inputs.
            # This is an oracle for language interpretation, never a submitted prediction.
            if "inputs" in question:
                try:
                    tool_result = core.solve(question["kind"], question["inputs"])
                    row["structured_reply"] = core.format_answer(tool_result)
                    row["structured_correct"] = score_reply(question["answer"], row["structured_reply"])
                except Exception as error:
                    row.update(structured_error=f"{type(error).__name__}: {error}", structured_correct=False)
            rows.append(row)
    if not rows:
        raise ValueError(f"No benchmark questions found in {directory}")
    by_kind = defaultdict(lambda: {"total": 0, "correct": 0, "structured_correct": 0, "errors": 0, "parse_mismatches": 0})
    for row in rows:
        stat = by_kind[row["kind"]]
        stat["total"] += 1
        stat["correct"] += row["correct"] is True
        stat["structured_correct"] += row.get("structured_correct") is True
        stat["errors"] += "error" in row
        stat["parse_mismatches"] += row["parse_matches_inputs"] is False
    summary = {"split": directory.name, "buildings": buildings, "total": len(rows),
               "correct": sum(r["correct"] is True for r in rows),
               "structured_correct": sum(r.get("structured_correct") is True for r in rows),
               "scored": sum(r["correct"] is not None for r in rows),
               "seconds": time.perf_counter() - started, "by_kind": dict(sorted(by_kind.items()))}
    output.mkdir(parents=True, exist_ok=True)
    (output / f"{directory.name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    (output / f"{directory.name}-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/spatial"))
    parser.add_argument("--check", choices=("text", "structured"), default="text",
                        help="Which score controls the exit status (both are always reported)")
    args = parser.parse_args()
    summaries = [evaluate(directory, args.output) for directory in args.directories]
    print(json.dumps(summaries, indent=2))
    metric = "structured_correct" if args.check == "structured" else "correct"
    if any(s[metric] < s["scored"] or (args.check == "text" and any(k["errors"] or k["parse_mismatches"] for k in s["by_kind"].values())) for s in summaries):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
