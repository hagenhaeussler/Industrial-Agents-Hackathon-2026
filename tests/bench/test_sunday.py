import json
from dataclasses import asdict
from pathlib import Path

import pytest

from bench.agent import Prediction
from bench.run_benchmark import Task, answer_record, constrained_prediction, isolated_infer, load_input, make_questions


@pytest.mark.parametrize("content", [
    '[{"id":"q1","text":"Where is the lectern?"}]',
    '{"questions":[{"id":"q1","question":"Where is the lectern?"}]}',
    '{"id":"q1","text":"Where is the lectern?"}\n',
    '{"id":"q1","text":"Where is the lectern?"}\n{"id":"q2","text":"Where is the desk?"}',
])
def test_supported_json_input_shapes(tmp_path, content):
    path = tmp_path / "questions.json"
    path.write_text(content)
    assert load_input(path)[0]["question"] == "Where is the lectern?"


def test_kit_csv_input(tmp_path):
    path = tmp_path / "questions.csv"
    path.write_text('question_id,building_id,kind,question\nq1,building,locate,Where is the lectern?\n')
    assert load_input(path)[0]["id"] == "q1"


def test_input_discards_answer_keys_and_structured_inputs(tmp_path):
    path = tmp_path / "questions.json"
    path.write_text('[{"id":"q1","text":"Where is the lectern?","answer":{"secret":42},"inputs":{"asset":"gold"}}]')
    assert not {"answer", "inputs"} & load_input(path)[0].keys()


def test_duplicate_question_ids_are_rejected(tmp_path):
    path = tmp_path / "questions.json"
    path.write_text('[{"id":"q1","text":"one"},{"id":"q1","text":"two"}]')
    with pytest.raises(ValueError, match="duplicate"):
        load_input(path)


def test_converter_removes_gold_fields(tmp_path):
    output = tmp_path / "questions.json"
    make_questions(Path("data/dev/proc-factory-dev-003"), output)
    assert all(set(question) == {"id", "text", "kind"} for question in json.loads(output.read_text())["questions"])


def test_unreachable_route_schema_is_explicit():
    prediction = asdict(Prediction("Answer: no route", kind="route", result={"route": {"reachable": False}}))
    question = {"id": "q1", "kind": None, "constraints": None}
    assert answer_record(question, prediction)["route"] == {"reachable": False, "space_path": [], "node_path": [], "element_path": [], "length_m": None}


def test_explicit_route_constraints_override_the_text():
    task = Task(Path("data/dev/proc-factory-dev-003"),
                "How do I get from Hall access 0.19 (Ground floor) to Office 1.01 (Floor 1)?", {"min_door_width_m": 100})
    prediction = constrained_prediction(task)
    assert prediction.result["route"]["reachable"] is False, prediction.reply


def test_timeout_terminates_a_question_worker():
    result = isolated_infer(Task(Path("data/dev/proc-factory-dev-003"), "Where is the lectern?"), 0.001)
    assert result["error"].startswith("Timeout")


def test_timeout_retains_the_allocated_budget_when_usage_is_unknown():
    result = isolated_infer(Task(Path("data/dev/proc-factory-dev-003"), "Where is the lectern?", max_cost=1), 0.001)
    assert result["cost"] == 1


def test_spatial_constraints_are_reported_instead_of_ignored():
    task = Task(Path("data/dev/proc-factory-dev-003"),
                "Which is the largest kitchen on the floor 1, and how big is it in m²?", {"step_free": True})
    prediction = constrained_prediction(task)
    assert prediction.error == "Explicit constraints require a route or tour question."


def test_rejected_constraints_keep_paid_interpretation_cost_for_checkpoint_resume(monkeypatch):
    from bench import run_benchmark

    computed = Prediction("Answer: 3", kind="count", result={"value": 3}, method="llm",
                          tokens={"input_tokens": 123, "output_tokens": 45}, cost=0.0123,
                          model="claude-haiku-5-5", tool_calls=2)
    monkeypatch.setattr(run_benchmark, "predict", lambda *_: computed)
    prediction = constrained_prediction(Task(Path("unused"), "Count the items", {"step_free": True}))
    assert prediction.error == "Explicit constraints require a route or tour question."
    assert "Answer:" not in prediction.reply
    assert prediction.result == {}
    assert prediction.cost == computed.cost
    assert prediction.tokens == computed.tokens
    assert prediction.model == computed.model
    assert prediction.method == computed.method
    assert prediction.tool_calls == computed.tool_calls
