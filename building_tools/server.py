"""MCP server for one building. It only translates: validation, units and failures belong to the tool functions."""

from collections.abc import Callable
from typing import Annotated, Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from building_tools import lookup, routes, spatial
from building_tools.building import Building, SpaceType, ToolInputError
from building_tools.network import RouteConditions

SERVER_INSTRUCTIONS = """Tools for one building. Every number they return is calculated from the building data.
Space and asset IDs come from find_spaces and find_assets. Areas are in m², lengths in m."""


def create_server(building: Building) -> FastMCP:
    """An MCP server whose tools answer questions about `building` only."""
    server = FastMCP(f"building-{building.id}", instructions=SERVER_INSTRUCTIONS)

    def run[T](tool: Callable[[], T]) -> T:
        try:
            return tool()
        except ToolInputError as error:
            raise ToolError(str(error)) from None

    @server.tool
    def building_overview() -> lookup.BuildingOverview:
        """Floors from lowest to highest with level, name and elevation; stairs and lifts with their IDs and names;
        and the space, room and asset types with their counts. Use it to map words such as "floor 2", "Lift 1" or
        "generic room" to data."""
        return run(lambda: lookup.building_overview(building))

    @server.tool
    def find_spaces(
        text: Annotated[
            str | None,
            Field(description='Space name or ref, optionally with the floor in brackets: "Office 0.12 (Ground floor)"'),
        ] = None,
        floor: Annotated[str | None, Field(description='Floor ID, name such as "Floor 2", or level number')] = None,
        space_type: Annotated[SpaceType | None, Field(description="Structural type of the space")] = None,
        room_type: Annotated[str | None, Field(description='Room type such as "office" or "generic room"')] = None,
        limit: Annotated[int, Field(ge=0, description="Maximum spaces listed; count and total cover all")] = 50,
    ) -> lookup.SpaceMatches:
        """Find spaces by name or ref, floor, space type and room type. Filters combine. Exact name or ref matches
        win over partial ones, and every match is returned, so duplicate names stay visible. Matches are sorted by
        area, largest first. `count` and `total_area_m2` cover every match, also beyond `limit`."""
        return run(lambda: lookup.find_spaces(building, text, floor, space_type, room_type, limit))

    @server.tool
    def find_assets(
        asset_type: Annotated[str | None, Field(description='Asset type such as "stove"')] = None,
        text: Annotated[str | None, Field(description="Part of the asset name")] = None,
        space_id: Annotated[str | None, Field(description="Only assets in this space")] = None,
        floor: Annotated[str | None, Field(description='Floor ID, name such as "Floor 2", or level number')] = None,
        limit: Annotated[int, Field(ge=0, description="Maximum assets listed; count covers all")] = 50,
    ) -> lookup.AssetMatches:
        """Find equipment and furniture by type, name, space and floor, with the space that holds each item."""
        return run(lambda: lookup.find_assets(building, asset_type, text, space_id, floor, limit))

    @server.tool
    def stacked_spaces(
        space_id: str,
        direction: Literal["above", "below"],
        floors: Annotated[int, Field(ge=1, description="How many floors up or down")] = 1,
    ) -> spatial.StackedSpaces:
        """Spaces on another floor whose outline overlaps this space's outline, largest overlap first, with the
        overlap in m² and as a share of each space. The space directly above or below is the one with the largest
        overlap on the next floor. For two or more floors, set `floors`; do not chain one-floor calls."""
        return run(lambda: spatial.stacked_spaces(building, space_id, direction, floors))

    @server.tool
    def shared_walls(
        space_id: str,
        count_types: Annotated[
            list[SpaceType] | None, Field(description="Space types that count; default room and hall")
        ] = None,
        min_length_m: Annotated[float, Field(gt=0)] = 1.0,
        max_gap_m: Annotated[float, Field(ge=0)] = 0.35,
    ) -> spatial.SharedWalls:
        """Spaces on the same floor that share a wall with this space: at least `min_length_m` of one outline runs
        within `max_gap_m` of the other, because walls have thickness. Doors do not matter. `count` is the number
        of spaces in `counted`; spaces of other types are listed in `not_counted` and are already left out."""
        return run(lambda: spatial.shared_walls(building, space_id, count_types, min_length_m, max_gap_m))

    @server.tool
    def distance_3d(first_space_id: str, second_space_id: str) -> spatial.Distance3D:
        """Straight-line distance in m between two space centres. A centre is the polygon centroid at the floor's
        elevation."""
        return run(lambda: spatial.distance_3d(building, first_space_id, second_space_id))

    @server.tool
    def route(
        stops: Annotated[list[str], Field(min_length=2, description="Space IDs to visit in order, start first")],
        conditions: RouteConditions | None = None,
        leg_conditions: Annotated[
            list[RouteConditions] | None, Field(description="Conditions per leg, if they differ between legs")
        ] = None,
    ) -> routes.Route:
        """Shortest walking route through the stops in order, with its length in m, every space passed and every
        door, opening, stair and lift used. The length follows the building's route model: walks inside spaces
        stay off the walls, stairs count 2 m per metre climbed, a lift 15 m plus 1 m per metre climbed. An
        unreachable leg says which conditions block it. A route never goes round the outside of the building."""
        return run(lambda: routes.route(building, stops, conditions, leg_conditions))

    @server.tool
    def reachable_spaces(
        start: Annotated[str, Field(description="Space ID where the walk starts")],
        conditions: RouteConditions | None = None,
        floor: Annotated[str | None, Field(description='Floor ID, name such as "Floor 2", or level number')] = None,
        space_types: Annotated[list[SpaceType] | None, Field(description="Only these space types")] = None,
        room_type: Annotated[str | None, Field(description='Only this room type, such as "meeting room"')] = None,
        asset_type: Annotated[
            str | None, Field(description='Only spaces holding this asset type, such as "stove"')
        ] = None,
        limit: Annotated[int, Field(ge=0, description="Maximum spaces listed; count covers all")] = 50,
    ) -> routes.ReachableSpaces:
        """Spaces a walk from `start` can reach under the conditions, nearest first, with walking distances in m.
        Use it to count reachable rooms, or to find the nearest space that holds an asset. The start space is
        included at distance 0 when it passes the filters."""
        return run(
            lambda: routes.reachable_spaces(
                building, start, conditions, floor, space_types, room_type, asset_type, limit
            )
        )

    @server.tool
    def exit_distance_change(
        floor: Annotated[str, Field(description="Floor whose spaces are compared")],
        change: Annotated[RouteConditions, Field(description="The change, such as added_doors or closed elements")],
        min_change_m: Annotated[float, Field(ge=0)] = 1.0,
        space_types: Annotated[list[SpaceType] | None, Field(description="Spaces compared; default rooms")] = None,
    ) -> routes.ExitDistanceChange:
        """How a change alters each space's walk out of the building, to its nearest entrance, on one floor.
        Compares the building as it is with the building under `change`, and counts the spaces whose walk became
        shorter or longer by more than `min_change_m`. An added door sits in the middle of the shared wall."""
        return run(lambda: routes.exit_distance_change(building, floor, change, min_change_m, space_types))

    return server
