"""Voice agent commands: python -m voice_agent sync --mcp-url URL | serve BUILDINGS_DIR"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import uvicorn
from elevenlabs import ElevenLabs

from voice_agent.agent import create_agent, sync
from voice_agent.server import create_app, elevenlabs_token_source
from voice_agent.settings import MissingSetting, load_settings, require_agent_id, require_mcp_token
from voice_agent.tools import MCP_PATH, building_files, load_buildings, mcp_app, voice_tools


def railway_mcp_url() -> str:
    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
    if not domain:
        raise MissingSetting("Pass --mcp-url. RAILWAY_PUBLIC_DOMAIN is only set on Railway.")
    return f"https://{domain}{MCP_PATH}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m voice_agent", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    sync_command = commands.add_parser("sync", help="create or update the ElevenLabs agent from voice_agent/agent.py")
    sync_command.add_argument(
        "--mcp-url",
        help=f"public URL of the tools, such as https://example.up.railway.app{MCP_PATH}. "
        "Defaults to this service's own URL on Railway, where sync runs before each deploy.",
    )
    sync_command.add_argument(
        "--create", action="store_true", help="create a new agent; only when ELEVENLABS_AGENT_ID is not set"
    )
    serve = commands.add_parser("serve", help="run the voice server with the tools for every building in a directory")
    serve.add_argument("buildings", type=Path, help="directory searched for building.json files, such as data")
    serve.add_argument("--host", default="127.0.0.1", help="0.0.0.0 inside a container")
    serve.add_argument("--port", type=int, default=8000)
    arguments = parser.parse_args(argv)

    try:
        settings = load_settings()
        mcp_token = require_mcp_token(settings)
        if arguments.command == "sync":
            mcp_url = arguments.mcp_url or railway_mcp_url()
            client = ElevenLabs(api_key=settings.api_key)
            if arguments.create:
                if settings.agent_id is not None:
                    raise MissingSetting("ELEVENLABS_AGENT_ID is set. Remove it to create a new agent.")
                agent_id = create_agent(client)
                print(f"Created agent. Set ELEVENLABS_AGENT_ID={agent_id} in .env and on Railway.")
            else:
                # Without --create, a missing ID stops here, so a deploy never creates agents.
                agent_id = require_agent_id(settings)
            sync(client, agent_id, mcp_url, mcp_token)
            print(f"Updated agent {agent_id}")
            return 0
        logging.basicConfig(level=logging.INFO)
        buildings = load_buildings(building_files(arguments.buildings))
        tools = mcp_app(asyncio.run(voice_tools(buildings)), mcp_token)
        app = create_app(elevenlabs_token_source(settings), tools, buildings.values(), settings.cors_origins)
        uvicorn.run(app, host=arguments.host, port=arguments.port)
        return 0
    except (MissingSetting, ValueError) as error:
        print(error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
