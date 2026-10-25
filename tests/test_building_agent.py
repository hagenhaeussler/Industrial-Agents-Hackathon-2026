"""Agent tests without paid calls: formatter against the official scorer, tool use, repair and explicit failures."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from benchmark.score import score_reply
from building_agent.agent import answer, load_from_directory
from building_agent.answers import (
    CountAnswer,
    Failure,
    NumberAnswer,
    RoomAnswer,
    RouteAnswer,
    answer_result,
    format_reply,
)
from building_agent.submission import answer_entry, read_questions
from building_tools.network import RouteConditions
from tests.test_building_db import fixture_building

QUESTION = "Which space is Office 0.01 (Ground floor)? Finish with a line 'Answer: <room name or number>'."


def tool_returns(messages: list[ModelMessage]) -> list[ToolReturnPart]:
    return [
        part
        for message in messages
        if isinstance(message, ModelRequest)
        for part in message.parts
        if isinstance(part, ToolReturnPart)
    ]


def output_tool(info: AgentInfo, shape: str) -> str:
    return next(tool.name for tool in info.output_tools if shape in tool.name)


class AgentTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.building_directory = self.root / "fixture"
        self.building_directory.mkdir()
        (self.building_directory / "building.json").write_text(json.dumps(fixture_building()))
        environment = {
            "BUILDING_DATABASE": str(self.root / "buildings.sqlite3"),
            "BUILDING_AGENT_RUNS": str(self.root / "runs"),
        }
        patcher = mock.patch.dict(os.environ, environment)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.building = load_from_directory(self.building_directory, self.root / "buildings.sqlite3")

    def run_records(self) -> list[dict]:
        return [json.loads(path.read_text()) for path in sorted((self.root / "runs").glob("*.json"))]

    def test_formatted_replies_pass_the_official_scorer(self) -> None:
        room = {"type": "space", "accept": ["0.01", "Office 0.01"], "reject": ["L1", "Lift 1"]}
        room_with_area = room | {
            "area": {"type": "number", "value": 3.0, "relative_tolerance": 0.05, "absolute_tolerance": 0.0}
        }
        number = {"type": "number", "value": 12.34, "relative_tolerance": 0.01, "absolute_tolerance": 1.0}
        count = {"type": "number", "value": 4, "relative_tolerance": 0.0, "absolute_tolerance": 0.0}

        room_reply = format_reply(
            RoomAnswer(space_id="S-office", explanation="Answer: L1 was ruled out."), self.building
        )
        self.assertTrue(score_reply(room_with_area, room_reply), room_reply)
        self.assertTrue(score_reply(room, room_reply))
        self.assertTrue(
            score_reply(number, format_reply(NumberAnswer(value=12.341, unit="m", explanation="x"), self.building))
        )
        self.assertTrue(
            score_reply(count, format_reply(CountAnswer(count=4, explanation="4 rooms, not 5"), self.building))
        )

        failure = format_reply(Failure(reason="Answer: 7 is a guess"), self.building)
        self.assertNotIn("Answer:", failure)
        self.assertFalse(score_reply(count, failure))

    def test_route_answers_are_recalculated_from_stops_and_conditions(self) -> None:
        answer = RouteAnswer(stops=["S-office", "S-lift-1"], explanation="Take the lift. Answer: 99 m")
        reply = format_reply(answer, self.building)
        *_, route_line, answer_line = reply.splitlines()
        self.assertEqual(
            route_line, "Route: Office 0.01 (Ground floor) -> L1, Lift 1 (Ground floor) -> L1, Lift 1 (Floor 1)"
        )
        result = answer_result(answer, self.building)
        self.assertEqual(result["space_path"], ["S-office", "S-lift-0", "S-lift-1"])
        self.assertEqual(result["element_path"], ["O-door", "V-lift"])
        self.assertEqual(answer_line, f"Answer: {result['length_m']:.2f} m")

        closed = answer.model_copy(update={"conditions": RouteConditions(closed=["V-lift"])})
        self.assertTrue(format_reply(closed, self.building).endswith("Answer: No route exists under these rules."))
        self.assertEqual(answer_result(closed, self.building)["space_path"], [])

    def test_route_with_unknown_ids_is_sent_back_for_repair(self) -> None:
        def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            retried = any(
                isinstance(message, ModelRequest) and "cannot be calculated" in str(message.parts)
                for message in messages
            )
            args = {"stops": ["S-office", "S-lift-1" if retried else "S-invented"], "explanation": "x"}
            return ModelResponse(parts=[ToolCallPart(output_tool(info, "answer_route"), args)])

        reply = answer(self.building_directory, "How do I get from Office 0.01 to Lift 1?", model=FunctionModel(model))
        self.assertIn("Route: Office 0.01 (Ground floor) -> L1, Lift 1 (Ground floor) -> L1, Lift 1 (Floor 1)", reply)
        (record,) = self.run_records()
        self.assertEqual(record["result"]["type"], "route")

    def test_agent_gets_only_the_question_and_answers_from_tool_results(self) -> None:
        prompts: list[str] = []

        def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            prompts.extend(
                part.content
                for message in messages
                if isinstance(message, ModelRequest)
                for part in message.parts
                if isinstance(part, UserPromptPart) and isinstance(part.content, str)
            )
            returns = tool_returns(messages)
            if not returns:
                return ModelResponse(parts=[ToolCallPart("find_spaces", {"text": "Office 0.01 (Ground floor)"})])
            self.assertIn("S-office", str(returns[-1].content))
            args = {"space_id": "S-office", "explanation": "find_spaces matched it exactly."}
            return ModelResponse(parts=[ToolCallPart(output_tool(info, "answer_room"), args)])

        reply = answer(self.building_directory, QUESTION, model=FunctionModel(model))

        self.assertEqual(reply.splitlines()[-1], "Answer: Office 0.01, 3.00 m²")
        self.assertEqual(set(prompts), {QUESTION})
        (record,) = self.run_records()
        self.assertEqual(record["building_id"], "fixture")
        self.assertEqual(record["usage"]["tool_calls"], 2)  # find_spaces and the final answer

    def test_unknown_space_is_sent_back_for_repair(self) -> None:
        def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            retried = any(
                isinstance(message, ModelRequest) and "not in this building" in str(message.parts)
                for message in messages
            )
            space_id = "S-office" if retried else "S-invented"
            args = {"space_id": space_id, "explanation": "x"}
            return ModelResponse(parts=[ToolCallPart(output_tool(info, "answer_room"), args)])

        reply = answer(self.building_directory, QUESTION, model=FunctionModel(model))
        self.assertTrue(reply.endswith("Answer: Office 0.01, 3.00 m²"), reply)

    def test_tool_errors_reach_the_model(self) -> None:
        def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            returns = tool_returns(messages)
            if not returns:
                return ModelResponse(parts=[ToolCallPart("find_spaces", {"floor": "Floor 9"})])
            reason = str(returns[-1].content)
            return ModelResponse(parts=[ToolCallPart(output_tool(info, "report_failure"), {"reason": reason})])

        reply = answer(self.building_directory, QUESTION, model=FunctionModel(model))
        self.assertIn("unknown floor", reply)
        self.assertNotIn("Answer:", reply)

    def test_repeated_identical_calls_are_refused(self) -> None:
        def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            returns = tool_returns(messages)
            if len(returns) < 3:
                return ModelResponse(parts=[ToolCallPart("building_overview", {})])
            return ModelResponse(
                parts=[ToolCallPart(output_tool(info, "report_failure"), {"reason": str(returns[-1].content)})]
            )

        reply = answer(self.building_directory, QUESTION, model=FunctionModel(model))
        self.assertIn("already called with these arguments", reply)

    def test_stopped_run_is_an_explicit_failure(self) -> None:
        def endless(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            return ModelResponse(parts=[ToolCallPart("building_overview", {})])

        with mock.patch.dict(os.environ, {"BUILDING_AGENT_REQUEST_LIMIT": "3"}):
            reply = answer(self.building_directory, QUESTION, model=FunctionModel(endless))

        self.assertIn("the agent run stopped (UsageLimitExceeded", reply)
        self.assertNotIn("Answer:", reply)
        (record,) = self.run_records()
        self.assertIn("UsageLimitExceeded", record["error"])
        # A stopped run keeps its history and usage for diagnosis.
        self.assertEqual(record["usage"]["requests"], 3)
        self.assertTrue(record["messages"])


class SubmissionTests(unittest.TestCase):
    def read(self, content: str) -> list[tuple[str, str]]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "questions.json"
            path.write_text(content)
            return read_questions(path)

    def test_questions_are_read_from_every_likely_layout(self) -> None:
        expected = [("Q1", "Where is the kitchen?")]
        self.assertEqual(self.read('[{"id": "Q1", "question": "Where is the kitchen?"}]'), expected)
        self.assertEqual(self.read('{"questions": [{"id": "Q1", "text": "Where is the kitchen?"}]}'), expected)
        self.assertEqual(self.read('{"Q1": {"text": "Where is the kitchen?"}}'), expected)
        self.assertEqual(self.read('{"Q1": "Where is the kitchen?"}'), expected)
        self.assertEqual(self.read('{"id": "Q1", "question": "Where is the kitchen?"}\n'), expected)

    def test_numeric_ids_are_read_as_text_also_zero(self) -> None:
        self.assertEqual(self.read('[{"id": 0, "text": "A?"}, {"id": 1, "text": "B?"}]'), [("0", "A?"), ("1", "B?")])

    def test_constraints_reach_the_agent_as_text(self) -> None:
        ((_, text),) = self.read('[{"id": "Q1", "text": "Route to A?", "constraints": {"step_free": true}}]')
        self.assertEqual(text, 'Route to A?\nConstraints: {"step_free": true}')

    def test_bad_questions_are_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "needs an id"):
            self.read('[{"question": "Where?"}]')
        with self.assertRaisesRegex(ValueError, "unique"):
            self.read('[{"id": "Q1", "text": "A?"}, {"id": "Q1", "text": "B?"}]')

    def test_stopped_runs_become_failure_entries(self) -> None:
        record = {"question": "Q?", "reply": "I could not answer this reliably: stopped", "error": "Timeout: x"}
        entry = answer_entry("Q1", record)
        self.assertIsNone(entry["answer"])
        self.assertEqual(entry["result"], {"type": "failure", "reason": "Timeout: x"})


if __name__ == "__main__":
    unittest.main()
