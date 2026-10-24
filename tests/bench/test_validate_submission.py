import csv

import pytest

from bench.validate_submission import validate_submission


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerows(rows)
    return path


@pytest.fixture
def template(tmp_path):
    return write_csv(tmp_path / "template.csv", [["question_id", "answer"], ["q1", ""], ["q2", ""]])


def test_valid_utf8_multiline_replies_are_accepted(template, tmp_path):
    submission = write_csv(tmp_path / "submission.csv", [["question_id", "answer"], ["q1", "Computed area.\nAnswer: 4 m²"], ["q2", "Answer: 0"]])
    assert validate_submission(submission, template) == []


@pytest.mark.parametrize("case", [
    ([["question_id", "answer"], ["q1", "Answer: 0"], ["q1", "Answer: 0"]], "Duplicate question ID: q1"),
    ([["question_id", "answer"], ["q1", "Answer: 0"]], "Missing question ID: q2"),
    ([["question_id", "answer"], ["q3", "Answer: 0"]], "Unknown question ID: q3"),
    ([["answer", "question_id"]], "Header must be question_id,answer."),
    ([["question_id", "answer"], ["q1", "Answer: "]], "missing non-empty Answer:"),
    ([["question_id", "answer"], ["q1", "Answer: 0", "extra"]], "expected two fields"),
])
def test_invalid_submission_reports_the_problem(template, tmp_path, case):
    rows, problem = case
    submission = write_csv(tmp_path / "submission.csv", rows)
    assert any(problem in message for message in validate_submission(submission, template))


def test_invalid_utf8_is_rejected(template, tmp_path):
    submission = tmp_path / "submission.csv"
    submission.write_bytes(b"\xff")
    assert "UTF-8" in validate_submission(submission, template)[0]


def test_file_above_size_limit_is_rejected(template, tmp_path):
    submission = tmp_path / "submission.csv"
    with submission.open("wb") as handle:
        handle.truncate(5_000_001)
    assert "exceeds" in validate_submission(submission, template)[0]
