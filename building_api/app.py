"""FastAPI app for validated building imports, stored buildings and routes."""

import hashlib
import sqlite3
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from pydantic import BaseModel

from building_api.imports import import_router
from building_api.localize import Localization, lifespan, localization_router
from building_api.preview import isometric_svg
from building_db.source import BuildingDocument
from building_db.store import connect_readonly, load_building
from building_tools import building as tool_building
from building_tools.building import Building, ToolInputError
from building_tools.network import RouteConditions
from building_tools.routes import PathPoint, Route, route, route_path


class BuildingSummary(BaseModel):
    id: str
    name: str
    source: str
    floors: int


class RouteView(BaseModel):
    """A route from the building tools and the points to draw it."""

    route: Route
    path: list[PathPoint]


def create_app(database: Path, localization: Localization | None = None) -> FastAPI:
    """An app that reads buildings from `database`, with a separate validated upload route.
    With `localization`, it also forwards camera photos to the localization service."""

    def connection() -> Iterator[sqlite3.Connection]:
        db = connect_readonly(database)
        try:
            yield db
        finally:
            db.close()

    Connection = Annotated[sqlite3.Connection, Depends(connection)]

    @lru_cache(maxsize=16)
    def prepared(building_id: str) -> Building:
        """A building ready for route calls. Kept so its walk cache serves later requests."""
        db = connect_readonly(database)
        try:
            return tool_building.load(db, building_id)
        finally:
            db.close()

    @lru_cache(maxsize=1024)
    def preview(building_id: str) -> tuple[str, str]:
        """The rendered preview and its ETag. Stored buildings do not change while the app runs."""
        db = connect_readonly(database)
        try:
            svg = isometric_svg(load_building(db, building_id))
        finally:
            db.close()
        return svg, f'"{hashlib.sha256(svg.encode()).hexdigest()[:16]}"'

    app = FastAPI(title="Locora API", lifespan=lifespan(localization))
    app.include_router(import_router(database))
    app.include_router(localization_router(localization))

    @app.get("/api/buildings")
    def list_buildings(db: Connection) -> list[BuildingSummary]:
        rows = db.execute(
            "SELECT b.id, b.name, b.source, COUNT(f.id) FROM buildings b"
            " LEFT JOIN floors f ON f.building_id = b.id GROUP BY b.id ORDER BY b.id"
        ).fetchall()
        return [BuildingSummary(id=i, name=n, source=s, floors=f) for i, n, s, f in rows]

    @app.get("/api/buildings/{building_id}", responses={404: {"description": "Building not stored"}})
    def get_building(building_id: str, db: Connection) -> BuildingDocument:
        try:
            return load_building(db, building_id)
        except KeyError:
            raise HTTPException(404, f"building {building_id} is not stored") from None

    @app.get(
        "/api/buildings/{building_id}/preview.svg",
        response_class=Response,
        responses={200: {"content": {"image/svg+xml": {}}}, 404: {"description": "Building not stored"}},
    )
    def get_preview(building_id: str, request: Request) -> Response:
        """An isometric exterior view for cards. Browsers reuse it and revalidate with the ETag in the background."""
        try:
            svg, etag = preview(building_id)
        except KeyError:
            raise HTTPException(404, f"building {building_id} is not stored") from None
        headers = {"ETag": etag, "Cache-Control": "public, max-age=3600, stale-while-revalidate=604800"}
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers=headers)
        return Response(svg, media_type="image/svg+xml", headers=headers)

    @app.get(
        "/api/buildings/{building_id}/route",
        responses={404: {"description": "Building not stored"}, 422: {"description": "Unknown stop or bad rule"}},
    )
    def get_route(
        building_id: str,
        stops: Annotated[list[str], Query(min_length=2, description="Space IDs in walking order")],
        step_free: bool = False,
        min_door_width_m: Annotated[float, Query(ge=0)] = 0.0,
        closed: Annotated[list[str] | None, Query(description="Closed space, opening or connector IDs")] = None,
    ) -> RouteView:
        """The same route the building tools give the agents, plus drawing points. Nothing is calculated here."""
        try:
            building = prepared(building_id)
        except ToolInputError:
            raise HTTPException(404, f"building {building_id} is not stored") from None
        conditions = RouteConditions(step_free=step_free, min_door_width_m=min_door_width_m, closed=closed or [])
        try:
            return RouteView(route=route(building, stops, conditions), path=route_path(building, stops, conditions))
        except ToolInputError as error:
            raise HTTPException(422, str(error)) from None

    return app
