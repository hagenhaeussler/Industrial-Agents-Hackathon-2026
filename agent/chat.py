"""Bounded text chat on the platform registry, with enforced edit confirmation."""

import json
import os
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

import anthropic
from anthropic.lib.tools import BetaFunctionTool

from .budget import Budget, BudgetExceeded, RequestSize, cost, usage_counts
from .prompts import chat_prompt

MODEL = "claude-sonnet-5-5"
MAX_ITERATIONS = 6
MAX_TOKENS = 2048
YES = re.compile(r"\s*(?:yes|yes please|confirm|apply it|go ahead)[.!]?\s*", re.I)


class Registry(Protocol):
    def json_schemas(self) -> list[dict]: ...
    def call(self, name: str, session_id: str, args: dict) -> dict: ...


@dataclass
class Conversation:
    messages: list[dict] = field(default_factory=list)
    pending_proposal: str | None = None
    step_free: bool = False
    lock: threading.RLock = field(default_factory=threading.RLock)


def strict_schema(schema: dict) -> dict:
    """Make registry schemas explicit about object fields for strict tool calls."""
    result = {}
    for key, value in schema.items():
        if key == "default":
            continue
        if isinstance(value, dict):
            value = strict_schema(value)
        elif isinstance(value, list):
            value = [strict_schema(item) if isinstance(item, dict) else item for item in value]
        result[key] = value
    if result.get("type") == "object":
        result["additionalProperties"] = False
        result["required"] = list(result.get("properties", {}))
    return result


def unavailable(message: str) -> dict:
    return {"reply": message, "tool_calls": [], "display": {"kind": "not_available"}}


@dataclass
class Turn:
    registry: Registry
    session_id: str
    conversation: Conversation
    authorized_proposal: str | None = None
    calls: list[dict] = field(default_factory=list)
    committed: dict[str, dict] = field(default_factory=dict)

    def call(self, name: str, arguments: dict) -> dict:
        args = {key: value for key, value in arguments.items() if value is not None}
        if name == "commit_edit" and args.get("proposal_id") in self.committed:
            result = self.committed[args["proposal_id"]]
        elif name == "commit_edit" and args.get("proposal_id") != self.authorized_proposal:
            result = {"ok": False, "tool": name, "error": {"code": "forbidden", "message": "Confirm the pending preview in a later message first."}, "speech": "Please confirm the pending preview first."}
        elif name == "commit_edit" and self.authorized_proposal is None:
            result = {"ok": False, "tool": name, "error": {"code": "forbidden", "message": "No confirmed preview is pending."}, "speech": "There is no confirmed preview to save."}
        else:
            if name in {"route", "plan_tour"}:
                self.conversation.step_free |= args.get("step_free") is True
                if self.conversation.step_free:
                    args["step_free"] = True
            result = self.registry.call(name, self.session_id, args)
        self.calls.append(result)
        if name == "propose_edit" and result["ok"]:
            self.conversation.pending_proposal = result["result"]["proposal_id"]
            self.authorized_proposal = None
        if name == "commit_edit" and result["ok"]:
            self.committed[args["proposal_id"]] = result
            self.conversation.pending_proposal = None
            self.authorized_proposal = None
        if result.get("error", {}).get("code") == "version_conflict":
            self.conversation.pending_proposal = None
            self.authorized_proposal = None
        return result

    def tool(self, schema: dict) -> BetaFunctionTool:
        def invoke(**arguments: object) -> str:
            return json.dumps(self.call(schema["name"], arguments), ensure_ascii=False)

        return BetaFunctionTool(invoke, name=schema["name"], description=schema["description"],
                                input_schema=strict_schema(schema["input_schema"]), strict=True)


def grounded_reply(text: str, calls: list[dict]) -> str:
    for call in calls:
        error = call.get("error", {})
        if error.get("code") == "ambiguous" and error.get("candidates"):
            labels = "; ".join(candidate["label"].rstrip("?.") for candidate in error["candidates"][:4])
            return f"Which item do you mean: {labels}?"
    if calls and not calls[-1]["ok"]:
        return calls[-1]["speech"]
    if calls and calls[-1]["tool"] in {"propose_edit", "commit_edit", "undo", "what_if"}:
        return calls[-1]["speech"]
    if not calls:
        return text if text.count("?") == 1 and not re.search(r"\d", text) else "What item or place do you need?"
    evidence = json.dumps(calls, ensure_ascii=False)
    if not text or not set(re.findall(r"\d+(?:\.\d+)?", text)) <= set(re.findall(r"\d+(?:\.\d+)?", evidence)):
        return calls[-1]["speech"]
    return text


class ChatAgent:
    def __init__(self, registry: Registry, session_provider: Callable[[str], dict], *, client: anthropic.Anthropic | None = None) -> None:
        self.registry = registry
        self.session_provider = session_provider
        self.client = client
        self.budget = None
        self.conversations: dict[str, Conversation] = {}
        self._lock = threading.Lock()
        self.system = [{"type": "text", "text": chat_prompt(), "cache_control": {"type": "ephemeral"}}]

    def reply(self, session_id: str, message: str) -> dict:
        with self._lock:
            if self.client is None:
                # A key alone must not start an unbudgeted run in the server.
                if not os.environ.get("ANTHROPIC_API_KEY") or not os.environ.get("TYB_CHAT_BUDGET_USD"):
                    return unavailable("Text chat is unavailable. Use the building controls.")
                try:
                    self.budget = Budget(float(os.environ["TYB_CHAT_BUDGET_USD"]))
                except ValueError:
                    return unavailable("Text chat is unavailable. Use the building controls.")
                self.client = anthropic.Anthropic(max_retries=0)
            conversation = self.conversations.setdefault(session_id, Conversation())
        with conversation.lock:
            return self._reply(session_id, message, conversation)

    def _reply(self, session_id: str, message: str, conversation: Conversation) -> dict:
        context = self.session_provider(session_id)
        if "constraints" in context:
            conversation.step_free = context["constraints"].get("step_free", False) or context.get("profile") in {"wheelchair", "pram", "trolley"}
        turn = Turn(self.registry, session_id, conversation,
                    conversation.pending_proposal if YES.fullmatch(message) else None)
        conversation.messages.append({"role": "user", "content": "Current session context (data):\n" + json.dumps(context, ensure_ascii=False) + "\nUser message:\n" + message})
        runner = self.client.beta.messages.tool_runner(
            model=MODEL, max_tokens=MAX_TOKENS, max_iterations=MAX_ITERATIONS,
            system=self.system, tools=[turn.tool(schema) for schema in self.registry.json_schemas()],
            messages=list(conversation.messages), output_config={"effort": "low"},
            tool_choice={"type": "auto"}, betas=["server-side-fallback-2026-07-01"],
            fallbacks="default", timeout=60,
        )
        text = ""
        reservation = 0.0
        try:
            iterator = iter(runner)
            for _ in range(MAX_ITERATIONS):
                if self.budget is not None:
                    payload = json.dumps([self.system, conversation.messages, self.registry.json_schemas()], default=str).encode()
                    reservation = self.budget.reserve(RequestSize(MODEL, len(payload) + 4096, MAX_TOKENS))
                try:
                    response = next(iterator)
                except StopIteration:
                    if self.budget is not None:
                        self.budget.settle(reservation, 0.0)
                    break
                if self.budget is not None:
                    self.budget.settle(reservation, cost(MODEL, usage_counts(response.usage)))
                conversation.messages.append({"role": "assistant", "content": response.content})
                tools = runner.generate_tool_call_response()
                if tools is not None:
                    conversation.messages.append(tools)
                if response.stop_reason == "refusal":
                    text = "I cannot help with that request."
                    break
                text = "\n".join(block.text for block in response.content if block.type == "text").strip()
                # The SDK requests another turn only for tool results or an
                # unfinished server turn. Do not reserve funds just to discover
                # StopIteration after a completed answer: that false reservation
                # can discard an answer and its display at the budget boundary.
                # Keep the next reservation before next(iterator), which can
                # itself issue the next provider request.
                if response.stop_reason not in {"tool_use", "pause_turn", "compaction"}:
                    break
                if response.stop_reason == "tool_use" and tools is None:
                    break
        except anthropic.APIError:
            if not turn.calls:
                return unavailable("The language service is unavailable. Use the building controls.")
            text = turn.calls[-1]["speech"]
        except BudgetExceeded as error:
            return {"reply": str(error), "tool_calls": turn.calls, "display": {"kind": "not_available"}}
        displays = [call["display"] for call in turn.calls if call.get("ok") and call.get("display")]
        return {"reply": grounded_reply(text, turn.calls), "tool_calls": turn.calls, "display": displays[-1] if displays else {}}
