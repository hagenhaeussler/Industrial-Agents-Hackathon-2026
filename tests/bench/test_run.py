import json

import pytest

from bench.agent import Prediction
from bench.run import RunConfig, checkpoint_key, load_checkpoint, load_questions, run, score_warmup, select_questions


@pytest.fixture
def context():
    return {"commit": "test", "source_hash": "source", "profile": "kit_1_1_0", "model": None, "prompt_version": "v1", "mode": "template"}


@pytest.mark.parametrize("field", ["commit", "source_hash", "profile", "model", "prompt_version", "mode"])
def test_every_run_setting_invalidates_checkpoint(context, field):
    question = {"id": "q1", "question": "Where is the lectern?"}
    assert checkpoint_key(question, "building", context) != checkpoint_key(question, "building", {**context, field: "changed"})


def test_wording_change_invalidates_checkpoint(context):
    assert checkpoint_key({"id": "q1", "question": "original"}, "building", context) != checkpoint_key({"id": "q1", "question": "new wording"}, "building", context)


def test_building_change_invalidates_checkpoint(context):
    question = {"id": "q1", "question": "Where is the lectern?"}
    assert checkpoint_key(question, "original", context) != checkpoint_key(question, "changed", context)


def test_truncated_checkpoint_tail_is_repaired(tmp_path):
    path = tmp_path / "checkpoint.jsonl"
    path.write_text('{"key":"complete"}\n{"key":')
    load_checkpoint(path)
    assert path.read_text() == '{"key":"complete"}\n'


def test_complete_checkpoint_without_newline_is_safe_to_append(tmp_path):
    path = tmp_path / "checkpoint.jsonl"
    path.write_text('{"key":"complete"}')
    load_checkpoint(path)
    assert path.read_text().endswith("\n")


def test_checkpoint_corruption_before_tail_is_reported(tmp_path):
    path = tmp_path / "checkpoint.jsonl"
    path.write_text('broken\n{"key":"complete"}\n')
    with pytest.raises(json.JSONDecodeError):
        load_checkpoint(path)


def test_resumed_predictions_are_scored_again_without_inference(tmp_path, monkeypatch):
    from bench import run as runner

    directory = tmp_path / "split" / "building"
    directory.mkdir(parents=True)
    (directory / "building.json").write_text('{}')
    question = {"id": "q1", "kind": "count", "question": "How many chairs?", "answer": {"type": "number", "value": 2, "relative_tolerance": 0, "absolute_tolerance": 0}}
    (directory / "questions.jsonl").write_text(json.dumps(question) + "\n")
    monkeypatch.setattr(runner, "OUTPUT", tmp_path / "output")
    monkeypatch.setattr(runner, "predict", lambda *args: Prediction("Answer: 2"))
    config = RunConfig(tmp_path / "split", "resume", mode="template")
    run(config)
    monkeypatch.setattr(runner, "predict", lambda *args: pytest.fail("Resume called inference"))
    assert run(config)["correct"] == 1


def test_unreachable_warmup_does_not_pass_for_a_failed_prediction():
    question = {"kind": "route_step_free", "answer": {"reachable": False}}
    assert not score_warmup(question, {"result": {}, "error": "solver bug", "reply": "No answer"})


@pytest.fixture
def paraphrase_config(tmp_path):
    directory = tmp_path / "split" / "building"
    directory.mkdir(parents=True)
    (directory / "building.json").write_text('{}')
    (directory / "questions_basic.jsonl").write_text(json.dumps({
        "id": "source", "kind": "count", "question": "Original wording",
        "answer": {"count": 2}, "inputs": {"secret": "gold-only"},
    }) + "\n")
    paraphrases = tmp_path / "paraphrases.jsonl"
    paraphrases.write_text(json.dumps({"id": "new", "source_id": "source", "building_id": "building",
                                       "kind": "count", "question": "Count the chairs."}) + "\n")
    return RunConfig(tmp_path / "split", "paraphrases", mode="template", paraphrases=paraphrases)


def test_paraphrase_source_mapping_selects_warmup_scoring(paraphrase_config, tmp_path, monkeypatch):
    from bench import run as runner

    monkeypatch.setattr(runner, "OUTPUT", tmp_path / "output")
    monkeypatch.setattr(runner, "predict", lambda *args: Prediction("Answer: 2", kind="count", result={"value": 2}))
    assert run(paraphrase_config)["correct"] == 1


def test_paraphrase_inference_receives_no_gold_or_source_wording(paraphrase_config, tmp_path, monkeypatch):
    from bench import run as runner

    received = []
    def capture(directory, text, mode):
        received.append((directory.name, text, mode))
        return Prediction("Answer: 2", kind="count", result={"value": 2})

    monkeypatch.setattr(runner, "OUTPUT", tmp_path / "output")
    monkeypatch.setattr(runner, "predict", capture)
    run(paraphrase_config)
    assert received == [("building", "Count the chairs.", "template")]


@pytest.mark.parametrize("change", [{"source_id": "absent"}, {"building_id": "other"}, {"kind": "route"}])
def test_invalid_paraphrase_links_are_rejected(paraphrase_config, change):
    path = paraphrase_config.paraphrases
    row = json.loads(path.read_text())
    path.write_text(json.dumps({**row, **change}) + "\n")
    with pytest.raises(ValueError):
        load_questions(paraphrase_config)


def test_per_kind_selection_keeps_less_common_kinds(tmp_path):
    questions = [(tmp_path, {"id": str(index), "kind": kind}) for index, kind in enumerate(["count"] * 5 + ["locate"] * 3)]
    selected = select_questions(questions, RunConfig(tmp_path, "subset", per_kind=2))
    assert [question["kind"] for _, question in selected] == ["count", "count", "locate", "locate"]
