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


def load_settings() -> VoiceSettings:
    load_dotenv()
    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        raise MissingSetting("ELEVENLABS_API_KEY is not set. Add it to .env.")
    return VoiceSettings(api_key=api_key, agent_id=os.environ.get("ELEVENLABS_AGENT_ID", "").strip() or None)


def require_agent_id(settings: VoiceSettings) -> str:
    if settings.agent_id is None:
        raise MissingSetting("ELEVENLABS_AGENT_ID is not set. Run `python -m voice_agent sync` and add the printed ID.")
    return settings.agent_id
