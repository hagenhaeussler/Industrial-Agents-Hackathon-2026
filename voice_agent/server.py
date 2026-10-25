"""HTTP server for the voice demo. The browser gets a short-lived conversation token, never the API key."""

import logging
from collections.abc import Callable

from elevenlabs import ElevenLabs
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from voice_agent.settings import VoiceSettings, require_agent_id

log = logging.getLogger(__name__)

TokenSource = Callable[[], str]
"""Returns a WebRTC conversation token for the agent."""


def elevenlabs_token_source(settings: VoiceSettings) -> TokenSource:
    client = ElevenLabs(api_key=settings.api_key)
    agent_id = require_agent_id(settings)
    return lambda: client.conversational_ai.conversations.get_webrtc_token(agent_id=agent_id).token


def create_app(token_source: TokenSource, tools: Starlette | None = None) -> Starlette:
    """`tools` is the MCP app from `voice_agent.tools`; it serves its own path and lifespan."""

    def conversation_token(request: Request) -> JSONResponse:
        try:
            token = token_source()
        except Exception:
            # The upstream error can contain request details; log it here and send the browser a plain message.
            log.exception("ElevenLabs conversation token request failed")
            return JSONResponse({"error": "Could not start a voice conversation."}, status_code=502)
        return JSONResponse({"token": token}, headers={"Cache-Control": "no-store"})

    routes: list[Route | Mount] = [Route("/api/voice/token", conversation_token, methods=["GET"])]
    if tools is None:
        return Starlette(routes=routes)
    return Starlette(routes=[*routes, Mount("/", app=tools)], lifespan=tools.router.lifespan_context)
