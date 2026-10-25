"""The `building.json` source format and the checks a building must pass before import."""

from collections import Counter
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from shapely.geometry import Polygon
from shapely.validation import explain_validity

OUTSIDE = "outside"
"""The space reference an entrance uses for the area outside the building."""

Point = tuple[float, float]


class SourceModel(BaseModel):
    # Unknown fields fail validation: the database could not return them unchanged.
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)


class BuildingInfo(SourceModel):
    id: str = Field(min_length=1)
    name: str
    source: str
    source_ref: dict[str, str]
    license: str
    attribution: str
    split: str
    units: Literal["m"]


class Floor(SourceModel):
    id: str = Field(min_length=1)
    level: int
    name: str
    elevation_m: float
    height_m: float = Field(gt=0)


class Space(SourceModel):
    id: str = Field(min_length=1)
    floor_id: str
    type: Literal["room", "corridor", "hall", "stair", "lift", "outdoor"]
    room_type: str
    name: str
    ref: str
    polygon: Annotated[list[Point], Field(min_length=3)]
    synthetic: bool


class Opening(SourceModel):
    id: str = Field(min_length=1)
    floor_id: str
    space_ids: tuple[str, str]
    kind: Literal["door", "opening", "entrance"]
    position: Point
    width_m: float = Field(gt=0)
    step_free: bool
    synthetic: bool


class VerticalConnector(SourceModel):
    id: str = Field(min_length=1)
    kind: Literal["stairs", "lift"]
    name: str
    floor_ids: Annotated[list[str], Field(min_length=2)]
    space_ids: Annotated[list[str], Field(min_length=2)]
    step_free: bool
    synthetic: bool


class Footprint(SourceModel):
    width_m: float = Field(gt=0)
    depth_m: float = Field(gt=0)
    rotation_deg: float


class Asset(SourceModel):
    id: str = Field(min_length=1)
    name: str
    category: str
    type: str
    space_id: str
    floor_id: str
    position: Point
    footprint: Footprint
    source: str


class BuildingDocument(SourceModel):
    building: BuildingInfo
    floors: list[Floor]
    spaces: list[Space]
    openings: list[Opening]
    vertical_connectors: list[VerticalConnector]
    assets: list[Asset]


class BuildingSourceError(Exception):
    """A building file that cannot be imported. `problems` lists every reason found."""

    def __init__(self, path: Path, problems: list[str]) -> None:
        super().__init__(f"{path}: " + "; ".join(problems))
        self.path = path
        self.problems = problems


def read_building(path: Path) -> BuildingDocument:
    """Parse and check one `building.json`. Raises BuildingSourceError with all problems found."""
    if path.name != "building.json":
        raise BuildingSourceError(path, ["only building.json files can be imported"])
    try:
        document = BuildingDocument.model_validate_json(path.read_bytes())
    except ValidationError as error:
        problems = [f"{'.'.join(map(str, issue['loc']))}: {issue['msg']}" for issue in error.errors()]
        raise BuildingSourceError(path, problems) from None
    problems = consistency_problems(document)
    if problems:
        raise BuildingSourceError(path, problems)
    return document


def consistency_problems(document: BuildingDocument) -> list[str]:
    """Check what the schema alone cannot: unique IDs, references, floor agreement and polygon validity."""
    problems = [f"duplicate id {entity_id}" for entity_id, count in id_counts(document).items() if count > 1]
    levels = Counter(floor.level for floor in document.floors)
    problems += [f"duplicate floor level {level}" for level, count in levels.items() if count > 1]

    floor_ids = {floor.id for floor in document.floors}
    space_floors = {space.id: space.floor_id for space in document.spaces}

    def check_space(owner: str, space_id: str, floor_id: str) -> None:
        if space_id not in space_floors:
            problems.append(f"{owner} references unknown space {space_id}")
        elif space_floors[space_id] != floor_id:
            problems.append(f"{owner} is on {floor_id}, but space {space_id} is on {space_floors[space_id]}")

    for space in document.spaces:
        if space.floor_id not in floor_ids:
            problems.append(f"space {space.id} references unknown floor {space.floor_id}")
        polygon = Polygon(space.polygon)
        if not polygon.is_valid:
            problems.append(f"space {space.id} has an invalid polygon: {explain_validity(polygon)}")

    for opening in document.openings:
        outside_count = opening.space_ids.count(OUTSIDE)
        if outside_count != (1 if opening.kind == "entrance" else 0):
            problems.append(f"opening {opening.id}: only an entrance connects exactly one side to {OUTSIDE!r}")
        for space_id in opening.space_ids:
            if space_id != OUTSIDE:
                check_space(f"opening {opening.id}", space_id, opening.floor_id)

    for connector in document.vertical_connectors:
        if len(connector.floor_ids) != len(connector.space_ids):
            problems.append(f"connector {connector.id} needs one space per floor")
        for floor_id, space_id in zip(connector.floor_ids, connector.space_ids, strict=False):
            check_space(f"connector {connector.id}", space_id, floor_id)

    for asset in document.assets:
        check_space(f"asset {asset.id}", asset.space_id, asset.floor_id)
    return problems


def id_counts(document: BuildingDocument) -> Counter[str]:
    sections = (
        document.floors,
        document.spaces,
        document.openings,
        document.vertical_connectors,
        document.assets,
    )
    return Counter(entity.id for section in sections for entity in section)
