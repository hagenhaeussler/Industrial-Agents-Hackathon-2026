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

    def test_route_matches_the_tool_and_has_drawing_points(self) -> None:
        source = read_building(DEV_BUILDING / "building.json")
        lift = next(c for c in source.vertical_connectors if c.kind == "lift")
        start, end = lift.space_ids[0], lift.space_ids[-1]
        response = self.client.get(f"/api/buildings/{source.building.id}/route", params={"stops": [start, end]})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["route"]["reachable"])
        self.assertEqual(body["path"][0]["floor_id"], lift.floor_ids[0])
        self.assertEqual(body["path"][-1]["floor_id"], lift.floor_ids[-1])

    def test_route_with_unknown_stop_is_rejected(self) -> None:
        source = read_building(DEV_BUILDING / "building.json")
        start = source.spaces[0].id
        response = self.client.get(f"/api/buildings/{source.building.id}/route", params={"stops": [start, "missing"]})
        self.assertEqual(response.status_code, 422)
        self.assertIn("missing", response.json()["detail"])

    def test_route_in_unknown_building_is_not_found(self) -> None:
        response = self.client.get("/api/buildings/missing/route", params={"stops": ["a", "b"]})
        self.assertEqual(response.status_code, 404)

    def test_preview_is_an_svg_that_browsers_can_cache(self) -> None:
        source = read_building(DEV_BUILDING / "building.json")
        response = self.client.get(f"/api/buildings/{source.building.id}/preview.svg")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/svg+xml")
        self.assertTrue(response.text.startswith("<svg"))
        self.assertIn("max-age", response.headers["cache-control"])

        again = self.client.get(
            f"/api/buildings/{source.building.id}/preview.svg", headers={"If-None-Match": response.headers["etag"]}
        )
        self.assertEqual(again.status_code, 304)
        self.assertEqual(again.content, b"")

    def test_preview_of_unknown_building_is_not_found(self) -> None:
        self.assertEqual(self.client.get("/api/buildings/missing/preview.svg").status_code, 404)

    def test_never_creates_a_missing_database(self) -> None:
        missing = self.directory / "missing.sqlite3"
        with self.assertRaises(sqlite3.OperationalError):
            TestClient(create_app(missing)).get("/api/buildings")
        self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
