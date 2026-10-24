"""Export the same schemas served at /openapi.json, without contacting providers."""
import json
from pathlib import Path
from .app import create_app


def main():
    path = Path(__file__).with_name('openapi.json')
    path.write_text(json.dumps(create_app().openapi(), indent=2, sort_keys=True) + '\n')
    print(f'Exported {path}')


if __name__ == '__main__':
    main()
