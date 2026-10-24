"""Typed, additive C1/C2 core payloads; the server exports its HTTP OpenAPI."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Payload(BaseModel):
    model_config = ConfigDict(extra='allow', allow_inf_nan=False)


class MobilityConstraints(Payload):
    step_free: bool = False
    min_door_width_m: float = Field(default=0, ge=0)
    closed: list[str] = Field(default_factory=list)
    no_transit_room_types: list[str] = Field(default_factory=list)


class Segment(Payload):
    floor_id: str
    kind: Literal['walk','lift','stairs']
    points: list[tuple[float,float]]
    length_m: float = Field(ge=0)
    geometry_length_m: float | None = Field(default=None, ge=0)
    space_id: str | None = None
    element_id: str | None = None
    to_floor_id: str | None = None
    fallback: bool = False


class Maneuver(Payload):
    i: int
    kind: Literal['depart','straight','turn_left','turn_right','slight_left','slight_right','u_turn','enter','take_lift','take_stairs','arrive']
    floor_id: str
    at: tuple[float,float]
    distance_m: float = Field(ge=0)
    text: str = Field(max_length=90)
    landmark: str | None = None
    element_id: str | None = None


class RouteResult(Payload):
    reachable: bool
    from_space_id: str
    to_space_id: str
    building_id: str
    building_version: int = Field(ge=0)
    content_hash: str
    profile: str
    constraints: MobilityConstraints
    length_m: float | None = Field(default=None, ge=0)
    length_m_exact: float | None = Field(default=None, ge=0)
    space_path: list[str] = Field(default_factory=list)
    node_path: list[str] = Field(default_factory=list)
    element_path: list[str] = Field(default_factory=list)
    segments: list[Segment] = Field(default_factory=list)
    maneuvers: list[Maneuver] = Field(default_factory=list)
    reason: str | None = None
    blocking_ids: list[str] = Field(default_factory=list)


class Stop(Payload):
    stop_id: str
    space_id: str
    asset_ids: list[str] = Field(default_factory=list)
    label: str
    status: Literal['pending','collected'] = 'pending'


class TourResult(Payload):
    tour_id: str | None = None
    revision: int = Field(ge=1)
    status: Literal['active','completed','blocked']
    building_id: str
    building_version: int = Field(ge=0)
    order_policy: Literal['fixed','optimized_exact','optimized_heuristic']
    start: dict
    end: dict | None = None
    stops: list[Stop]
    order: list[str]
    legs: list[RouteResult]
    length_m: float = Field(ge=0)
    unreachable_stops: list[dict]
    profile: str
    constraints: MobilityConstraints
