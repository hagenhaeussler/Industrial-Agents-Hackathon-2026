"""Building API tests: a stored building is served unchanged, and unknown buildings fail clearly."""

import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient

from building_api.app import create_app
from building_db.source import BuildingDocument, read_building
from building_db.store import connect, connect_readonly, import_building, load_building
from tests.test_building_db import DEV_BUILDING, sorted_by_id


class BuildingApiTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        database = self.directory / "buildings.sqlite3"
        db = connect(database)
        with db:
            import_building(db, DEV_BUILDING / "building.json")
        db.close()
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

    def test_request_connection_works_in_another_thread(self) -> None:
        # FastAPI may open a request's connection in one worker thread and use it in another.
        db = connect_readonly(self.directory / "buildings.sqlite3")
        self.addCleanup(db.close)
        with ThreadPoolExecutor(max_workers=1) as pool:
            building = pool.submit(
                load_building, db, read_building(DEV_BUILDING / "building.json").building.id
            ).result()
        self.assertEqual(building.building.id, read_building(DEV_BUILDING / "building.json").building.id)

    def test_never_creates_a_missing_database(self) -> None:
        missing = self.directory / "missing.sqlite3"
        with self.assertRaises(sqlite3.OperationalError):
            TestClient(create_app(missing)).get("/api/buildings")
        self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
