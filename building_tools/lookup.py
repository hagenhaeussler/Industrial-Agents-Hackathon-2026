"""Lookup tools: building overview, space search and asset search."""

import re
from collections import Counter
from typing import Literal

from building_db.source import Space
from building_tools.building import (
    Building,
    FloorSummary,
    SpaceSummary,
    SpaceType,
    ToolResult,
    normalize,
)


class FloorOverview(FloorSummary):
    height_m: float
    space_count: int


class ConnectorSummary(ToolResult):
    id: str
    name: str
    kind: Literal["stairs", "lift"]
    step_free: bool
    floors: list[str]
    """Names of the floors it serves, lowest first."""


class BuildingOverview(ToolResult):
    building_id: str
    name: str
    floors: list[FloorOverview]
    connectors: list[ConnectorSummary]
    """Stairs and lifts. Use their IDs to close them in route conditions."""
    space_types: dict[str, int]
    room_types: dict[str, int]
    asset_types: dict[str, int]


def building_overview(building: Building) -> BuildingOverview:
    """Floors from lowest to highest, stairs and lifts, and the space, room and asset types with their counts."""
    levels = {floor.id: floor.level for floor in building.floors}
    spaces_per_floor = Counter(space.floor_id for space in building.document.spaces)
    return BuildingOverview(
        building_id=building.id,
        name=building.document.building.name,
        floors=[
            FloorOverview(
                **building.floor_summary(floor).model_dump(),
                height_m=floor.height_m,
                space_count=spaces_per_floor[floor.id],
            )
            for floor in building.floors
        ],
        connectors=[
            ConnectorSummary(
                id=connector.id,
                name=connector.name,
                kind=connector.kind,
                step_free=connector.step_free,
                floors=[building.floor_by_id[f].name for f in sorted(connector.floor_ids, key=levels.__getitem__)],
            )
            for connector in building.document.vertical_connectors
        ],
        space_types=dict(Counter(space.type for space in building.document.spaces).most_common()),
        room_types=dict(Counter(space.room_type for space in building.document.spaces).most_common()),
        asset_types=dict(Counter(asset.type for asset in building.document.assets).most_common()),
    )


class SpaceMatches(ToolResult):
    match: Literal["exact", "partial", "filter"]
    count: int
    total_area_m2: float
    spaces: list[SpaceSummary]
    """Largest first. Shortened to `limit`; `count` and `total_area_m2` cover every match."""


FLOOR_SUFFIX = re.compile(r"^(?P<name>.*\S)\s*\((?P<floor>[^()]+)\)\s*$")


def find_spaces(
    building: Building,
    text: str | None = None,
    floor: str | None = None,
    space_type: SpaceType | None = None,
    room_type: str | None = None,
    limit: int = 50,
) -> SpaceMatches:
    """Spaces by name or ref, floor, space type and room type. All filters are optional and combine.

    A trailing floor in brackets, as in "Office 0.12 (Ground floor)", is read as the floor filter. Exact name or
    ref matches win over partial name matches. Every match is returned, so duplicate names stay visible.
    """
    if text is not None and floor is None:
        suffix = FLOOR_SUFFIX.match(text)
        if suffix and any(normalize(suffix["floor"]) == normalize(f.name) for f in building.floors):
            text, floor = suffix["name"], suffix["floor"]

    candidates = building.document.spaces
    if floor is not None:
        floor_id = building.floor(floor).id
        candidates = [space for space in candidates if space.floor_id == floor_id]
    if space_type is not None:
        candidates = [space for space in candidates if space.type == space_type]
    if room_type is not None:
        wanted_type = building.room_type(room_type)
        candidates = [space for space in candidates if normalize(space.room_type) == wanted_type]

    match: Literal["exact", "partial", "filter"] = "filter"
    if text is not None:
        wanted = normalize(text)
        exact = [space for space in candidates if wanted in (normalize(space.name), normalize(space.ref))]
        match = "exact" if exact else "partial"
        candidates = exact or [space for space in candidates if wanted in normalize(space.name)]

    return space_matches(building, candidates, match, limit)


def space_matches(
    building: Building, spaces: list[Space], match: Literal["exact", "partial", "filter"], limit: int
) -> SpaceMatches:
    ranked = sorted(spaces, key=lambda space: building.area_by_id[space.id], reverse=True)
    return SpaceMatches(
        match=match,
        count=len(ranked),
        total_area_m2=round(sum(building.area_by_id[space.id] for space in ranked), 2),
        spaces=[building.space_summary(space) for space in ranked[: max(limit, 0)]],
    )


class AssetSummary(ToolResult):
    id: str
    name: str
    type: str
    category: str
    space: SpaceSummary
    position: tuple[float, float]


class AssetMatches(ToolResult):
    count: int
    assets: list[AssetSummary]
    """Shortened to `limit`; `count` covers every match."""


def find_assets(
    building: Building,
    asset_type: str | None = None,
    text: str | None = None,
    space_id: str | None = None,
    floor: str | None = None,
    limit: int = 50,
) -> AssetMatches:
    """Assets by type (such as "stove"), name text, space and floor. All filters are optional and combine."""
    if space_id is not None:
        building.space(space_id)
    floor_id = building.floor(floor).id if floor is not None else None
    wanted_type = building.asset_type(asset_type) if asset_type is not None else None

    assets = [
        asset
        for asset in building.document.assets
        if (wanted_type is None or normalize(asset.type) == wanted_type)
        and (text is None or normalize(text) in normalize(asset.name))
        and (space_id is None or asset.space_id == space_id)
        and (floor_id is None or asset.floor_id == floor_id)
    ]
    return AssetMatches(
        count=len(assets),
        assets=[
            AssetSummary(
                id=asset.id,
                name=asset.name,
                type=asset.type,
                category=asset.category,
                space=building.space_summary(building.space_by_id[asset.space_id]),
                position=asset.position,
            )
            for asset in assets[: max(limit, 0)]
        ],
    )
