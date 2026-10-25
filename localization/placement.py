"""Place a localized camera in a building: floor, space, plan position and heading.

`building.json` files made by `floor_plan` store `source_ref.building_from_map`, the 4 x 4 transform from the
localization map to the plan (x right, y up, z height above the ground floor).
"""

from dataclasses import dataclass

import numpy as np
from shapely.geometry import Point, Polygon

PHONE_ABOVE_FLOOR_M = 0.5  # a hand-held phone is at least this high above the floor it is on
NEAREST_SPACE_M = 0.5  # a position this close to a space counts as inside, as walls have thickness


@dataclass(frozen=True)
class Placement:
    floor_id: str
    space_id: str | None  # None when the position is in no space
    position: tuple[float, float]
    height_m: float  # camera height above the floor
    heading_deg: float  # viewing direction in the plan, counterclockwise from +x


class BuildingFrame:
    """The plan geometry needed to place cameras, read once from a building document."""

    def __init__(self, building: dict):
        self.building_id: str = building["building"]["id"]
        self.building_from_map = np.array(building["building"]["source_ref"]["building_from_map"], float)
        self.floors = sorted(building["floors"], key=lambda floor: floor["elevation_m"])
        self.spaces = [(space["id"], space["floor_id"], Polygon(space["polygon"])) for space in building["spaces"]]

    def place(self, world_from_cam: np.ndarray) -> Placement:
        x, y, z = self.building_from_map[:3, :3] @ world_from_cam[:3, 3] + self.building_from_map[:3, 3]
        floor = self.floors[0]
        for candidate in self.floors:
            if candidate["elevation_m"] <= z - PHONE_ABOVE_FLOOR_M:
                floor = candidate
        point = Point(x, y)
        on_floor = [(space_id, polygon) for space_id, floor_id, polygon in self.spaces if floor_id == floor["id"]]
        space_id = next((space_id for space_id, polygon in on_floor if polygon.contains(point)), None)
        if space_id is None and on_floor:
            distance, nearest = min((polygon.distance(point), space_id) for space_id, polygon in on_floor)
            space_id = nearest if distance <= NEAREST_SPACE_M else None
        dx, dy, _ = self.building_from_map[:3, :3] @ world_from_cam[:3, 2]  # the camera looks along its z axis
        return Placement(
            floor_id=floor["id"],
            space_id=space_id,
            position=(round(float(x), 3), round(float(y), 3)),
            height_m=round(float(z - floor["elevation_m"]), 3),
            heading_deg=round(float(np.degrees(np.arctan2(dy, dx))), 1),
        )
