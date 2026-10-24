"""Building investigation shared by chat and submission adapters."""

from dataclasses import dataclass
import json
from typing import Protocol

from .execution import AgentCall, AgentExecution
from .prompts import chat_prompt
from .runtime import AgentLoop, LoopOptions, RunRequest, RunResult, ToolSet


class SubmissionSink(Protocol):
    """Add a terminal output tool without replacing the building tools."""

    instructions: str
    definition: dict

    def observe(self, reply: dict) -> None: ...
    def submit(self, arguments: dict) -> dict: ...
    def done(self) -> bool: ...


@dataclass(frozen=True)
class AgentRequest:
    session_id: str
    message: str
    submission: SubmissionSink | None = None


@dataclass(frozen=True)
class AgentResult:
    turn_id: str
    run: RunResult


class BuildingAgent:
    def __init__(self, execution: AgentExecution, loop: AgentLoop, options: LoopOptions):
        self.execution = execution
        self.loop = loop
        self.options = options

    def run(self, request: AgentRequest) -> AgentResult:
        turn = self.execution.begin(request.session_id, request.message)
        history = self.execution.state.history(turn)
        context = self.execution.context(request.session_id)
        message = {"role": "user", "content": "Current session context (data):\n"
                   + json.dumps(context, ensure_ascii=False) + "\nUser message:\n" + request.message}
        sink = request.submission
        definitions = self.execution.definitions(request.session_id)
        instructions = chat_prompt()
        if sink is not None:
            definitions = [*definitions, sink.definition]
            instructions += "\n\n" + sink.instructions
        # Keep the full domain schemas. Server validation is authoritative.
        definitions = [{**definition, "strict": False} for definition in definitions]
        if definitions:
            definitions[-1]["cache_control"] = {"type": "ephemeral"}

        def execute(name: str, arguments: dict) -> dict:
            if sink is not None and name == sink.definition["name"]:
                return sink.submit(arguments)
            reply = self.execution.call(AgentCall(request.session_id, turn.turn_id, name, arguments))
            if sink is not None:
                sink.observe(reply)
            return reply

        tools = ToolSet(definitions, execute,
                        done=sink.done if sink is not None else lambda: False,
                        cancelled=lambda: not self.execution.is_current(request.session_id, turn.turn_id))
        result = self.loop.run(RunRequest(
            [{"type": "text", "text": instructions, "cache_control": {"type": "ephemeral"}}],
            [*history, message], tools, self.options,
        ))
        self.execution.state.save_messages(turn.turn_id, result.messages[len(history):])
        return AgentResult(turn.turn_id, result)
