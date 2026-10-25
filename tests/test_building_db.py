"""Building database tests: import fidelity, stored room areas, safe re-import and rejected input."""

import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from typing import Any

from building_db.source import BuildingDocument, read_building
from building_db.store import connect, import_building, load_building

REPO = Path(__file__).resolve().parents[1]
DEV_BUILDING = REPO / "data" / "dev" / "osm-way22744230"


def sorted_by_id(document: BuildingDocument) -> BuildingDocument:
    """The source in the order load_building returns it."""
    sections = ("floors", "spaces", "openings", "vertical_connectors", "assets")
    return document.model_copy(
        update={name: sorted(getattr(document, name), key=lambda entity: entity.id) for name in sections}
    )


def fixture_building() -> dict[str, Any]:
    """A two-floor building with an L-shaped office (3 m²), a door, an entrance, a lift and an asset."""
    return {
        "building": {
            "id": "fixture",
            "name": "Fixture",
            "source": "fixture",
            "source_ref": {},
            "license": "CC0-1.0",
            "attribution": "test fixture",
            "split": "dev",
            "units": "m",
        },
        "floors": [
            {"id": "F0", "level": 0, "name": "Ground floor", "elevation_m": 0.0, "height_m": 3.0},
            {"id": "F1", "level": 1, "name": "Floor 1", "elevation_m": 3.0, "height_m": 3.0},
        ],
        "spaces": [
            {
                "id": "S-office",
                "floor_id": "F0",
                "type": "room",
                "room_type": "office",
                "name": "Office 0.01",
                "ref": "0.01",
                "polygon": [[0, 0], [2, 0], [2, 1], [1, 1], [1, 2], [0, 2]],
                "synthetic": False,
            },
            {
                "id": "S-lift-0",
                "floor_id": "F0",
                "type": "lift",
                "room_type": "lift",
                "name": "Lift 1",
                "ref": "L1",
                "polygon": [[2, 0], [3, 0], [3, 1], [2, 1]],
                "synthetic": False,
            },
            {
                "id": "S-lift-1",
                "floor_id": "F1",
                "type": "lift",
                "room_type": "lift",
                "name": "Lift 1",
                "ref": "L1",
                "polygon": [[2, 0], [3, 0], [3, 1], [2, 1]],
                "synthetic": False,
            },
        ],
        "openings": [
            {
                "id": "O-door",
                "floor_id": "F0",
                "space_ids": ["S-office", "S-lift-0"],
                "kind": "door",
                "position": [2.0, 0.5],
                "width_m": 0.9,
                "step_free": True,
                "synthetic": False,
            },
            {
                "id": "O-entrance",
                "floor_id": "F0",
                "space_ids": ["outside", "S-office"],
                "kind": "entrance",
                "position": [0.0, 1.0],
                "width_m": 1.2,
                "step_free": True,
                "synthetic": False,
            },
        ],
        "vertical_connectors": [
            {
                "id": "V-lift",
                "kind": "lift",
                "name": "Lift 1",
                "floor_ids": ["F0", "F1"],
                "space_ids": ["S-lift-0", "S-lift-1"],
                "step_free": True,
                "synthetic": False,
            }
        ],
        "assets": [
            {
                "id": "A-desk",
                "name": "Desk 1",
                "category": "furniture",
                "type": "desk",
                "space_id": "S-office",
                "floor_id": "F0",
                "position": [0.5, 0.5],
                "footprint": {"width_m": 1.4, "depth_m": 0.7, "rotation_deg": 90.0},
                "source": "generated",
            }
        ],
    }


class BuildingDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.database = self.root / "buildings.sqlite3"
        self.connection = connect(self.database)
        self.addCleanup(self.connection.close)

    def write_building(self, content: dict[str, Any], folder: str = "fixture") -> Path:
        path = self.root / folder / "building.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(content))
        return path

    def count(self, table: str) -> int:
        return self.connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]

    def test_dev_building_reads_back_unchanged(self) -> None:
        path = DEV_BUILDING / "building.json"
        source = read_building(path)

        result = import_building(self.connection, path)

        self.assertEqual(result.status, "imported", result.message)
        self.assertEqual(load_building(self.connection, source.building.id), sorted_by_id(source))

    def test_stored_room_areas_match_dev_answers(self) -> None:
        # Gold answers serve only as an independent check of the stored areas.
        import_building(self.connection, DEV_BUILDING / "building.json")
        questions = [json.loads(line) for line in (DEV_BUILDING / "questions.jsonl").read_text().splitlines()]
        checked = 0
        for question in questions:
            answer = question["answer"]
            if question["kind"] == "largest_room":
                (area,) = self.connection.execute(
                    "SELECT area_m2 FROM spaces WHERE id = ?", (answer["space_id"],)
                ).fetchone()
                self.assertAlmostEqual(area, answer["area"]["value"], delta=0.005, msg=question["id"])
                checked += 1
            elif question["kind"] == "floor_area_total":
                (total,) = self.connection.execute(
                    "SELECT sum(area_m2) FROM spaces WHERE floor_id = ? AND room_type = ?",
                    (question["inputs"]["floor_id"], question["inputs"]["room_type"]),
                ).fetchone()
                self.assertAlmostEqual(total, answer["value"], delta=0.005, msg=question["id"])
                checked += 1
        self.assertGreater(checked, 0)

    def test_area_follows_polygon_changes_and_needs_no_function_to_read(self) -> None:
        import_building(self.connection, self.write_building(fixture_building()))
        office = ("fixture", "S-office")
        area_sql = "SELECT area_m2 FROM spaces WHERE building_id = ? AND id = ?"
        self.assertAlmostEqual(self.connection.execute(area_sql, office).fetchone()[0], 3.0)

        with self.connection:
            self.connection.execute(
                "UPDATE spaces SET polygon = ? WHERE building_id = ? AND id = ?",
                (json.dumps([[0, 0], [1, 0], [1, 1], [0, 1]]), *office),
            )

        plain_reader = sqlite3.connect(self.database)
        self.addCleanup(plain_reader.close)
        self.assertAlmostEqual(plain_reader.execute(area_sql, office).fetchone()[0], 1.0)

    def test_reimport_is_safe_and_changed_content_is_not_overwritten(self) -> None:
        content = fixture_building()
        path = self.write_building(content)
        import_building(self.connection, path)

        same_content_other_layout = self.root / "copy" / "building.json"
        same_content_other_layout.parent.mkdir()
        same_content_other_layout.write_text(json.dumps(content, indent=2))
        self.assertEqual(import_building(self.connection, same_content_other_layout).status, "unchanged")

        changed = copy.deepcopy(content)
        changed["floors"][0]["name"] = "Renamed floor"
        result = import_building(self.connection, self.write_building(changed, "changed"))

        self.assertEqual(result.status, "conflict")
        self.assertEqual(load_building(self.connection, "fixture").floors[0].name, "Ground floor")

    def test_invalid_building_is_rejected_with_reasons_and_leaves_nothing_behind(self) -> None:
        broken = fixture_building()
        broken["spaces"][0]["polygon"] = [[0, 0], [1, 1], [1, 0], [0, 1]]  # self-intersecting
        broken["assets"][0]["space_id"] = "S-missing"
        broken["openings"][1]["kind"] = "door"  # a door cannot lead outside

        result = import_building(self.connection, self.write_building(broken))

        self.assertEqual(result.status, "failed")
        self.assertIn("S-office has an invalid polygon", result.message)
        self.assertIn("unknown space S-missing", result.message)
        self.assertIn("O-entrance", result.message)
        self.assertEqual(self.count("buildings"), 0)

    def test_unknown_source_fields_are_rejected(self) -> None:
        extended = fixture_building()
        extended["spaces"][0]["colour"] = "blue"

        result = import_building(self.connection, self.write_building(extended))

        self.assertEqual(result.status, "failed")
        self.assertIn("colour", result.message)

    def test_only_building_files_are_imported(self) -> None:
        result = import_building(self.connection, DEV_BUILDING / "questions.jsonl")

        self.assertEqual(result.status, "failed")
        self.assertEqual(self.count("buildings"), 0)


if __name__ == "__main__":
    unittest.main()
