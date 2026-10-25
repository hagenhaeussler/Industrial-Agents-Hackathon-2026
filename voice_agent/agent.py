"""The ElevenLabs agent definition and its sync. This file is the source of truth for the agent's settings."""

from importlib import resources
from typing import Any

from elevenlabs import ElevenLabs

AGENT_NAME = "Building voice agent"
FIRST_MESSAGE = "Hi! Ask me anything about this building."
MCP_SERVER_NAME = "Building tools"
MCP_SECRET_NAME = "building-mcp-authorization"
# Optional context the UI passes as dynamic variables when it starts a conversation; prompt.md uses them. An empty
# string means unknown. `building_id` is also set by the UI but only goes into the MCP header, so it has no default.
CONTEXT_VARIABLES = ("current_space_id", "current_space_name", "destination_id", "destination_name")


def system_prompt() -> str:
    return resources.files("voice_agent").joinpath("prompt.md").read_text(encoding="utf-8")


def conversation_config(mcp_server_id: str) -> dict[str, Any]:
    """Speech recognition, LLM and speech output all run at ElevenLabs. Unset fields keep ElevenLabs' defaults."""
    return {
        "agent": {
            "language": "en",
            "first_message": FIRST_MESSAGE,
            "dynamic_variables": {"dynamic_variable_placeholders": dict.fromkeys(CONTEXT_VARIABLES, "")},
            "prompt": {
                "prompt": system_prompt(),
                "llm": "claude-sonnet-5-5",
                # Tested against low: same reply time (2 to 5 s) and better tool choice, such as comparing every toilet.
                "reasoning_effort": "medium",
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


def mcp_server_identity(mcp_url: str) -> dict[str, Any]:
    """Fields ElevenLabs sets only when it creates an integration."""
    return {
        "name": MCP_SERVER_NAME,
        "description": "Read-only tools for the selected building: rooms, equipment, distances and routes.",
        "url": mcp_url,
        "transport": "STREAMABLE_HTTP",
    }


def mcp_server_behavior(secret_id: str) -> dict[str, Any]:
    """Fields sync updates on an existing integration."""
    return {
        # The tools only read, so they run without asking the user first.
        "approval_policy": "auto_approve_all",
        "request_headers": {
            "Authorization": {"secret_id": secret_id},
            # The UI sets building_id when it starts the conversation; the server answers for that building.
            "X-Building-Id": {"variable_name": "building_id"},
        },
        # Speech before a tool call was repeated after the result. A sound fills the pause instead.
        "pre_tool_speech": "off",
        "tool_call_sound": "typing",
    }


def store_secret(client: ElevenLabs, name: str, value: str) -> str:
    """Create or overwrite a workspace secret, so the token never appears in plain agent settings."""
    secrets = client.conversational_ai.secrets
    existing = next((secret for secret in secrets.list(search=name).secrets if secret.name == name), None)
    if existing is None:
        return secrets.create(name=name, value=value).secret_id
    secrets.update(existing.secret_id, name=name, value=value)
    return existing.secret_id


def create_agent(client: ElevenLabs) -> str:
    """An empty private agent; `sync` fills in its settings and tools."""
    return client.conversational_ai.agents.create(
        name=AGENT_NAME, conversation_config={}, platform_settings=platform_settings()
    ).agent_id


def sync(client: ElevenLabs, agent_id: str, mcp_url: str, mcp_token: str) -> None:
    """Make the agent match this file, with its own MCP integration and secret.

    Only integrations attached to this agent are reused or removed, so other agents in the workspace are safe.
    ElevenLabs cannot change an integration's URL, so a new URL gets a new integration and the old one is removed.
    """
    agents = client.conversational_ai.agents
    servers = client.conversational_ai.mcp_servers
    attached = set(agents.get(agent_id).conversation_config.agent.prompt.mcp_server_ids or [])
    secret_id = store_secret(client, f"{MCP_SECRET_NAME}-{agent_id}", f"Bearer {mcp_token}")
    behavior = mcp_server_behavior(secret_id)
    ours = [server for server in servers.list().mcp_servers if server.id in attached]
    current = next((server for server in ours if server.config.url == mcp_url), None)
    if current is None:
        mcp_server_id = servers.create(config=mcp_server_identity(mcp_url) | behavior).id
    else:
        mcp_server_id = current.id
        servers.update(mcp_server_id, **behavior)

    agents.update(
        agent_id,
        name=AGENT_NAME,
        conversation_config=conversation_config(mcp_server_id),
        platform_settings=platform_settings(),
    )
    for stale in ours:
        if stale.id != mcp_server_id:
            servers.delete(stale.id)
