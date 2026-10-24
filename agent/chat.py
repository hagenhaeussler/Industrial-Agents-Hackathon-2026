"""Interactive LLM agent; shared execution rules stay outside the model loop."""

import os
import threading

import anthropic

from server.errors import ServiceError

from .budget import PersistentBudget
from .execution import AgentExecution
from .config import MODEL, MAX_TOKENS, configured_options
from .core import AgentRequest, BuildingAgent
from .runtime import AgentLoop, LoopOptions


def unavailable(message: str) -> dict:
    return {"reply": message, "tool_calls": [], "display": {"kind": "not_available"}, "status": "unavailable"}


class ChatAgent:
    def __init__(self, execution: AgentExecution, *, client: anthropic.Anthropic | None = None, options: LoopOptions | None = None):
        self.execution = execution
        self.client = client
        self.options = options or configured_options()
        self.budget = None
        self._lock = threading.Lock()

    def _configure(self) -> bool:
        with self._lock:
            if self.client is not None:
                return True
            if not os.environ.get("ANTHROPIC_API_KEY"):
                return False
            try:
                dollars = float(os.environ.get("TYB_CHAT_BUDGET_USD", "0"))
                allocation = os.environ.get("TYB_CHAT_BUDGET_ID", "chat")
                self.budget = PersistentBudget(self.execution.state, (allocation, dollars))
            except ValueError:
                return False
            self.client = anthropic.Anthropic(max_retries=0)
            return True

    def reply(self, session_id: str, message: str) -> dict:
        if not self._configure():
            return unavailable("Text chat is unavailable. Configure an approved model budget and credentials.")
        outcome = BuildingAgent(self.execution, AgentLoop(self.client.beta.messages, self.budget), self.options).run(
            AgentRequest(session_id, message))
        result = outcome.run
        calls = result.calls
        displays = [call["display"] for call in calls if call.get("ok") and call.get("display")]
        if result.reason == "end_turn" and not result.text and not result.calls:
            result.reason = "empty_response"
        complete = result.reason == "end_turn"
        # Number matching is not factual validation. Successful tools establish
        # routes and changes; final model prose remains a model-generated answer.
        reply = result.text if complete and result.text else self._stopped_reply(result)
        try:
            self.execution.state.require_current(session_id, outcome.turn_id)
        except ServiceError as exc:
            return {"reply": exc.message, "tool_calls": calls, "display": {}, "status": "superseded"}
        return {"reply": reply, "tool_calls": calls, "display": displays[-1] if displays else {},
                "status": "completed" if complete else "incomplete", "stop_reason": result.reason,
                "usage": dict(result.tokens), "cost_usd": result.cost,
                "sources": [call["request_id"] for call in calls if call.get("ok") and "request_id" in call]}

    @staticmethod
    def _stopped_reply(result) -> str:
        if result.reason == "end_turn" and result.calls:
            return result.calls[-1].get("speech", "The tools completed. Check the result in the application.")
        if result.reason == "refusal":
            return "I cannot help with that request."
        details = result.calls[-1].get("speech", "") if result.calls else ""
        reason = {
            "empty_response": "The language service returned an empty answer. Please try again.",
            "provider_error": "The language service failed before the answer was complete.",
            "budget_limit": result.error or "The model budget is exhausted.",
            "time_limit": "The agent reached its time limit.",
            "tool_limit": "The agent reached its tool limit.",
            "step_limit": "The agent reached its model request limit.",
            "max_tokens": "The model response was cut off before completion.",
            "model_context_window_exceeded": "The model could not fit this request in its context.",
            "context_limit": "The agent reached its context limit. Narrow this request or start a new session.",
        }.get(result.reason, "The language service returned an incomplete answer.")
        return (details + " " + reason).strip()
