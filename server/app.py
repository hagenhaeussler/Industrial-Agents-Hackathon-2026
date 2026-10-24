"""One-worker FastAPI service; API routes precede the SPA history fallback."""

from contextlib import asynccontextmanager
import asyncio
import anyio
import logging
import os
from pathlib import Path
import sqlite3
import subprocess

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from .buildings import BuildingCatalog, BuildingSnapshot, BuildingSummary
from .config import REPO_ROOT, Settings
from .state import StateStore
from .errors import ServiceError
from .service import PlatformService
from .tools import ToolRegistry, registry
from .markers import MarkerService
from .ws import BuildingHub
from .routes_live import router as live_router
from .voice import router as voice_router
from .teams import router as teams_router
from .colab import ColabRuntime, router as colab_router

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
            await anyio.to_thread.run_sync(application.state.store.initialize)
            if application.state.colab is not None:
                await anyio.to_thread.run_sync(application.state.colab.initialize)
            application.state.state_dir_writable = True
        except (OSError, sqlite3.Error):
            logger.exception("Cannot initialise persistent state directory")
            application.state.state_dir_writable = False
        registry.configure(application.state.service, application.state.hub.notify)
        application.state.hub.start()
        # Warm real base snapshots without blocking health/startup on geometry.
        async def warm():
            records = await anyio.to_thread.run_sync(catalog.records)
            targets = [key for key in records if key.startswith('hero-')]
            if 'proc-factory-dev-003' in records:
                targets.append('proc-factory-dev-003')
            for building_id in targets:
                try:
                    await anyio.to_thread.run_sync(application.state.service.current, building_id)
                except Exception:
                    logger.exception('Could not warm building %s', building_id)
        task = asyncio.create_task(warm()) if application.state.state_dir_writable else None
        yield
        if task:
            await task
        await application.state.hub.close()

    application = FastAPI(title="Talk to Your Building", version="C9", lifespan=lifespan)
    application.state.settings = settings
    application.state.catalog = catalog
    application.state.store = StateStore(settings.state_dir,
        admin_token=settings.admin_token if isinstance(settings.admin_token, str) else "",
        demo_mode=settings.demo_mode and settings.allow_unauthenticated_demo_admin)
    application.state.state_dir_writable = False
    application.state.hub = BuildingHub()
    application.state.service = PlatformService(catalog, application.state.store, settings.profile, application.state.hub.notify)
    application.state.registry = ToolRegistry(application.state.service, application.state.hub.notify)
    application.state.markers = MarkerService(application.state.service, settings.public_base_url)
    application.state.service.marker_generator = application.state.markers.generate
    application.state.chat_agent = None
    application.state.colab = ColabRuntime(settings.colab_dir, settings.state_dir) if settings.colab_dir is not None else None
    application.add_middleware(GZipMiddleware, minimum_size=1000)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"], allow_headers=["*"],
    )

    @application.exception_handler(ServiceError)
    async def service_error_handler(request: Request, exc: ServiceError):
        return JSONResponse(status_code=exc.status, content={'detail': exc.message, 'error': exc.payload()})

    @application.exception_handler(Exception)
    async def internal_error_handler(request: Request, exc: Exception):
        from .state import identifier
        request_id = identifier('req')
        logger.exception('Request failed (%s)', request_id)
        return JSONResponse(status_code=500, content={'detail': 'The building request failed.',
            'error': {'code': 'internal', 'message': 'The building request failed.', 'request_id': request_id}})

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
            "detail": jsonable_encoder(exc.errors()), "error": {"code": "invalid_args", "message": "Request arguments are invalid."},
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
        return application.state.service.snapshot(building_id, version)

    application.include_router(live_router)
    application.include_router(voice_router)
    application.include_router(teams_router)
    application.include_router(colab_router)

    @application.websocket('/ws/buildings/{building_id}')
    async def building_socket(socket: WebSocket, building_id: str):
        try:
            await anyio.to_thread.run_sync(catalog.get, building_id)
        except KeyError:
            await socket.close(code=1008)
            return
        await application.state.hub.connection(socket, building_id, lambda: application.state.store.version(building_id))


    @application.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.split("/", 1)[0] in {"api", "ws", "health"}:
            raise api_error(404, "not_found", "This API endpoint does not exist.")
        if path == "devtest":
            path = "devtest.html"
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
