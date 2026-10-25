"""Bounded JSON uploads through the same validated importer used by the command line."""

import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from building_db.store import connect_existing, import_building

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


class BuildingImport(BaseModel):
    id: str
    status: Literal["imported", "unchanged"]


def save_upload(database: Path, content: bytes) -> BuildingImport:
    """Validate and store one upload. Untrusted names and IDs never become file paths."""
    with TemporaryDirectory(prefix="locora-import-") as directory:
        path = Path(directory) / "building.json"
        path.write_bytes(content)
        with closing(connect_existing(database)) as db:
            result = import_building(db, path)
    if result.status == "failed":
        raise HTTPException(422, f"Invalid building.json: {result.message}")
    if result.status == "conflict":
        raise HTTPException(
            409, "A building with this ID and different content is already stored. Nothing was changed."
        )
    if result.building_id is None:
        raise RuntimeError("successful import has no building ID")
    return BuildingImport(id=result.building_id, status=result.status)


def import_router(database: Path) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/api/buildings/import",
        response_model=BuildingImport,
        responses={
            201: {"model": BuildingImport},
            409: {"description": "Building ID conflict"},
            413: {"description": "File exceeds 20 MiB"},
            415: {"description": "JSON required"},
            422: {"description": "Invalid building"},
            503: {"description": "Storage unavailable"},
        },
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/BuildingDocument"}},
                },
            }
        },
    )
    async def upload_building(request: Request, response: Response) -> BuildingImport:
        if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
            raise HTTPException(415, "Upload building.json as application/json.")
        content = bytearray()
        async for chunk in request.stream():
            if len(content) + len(chunk) > MAX_UPLOAD_BYTES:
                raise HTTPException(413, "The file exceeds the 20 MiB limit.")
            content.extend(chunk)
        if not content:
            raise HTTPException(422, "The file is empty. Choose a building.json file.")
        try:
            imported = await run_in_threadpool(save_upload, database, bytes(content))
        except (OSError, sqlite3.Error, RuntimeError):
            raise HTTPException(503, "The building could not be saved. Try again.") from None
        response.status_code = 201 if imported.status == "imported" else 200
        return imported

    return router
