"""Official evaluator entry point. Inference reads only the supplied building."""

import json
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from core.building import Building, load_building
from starter_agent.building_map import MapError
from agent.budget import Budget

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
        reply=f"I could not determine a unique answer: {reason}. Please name the exact room.",
        error=reason,
        method="unanswered",
    )


def fallback(building: Building, question: str, reason: str) -> Prediction:
    import os

    if _BUDGET is None or not os.environ.get("ANTHROPIC_API_KEY"):
        return unanswered(reason)
    if reason.startswith("Ambiguous"):
        return unanswered(reason)
    from .llm_fallback import interpret

    return interpret(building, question, (_BUDGET, None))


def configure_budget(dollars: float | None) -> None:
    """Only a caller with a written allocation may enable paid interpretation."""
    global _BUDGET
    _BUDGET = Budget(dollars) if dollars is not None else None


def predict(directory: Path, question: str, mode: str = "hybrid") -> Prediction:
    """Keep failures local to a question and retain computed data for evaluation."""
    try:
        building = load_base(directory)
        if mode == "llm":
            return fallback(building, question, "The language model fallback is not available")
        try:
            kind, inputs = parse_question(building, question)
        except MapError as error:
            return fallback(building, question, str(error)) if mode == "hybrid" else unanswered(str(error))
        from core.spatial import solve

        result = solve(building, kind, inputs)
        return Prediction(reply=serialize(building, kind, result), kind=kind, inputs=inputs, result=result)
    except Exception as error:
        LOGGER.debug("Question failed", exc_info=True)
        reason = f"{type(error).__name__}: {error}"
        return Prediction(reply=f"I could not compute this answer: {reason}", error=reason, method="error")


def answer(building_directory: Path, question_text: str) -> str:
    return predict(building_directory, question_text).reply
