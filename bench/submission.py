"""Select an observed calculation and serialize it without another solver call."""

from copy import deepcopy

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from agent.runtime import tool_failure
from core.building import Building

from .agent import Prediction
from .serialize import serialize


class SubmitArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    request_id: str = Field(min_length=1, max_length=128)


class Submission:
    instructions = """Submission mode: use the same building tools to answer the original question.
This is a single isolated question. Do not ask a follow-up or choose an arbitrary ambiguous match.
Use spatial_query for count, locate, areas and spatial calculations. Use query_route or query_tour
for routes from explicit start IDs and temporary closures, without starting live navigation.
After a successful calculation, call submit_answer with that result's request_id.
Do not put kind, inputs or answer text into submit_answer. It only selects an observed result.
Only the serializer writes the required Answer line. Your prose cannot submit an answer.
If the tools cannot establish an answer, explain the missing information and stop without submitting.
"""
    definition = {"name": "submit_answer", "description": "Select a successful calculation from this run by request_id. The serializer formats its stored result.",
                  "input_schema": SubmitArgs.model_json_schema()}

    def __init__(self, building: Building):
        self.building = building
        self.observed: dict[str, dict] = {}
        self.prediction: Prediction | None = None

    def observe(self, reply: dict) -> None:
        if reply.get("ok") and reply.get("request_id"):
            self.observed[reply["request_id"]] = deepcopy(reply)

    def submit(self, arguments: dict) -> dict:
        if self.done():
            return tool_failure("already_submitted", "An answer was already submitted.")
        try:
            args = SubmitArgs.model_validate(arguments)
            source = self.observed.get(args.request_id)
            if source is None:
                return tool_failure("invalid_result", "Choose a successful result request_id from this run.")
            result = source["result"]
            calculation = result.get("calculation")
            if calculation is None:
                return tool_failure("invalid_result", "This tool result is not a calculation. Use spatial_query, query_route or query_tour first.")
            kind, inputs = calculation["kind"], calculation["inputs"]
            computed = {"route": result} if kind == "route" else result
            reply = serialize(self.building, kind, computed)
        except (ValidationError, ValueError, KeyError, TypeError):
            return tool_failure("invalid_result", "Provide only a valid request_id for a supported computed result.")
        self.prediction = Prediction(reply=reply, kind=kind, inputs=inputs, result=computed, method="llm")
        return {"ok": True, "submitted": True, "source_request_id": args.request_id}

    def done(self) -> bool:
        return self.prediction is not None
