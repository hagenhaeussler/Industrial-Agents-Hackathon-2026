"""Answer shapes the agent returns, and the formatter that writes the benchmark reply from them."""

import re

from pydantic import BaseModel, ConfigDict, Field

from building_tools.building import Building
from building_tools.network import RouteConditions
from building_tools.routes import Route, route


class Shape(BaseModel):
    # The explanation comes first in each shape, so the model states its reasoning before it commits to a value.
    model_config = ConfigDict(extra="forbid")


class NumberAnswer(Shape):
    """A measured quantity, such as an area or a distance, taken from tool results."""

    explanation: str = Field(description="One or two sentences on how the tools produced the value")
    value: float = Field(allow_inf_nan=False)
    unit: str = Field(description='Unit of the value, such as "m" or "m2"')


class CountAnswer(Shape):
    """A number of things, such as rooms, taken from tool results."""

    explanation: str = Field(description="One or two sentences on what was counted")
    count: int = Field(ge=0)


class RoomAnswer(Shape):
    """One space of the building, identified by its ID from a tool result."""

    explanation: str = Field(description="One or two sentences on why this is the space")
    space_id: str
    asset_id: str | None = Field(
        default=None, description="When the question asks where an item is: the item's ID; it must be in the space"
    )


class RouteAnswer(Shape):
    """A walking route through stops in order. The route itself is recalculated from the stops and conditions."""

    explanation: str = Field(description="One or two sentences on the route and the rules it follows")
    stops: list[str] = Field(min_length=2, description="Space IDs to visit in order, start first, as passed to route")
    conditions: RouteConditions | None = None
    leg_conditions: list[RouteConditions] | None = None


class Failure(Shape):
    """The question cannot be answered reliably with the available tools or data."""

    reason: str = Field(description="What is missing or ambiguous")


Answer = NumberAnswer | CountAnswer | RoomAnswer | RouteAnswer | Failure

ANSWER_MARK = re.compile(r"\W*\banswer\W*:.*$", flags=re.IGNORECASE)


def plain(text: str) -> str:
    """Free text without any "Answer:" part, so the formatter's line is the only answer."""
    lines = (ANSWER_MARK.sub("", line).rstrip() for line in text.strip().splitlines())
    return "\n".join(line for line in lines if line)


def room_label(building: Building, space_id: str) -> str:
    """The space's name, with its ref first when the name does not contain it."""
    space = building.space(space_id)
    if space.ref and space.ref not in space.name:
        return f"{space.ref}, {space.name}"
    return space.name


def answer_route(answer: RouteAnswer, building: Building) -> Route:
    """The route an answer stands for. Raises ToolInputError for unknown stops or element IDs."""
    return route(building, answer.stops, answer.conditions, answer.leg_conditions)


def route_spaces(found: Route) -> list[str]:
    """Space IDs of the whole route in order. A stop between two legs appears once."""
    spaces: list[str] = []
    for leg in found.legs:
        spaces += [space.id for space in leg.spaces if not spaces or space.id != spaces[-1]]
    return spaces


def floor_name(building: Building, space_id: str) -> str:
    return building.floor_by_id[building.space(space_id).floor_id].name


def format_reply(answer: Answer, building: Building) -> str:
    """The full reply. Exactly one final `Answer:` line, except for failures, which have none."""
    match answer:
        case NumberAnswer(value=value, explanation=explanation):
            return f"{plain(explanation)}\nAnswer: {value:.2f}"
        case CountAnswer(count=count, explanation=explanation):
            return f"{plain(explanation)}\nAnswer: {count}"
        case RoomAnswer(space_id=space_id, asset_id=str(), explanation=explanation):
            # An item is located by its room and floor; its room's area would mean nothing here.
            return f"{plain(explanation)}\nAnswer: {room_label(building, space_id)} ({floor_name(building, space_id)})"
        case RoomAnswer(space_id=space_id, explanation=explanation):
            # The stored area is always written, so questions about a room's size need no extra field.
            area = building.area_by_id[building.space(space_id).id]
            return f"{plain(explanation)}\nAnswer: {room_label(building, space_id)}, {area:.2f} m²"
        case RouteAnswer(explanation=explanation):
            found = answer_route(answer, building)
            if not found.reachable:
                return f"{plain(explanation)}\nAnswer: No route exists under these rules."
            # Names repeat across floors, such as a lift shaft, so each step names its floor.
            path = " -> ".join(
                f"{room_label(building, space_id)} ({floor_name(building, space_id)})"
                for space_id in route_spaces(found)
            )
            return f"{plain(explanation)}\nRoute: {path}\nAnswer: {found.length_m:.2f} m"
        case Failure(reason=reason):
            return f"I could not answer this reliably: {plain(reason)}"


def answer_result(answer: Answer, building: Building) -> dict:
    """The calculation result saved in run records: the space, number or route the reply states."""
    match answer:
        case NumberAnswer(value=value, unit=unit):
            return {"type": "number", "value": round(value, 2), "unit": unit}
        case CountAnswer(count=count):
            return {"type": "count", "value": count}
        case RoomAnswer(space_id=space_id, asset_id=asset_id):
            space = building.space(space_id)
            floor = building.floor_by_id[space.floor_id]
            result = {
                "type": "space",
                "space_id": space_id,
                "space_name": space.name,
                "floor_level": floor.level,
                "floor_name": floor.name,
                "area_m2": round(building.area_by_id[space_id], 2),
            }
            if asset_id is not None:
                asset = building.asset_by_id[asset_id]
                result |= {"asset_id": asset_id, "asset_name": asset.name, "position": list(asset.position)}
            return result
        case RouteAnswer():
            found = answer_route(answer, building)
            elements = [element.id for leg in found.legs for element in leg.elements]
            return {
                "type": "route",
                "reachable": found.reachable,
                "space_path": route_spaces(found) if found.reachable else [],
                "element_path": elements if found.reachable else [],
                "length_m": found.length_m,
            }
        case Failure(reason=reason):
            return {"type": "failure", "reason": plain(reason)}
