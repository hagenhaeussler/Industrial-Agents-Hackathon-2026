"""FastAPI app that serves stored buildings in the building.json format. It never writes."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from building_db.source import BuildingDocument
from building_db.store import connect, load_building


class BuildingSummary(BaseModel):
    id: str
    name: str
    source: str
    floors: int


def create_app(database: Path) -> FastAPI:
    """An app that reads buildings from `database`. The file is opened per request, not at creation."""

    def connection() -> Iterator[sqlite3.Connection]:
        db = connect(database)
        try:
            yield db
        finally:
            db.close()

    Connection = Annotated[sqlite3.Connection, Depends(connection)]
    app = FastAPI(title="Building API")

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

    return app
