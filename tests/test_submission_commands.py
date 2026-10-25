"""Exercise the jury commands with real calculation tools and a local test model."""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, ToolCallPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from benchmark.score import committed_answer
from building_agent import batch, submission
from building_agent.agent import build_agent
from tests.test_building_db import fixture_building


class SubmissionCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.building_dir = self.root / "jury-building"
        self.building_dir.mkdir()
        (self.building_dir / "building.json").write_text(json.dumps(fixture_building()), encoding="utf-8")
        self.questions_path = self.root / "questions.json"
        self.output_path = self.root / "output" / "answers.json"
        self.prompts: set[str] = set()
        environment = mock.patch.dict(os.environ, {
            "PYTHON_DOTENV_DISABLED": "1",
            "ANTHROPIC_API_KEY": "",
            "BUILDING_AGENT_RUNS": str(self.root / "runs"),
            "BUILDING_DATABASE": str(self.root / "original.sqlite3"),
        })
        environment.start()
        self.addCleanup(environment.stop)

    def model(self, messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        prompts = [
            part.content
            for message in messages if isinstance(message, ModelRequest)
            for part in message.parts if isinstance(part, UserPromptPart) and isinstance(part.content, str)
        ]
        self.prompts.update(prompts)
        question = prompts[-1]
        if question.startswith("Route"):
            args = {"stops": ["S-office", "S-lift-1"], "explanation": "Use the lift."}
            if "closed" in question:
                args["conditions"] = {"closed": ["O-door"]}
            name = "answer_route"
        elif question == "Where is the desk?":
            name = "answer_room"
            args = {"space_id": "S-office", "asset_id": "A-desk", "explanation": "The desk is in the office."}
        elif question == "Count rooms.":
            name = "answer_count"
            args = {"count": 1, "explanation": "There is one office."}
        else:
            name = "report_failure"
            args = {"reason": "The requested room is ambiguous."}
        return ModelResponse(parts=[ToolCallPart(name, args)])

    def test_jury_command_writes_routes_locations_counts_and_failures_in_one_format(self) -> None:
        questions = [
            {"question_id": "route", "question": "Route to the lift upstairs."},
            {"id": "blocked", "text": "Route to the lift upstairs.", "constraints": {"closed": ["O-door"]}},
            {"id": "desk", "text": "Where is the desk?"},
            {"id": "count", "text": "Count rooms.", "answer": "PRIVATE LABEL", "inputs": {"count": 999}},
            {"id": "failure", "text": "Find the ambiguous room."},
        ]
        self.questions_path.write_text(json.dumps(questions), encoding="utf-8")
        argv = ["run_benchmark", str(self.building_dir), str(self.questions_path), str(self.output_path), "--workers", "1"]
        with (
            mock.patch("sys.argv", argv),
            mock.patch(
                "building_agent.agent.build_agent",
                side_effect=lambda building, model, effort: build_agent(building, FunctionModel(self.model), effort),
            ),
            redirect_stdout(io.StringIO()),
        ):
            submission.main()
        entries = json.loads(self.output_path.read_text(encoding="utf-8"))
        self.assertEqual([entry["question_id"] for entry in entries], ["route", "blocked", "desk", "count", "failure"])
        self.assertTrue(all(set(entry) == {"question_id", "answer"} for entry in entries))
        answers = {entry["question_id"]: entry["answer"] for entry in entries}
        route = answers["route"]
        self.assertIn('Route space IDs: ["S-office", "S-lift-0", "S-lift-1"]', route)
        self.assertIn('Route element IDs: ["O-door", "V-lift"]', route)
        self.assertIn("Reachable: true", route)
        self.assertGreater(float(committed_answer(route).removesuffix(" m")), 18.0)
        self.assertIn("Route space IDs: []", answers["blocked"])
        self.assertIn("Reachable: false\nLength (m): null", answers["blocked"])
        self.assertEqual(committed_answer(answers["blocked"]), "No route exists under these rules.")
        self.assertIn("Space ID: S-office\nItem ID: A-desk", answers["desk"])
        self.assertEqual(committed_answer(answers["desk"]), "Office 0.01 (Ground floor)")
        self.assertEqual(answers["count"], "1")
        self.assertIsNone(answers["failure"])
        self.assertEqual(self.prompts, {
            "Route to the lift upstairs.",
            'Route to the lift upstairs.\nConstraints: {"closed": ["O-door"]}',
            "Where is the desk?", "Count rooms.", "Find the ambiguous room.",
        })

    def test_batch_writes_jury_json_by_default(self) -> None:
        split = self.root / "test"
        building_dir = split / "fixture"
        building_dir.mkdir(parents=True)
        (building_dir / "questions.jsonl").write_text(
            json.dumps({"id": "Q1", "kind": "shared_walls_count", "question": "Count rooms."}) + "\n",
            encoding="utf-8",
        )
        record = {"question": "Count rooms.", "reply": "One office.\nAnswer: 1"}
        with (
            mock.patch.object(batch, "RESULTS_DIRECTORY", self.root / "benchmark"),
            mock.patch.object(batch, "answer_all", return_value={"Q1": record}),
            redirect_stdout(io.StringIO()),
        ):
            batch.run_batch(split, workers=1, name="jury")
        saved = json.loads((self.root / "benchmark" / "jury_answers.json").read_text(encoding="utf-8"))
        self.assertEqual(saved, [{"question_id": "Q1", "answer": "1"}])

    def test_invalid_command_inputs_stop_before_agent_calls(self) -> None:
        self.questions_path.write_text('[{"id": "Q1", "text": "Count rooms."}]', encoding="utf-8")
        cases = (
            [str(self.building_dir), str(self.questions_path), str(self.questions_path)],
            [str(self.building_dir), str(self.questions_path), str(self.building_dir / "building.json")],
            [str(self.building_dir), str(self.questions_path), str(self.output_path), "--workers", "0"],
            [str(self.root / "missing"), str(self.questions_path), str(self.output_path)],
        )
        with mock.patch.object(submission, "answer_all") as run:
            for arguments in cases:
                with (
                    self.subTest(arguments=arguments),
                    mock.patch("sys.argv", ["run_benchmark", *arguments]),
                    self.assertRaises(SystemExit),
                    mock.patch("sys.stderr", new_callable=io.StringIO),
                ):
                    submission.main()
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
