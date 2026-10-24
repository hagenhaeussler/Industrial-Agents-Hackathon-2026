"""Server-only ElevenLabs WebRTC token exchange (no provider key in responses)."""

import os
from typing import Literal

import httpx
from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/voice", tags=["voice"])
TOKEN_URL = "https://api.elevenlabs.io/v1/convai/conversation/token"


class VoiceToken(BaseModel):
    token: str
    agent_id: str


def unavailable(message: str) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": message, "error": {"code": "voice_unavailable", "message": message}},
        headers={"Cache-Control": "no-store"},
    )


@router.get("/token", response_model=VoiceToken, responses={503: {"description": "Voice unavailable; use text chat."}})
def conversation_token(response: Response, agent: Literal["navigator", "admin"] = "navigator"):
    """Mint a fresh short-lived token; provider configuration remains server-side."""
    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    agent_id = os.environ.get(f"ELEVENLABS_AGENT_ID_{agent.upper()}", "").strip()
    if not api_key or not agent_id:
        return unavailable("Voice is not configured yet. Please use text chat.")
    try:
        with httpx.Client(timeout=10.0) as client:
            provider_response = client.get(TOKEN_URL, params={"agent_id": agent_id}, headers={"xi-api-key": api_key})
            provider_response.raise_for_status()
            body = provider_response.json()
        token = body.get("token") if isinstance(body, dict) else None
        if not isinstance(token, str) or not token.strip():
            return unavailable("The voice provider could not start a session. Please use text chat.")
    except (httpx.HTTPError, ValueError):
        # Provider error text/URLs can contain credentials; return only our fixed message.
        return unavailable("The voice provider is unavailable. Please use text chat.")
    response.headers["Cache-Control"] = "no-store"
    return VoiceToken(token=token, agent_id=agent_id)
