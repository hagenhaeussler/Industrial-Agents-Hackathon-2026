"""A stored building prepared for tool calls: lookups by ID, floor references and shared result models."""

import sqlite3
import unicodedata
from typing import Literal

from pydantic import BaseModel, ConfigDict
from shapely.geometry import Polygon

from building_db.source import BuildingDocument, Floor, Space
from building_db.store import load_building
from building_tools.walks import Walk

SpaceType = Literal["room", "corridor", "hall", "stair", "lift", "outdoor"]


class ToolInputError(ValueError):
    """A tool request the building cannot answer, such as an unknown ID. The message is shown to the agent."""


class ToolResult(BaseModel):
    model_config = ConfigDict(frozen=True)


class FloorSummary(ToolResult):
    id: str
    level: int
    name: str
    elevation_m: float


class SpaceSummary(ToolResult):
    id: str
    name: str
    ref: str
    type: SpaceType
    room_type: str
    floor_id: str
    floor_name: str
    area_m2: float


def normalize(text: str) -> str:
    """Comparable form of a name: case, Unicode form, underscores and spacing do not matter."""
    return " ".join(unicodedata.normalize("NFKC", text).casefold().replace("_", " ").split())


class Building:
    """One building from the database. Areas come from the stored `area_m2` column."""

    def __init__(self, document: BuildingDocument, areas: dict[str, float]) -> None:
        self.document = document
        self.floors = sorted(document.floors, key=lambda floor: floor.level)
        self.floor_by_id = {floor.id: floor for floor in document.floors}
        self.space_by_id = {space.id: space for space in document.spaces}
        self.area_by_id = areas
        self.polygon_by_id = {space.id: Polygon(space.polygon) for space in document.spaces}
        self.connector_by_id = {connector.id: connector for connector in document.vertical_connectors}
        self.walk_cache: dict[str, list[Walk]] = {}
        """Walks inside each space, computed on first use by the route network."""

    @property
    def id(self) -> str:
        return self.document.building.id

    def space(self, space_id: str) -> Space:
        try:
            return self.space_by_id[space_id]
        except KeyError:
            raise ToolInputError(f"unknown space id {space_id!r}; use find_spaces to get space ids") from None

    def floor(self, reference: str) -> Floor:
        """Resolve a floor by ID, by name such as "Floor 2" or "Ground floor", or by level number such as "-1"."""
        wanted = normalize(reference)
        for floor in self.floors:
            if wanted in (normalize(floor.id), normalize(floor.name), str(floor.level)):
                return floor
        known = ", ".join(f"{floor.name} (level {floor.level})" for floor in self.floors)
        raise ToolInputError(f"unknown floor {reference!r}; this building has: {known}")

    def spaces_on(self, floor_id: str) -> list[Space]:
        return [space for space in self.document.spaces if space.floor_id == floor_id]

    def floor_summary(self, floor: Floor) -> FloorSummary:
        return FloorSummary(id=floor.id, level=floor.level, name=floor.name, elevation_m=floor.elevation_m)

    def space_summary(self, space: Space) -> SpaceSummary:
        return SpaceSummary(
            id=space.id,
            name=space.name,
            ref=space.ref,
            type=space.type,
            room_type=space.room_type,
            floor_id=space.floor_id,
            floor_name=self.floor_by_id[space.floor_id].name,
            area_m2=round(self.area_by_id[space.id], 2),
        )


def load(connection: sqlite3.Connection, building_id: str) -> Building:
    """Read one building and its stored areas. Raises ToolInputError if the building is not stored."""
    try:
        document = load_building(connection, building_id)
    except KeyError:
        raise ToolInputError(f"building {building_id!r} is not in the database") from None
    areas = dict(connection.execute("SELECT id, area_m2 FROM spaces WHERE building_id = ?", (building_id,)))
    return Building(document, areas)
