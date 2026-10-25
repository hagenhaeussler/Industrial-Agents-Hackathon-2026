"""Command line import: python -m building_db import DATABASE BUILDING_JSON..."""

import argparse
import sys
from pathlib import Path

from building_db.store import connect, import_building


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m building_db", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    import_command = commands.add_parser("import", help="import building.json files into a database")
    import_command.add_argument("database", type=Path, help="SQLite file, created if missing")
    import_command.add_argument("buildings", type=Path, nargs="+", help="building.json files")
    arguments = parser.parse_args(argv)

    connection = connect(arguments.database)
    try:
        results = [import_building(connection, path) for path in arguments.buildings]
    finally:
        connection.close()
    for result in results:
        details = f": {result.message}" if result.message else ""
        print(f"{result.status:<9} {result.building_id or '-'} {result.path}{details}")
    return 0 if all(result.status in ("imported", "unchanged") for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
