"""The ElevenLabs agent definition and its sync. This file is the source of truth for the agent's settings."""

from importlib import resources
from typing import Any

from elevenlabs import ElevenLabs

AGENT_NAME = "Building voice agent"
FIRST_MESSAGE = "Hi! Ask me anything about this building."
MCP_SERVER_NAME = "Building tools"
MCP_SECRET_NAME = "building-mcp-authorization"


def system_prompt() -> str:
    return resources.files("voice_agent").joinpath("prompt.md").read_text(encoding="utf-8")


def conversation_config(mcp_server_id: str) -> dict[str, Any]:
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
                "mcp_server_ids": [mcp_server_id],
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


def mcp_server_config(mcp_url: str, secret_id: str) -> dict[str, Any]:
    return {
        "name": MCP_SERVER_NAME,
        "description": "Read-only tools for one building: rooms, equipment, distances and routes.",
        "url": mcp_url,
        "transport": "STREAMABLE_HTTP",
        # The tools only read, so they run without asking the user first.
        "approval_policy": "auto_approve_all",
        "request_headers": {"Authorization": {"secret_id": secret_id}},
    }


def store_secret(client: ElevenLabs, name: str, value: str) -> str:
    """Create or overwrite a workspace secret, so the token never appears in plain agent settings."""
    secrets = client.conversational_ai.secrets
    existing = next((secret for secret in secrets.list(search=name).secrets if secret.name == name), None)
    if existing is None:
        return secrets.create(name=name, value=value).secret_id
    secrets.update(existing.secret_id, name=name, value=value)
    return existing.secret_id


def sync(client: ElevenLabs, agent_id: str | None, mcp_url: str, mcp_token: str) -> str:
    """Make ElevenLabs match this file: the MCP integration and the agent. Returns the agent ID.

    ElevenLabs cannot change an integration's URL, so a new URL gets a new integration and the old one is removed.
    """
    servers = client.conversational_ai.mcp_servers
    secret_id = store_secret(client, MCP_SECRET_NAME, f"Bearer {mcp_token}")
    config = mcp_server_config(mcp_url, secret_id)
    ours = [server for server in servers.list().mcp_servers if server.config.name == MCP_SERVER_NAME]
    current = next((server for server in ours if server.config.url == mcp_url), None)
    if current is None:
        mcp_server_id = servers.create(config=config).id
    else:
        mcp_server_id = current.id
        servers.update(
            mcp_server_id, approval_policy=config["approval_policy"], request_headers=config["request_headers"]
        )

    settings = {
        "name": AGENT_NAME,
        "conversation_config": conversation_config(mcp_server_id),
        "platform_settings": platform_settings(),
    }
    if agent_id is None:
        agent_id = client.conversational_ai.agents.create(**settings).agent_id
    else:
        client.conversational_ai.agents.update(agent_id, **settings)

    for stale in ours:
        if stale.id != mcp_server_id:
            servers.delete(stale.id)
    return agent_id
