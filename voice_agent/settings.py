"""Voice settings from the environment or `.env`. Secrets stay on the server."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class MissingSetting(RuntimeError):
    """A required environment variable is empty or missing."""


@dataclass(frozen=True)
class VoiceSettings:
    api_key: str
    agent_id: str | None
    """None until `python -m voice_agent sync` has created the agent."""
    mcp_token: str | None
    """Bearer token that ElevenLabs sends to our MCP endpoint."""
    cors_origins: tuple[str, ...] = ()
    """Browser origins on other domains that may call the voice routes, such as the deployed UI."""


def load_settings() -> VoiceSettings:
    load_dotenv()
    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        raise MissingSetting("ELEVENLABS_API_KEY is not set. Add it to .env.")
    return VoiceSettings(
        api_key=api_key,
        agent_id=os.environ.get("ELEVENLABS_AGENT_ID", "").strip() or None,
        mcp_token=os.environ.get("BUILDING_MCP_TOKEN", "").strip() or None,
        cors_origins=tuple(
            origin
            for origin in (part.strip() for part in os.environ.get("VOICE_CORS_ORIGINS", "").split(","))
            if origin
        ),
    )


def require_agent_id(settings: VoiceSettings) -> str:
    if settings.agent_id is None:
        raise MissingSetting(
            "ELEVENLABS_AGENT_ID is not set. Run `python -m voice_agent sync --create` once and set the printed ID."
        )
    return settings.agent_id


def require_mcp_token(settings: VoiceSettings) -> str:
    if settings.mcp_token is None:
        raise MissingSetting(
            "BUILDING_MCP_TOKEN is not set. Generate one, for example with `openssl rand -hex 32`, and add it to .env."
        )
    return settings.mcp_token
