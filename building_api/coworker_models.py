"""Public coworker state. Coordinates always use the source building's plan frame."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class WireModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class Position(WireModel):
    floor_id: str
    x: float
    y: float
    space_id: str
    space_name: str


class TimedPoint(WireModel):
    floor_id: str
    x: float
    y: float
    at: float


class Journey(WireModel):
    points: list[TimedPoint]
    destination_name: str
    arrives_at: float


class Coworker(WireModel):
    id: str
    name: str
    role: str
    color: str
    position: Position
    activity: str
    journey: Journey | None


class ChatMessage(WireModel):
    id: str
    member_id: str
    role: Literal["user", "assistant"]
    text: str
    created_at: float


class SessionState(WireModel):
    session_id: str
    server_time: float
    members: list[Coworker]
    messages: list[ChatMessage]
    chat_available: bool
    unavailable_reason: str | None
    total_cost_usd: float


class SendMessage(WireModel):
    member_id: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=2000)
    request_id: str = Field(min_length=16, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
