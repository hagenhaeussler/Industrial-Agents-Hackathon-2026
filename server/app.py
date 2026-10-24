"""One-worker FastAPI service; API routes precede the SPA history fallback."""

from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
import sqlite3
import subprocess

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from .buildings import BuildingCatalog, BuildingSnapshot, BuildingSummary
from .config import REPO_ROOT, Settings
from .state import StateStore

logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    ok: bool
    commit: str
    profile: str
    state_dir_writable: bool
    buildings: int


def commit_sha() -> str:
    if sha := os.environ.get("RAILWAY_GIT_COMMIT_SHA"):
        return sha
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True,
            stderr=subprocess.DEVNULL, timeout=2,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def api_error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status, detail={"code": code, "message": message})


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    catalog = BuildingCatalog(settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        try:
            application.state.store.initialize()
            application.state.state_dir_writable = True
        except (OSError, sqlite3.Error):
            logger.exception("Cannot initialise persistent state directory")
            application.state.state_dir_writable = False
        yield

    application = FastAPI(title="Talk to Your Building", version="C1", lifespan=lifespan)
    application.state.settings = settings
    application.state.catalog = catalog
    application.state.store = StateStore(settings.state_dir)
    application.state.state_dir_writable = False
    application.add_middleware(GZipMiddleware, minimum_size=1000)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"], allow_headers=["*"],
    )

    @application.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            error = exc.detail
            detail = error["message"]
        else:
            detail = exc.detail
            code = {404: "not_found", 403: "forbidden", 422: "invalid_args"}.get(exc.status_code, "internal")
            error = {"code": code, "message": str(detail)}
        return JSONResponse(status_code=exc.status_code, content={"detail": detail, "error": error}, headers=exc.headers)

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={
            "detail": exc.errors(), "error": {"code": "invalid_args", "message": "Request arguments are invalid."},
        })

    @application.get("/health", response_model=HealthResponse)
    def health():
        writable = application.state.state_dir_writable
        result = HealthResponse(
            ok=writable, commit=commit_sha(), profile=settings.profile,
            state_dir_writable=writable, buildings=len(catalog.records()),
        )
        if not writable:
            return JSONResponse(status_code=503, content=result.model_dump())
        return result

    @application.get("/api/buildings", response_model=list[BuildingSummary])
    def buildings():
        return [record.summary for record in catalog.records().values()]

    @application.get("/api/buildings/{building_id}", response_model=BuildingSnapshot)
    def snapshot(building_id: str, version: int | None = Query(default=None, ge=0)):
        if version not in (None, 0):
            raise api_error(409, "version_conflict", "Only base version 0 is available before the event store is connected.")
        try:
            return catalog.snapshot(building_id)
        except KeyError as exc:
            raise api_error(404, "not_found", str(exc.args[0])) from exc

    @application.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.split("/", 1)[0] in {"api", "ws", "health"}:
            raise api_error(404, "not_found", "This API endpoint does not exist.")
        static_root = settings.static_dir.resolve()
        candidate = (static_root / path).resolve()
        if not candidate.is_relative_to(static_root):
            raise api_error(404, "not_found", "File not found.")
        if candidate.is_file():
            return FileResponse(candidate)
        # Missing bundled assets should never return HTML under a JS/CSS URL.
        if path.startswith("assets/") or Path(path).suffix:
            raise api_error(404, "not_found", "File not found.")
        index = static_root / "index.html"
        if index.is_file():
            return FileResponse(index, headers={"Cache-Control": "no-cache"})
        raise api_error(404, "not_available", "The web application has not been built yet.")

    return application


app = create_app()
