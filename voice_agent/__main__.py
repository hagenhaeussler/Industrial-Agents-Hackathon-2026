"""Voice agent commands: python -m voice_agent sync | serve"""

import argparse
import logging
import sys

import uvicorn
from elevenlabs import ElevenLabs

from voice_agent.agent import sync_agent
from voice_agent.server import create_app, elevenlabs_token_source
from voice_agent.settings import MissingSetting, load_settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m voice_agent", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("sync", help="create or update the ElevenLabs agent from voice_agent/agent.py")
    serve = commands.add_parser("serve", help="run the voice server")
    serve.add_argument("--host", default="127.0.0.1", help="0.0.0.0 inside a container")
    serve.add_argument("--port", type=int, default=8000)
    arguments = parser.parse_args(argv)

    try:
        settings = load_settings()
        if arguments.command == "sync":
            agent_id = sync_agent(ElevenLabs(api_key=settings.api_key), settings.agent_id)
            if settings.agent_id is None:
                print(f"Created agent. Add this line to .env:\nELEVENLABS_AGENT_ID={agent_id}")
            else:
                print(f"Updated agent {agent_id}")
            return 0
        logging.basicConfig(level=logging.INFO)
        uvicorn.run(create_app(elevenlabs_token_source(settings)), host=arguments.host, port=arguments.port)
        return 0
    except MissingSetting as error:
        print(error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
