"""Explicit model/tool loop shared by interactive chat and batch interpretation."""

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
import json
import math
import time
from typing import Protocol

import anthropic

from .budget import BudgetAccount, BudgetExceeded, RequestSize, cost, usage_counts


class MessagesClient(Protocol):
    def create(self, **kwargs: object) -> object: ...


@dataclass(frozen=True)
class LoopOptions:
    model: str = "claude-sonnet-5-5"
    max_steps: int = 24
    max_tool_calls: int = 128
    max_tokens: int = 4096
    max_seconds: float = 90
    request_timeout: float = 30
    max_context_bytes: int = 256_000
    effort: str = "low"

    def __post_init__(self):
        if any(value <= 0 for value in (self.max_steps, self.max_tool_calls, self.max_tokens, self.max_context_bytes)):
            raise ValueError("Agent request, tool and token limits must be positive.")
        if any(not math.isfinite(value) or value <= 0 for value in (self.max_seconds, self.request_timeout)):
            raise ValueError("Agent time limits must be positive and finite.")


@dataclass
class ToolSet:
    definitions: list[dict]
    execute: Callable[[str, dict], dict]
    done: Callable[[], bool] = lambda: False
    cancelled: Callable[[], bool] = lambda: False


@dataclass
class RunRequest:
    system: list[dict]
    messages: list[dict]
    tools: ToolSet
    options: LoopOptions = field(default_factory=LoopOptions)


@dataclass
class RunResult:
    messages: list[dict]
    text: str = ""
    reason: str = "step_limit"
    calls: list[dict] = field(default_factory=list)
    tokens: Counter = field(default_factory=Counter)
    cost: float = 0
    requests: int = 0
    error: str | None = None


def tool_failure(code: str, message: str) -> dict:
    return {"ok": False, "error": {"code": code, "message": message}, "speech": message}


def observation(result: dict) -> dict:
    """Keep model evidence and errors; send geometry only to the application."""
    if "model_result" in result:
        return result["model_result"]
    return result


class AgentLoop:
    def __init__(self, client: MessagesClient, budget: BudgetAccount | None = None):
        self.client = client
        self.budget = budget

    def run(self, request: RunRequest) -> RunResult:
        options = request.options
        result = RunResult(messages=list(request.messages))
        deadline = time.monotonic() + options.max_seconds
        executed: dict[str, tuple[str, dict, dict]] = {}
        for _ in range(options.max_steps):
            if request.tools.cancelled():
                result.reason = "cancelled"
                break
            if request.tools.done():
                result.reason = "submitted"
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                result.reason = "time_limit"
                break
            response = self._request(request, result, remaining)
            if response is None:
                break
            blocks = [block.model_dump(mode="json", exclude_none=True) for block in response.content]
            # A truncated tool block is not an instruction to perform an action.
            if response.stop_reason in {"max_tokens", "model_context_window_exceeded", "refusal"}:
                result.reason = response.stop_reason
                break
            tool_blocks = [block for block in blocks if block["type"] == "tool_use"]
            if tool_blocks and response.stop_reason != "tool_use":
                result.reason = "invalid_response"
                break
            if not tool_blocks:
                result.messages.append({"role": "assistant", "content": blocks})
                if response.stop_reason in {"pause_turn", "compaction"}:
                    continue
                result.text = "\n".join(block["text"] for block in blocks if block["type"] == "text").strip()
                result.reason = "end_turn" if response.stop_reason in {"end_turn", "stop_sequence"} else "invalid_response"
                break
            result.messages.append({"role": "assistant", "content": blocks})
            replies = []
            for block in tool_blocks:
                attempted = False
                if request.tools.cancelled():
                    reply = tool_failure("version_conflict", "This turn was superseded. The tool did not run.")
                    result.reason = "cancelled"
                elif request.tools.done():
                    reply = tool_failure("already_submitted", "The final result was already submitted. This tool did not run.")
                elif time.monotonic() >= deadline:
                    reply = tool_failure("time_limit", "The agent time limit was reached before this tool ran.")
                    result.reason = "time_limit"
                elif len(result.calls) >= options.max_tool_calls:
                    reply = tool_failure("tool_limit", "The agent tool limit was reached before this tool ran.")
                    result.reason = "tool_limit"
                else:
                    reply = self._execute(request.tools, block, executed)
                    attempted = True
                if attempted:
                    result.calls.append(reply)
                replies.append({"type": "tool_result", "tool_use_id": block["id"],
                                "content": json.dumps(observation(reply), ensure_ascii=False),
                                "is_error": reply.get("ok") is False})
            result.messages.append({"role": "user", "content": replies})
            if request.tools.cancelled():
                result.reason = "cancelled"
                break
            if request.tools.done():
                result.reason = "submitted"
                break
            if len(result.calls) >= options.max_tool_calls:
                result.reason = "tool_limit"
                break
            if result.reason in {"time_limit", "tool_limit"}:
                break
        return result

    def _request(self, request: RunRequest, result: RunResult, remaining: float):
        options = request.options
        payload = {"model": options.model, "max_tokens": options.max_tokens,
                   "system": request.system, "messages": result.messages,
                   "tools": request.tools.definitions, "tool_choice": {"type": "auto"},
                   "output_config": {"effort": options.effort}}
        reserved = 0.0
        size = len(json.dumps(payload, ensure_ascii=True).encode()) + 4096
        if size > options.max_context_bytes:
            result.reason = "context_limit"
            return None
        try:
            if self.budget is not None:
                reserved = self.budget.reserve(RequestSize(options.model, size, options.max_tokens))
            result.requests += 1
            response = self.client.create(**payload, timeout=min(remaining, options.request_timeout))
        except BudgetExceeded as exc:
            result.reason, result.error = "budget_limit", str(exc)
            return None
        except anthropic.APIError as exc:
            # No usage report means the reservation remains spent, including on timeout.
            result.cost += reserved
            result.reason, result.error = "provider_error", type(exc).__name__
            return None
        counts = usage_counts(response.usage)
        actual = cost(options.model, counts)
        if self.budget is not None:
            self.budget.settle(reserved, actual)
        result.tokens.update(counts)
        result.cost += actual
        return response

    @staticmethod
    def _execute(tools: ToolSet, block: dict, executed: dict) -> dict:
        name, arguments = block["name"], block["input"]
        if block["id"] in executed:
            previous_name, previous_args, previous_result = executed[block["id"]]
            if name == previous_name and arguments == previous_args:
                return previous_result
            return tool_failure("invalid_args", "A tool call ID was reused with different arguments.")
        if name not in {tool["name"] for tool in tools.definitions}:
            return tool_failure("unknown_tool", "Choose a tool from the available definitions.")
        if not isinstance(arguments, dict):
            return tool_failure("invalid_args", "Tool arguments must be an object.")
        reply = tools.execute(name, arguments)
        executed[block["id"]] = name, arguments, reply
        return reply
