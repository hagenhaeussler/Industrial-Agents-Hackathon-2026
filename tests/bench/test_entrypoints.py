import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from agent import config as agent_config
from agent.runtime import LoopOptions
from bench import agent, llm_fallback, run as runner, run_benchmark as sunday


BUILDING = Path("data/dev/proc-factory-dev-003")
TEMPLATE_QUESTION = "How many toilet items are on the floor 2?"


@pytest.fixture(autouse=True)
def no_paid_calls(monkeypatch):
    monkeypatch.setattr(agent, "_BUDGET", None)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    def reject_client(*args, **kwargs):
        pytest.fail("Entrypoint tests must not create a provider client")

    monkeypatch.setattr(llm_fallback.anthropic, "Anthropic", reject_client)


@pytest.mark.parametrize("entrypoint", [agent.predict, agent.answer])
@pytest.mark.parametrize("question", [TEMPLATE_QUESTION, "Where is the office?", "Investigate this unfamiliar request."])
def test_default_entrypoints_send_original_question_to_llm(monkeypatch, entrypoint, question):
    agent.configure_budget(1)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "offline-test-credential")
    received = []

    def interpret(building, text, settings):
        received.append((building.content_hash, text, settings))
        return agent.Prediction("Answer: 7", method="llm")

    monkeypatch.setattr(llm_fallback, "interpret", interpret)
    monkeypatch.setattr(agent, "parse_question", lambda *_: pytest.fail("Default inference called the template parser"))
    entrypoint(BUILDING, question)
    assert received == [(agent.load_base(BUILDING).content_hash, question, (agent._BUDGET, None))]


@pytest.mark.parametrize("allocation,credential,reason", [
    (None, None, "approved benchmark budget"),
    (None, "offline-test-credential", "approved benchmark budget"),
    (1, None, "ANTHROPIC_API_KEY"),
])
def test_missing_allocation_or_credentials_does_not_use_templates(monkeypatch, allocation, credential, reason):
    agent.configure_budget(allocation)
    if credential:
        monkeypatch.setenv("ANTHROPIC_API_KEY", credential)
    monkeypatch.setattr(llm_fallback, "interpret", lambda *_: pytest.fail("Unavailable inference called the interpreter"))
    monkeypatch.setattr(agent, "parse_question", lambda *_: pytest.fail("Unavailable inference called the template parser"))
    prediction = agent.predict(Path("data/dev/osm-way22744230"), TEMPLATE_QUESTION)
    assert (prediction.method, reason in prediction.error, "Answer:" in prediction.reply) == ("unanswered", True, False)


@pytest.mark.parametrize("allocation", [0, -1, float("inf"), float("nan")])
def test_invalid_allocations_are_rejected(allocation):
    with pytest.raises(ValueError, match="positive finite"):
        agent.configure_budget(allocation)


def test_template_mode_is_an_offline_baseline(monkeypatch):
    monkeypatch.setattr(llm_fallback, "interpret", lambda *_: pytest.fail("Template mode called the interpreter"))
    prediction = agent.predict(Path("data/dev/osm-way22744230"), TEMPLATE_QUESTION, mode="template")
    assert (prediction.reply, prediction.method, prediction.cost) == ("Answer: 3", "template", 0)


@pytest.mark.parametrize("mode", ["hybrid", "typo"])
def test_unknown_mode_is_an_explicit_local_error(mode):
    prediction = agent.predict(BUILDING, "Where is the office?", mode=mode)
    assert (prediction.method, "Mode must be" in prediction.error, "Answer:" in prediction.reply) == ("error", True, False)


def test_llm_failure_does_not_try_templates(monkeypatch):
    agent.configure_budget(1)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "offline-test-credential")

    def fail(*args):
        raise ValueError("Interpretation failed")

    monkeypatch.setattr(llm_fallback, "interpret", fail)
    monkeypatch.setattr(agent, "parse_question", lambda *_: pytest.fail("Failed inference called the template parser"))
    assert agent.predict(BUILDING, TEMPLATE_QUESTION).error == "ValueError: Interpretation failed"


def test_interpreter_usage_and_unanswered_result_are_preserved(monkeypatch):
    agent.configure_budget(1)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "offline-test-credential")
    expected = agent.Prediction("Please name the exact office.", error="Ambiguous", method="unanswered",
                                tokens={"input_tokens": 123}, cost=0.001, model="claude-sonnet-5-5", tool_calls=2)
    monkeypatch.setattr(llm_fallback, "interpret", lambda *_: expected)
    assert agent.predict(BUILDING, "Where is the office?") is expected


def test_threads_receive_one_shared_budget(monkeypatch):
    agent.configure_budget(1)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "offline-test-credential")
    received = []

    def interpret(building, question, settings):
        received.append(settings[0])
        return agent.unanswered("Offline test")

    monkeypatch.setattr(llm_fallback, "interpret", interpret)
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(lambda text: agent.predict(BUILDING, text), ["one", "two", "three"]))
    assert received == [agent._BUDGET] * 3


def test_unbudgeted_prediction_batch_clears_previous_allocation(tmp_path, monkeypatch):
    agent.configure_budget(1)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "offline-test-credential")
    monkeypatch.setattr(llm_fallback, "interpret", lambda *_: pytest.fail("Batch reused an earlier allocation"))
    monkeypatch.setattr(runner, "OUTPUT", tmp_path)
    rows = runner.predictions(runner.RunConfig(BUILDING.parent, "unbudgeted"),
                              [(BUILDING, {"id": "offline", "question": TEMPLATE_QUESTION})], {})
    assert (rows[0]["method"], agent._BUDGET) == ("unanswered", None)


def test_resumed_spend_reduces_shared_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "OUTPUT", tmp_path)
    checkpoint = tmp_path / "resume" / "checkpoint.jsonl"
    checkpoint.parent.mkdir()
    checkpoint.write_text(json.dumps({"key": "previous-context", "cost": 0.3}) + "\n")
    runner.predictions(runner.RunConfig(BUILDING.parent, "resume", max_cost=1), [], {})
    assert agent._BUDGET.limit == pytest.approx(0.7)


@pytest.fixture
def configured_metadata(monkeypatch):
    options = replace(LoopOptions(), max_steps=7, max_tool_calls=17, max_seconds=21)
    monkeypatch.setattr(agent_config, "configured_options", lambda: options)
    return options


def test_llm_metadata_uses_common_configuration_without_an_allocation(configured_metadata):
    from agent.prompts import PROMPT_VERSION as AGENT_PROMPT_VERSION

    context = runner.execution_context("llm")
    assert context == {
        "mode": "llm", "model": configured_metadata.model, "agent_options": asdict(configured_metadata),
        "prompt_version": AGENT_PROMPT_VERSION + "+" + llm_fallback.PROMPT_VERSION,
        "prompt_versions": {"agent": AGENT_PROMPT_VERSION, "submission": llm_fallback.PROMPT_VERSION},
    }


def test_template_metadata_does_not_require_model_configuration(monkeypatch):
    monkeypatch.setattr(agent_config, "configured_options", lambda: pytest.fail("Template baseline read model configuration"))
    assert runner.execution_context("template") == {
        "mode": "template", "model": None, "agent_options": None,
        "prompt_version": agent.PROMPT_VERSION, "prompt_versions": {"template": agent.PROMPT_VERSION},
    }


@pytest.mark.parametrize("module,arguments", [
    (runner, ["bench.run", "data/dev", "--name", "offline"]),
    (sunday, ["bench.run_benchmark", "building", "questions.json", "answers.json"]),
])
def test_command_line_defaults_to_llm(monkeypatch, module, arguments):
    import sys

    received = []
    monkeypatch.setattr(sys, "argv", arguments)
    monkeypatch.setattr(module, "run", lambda options: received.append(options.mode))
    module.main()
    assert received == ["llm"]


@pytest.mark.parametrize("field,value", [("model", "claude-haiku-5-5"), ("max_steps", 3),
                                        ("max_tool_calls", 4), ("max_seconds", 12), ("max_tokens", 100)])
def test_common_configuration_changes_invalidate_checkpoints(monkeypatch, configured_metadata, field, value):
    question = {"id": "one", "question": "Original question"}
    before = runner.checkpoint_key(question, "building", runner.execution_context("llm"))
    monkeypatch.setattr(agent_config, "configured_options", lambda: replace(configured_metadata, **{field: value}))
    assert runner.checkpoint_key(question, "building", runner.execution_context("llm")) != before


@pytest.mark.parametrize("module", ["agent.prompts", "bench.llm_fallback"])
def test_prompt_version_changes_invalidate_checkpoints(monkeypatch, configured_metadata, module):
    import importlib

    question = {"id": "one", "question": "Original question"}
    before = runner.checkpoint_key(question, "building", runner.execution_context("llm"))
    monkeypatch.setattr(importlib.import_module(module), "PROMPT_VERSION", "changed-version")
    assert runner.checkpoint_key(question, "building", runner.execution_context("llm")) != before


@pytest.mark.parametrize("relative", ["server/tools.py", "agent/skills/entities.md"])
def test_shared_tools_and_prompt_recipes_change_source_hash(tmp_path, monkeypatch, relative):
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text("before")
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    before = runner.source_hash()
    path.write_text("after")
    assert runner.source_hash() != before


@pytest.mark.parametrize("mode", ["llm", "template"])
def test_sunday_mode_and_metadata_survive_checkpoint_resume(tmp_path, monkeypatch, configured_metadata, mode):
    questions = tmp_path / "questions.json"
    questions.write_text(json.dumps([{"id": "one", "text": "Original question"}]))
    received = []

    def infer(task, timeout):
        received.append(task)
        return asdict(agent.Prediction("Answer: 2", kind="count", result={"value": 2}, method=mode))

    monkeypatch.setattr(sunday, "isolated_infer", infer)
    options = sunday.Options(BUILDING, questions, tmp_path / "answers.json", mode=mode)
    before = sunday.run(options)
    after = sunday.run(options)
    assert (before, [task.mode for task in received]) == (after, [mode])


def test_sunday_configuration_change_recomputes_question(tmp_path, monkeypatch, configured_metadata):
    questions = tmp_path / "questions.json"
    questions.write_text(json.dumps([{"id": "one", "text": "Original question"}]))
    received = []

    def infer(task, timeout):
        received.append(task)
        return asdict(agent.unanswered("Offline test"))

    monkeypatch.setattr(sunday, "isolated_infer", infer)
    options = sunday.Options(BUILDING, questions, tmp_path / "answers.json")
    sunday.run(options)
    monkeypatch.setattr(agent_config, "configured_options", lambda: replace(configured_metadata, max_steps=8))
    sunday.run(options)
    assert len(received) == 2


def test_sunday_explicit_template_mode_applies_and_records_constraints():
    prediction = sunday.constrained_prediction(sunday.Task(
        BUILDING, "How do I get from Hall access 0.19 (Ground floor) to Office 1.01 (Floor 1)?",
        {"min_door_width_m": 100}, mode="template",
    ))
    assert (prediction.result["route"]["reachable"], prediction.constraint_overrides) == (
        False, {"min_door_width_m": {"parsed": 0.0, "supplied": 100}},
    ), prediction.reply


def test_sunday_overrides_keep_other_constraints_from_the_shared_tool(monkeypatch):
    computed = agent.predict(BUILDING,
        "How do I get from Hall access 0.19 (Ground floor) to Office 1.01 (Floor 1)?", mode="template")
    route = computed.result["route"]
    computed = replace(computed, result={"route": {**route, "constraints": {
        **route["constraints"], "step_free": True, "min_door_width_m": 2,
    }}})
    monkeypatch.setattr(sunday, "predict", lambda *_: computed)
    prediction = sunday.constrained_prediction(sunday.Task(BUILDING, "Original question", {"min_door_width_m": 100}, mode="template"))
    assert (prediction.result["route"]["constraints"]["step_free"], prediction.constraint_overrides) == (
        True, {"min_door_width_m": {"parsed": 2, "supplied": 100}},
    )


@pytest.mark.parametrize("constraints", [{"min_door_width_m": -1}, {"step_free": "yes"}, {"unknown": 1}, {"closed": ["missing"]}])
def test_sunday_invalid_constraints_keep_interpretation_usage(monkeypatch, constraints):
    computed = agent.predict(BUILDING,
        "How do I get from Hall access 0.19 (Ground floor) to Office 1.01 (Floor 1)?", mode="template")
    computed = replace(computed, method="llm", tokens={"input_tokens": 123}, cost=0.01,
                       model="claude-sonnet-5-5", tool_calls=4)
    monkeypatch.setattr(sunday, "predict", lambda *_: computed)
    prediction = sunday.constrained_prediction(sunday.Task(BUILDING, "Original question", constraints, mode="template"))
    assert (bool(prediction.error), prediction.result, "Answer:" in prediction.reply,
            prediction.tokens, prediction.cost, prediction.model, prediction.tool_calls) == (
        True, {}, False, computed.tokens, computed.cost, computed.model, computed.tool_calls,
    )


def test_sunday_passes_constraints_into_inference_before_calculation(monkeypatch):
    received = []
    expected = agent.Prediction('Answer: no route', kind='route', result={'route': {'reachable': False}}, method='llm')
    def predict(directory, text, mode, *, constraints):
        received.append((directory, text, mode, constraints))
        return expected
    monkeypatch.setattr(sunday, 'predict', predict)
    monkeypatch.setattr(sunday, 'apply_constraints', lambda *_: pytest.fail('Product inference must not have another calculation path'))
    constraints = {'step_free': True, 'closed': ['stairs']}
    result = sunday.constrained_prediction(sunday.Task(BUILDING, 'Original question', constraints))
    assert result is expected
    assert received == [(BUILDING, 'Original question', 'llm', constraints)]
