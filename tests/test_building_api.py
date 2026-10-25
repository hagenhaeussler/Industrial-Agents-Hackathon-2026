"""Building API tests: a stored building is served unchanged, and unknown buildings fail clearly."""

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from building_api.app import create_app
from building_db.source import BuildingDocument, read_building
from building_db.store import connect, import_building
from tests.test_building_db import DEV_BUILDING, sorted_by_id


class BuildingApiTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        database = Path(directory.name) / "buildings.sqlite3"
        with connect(database) as db:
            import_building(db, DEV_BUILDING / "building.json")
        self.client = TestClient(create_app(database))

    def test_serves_a_stored_building_in_the_source_format(self) -> None:
        source = read_building(DEV_BUILDING / "building.json")
        response = self.client.get(f"/api/buildings/{source.building.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(BuildingDocument.model_validate_json(response.content), sorted_by_id(source))

    def test_lists_stored_buildings_with_floor_count(self) -> None:
        source = read_building(DEV_BUILDING / "building.json")
        response = self.client.get("/api/buildings")
        self.assertEqual(
            response.json(),
            [
                {
                    "id": source.building.id,
                    "name": source.building.name,
                    "source": source.building.source,
                    "floors": len(source.floors),
                }
            ],
        )

    def test_unknown_building_is_not_found(self) -> None:
        response = self.client.get("/api/buildings/missing")
        self.assertEqual(response.status_code, 404)
        self.assertIn("missing", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
