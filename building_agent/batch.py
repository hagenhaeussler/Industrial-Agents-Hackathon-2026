"""Run the agent on many benchmark questions in parallel, then score with the official scorer.

  uv run python -m building_agent.batch data/dev --workers 10 --per-kind 2

The agent gets only the question text. Expected answers are read for scoring after every reply is in.
Output matches `benchmark.evaluate`: replies in agent_output/benchmark/<name>.jsonl, optional submission CSV.
`--answers-json` also writes the answers in the answers.json format of `run_benchmark`.
"""

import argparse
import json
import time
from collections import Counter
from pathlib import Path

from benchmark.evaluate import RESULTS_DIRECTORY, load_questions, report, sample_per_kind, write_submission_csv
from benchmark.score import score_reply
from building_agent.submission import answer_all, answer_entry, print_usage, write_answers


def run_batch(
    directory: Path,
    workers: int,
    name: str,
    per_kind: int | None = None,
    kinds: list[str] | None = None,
    submission_csv: Path | None = None,
    answers_json: Path | None = None,
) -> None:
    questions = [item for item in load_questions(directory) if not kinds or item[1]["kind"] in kinds]
    selected = sample_per_kind(questions, per_kind)

    started = time.monotonic()
    records = answer_all([(building, q["id"], q["question"]) for building, q in selected], workers)

    results: Counter[tuple[str, bool]] = Counter()
    RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    results_path = RESULTS_DIRECTORY / f"{name}.jsonl"
    with results_path.open("w", encoding="utf-8") as log:
        for _, question in selected:
            record = records[question["id"]]
            # The public test set has no answers: then replies are only saved.
            correct = score_reply(question["answer"], record["reply"]) if "answer" in question else None
            if correct is not None:
                results[(question["kind"], correct)] += 1
            line = {
                "id": question["id"],
                "kind": question["kind"],
                "correct": correct,
                "question": question["question"],
                "answer": question.get("answer"),
                "reply": record["reply"],
                "result": record.get("result"),
                "usage": record.get("usage"),
                "error": record.get("error"),
            }
            log.write(json.dumps(line, ensure_ascii=False) + "\n")
            outcome = {True: "OK ", False: "BAD", None: "saved"}[correct]
            print(f"[benchmark] {question['id']:34s} {question['kind']:20s} {outcome}")

    if results:
        report(results)
    if submission_csv is not None:
        write_submission_csv(submission_csv, [(q["id"], records[q["id"]]["reply"]) for _, q in selected])
    if answers_json is not None:
        write_answers(answers_json, (answer_entry(q["id"], records[q["id"]]) for _, q in selected))
    print_usage(list(records.values()), time.monotonic() - started)
    print(f"replies saved to {results_path}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="building_agent.batch")
    parser.add_argument("directory", type=Path, help="a split directory such as data/dev")
    parser.add_argument("--workers", type=int, default=10, help="questions answered at the same time")
    parser.add_argument("--per-kind", type=int, default=None, help="sample this many questions per kind")
    parser.add_argument("--kinds", nargs="+", default=None, help="only these question kinds")
    parser.add_argument("--name", default="batch", help="file name for the saved replies")
    parser.add_argument("--submission-csv", type=Path, default=None, help="also write question_id,answer")
    parser.add_argument("--answers-json", type=Path, default=None, help="also write answers.json")
    arguments = parser.parse_args()
    run_batch(
        arguments.directory,
        arguments.workers,
        arguments.name,
        arguments.per_kind,
        arguments.kinds,
        arguments.submission_csv,
        arguments.answers_json,
    )


if __name__ == "__main__":
    main()
