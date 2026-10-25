"""HTTP server for the voice demo. The browser gets a short-lived conversation token, never the API key."""

import logging
from collections.abc import Callable, Iterable, Sequence

from elevenlabs import ElevenLabs
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from building_tools.building import Building
from voice_agent.photo import PhotoService, photo_routes
from voice_agent.settings import VoiceSettings, require_agent_id

log = logging.getLogger(__name__)

TokenSource = Callable[[], str]
"""Returns a WebRTC conversation token for the agent."""


def elevenlabs_token_source(settings: VoiceSettings) -> TokenSource:
    client = ElevenLabs(api_key=settings.api_key)
    agent_id = require_agent_id(settings)
    return lambda: client.conversational_ai.conversations.get_webrtc_token(agent_id=agent_id).token


def create_app(
    token_source: TokenSource,
    tools: Starlette | None = None,
    buildings: Iterable[Building] = (),
    cors_origins: Sequence[str] = (),
    photos: PhotoService | None = None,
) -> Starlette:
    """`tools` is the MCP app from `voice_agent.tools`; it serves its own path and lifespan. `buildings` are the
    buildings it serves; a conversation passes one of their IDs as the `building_id` dynamic variable. `cors_origins`
    lets a UI on another domain call the voice routes."""
    building_list = sorted(
        ({"id": building.id, "name": building.document.building.name} for building in buildings),
        key=lambda building: building["name"].casefold(),
    )

    def list_buildings(request: Request) -> JSONResponse:
        return JSONResponse(building_list)

    def conversation_token(request: Request) -> JSONResponse:
        try:
            token = token_source()
        except Exception:
            # The upstream error can contain request details; log it here and send the browser a plain message.
            log.exception("ElevenLabs conversation token request failed")
            return JSONResponse({"error": "Could not start a voice conversation."}, status_code=502)
        return JSONResponse({"token": token}, headers={"Cache-Control": "no-store"})

    routes: list[Route | Mount] = [
        Route("/api/voice/token", conversation_token, methods=["GET"]),
        Route("/api/voice/buildings", list_buildings, methods=["GET"]),
        *photo_routes(photos, list(cors_origins)),
    ]
    # No cookies or browser MCP access. Photos use an explicit origin check as well as CORS.
    middleware = [Middleware(CORSMiddleware, allow_origins=list(cors_origins),
                             allow_methods=["GET", "POST"], allow_headers=["Content-Type"])]
    if tools is None:
        return Starlette(routes=routes, middleware=middleware)
    return Starlette(
        routes=[*routes, Mount("/", app=tools)], middleware=middleware, lifespan=tools.router.lifespan_context
    )
