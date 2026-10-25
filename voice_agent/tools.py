"""The building tools for ElevenLabs: the shared MCP server for every served building, behind a bearer token."""

import hmac
from collections.abc import Iterable
from pathlib import Path
from typing import Annotated, Any

import mcp.types as mt
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools import Tool, forward_raw
from fastmcp.tools.base import ToolResult
from fastmcp.tools.tool_transform import ArgTransform, TransformedTool
from pydantic import Field
from starlette.applications import Starlette
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from building_db.store import connect, import_building
from building_tools.building import Building, load
from building_tools.network import RouteConditions
from building_tools.server import create_server

MCP_PATH = "/mcp"
# ElevenLabs fills this header from the conversation's `building_id` dynamic variable on every tool call.
BUILDING_HEADER = "x-building-id"

# ElevenLabs drops tools whose parameters hold nested objects such as RouteConditions. These tools get flat
# condition parameters instead; the calculation stays in building_tools. The UI reads `stops`, `step_free`, `closed`
# and `min_door_width_m` from route tool calls to draw the same route, so keep these names stable.
FLAT_CONDITION_TOOLS = ("route", "reachable_spaces")
# Needs added doors as pairs, which also has no flat form. It answers benchmark what-if questions, not visitors.
HIDDEN_TOOLS = {"exit_distance_change"}


def condition_field(name: str) -> Any:
    return Field(description=RouteConditions.model_fields[name].description)


async def with_flat_conditions(
    step_free: Annotated[bool, condition_field("step_free")] = False,
    min_door_width_m: Annotated[float, condition_field("min_door_width_m"), Field(ge=0)] = 0.0,
    closed: Annotated[list[str] | None, condition_field("closed")] = None,
    no_pass_through_room_types: Annotated[list[str] | None, condition_field("no_pass_through_room_types")] = None,
    **arguments: Any,
) -> Any:
    conditions = RouteConditions(
        step_free=step_free,
        min_door_width_m=min_door_width_m,
        closed=closed or [],
        no_pass_through_room_types=no_pass_through_room_types or [],
    )
    return await forward_raw(conditions=conditions.model_dump(), **arguments)


def flatten_conditions(tool: Tool) -> TransformedTool:
    hidden = {
        name: ArgTransform(hide=True)
        for name in ("conditions", "leg_conditions")
        if name in tool.parameters["properties"]
    }
    return TransformedTool.from_tool(tool, transform_fn=with_flat_conditions, transform_args=hidden)


async def voice_server(building: Building) -> FastMCP:
    """The shared server for one building, with tool schemas ElevenLabs accepts."""
    server = create_server(building)
    for name in FLAT_CONDITION_TOOLS:
        tool = await server.get_tool(name)
        if tool is None:
            raise RuntimeError(f"building_tools no longer has the tool {name!r}")
        server.local_provider.remove_tool(name)
        server.add_tool(flatten_conditions(tool))
    server.disable(names=HIDDEN_TOOLS)
    return server


class SelectBuilding(Middleware):
    """Runs each tool call on the server of the building named in the request's building header."""

    def __init__(self, servers: dict[str, FastMCP]) -> None:
        self.servers = servers

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        building_id = get_http_headers().get(BUILDING_HEADER, "")
        server = self.servers.get(building_id)
        if server is None:
            raise ToolError(
                "No building is selected for this conversation." if not building_id else "Unknown building."
            )
        return await server.call_tool(context.message.name, context.message.arguments)


async def voice_tools(buildings: dict[str, Building]) -> FastMCP:
    """One MCP server for all buildings. The tool list is the same for every building, so it comes from any one of
    them; each call runs on the building the conversation selected."""
    if not buildings:
        raise ValueError("no buildings to serve")
    servers = {building_id: await voice_server(building) for building_id, building in buildings.items()}
    front = await voice_server(next(iter(buildings.values())))
    front.add_middleware(SelectBuilding(servers))
    return front


def load_buildings(paths: Iterable[Path]) -> dict[str, Building]:
    """Import building.json files into an in-memory database and load them for the tools, by building ID."""
    connection = connect(":memory:")
    try:
        ids = []
        for path in paths:
            result = import_building(connection, path)
            if result.building_id is None or result.status not in ("imported", "unchanged"):
                raise ValueError(f"cannot load {path}: {result.status} {result.message}".strip())
            ids.append(result.building_id)
        return {building_id: load(connection, building_id) for building_id in ids}
    finally:
        connection.close()


def building_files(root: Path) -> list[Path]:
    """Every building.json under `root`, such as data/."""
    paths = sorted(root.glob("**/building.json"))
    if not paths:
        raise ValueError(f"no building.json under {root}")
    return paths


class BearerAuth:
    """Rejects requests without `Authorization: Bearer <token>`. The MCP endpoint is public for ElevenLabs."""

    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self.expected = f"Bearer {token}".encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            supplied = dict(scope["headers"]).get(b"authorization", b"")
            if not hmac.compare_digest(supplied, self.expected):
                await JSONResponse({"error": "unauthorized"}, status_code=401)(scope, receive, send)
                return
        await self.app(scope, receive, send)


def mcp_app(server: FastMCP, token: str) -> Starlette:
    # Stateless: each tool call stands alone, so redeploys and restarts do not break ElevenLabs sessions.
    return server.http_app(
        path=MCP_PATH, stateless_http=True, middleware=[StarletteMiddleware(BearerAuth, token=token)]
    )
