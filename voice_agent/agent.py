"""The ElevenLabs agent definition and its sync. This file is the source of truth for the agent's settings."""

from importlib import resources
from typing import Any

from elevenlabs import ElevenLabs

AGENT_NAME = "Building voice agent"
FIRST_MESSAGE = "Hi! Ask me anything about this building."


def system_prompt() -> str:
    return resources.files("voice_agent").joinpath("prompt.md").read_text(encoding="utf-8")


def conversation_config() -> dict[str, Any]:
    """Speech recognition, LLM and speech output all run at ElevenLabs. Unset fields keep ElevenLabs' defaults."""
    return {
        "agent": {
            "language": "en",
            "first_message": FIRST_MESSAGE,
            "prompt": {
                "prompt": system_prompt(),
                "llm": "claude-sonnet-5-5",
                # Low effort keeps turn-taking fast; tools do the calculations.
                "reasoning_effort": "low",
                "backup_llm_config": {"preference": "override", "order": ["claude-haiku-5-5"]},
            },
        },
    }


def platform_settings() -> dict[str, Any]:
    # Private agent: a conversation needs a short-lived token from our server, so the API key never reaches a browser.
    # The token route is public on Railway, so call limits cap what an anonymous caller can start.
    return {
        "auth": {"enable_auth": True},
        "call_limits": {"agent_concurrency_limit": 3, "daily_limit": 200},
    }


def sync_agent(client: ElevenLabs, agent_id: str | None) -> str:
    """Create the agent, or update the existing one to match this file. Returns the agent ID."""
    if agent_id is None:
        created = client.conversational_ai.agents.create(
            name=AGENT_NAME, conversation_config=conversation_config(), platform_settings=platform_settings()
        )
        return created.agent_id
    client.conversational_ai.agents.update(
        agent_id, name=AGENT_NAME, conversation_config=conversation_config(), platform_settings=platform_settings()
    )
    return agent_id
