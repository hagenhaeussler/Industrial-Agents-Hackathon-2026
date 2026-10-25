"""The `building.json` source format and the checks a building must pass before import."""

import json
import math
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
    id: str = Field(min_length=1, pattern=r"^[^\s/\\\x00-\x1f\x7f]+$")
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
    floors: Annotated[list[Floor], Field(min_length=1)]
    spaces: Annotated[list[Space], Field(min_length=1)]
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
        content = path.read_bytes().removeprefix(b"\xef\xbb\xbf")
        # Reject repeated keys before the model parser can silently keep the last value.
        json.loads(content, object_pairs_hook=unique_json_keys)
        document = BuildingDocument.model_validate_json(content)
    except ValidationError as error:
        problems = [f"{'.'.join(map(str, issue['loc']))}: {issue['msg']}" for issue in error.errors()]
        raise BuildingSourceError(path, problems) from None
    except (ValueError, RecursionError) as error:
        raise BuildingSourceError(path, [f"invalid JSON: {error}"]) from None
    problems = consistency_problems(document)
    if problems:
        raise BuildingSourceError(path, problems)
    return document


def unique_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def consistency_problems(document: BuildingDocument) -> list[str]:
    """Check what the schema alone cannot: unique IDs, references, floor agreement and polygon validity."""
    problems = [f"duplicate id {entity_id}" for entity_id, count in id_counts(document).items() if count > 1]
    if document.building.id in (".", ".."):
        problems.append("building id must not be '.' or '..'")
    if OUTSIDE in id_counts(document):
        problems.append(f"{OUTSIDE!r} is reserved for the area outside the building")
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
        elif not math.isfinite(polygon.area) or polygon.area <= 0:
            problems.append(f"space {space.id} must have a finite, positive area")

    for opening in document.openings:
        if opening.floor_id not in floor_ids:
            problems.append(f"opening {opening.id} references unknown floor {opening.floor_id}")
        outside_count = opening.space_ids.count(OUTSIDE)
        if outside_count != (1 if opening.kind == "entrance" else 0):
            problems.append(f"opening {opening.id}: only an entrance connects exactly one side to {OUTSIDE!r}")
        for space_id in opening.space_ids:
            if space_id != OUTSIDE:
                check_space(f"opening {opening.id}", space_id, opening.floor_id)

    for connector in document.vertical_connectors:
        if len(set(connector.floor_ids)) != len(connector.floor_ids):
            problems.append(f"connector {connector.id} repeats a floor")
        if len(connector.floor_ids) != len(connector.space_ids):
            problems.append(f"connector {connector.id} needs one space per floor")
        for floor_id, space_id in zip(connector.floor_ids, connector.space_ids, strict=False):
            if floor_id not in floor_ids:
                problems.append(f"connector {connector.id} references unknown floor {floor_id}")
            check_space(f"connector {connector.id}", space_id, floor_id)

    for asset in document.assets:
        if asset.floor_id not in floor_ids:
            problems.append(f"asset {asset.id} references unknown floor {asset.floor_id}")
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
