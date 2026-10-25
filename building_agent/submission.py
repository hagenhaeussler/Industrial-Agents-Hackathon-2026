"""The benchmark command for a new building, and the answers.json file it writes.

  uv run run_benchmark <building_dir> <questions.json> <answers.json>

`questions.json` holds one entry per question with an id, the question text and optional constraints. It can be
a JSON list, an object with a "questions" list, an object keyed by question id, or JSON Lines.
"""

import argparse
import json
import os
import tempfile
import time
from collections import Counter
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from pathlib import Path

from benchmark.score import committed_answer
from building_agent.agent import Settings, load_from_directory, run_question

Job = tuple[Path, str, str]
"""Building directory, question id and the question text the agent gets."""


def read_questions(path: Path) -> list[tuple[str, str]]:
    """(id, text) pairs. Constraints, if given, are added to the text, because the agent sees only text."""
    content = path.read_text(encoding="utf-8")
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        data = [json.loads(line) for line in content.splitlines() if line.strip()]
    if isinstance(data, dict) and "questions" in data:
        data = data["questions"]
    elif isinstance(data, dict) and "id" in data:  # JSON Lines with one question
        data = [data]
    elif isinstance(data, dict):
        data = [{"id": key, **(entry if isinstance(entry, dict) else {"text": entry})} for key, entry in data.items()]
    questions = []
    for entry in data:
        text = entry.get("question") or entry.get("text")
        if not entry.get("id") or not text:
            raise ValueError(f"each question needs an id and a question or text field: {entry!r}")
        if entry.get("constraints"):
            text += f"\nConstraints: {json.dumps(entry['constraints'], ensure_ascii=False)}"
        questions.append((str(entry["id"]), text))
    if len({question_id for question_id, _ in questions}) != len(questions):
        raise ValueError("question ids must be unique")
    return questions


def answer_all(jobs: list[Job], workers: int) -> dict[str, dict]:
    """Run records by question id. Each building is imported once first, so parallel runs only read."""
    database = Settings.from_env().database
    for building_directory in sorted({job[0] for job in jobs}):
        load_from_directory(building_directory, database)
    records: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run_question, directory, text): question_id for directory, question_id, text in jobs}
        for done, future in enumerate(as_completed(futures), start=1):
            records[futures[future]] = future.result()
            print(f"[batch] {done:4d}/{len(jobs)} {futures[future]}", flush=True)
    return records


def answer_entry(question_id: str, record: dict) -> dict:
    """One answers.json entry: the full reply, its answer line and the answer as data."""
    result = record.get("result") or {"type": "failure", "reason": record.get("error") or record["reply"]}
    return {
        "id": question_id,
        "question": record["question"],
        "answer": committed_answer(record["reply"]),
        "reply": record["reply"],
        "result": result,
    }


def write_answers(path: Path, entries: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entries = list(entries)
    path.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"answers.json with {len(entries)} answers saved to {path}")


def print_usage(records: list[dict], seconds: float) -> None:
    """Totals across the batch: cost, tokens and cache use."""
    usages = [record["usage"] for record in records if record.get("usage")]
    cost = sum((Decimal(usage["cost_usd"]) for usage in usages if usage["cost_usd"]), Decimal(0))
    totals = Counter()
    for usage in usages:
        totals.update({key: value for key, value in usage.items() if isinstance(value, int)})
    errors = sum(1 for record in records if record.get("error"))
    print(f"\n{len(records)} questions in {seconds:.0f} s, {errors} stopped runs, cost ${cost:.4f}")
    print(f"tokens: {dict(totals)}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="run_benchmark", description="Answer every question about one building.")
    parser.add_argument("building_dir", type=Path, help="directory with building.json")
    parser.add_argument("questions", type=Path, help="questions.json")
    parser.add_argument("answers", type=Path, help="answers.json to write")
    parser.add_argument("--workers", type=int, default=10, help="questions answered at the same time")
    arguments = parser.parse_args()
    questions = read_questions(arguments.questions)
    started = time.monotonic()
    # A fresh database, so a stored building with the same id and other content cannot block the import.
    with tempfile.TemporaryDirectory() as directory:
        os.environ["BUILDING_DATABASE"] = str(Path(directory) / "buildings.sqlite3")
        jobs = [(arguments.building_dir, question_id, text) for question_id, text in questions]
        records = answer_all(jobs, arguments.workers)
    write_answers(arguments.answers, (answer_entry(question_id, records[question_id]) for question_id, _ in questions))
    print_usage(list(records.values()), time.monotonic() - started)


if __name__ == "__main__":
    main()
