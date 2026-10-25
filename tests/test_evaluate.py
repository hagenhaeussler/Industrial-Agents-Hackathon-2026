"""Offline evaluator tests with synthetic questions and a fixture agent."""

import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, call, patch

from benchmark import evaluate


class EvaluatorTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.root = Path(temporary_directory.name)
        self.split = self.root / "dev"
        self.building_directory = self.split / "fixture-building"
        self.building_directory.mkdir(parents=True)
        self.questions_path = self.building_directory / "questions.jsonl"
        self.question = {
            "id": "fixture-question",
            "building_id": "fixture-building",
            "kind": "shared_walls_count",
            "question": "How many rooms share a wall with the fixture room?",
            "answer": {
                "type": "number",
                "value": 2,
                "relative_tolerance": 0,
                "absolute_tolerance": 0,
            },
        }
        self.questions_path.write_text(json.dumps(self.question) + "\n", encoding="utf-8")
        self.reply = "Fixture reply with a comma, and a new line.\nAnswer: 2"
        self.agent = Mock(spec=["__call__"], return_value=self.reply)
        fixture_module = ModuleType("fixture_agent")
        fixture_module.answer = self.agent
        for replacement in (
            patch.dict(sys.modules, {"fixture_agent": fixture_module}),
            patch.object(evaluate, "RESULTS_DIRECTORY", self.root / "results"),
        ):
            replacement.start()
            self.addCleanup(replacement.stop)

    def test_agent_receives_only_building_path_and_question(self) -> None:
        with redirect_stdout(io.StringIO()):
            evaluate.run(self.split, None, "fixture_agent:answer", "dev")

        self.assertEqual(
            self.agent.call_args_list,
            [call(self.building_directory, self.question["question"])],
        )

    def test_scored_reply_is_preserved_in_submission(self) -> None:
        submission_path = self.root / "submission.csv"
        with redirect_stdout(io.StringIO()):
            evaluate.run(self.split, None, "fixture_agent:answer", "dev", submission_path)

        result = json.loads((self.root / "results/dev.jsonl").read_text(encoding="utf-8"))
        with submission_path.open(newline="", encoding="utf-8") as handle:
            submission = list(csv.reader(handle))
        self.assertEqual(
            (result["correct"], submission),
            (True, [["question_id", "answer"], ["fixture-question", self.reply]]),
        )

    def test_questions_without_gold_answers_are_saved_without_a_score(self) -> None:
        del self.question["answer"]
        self.questions_path.write_text(json.dumps(self.question) + "\n", encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            evaluate.run(self.split, None, "fixture_agent:answer", "test")

        result = json.loads((self.root / "results/test.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(
            (result["correct"], result["answer"], result["reply"]),
            (None, None, self.reply),
        )

    def test_command_requires_an_explicit_agent(self) -> None:
        result = subprocess.run(
            [sys.executable, "-B", "-m", "benchmark.evaluate", str(self.split)],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual((result.returncode, "--agent" in result.stderr), (2, True))
