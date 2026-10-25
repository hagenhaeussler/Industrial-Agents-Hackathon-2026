"""Benchmark entry point: `answer(building_directory, question_text)` runs the agent on one question.

The agent sees the question text and the tools of one building. Nothing else from the dataset reaches it.
"""

import json
import os
import time
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha1
from pathlib import Path
from typing import get_args
from uuid import uuid4

from dotenv import load_dotenv
from pydantic_ai import Agent, ModelRetry, RunContext, ToolFailed, ToolOutput, capture_run_messages
from pydantic_ai.mcp import CallToolFunc, MCPToolset, ProcessToolCallback, ToolResult
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter, ModelResponse, ToolCallPart
from pydantic_ai.models import Model
from pydantic_ai.models.anthropic import AnthropicModelSettings
from pydantic_ai.profiles.anthropic import AnthropicEffort
from pydantic_ai.usage import UsageLimits

from building_agent.answers import (
    Answer,
    CountAnswer,
    Failure,
    NumberAnswer,
    RoomAnswer,
    RouteAnswer,
    answer_result,
    answer_route,
    format_reply,
)
from building_db.store import connect, import_building
from building_tools.building import Building, ToolInputError, load
from building_tools.server import create_server

REPO = Path(__file__).resolve().parents[1]
INSTRUCTIONS = (Path(__file__).with_name("instructions.md")).read_text()
PROMPT_VERSION = sha1(INSTRUCTIONS.encode()).hexdigest()[:8]

load_dotenv(REPO / ".env")
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")


@dataclass(frozen=True)
class Settings:
    """Run settings. Limits stop a run with an explicit failure, never with a guess."""

    model: str
    effort: AnthropicEffort
    cost_limit_usd: Decimal
    request_limit: int
    database: Path
    runs_directory: Path

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ.get
        return cls(
            model=env("BUILDING_AGENT_MODEL", "anthropic:claude-sonnet-5-5"),
            effort=effort(env("BUILDING_AGENT_EFFORT", "medium")),
            cost_limit_usd=Decimal(env("BUILDING_AGENT_COST_LIMIT_USD", "1.00")),
            request_limit=int(env("BUILDING_AGENT_REQUEST_LIMIT", "60")),
            database=Path(env("BUILDING_DATABASE", str(REPO / "buildings.sqlite3"))),
            runs_directory=Path(env("BUILDING_AGENT_RUNS", str(REPO / "agent_output" / "runs"))),
        )


def effort(value: str) -> AnthropicEffort:
    for level in get_args(AnthropicEffort):
        if level == value:
            return level
    raise ValueError(f"BUILDING_AGENT_EFFORT must be one of {get_args(AnthropicEffort)}, not {value!r}")


def build_agent(building: Building, model: Model | str, effort: AnthropicEffort) -> Agent[None, Answer]:
    """An agent whose only tools are the MCP tools of `building`."""
    agent = Agent(
        model,
        instructions=INSTRUCTIONS,
        output_type=[
            ToolOutput(NumberAnswer, name="answer_number"),
            ToolOutput(CountAnswer, name="answer_count"),
            ToolOutput(RoomAnswer, name="answer_room"),
            ToolOutput(RouteAnswer, name="answer_route"),
            ToolOutput(Failure, name="report_failure"),
        ],
        toolsets=[MCPToolset(create_server(building), tool_error_behavior="failed", process_tool_call=repeat_guard())],
        # Instructions and tool definitions are the same for every question, so parallel runs read them from the
        # cache. The automatic breakpoint caches the growing history within one run.
        model_settings=AnthropicModelSettings(
            anthropic_effort=effort,
            anthropic_cache=True,
            anthropic_cache_instructions=True,
            anthropic_cache_tool_definitions=True,
        ),
        name="building-agent",
    )

    @agent.output_validator
    def known_ids(answer: Answer) -> Answer:
        if isinstance(answer, RoomAnswer) and answer.space_id not in building.space_by_id:
            raise ModelRetry(f"space_id {answer.space_id!r} is not in this building; use an id from find_spaces")
        if isinstance(answer, RouteAnswer):
            try:
                answer_route(answer, building)
            except ToolInputError as error:
                raise ModelRetry(f"this route cannot be calculated: {error}") from error
        return answer

    return agent


REPEAT_LIMIT = 2


def repeat_guard() -> ProcessToolCallback:
    """Refuse a tool call that repeats an earlier one more than REPEAT_LIMIT times: its result cannot change.

    Without it the model can loop on the same call until the request limit stops the run.
    """
    calls: Counter[str] = Counter()

    async def guard(_: RunContext, call_tool: CallToolFunc, name: str, args: dict) -> ToolResult:
        key = name + json.dumps(args, sort_keys=True)
        calls[key] += 1
        if calls[key] > REPEAT_LIMIT:
            raise ToolFailed(
                f"{name} was already called with these arguments and its result does not change. Use the earlier "
                "result. If the tools cannot answer the question, call report_failure."
            )
        return await call_tool(name, args)

    return guard


def load_from_directory(building_directory: Path, database: Path) -> Building:
    """Import the directory's building.json if needed and load it. Raises RuntimeError if the import fails."""
    connection = connect(database)
    try:
        result = import_building(connection, building_directory / "building.json")
        if result.building_id is None or result.status in ("failed", "conflict"):
            raise RuntimeError(f"building import {result.status}: {result.message}")
        return load(connection, result.building_id)
    finally:
        connection.close()


def answer(building_directory: Path, question_text: str, model: Model | str | None = None) -> str:
    """The agent's full reply to one question. A stopped or failed run returns an explicit failure reply."""
    return run_question(building_directory, question_text, model)["reply"]


def run_question(building_directory: Path, question_text: str, model: Model | str | None = None) -> dict:
    """Run the agent on one question and return the saved run record, including `reply` and `usage`."""
    settings = Settings.from_env()
    started = time.monotonic()
    record: dict = {"question": question_text, "model": str(model or settings.model), "prompt": PROMPT_VERSION}
    messages: list[ModelMessage] = []
    try:
        building = load_from_directory(Path(building_directory), settings.database)
        record["building_id"] = building.id
        agent = build_agent(building, model or settings.model, settings.effort)
        with capture_run_messages() as messages:
            result = agent.run_sync(
                question_text,
                usage_limits=UsageLimits(request_limit=settings.request_limit, cost_limit=settings.cost_limit_usd),
            )
        reply = format_reply(result.output, building)
        record["output"] = result.output.model_dump(mode="json")
        record["result"] = answer_result(result.output, building)
    except Exception as error:  # noqa: BLE001 - the run boundary: every failure becomes an explicit reply
        reply = f"I could not answer this reliably: the agent run stopped ({type(error).__name__}: {error})"
        record["error"] = f"{type(error).__name__}: {error}"
    # Usage comes from the captured messages, so stopped runs also report what they cost.
    record |= {
        "reply": reply,
        "seconds": round(time.monotonic() - started, 2),
        "usage": usage_of(messages),
        "messages": json.loads(ModelMessagesTypeAdapter.dump_json(messages)),
    }
    save_record(settings.runs_directory, record)
    return record


def usage_of(messages: list[ModelMessage]) -> dict:
    """Requests, tool calls, tokens and cost of one run."""
    responses = [message for message in messages if isinstance(message, ModelResponse)]
    try:
        cost: str | None = str(sum((response.cost().total_price for response in responses), Decimal(0)))
    except LookupError:  # no price data, for example for test models
        cost = None
    return {
        "requests": len(responses),
        "tool_calls": sum(isinstance(part, ToolCallPart) for response in responses for part in response.parts),
        "input_tokens": sum(response.usage.input_tokens for response in responses),
        "cache_write_tokens": sum(response.usage.cache_write_tokens for response in responses),
        "cache_read_tokens": sum(response.usage.cache_read_tokens for response in responses),
        "output_tokens": sum(response.usage.output_tokens for response in responses),
        "cost_usd": cost,
    }


def save_record(directory: Path, record: dict) -> None:
    """Keep each run's question, tool calls, usage and reply, so failures can be inspected."""
    directory.mkdir(parents=True, exist_ok=True)
    # Parallel runs of the same question text can end in the same second, so a random part keeps names unique.
    question = sha1(record["question"].encode()).hexdigest()[:12]
    name = f"{time.strftime('%Y%m%d-%H%M%S')}-{question}-{uuid4().hex[:8]}.json"
    (directory / name).write_text(json.dumps(record, indent=2, ensure_ascii=False))
