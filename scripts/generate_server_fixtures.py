"""Generate labelled C2 examples from real kit geometry, without live state or gold labels."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from starter_agent.building_map import BuildingMap

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_TIME = "2026-10-24T20:00:00Z"
COMMAND = "uv run python scripts/generate_server_fixtures.py"


def metadata(replace_by: str) -> dict:
    return {
        "producer": "Manuel's codex",
        "contract": "C2",
        "generated_by": COMMAND,
        "replace_by": replace_by,
        "kind": "contract example with real building IDs and geometry; not live server state",
    }


def generate(building_path: Path, output_dir: Path) -> dict[str, dict]:
    # BuildingMap.load opens building.json only; questions and their labels are never read.
    building = BuildingMap.load(building_path)
    building_id = building.data["building"]["id"]
    ground = min(building.floors.values(), key=lambda floor: (floor["level"], floor["id"]))
    spaces = sorted((space for space in building.spaces.values() if space["floor_id"] == ground["id"]),
                    key=lambda space: (space.get("type") != "corridor", space["id"]))
    if not spaces:
        raise ValueError("Fixture building has no starting space on its lowest floor.")
    start = spaces[0]
    lifts = sorted((item for item in building.connectors.values() if item["kind"] == "lift"),
                   key=lambda item: item["id"])
    if not lifts:
        raise ValueError("Fixture building has no real lift to close.")
    lift = lifts[0]
    session = {
        "_fixture": metadata("POST /api/sessions; GET /api/sessions/{session_id}"),
        "session_id": "b73bc7e4e0984aa28d94755aeef5160b",
        "building_id": building_id,
        "device": "desk",
        "role": "navigator",
        "profile": "walk",
        "constraints": {},
        "position": {
            "space_id": start["id"], "floor_id": start["floor_id"],
            "point": list(building.anchor(start["id"])), "heading_deg": None,
            "source": "desk", "marker_id": None, "confidence": "medium", "updated_at": FIXTURE_TIME,
        },
        "active_tour_id": None,
        "updated_at": FIXTURE_TIME,
    }
    event = {
        "event_id": "evt-1", "building_id": building_id, "building_version": 1,
        "kind": "close", "edit": {"action": "close", "target": lift["id"], "second_target": None, "value": None},
        "undoes": None, "op_id": "d348444a-7a98-4f56-96ec-25e742b32d9b", "proposal_id": "prp_fixtureclose",
        "session_id": "1b037bf2fcbf4b4693abc81ce7b760dd", "author_role": "admin",
        "summary": f"{lift['name']} closed", "created_at": FIXTURE_TIME,
    }
    events = {
        "_fixture": metadata(f"GET /api/buildings/{building_id}/events; WS /ws/buildings/{building_id}"),
        "building_id": building_id,
        "events": [event],
        "messages": [
            {"type": "hello", "building_id": building_id, "building_version": 0},
            {"type": "building_changed", "building_id": building_id, "building_version": 1,
             "event": event, "at": FIXTURE_TIME},
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {"session.json": session, "events_close_lift.json": events}
    for filename, payload in payloads.items():
        (output_dir / filename).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payloads


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--building", type=Path, default=ROOT / "data/dev/proc-factory-dev-003")
    parser.add_argument("--output", type=Path, default=ROOT / "fixtures")
    args = parser.parse_args()
    payloads = generate(args.building, args.output)
    session = payloads["session.json"]
    target = payloads["events_close_lift.json"]["events"][0]["edit"]["target"]
    print(f"Wrote {len(payloads)} C2 fixture files: building={session['building_id']}, "
          f"start={session['position']['space_id']}, lift={target}. These are labelled examples, not live state.")


if __name__ == "__main__":
    main()
