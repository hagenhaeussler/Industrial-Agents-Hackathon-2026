"""Validate the submission file without opening question or answer-key files."""

import argparse
import csv
import re
from collections import Counter
from pathlib import Path

MAX_BYTES = 5_000_000
COLUMNS = ["question_id", "answer"]
ANSWER_LINE = re.compile(r"^Answer:\s*\S.*$", re.MULTILINE)


def read_rows(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, strict=True)
        return next(reader, []), list(reader)


def validate_submission(submission: Path, template: Path) -> list[str]:
    problems = []
    try:
        if submission.stat().st_size > MAX_BYTES:
            return [f"Submission exceeds {MAX_BYTES} bytes."]
        template_header, template_rows = read_rows(template)
        header, rows = read_rows(submission)
    except (OSError, UnicodeError, csv.Error) as error:
        return [f"Cannot read UTF-8 CSV: {error}"]
    if template_header != COLUMNS:
        return [f"Unexpected template header: {template_header}"]
    if header != COLUMNS:
        problems.append(f"Header must be {','.join(COLUMNS)}.")
    expected = {row[0] for row in template_rows if row}
    counts: Counter[str] = Counter()
    for line, row in enumerate(rows, start=2):
        if len(row) != len(COLUMNS):
            problems.append(f"Row {line}: expected two fields.")
            continue
        question_id, reply = row
        counts[question_id] += 1
        if not ANSWER_LINE.search(reply):
            problems.append(f"Row {line} ({question_id}): missing non-empty Answer: line.")
    problems.extend(f"Missing question ID: {item}" for item in sorted(expected - counts.keys()))
    problems.extend(f"Unknown question ID: {item}" for item in sorted(counts.keys() - expected))
    problems.extend(f"Duplicate question ID: {item}" for item, count in sorted(counts.items()) if count > 1)
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("submission", type=Path)
    parser.add_argument("template", type=Path)
    arguments = parser.parse_args()
    problems = validate_submission(arguments.submission, arguments.template)
    if problems:
        parser.exit(1, "\n".join(problems) + "\n")
    print("ok: exact template IDs, two columns, UTF-8, size limit, Answer: lines")


if __name__ == "__main__":
    main()
