"""Write committed answers from computed results, without model-generated values."""

import math
import re
from collections.abc import Callable
from typing import Protocol


class BuildingLabels(Protocol):
    spaces: dict[str, dict]
    floors: dict[str, dict]
    assets: dict[str, dict]


def number(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("The computed value must be a number.")
    if not math.isfinite(value):
        raise ValueError("The computed value must be finite.")
    return str(value) if isinstance(value, int) else f"{value:.6f}"


def room_label(building: BuildingLabels, space_id: str) -> str:
    space = building.spaces[space_id]
    level = building.floors[space["floor_id"]]["level"]
    suffix = re.search(r"-S(\d+)$", space_id)
    fallback = f"{level}.{int(suffix[1]):02d}" if suffix else space["name"]
    return f"{space.get('ref') or fallback}, {space['name']}"


def largest_room(building: BuildingLabels, result: dict) -> str:
    return f"{room_label(building, result['space_id'])}, {number(result['area_m2'])} m²"


def room_stacked(building: BuildingLabels, result: dict) -> str:
    return room_label(building, result["space_id"])


def numeric_answer(building: BuildingLabels, result: dict) -> str:
    return number(result["value"])


def count_answer(building: BuildingLabels, result: dict) -> str:
    value = result["value"]
    number(value)
    if int(value) != value or value < 0:
        raise ValueError("A count must be a nonnegative integer.")
    return str(int(value))


def locate(building: BuildingLabels, result: dict) -> str:
    asset = building.assets[result["asset_id"]]
    space = building.spaces[result["space_id"]]
    floor = building.floors[space["floor_id"]]
    return f"{asset['name']} in {space['name']} ({floor['name']})"


def route(building: BuildingLabels, result: dict) -> str:
    computed = result["route"]
    if computed["reachable"] is False:
        return "no route"
    names = [building.spaces[space_id]["name"] for space_id in computed["space_path"]]
    return f"{number(computed['length_m'])} m via {' → '.join(names)}"


def tour(building: BuildingLabels, result: dict) -> str:
    if result.get("reachable") is False:
        return "no route"
    legs = result["legs"]
    names = [building.spaces[space_id]["name"] for leg in legs for space_id in leg["space_path"]]
    return f"{number(result['length_m'])} m via {' → '.join(names)}"


SERIALIZERS: dict[str, Callable[[BuildingLabels, dict], str]] = {
    "largest_room": largest_room,
    "room_stacked": room_stacked,
    "floor_area_total": numeric_answer,
    "errand": numeric_answer,
    "straight_line_3d": numeric_answer,
    "shared_walls_count": count_answer,
    "wide_delivery_count": count_answer,
    "step_free_reachable_count": count_answer,
    "what_if_door": count_answer,
    "count": count_answer,
    "locate": locate,
    "route": route,
    "route_step_free": route,
    "route_with_closure": route,
    "tour": tour,
}


def serialize(building: BuildingLabels, kind: str, result: dict) -> str:
    """Format one computed result according to the shared answer contract."""
    try:
        formatter = SERIALIZERS[kind]
    except KeyError as error:
        raise ValueError(f"Unsupported answer kind: {kind}") from error
    text = formatter(building, result)
    if "\n" in text or "\r" in text:
        raise ValueError("An answer must fit on one line.")
    return f"Answer: {text}"
