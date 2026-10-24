"""Official evaluator entry point. Inference reads only the supplied building."""

import json
import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from agent.budget import Budget
from core.building import Building, load_building
from starter_agent.building_map import MapError

from .serialize import serialize
from .templates import parse_question

LOGGER = logging.getLogger(__name__)
PROMPT_VERSION = "templates-v1"
_BUDGET: Budget | None = None


@dataclass
class Prediction:
    reply: str
    kind: str | None = None
    inputs: dict = field(default_factory=dict)
    result: dict = field(default_factory=dict)
    error: str | None = None
    method: str = "template"
    tokens: dict[str, int] = field(default_factory=dict)
    cost: float = 0.0
    model: str | None = None
    tool_calls: int = 0
    constraint_overrides: dict = field(default_factory=dict)


@lru_cache(maxsize=64)
def _cached_building(path: str, content: str) -> Building:
    return load_building(json.loads(content))


def load_base(directory: Path) -> Building:
    path = directory / "building.json" if directory.is_dir() else directory
    content = path.read_text(encoding="utf-8")
    return load_building(_cached_building(str(path.resolve()), content))


def unanswered(reason: str) -> Prediction:
    return Prediction(
        reply=f"I could not answer this question: {reason}.",
        error=reason,
        method="unanswered",
    )


def llm_prediction(building: Building, question: str, *, constraints: dict | None = None) -> Prediction:
    budget = _BUDGET
    if budget is None:
        return unanswered("An approved benchmark budget is required. Configure an explicit max-cost allocation")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return unanswered("ANTHROPIC_API_KEY is not configured")
    from .llm_fallback import interpret

    if constraints is not None:
        return interpret(building, question, (budget, None), constraints=constraints)
    return interpret(building, question, (budget, None))


def configure_budget(dollars: float | None) -> None:
    """Only a caller with a written allocation may enable paid interpretation."""
    global _BUDGET
    _BUDGET = Budget(dollars) if dollars is not None else None


def validate_mode(mode: str) -> None:
    if mode not in {"llm", "template"}:
        raise ValueError("Mode must be 'llm' or 'template'. The 'hybrid' mode was removed")


def predict(directory: Path, question: str, mode: str = "llm", *, constraints: dict | None = None) -> Prediction:
    """Keep failures local to a question and retain computed data for evaluation."""
    try:
        validate_mode(mode)
        building = load_base(directory)
        if mode == "llm":
            return llm_prediction(building, question, constraints=constraints)
        try:
            kind, inputs = parse_question(building, question)
        except MapError as error:
            return unanswered(str(error))
        from core.spatial import solve

        result = solve(building, kind, inputs)
        return Prediction(reply=serialize(building, kind, result), kind=kind, inputs=inputs, result=result)
    except Exception as error:
        LOGGER.debug("Question failed", exc_info=True)
        reason = f"{type(error).__name__}: {error}"
        return Prediction(reply=f"I could not compute this answer: {reason}", error=reason, method="error")


def answer(building_directory: Path, question_text: str) -> str:
    return predict(building_directory, question_text).reply
