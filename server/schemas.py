"""Validated transport models; session permissions never come from tool args."""
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Position(Input):
    space_id: str
    floor_id: str | None = None
    point: tuple[FiniteFloat, FiniteFloat] | None = None
    heading_deg: FiniteFloat | None = None
    source: Literal['desk', 'tour_start', 'marker', 'manual'] = 'manual'
    marker_id: str | None = None
    confidence: Literal['high', 'medium', 'low'] = 'low'
    updated_at: str | None = None


class Constraints(Input):
    step_free: bool = False
    min_door_width_m: FiniteFloat = Field(default=0, ge=0)
    closed: list[str] = Field(default_factory=list)
    no_transit_room_types: list[str] = Field(default_factory=list)


class SessionCreate(Input):
    building_id: str
    device: Literal['desk', 'phone'] = 'desk'
    role: Literal['navigator', 'admin'] = 'navigator'
    profile: Literal['walk', 'wheelchair', 'pram', 'trolley'] = 'walk'


class SessionPatch(Input):
    profile: Literal['walk', 'wheelchair', 'pram', 'trolley'] | None = None
    constraints: Constraints | None = None
    position: Position | None = None
    active_tour_id: str | None = None


class Session(BaseModel):
    session_id: str
    building_id: str
    device: str
    role: str
    profile: str
    constraints: dict[str, Any]
    position: Position | None
    active_tour_id: str | None
    updated_at: str


class ToolCall(Input):
    session_id: str
    args: dict[str, Any] = Field(default_factory=dict)


class ToolResponse(BaseModel):
    model_config = ConfigDict(extra='allow')
    ok: bool
    tool: str
    request_id: str
    building_version: int | None = None
    building_id: str | None = None
    result: dict[str, Any] | list[Any] | None = None
    error: dict[str, Any] | None = None
    speech: str
    display: dict[str, Any] | None = None
    trace: list[dict[str, Any]] = Field(default_factory=list)


class TourCreate(Input):
    session_id: str
    start: str | dict[str, Any] | None = None
    items: list[str] = Field(min_length=1, max_length=100)
    keep_order: bool = False
    end: str | dict[str, Any] | None = None


class TourProgress(Input):
    stop_id: str = Field(description="Collection stop ID, or reserved 'end' with status 'collected' to confirm final arrival.")
    status: Literal['collected', 'pending']


class TourReplan(Input):
    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    session_id: str
    position: Position = Field(alias='from')
    reason: str | dict[str, Any] | None = None
    constraints: Constraints | None = None


class MarkerInput(Input):
    space_id: str
    point: tuple[FiniteFloat, FiniteFloat]
    heading_deg: FiniteFloat
    label: str = Field(min_length=1, max_length=240)


class MarkerCreate(Input):
    markers: list[MarkerInput] = Field(min_length=1, max_length=500)


class ChatInput(Input):
    session_id: str
    message: str = Field(min_length=1, max_length=10000)


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[dict[str, Any]]
    display: dict[str, Any]


class DemoReset(Input):
    building_id: str


class RouteSegment(BaseModel):
    model_config = ConfigDict(extra='allow')
    floor_id: str
    kind: str
    points: list[tuple[float, float]]
    length_m: float
    geometry_length_m: float | None = None
    fallback: bool | None = None
    space_id: str | None = None
    element_id: str | None = None
    to_floor_id: str | None = None


class Maneuver(BaseModel):
    model_config = ConfigDict(extra='allow')
    i: int
    kind: str
    floor_id: str
    at: tuple[float, float]
    distance_m: float
    text: str
    landmark: str | None = None
    element_id: str | None = None


class RouteResult(BaseModel):
    model_config = ConfigDict(extra='allow')
    reachable: bool
    from_space_id: str
    to_space_id: str
    building_id: str
    building_version: int
    content_hash: str
    constraints: Constraints
    profile: str
    length_m: float | None = None
    length_m_exact: float | None = None
    start_position: tuple[float, float] | None = None
    destination_position: tuple[float, float] | None = None
    building_closed: list[str] = Field(default_factory=list)
    space_path: list[str] = Field(default_factory=list)
    element_path: list[str] = Field(default_factory=list)
    node_path: list[str] = Field(default_factory=list)
    segments: list[RouteSegment] = Field(default_factory=list)
    maneuvers: list[Maneuver] = Field(default_factory=list)
    reason: str | None = None
    blocking_ids: list[str] = Field(default_factory=list)


class TourStop(BaseModel):
    model_config = ConfigDict(extra='allow')
    stop_id: str
    space_id: str
    asset_ids: list[str]
    label: str
    status: Literal['collected', 'pending']


class TourResult(BaseModel):
    model_config = ConfigDict(extra='allow')
    mobility_profile: Literal['walk', 'wheelchair', 'pram', 'trolley'] = 'walk'
    tour_id: str
    revision: int
    status: str
    building_id: str
    building_version: int
    building_state_id: str | None = Field(default=None, description="Opaque building-state identity; compare with the snapshot even when numeric versions match after a reset.")
    order_policy: str
    building_closed: list[str] = Field(default_factory=list)
    start: dict[str, Any]
    end: dict[str, Any] | None
    stops: list[TourStop]
    order: list[str]
    legs: list[RouteResult]
    length_m: float
    unreachable_stops: list[dict[str, Any]]
    changed_because: dict[str, Any] | None
    profile: str
    constraints: Constraints
