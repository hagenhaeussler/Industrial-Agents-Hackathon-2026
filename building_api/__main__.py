"""Command line: serve the API or print its OpenAPI schema for the TypeScript type generator."""

import argparse
import json
import sys
from pathlib import Path

import uvicorn

from building_api.app import create_app
from building_api.web import add_web_app


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m building_api")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="serve buildings from a database over HTTP")
    serve.add_argument("database", type=Path)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--web", type=Path, help="also serve the built web app from this directory")
    commands.add_parser("openapi", help="print the OpenAPI schema as JSON")
    args = parser.parse_args()

    if args.command == "openapi":
        # The schema does not depend on database content, so no file is opened.
        json.dump(create_app(Path("unused")).openapi(), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return
    if not args.database.is_file():
        sys.exit(f"building database {args.database} does not exist")
    app = create_app(args.database)
    if args.web:
        add_web_app(app, args.web)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
