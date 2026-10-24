"""One execution policy for model calls from text and hosted voice agents."""

from dataclasses import dataclass
from collections.abc import Callable
from typing import Protocol

from server.errors import ServiceError
from server.public import public_payload

from .runtime import tool_failure
from .state import AgentState, TurnState


class Registry(Protocol):
    def json_schemas(self, role: str | None = None) -> list[dict]: ...
    def call(self, name: str, session_id: str, args: dict) -> dict: ...


@dataclass(frozen=True)
class AgentCall:
    session_id: str
    turn_id: str
    name: str
    arguments: dict


def compact_observation(reply: dict) -> dict:
    """Remove render-only route detail, retaining facts, constraints and errors."""
    geometry = {"segments", "node_path", "space_path", "element_path", "trace", "display", "model_result"}

    def compact(value):
        if isinstance(value, dict):
            return {key: compact(item) for key, item in value.items() if key not in geometry}
        if isinstance(value, list):
            return [compact(item) for item in value]
        return value

    return compact(reply)


class AgentExecution:
    def __init__(self, registry: Registry, session_provider: Callable[[str], dict], state: AgentState):
        self.registry = registry
        self.session_provider = session_provider
        self.state = state

    def begin(self, session_id: str, message: str, channel: str = "text") -> TurnState:
        self.session_provider(session_id)
        with self.state.lock(session_id):
            return self.state.begin(session_id, message, channel)

    def is_current(self, session_id: str, turn_id: str) -> bool:
        try:
            self.state.require_current(session_id, turn_id)
            return True
        except ServiceError as exc:
            if exc.code == "version_conflict":
                return False
            raise

    def context(self, session_id: str) -> dict:
        return public_payload(self.session_provider(session_id))

    def definitions(self, session_id: str) -> list[dict]:
        return self.registry.json_schemas(role=self.session_provider(session_id)["role"])

    def call(self, call: AgentCall) -> dict:
        with self.state.lock(call.session_id):
            try:
                turn = self.state.require_current(call.session_id, call.turn_id)
                if call.name == "commit_edit" and (not turn.authorized_proposal or call.arguments.get("proposal_id") != turn.authorized_proposal):
                    raise ServiceError("confirmation_required", "Confirm the pending preview in a later user message first.", status=403)
                result = self.registry.call(call.name, call.session_id, call.arguments)
                if result.get("ok") and call.name == "propose_edit":
                    self.state.remember_proposal(turn, result["result"]["proposal_id"])
                if (result.get("ok") and call.name == "commit_edit") or result.get("error", {}).get("code") == "version_conflict":
                    self.state.remember_proposal(turn, None)
                result["model_result"] = compact_observation(result)
                self.state.record_observation(turn, result["model_result"])
                return result
            except ServiceError as exc:
                failure = tool_failure(exc.code, exc.message)
                failure.update(tool=call.name, request_id=call.turn_id)
                return failure
