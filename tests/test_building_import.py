"""Upload tests through HTTP and the real database, including failed and concurrent writes."""

import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

from fastapi.testclient import TestClient

from building_api.app import create_app
from building_db.source import BuildingDocument, read_building
from building_db.store import connect, connect_readonly, load_building
from tests.test_building_db import REPO, fixture_building, sorted_by_id


class BuildingImportTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.database = Path(directory.name) / "buildings.sqlite3"
        connect(self.database).close()
        self.client = TestClient(create_app(self.database))
        self.addCleanup(self.client.close)

    def upload(self, document: dict[str, object]):
        return self.client.post(
            "/api/buildings/import", content=json.dumps(document), headers={"Content-Type": "application/json"}
        )

    def assert_empty_database(self) -> None:
        with closing(connect_readonly(self.database)) as db:
            for table in (
                "buildings",
                "floors",
                "spaces",
                "openings",
                "vertical_connectors",
                "connector_stops",
                "assets",
            ):
                self.assertEqual(db.execute(f"SELECT count(*) FROM {table}").fetchone()[0], 0, table)

    def test_upload_is_saved_and_available_to_the_previewer_and_routes(self) -> None:
        content = fixture_building()
        response = self.upload(content)
        self.assertEqual((response.status_code, response.json()), (201, {"id": "fixture", "status": "imported"}))
        source = BuildingDocument.model_validate_json(json.dumps(content))
        served = self.client.get("/api/buildings/fixture")
        self.assertEqual(BuildingDocument.model_validate_json(served.content), sorted_by_id(source))
        self.assertEqual(self.client.get("/api/buildings").json()[0]["id"], "fixture")
        route = self.client.get("/api/buildings/fixture/route", params={"stops": ["S-office", "S-lift-1"]})
        self.assertTrue(route.json()["route"]["reachable"])
        # Use a new connection to prove the response followed a committed write.
        with closing(connect_readonly(self.database)) as db:
            self.assertEqual(load_building(db, "fixture"), sorted_by_id(source))

    def test_identical_upload_with_different_whitespace_opens_the_existing_building(self) -> None:
        content = fixture_building()
        self.upload(content)
        response = self.client.post(
            "/api/buildings/import",
            content=json.dumps(content, indent=4, sort_keys=True),
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        self.assertEqual((response.status_code, response.json()), (200, {"id": "fixture", "status": "unchanged"}))

    def test_changed_upload_does_not_overwrite_an_existing_building(self) -> None:
        original = fixture_building()
        self.upload(original)
        changed = fixture_building()
        changed["building"]["name"] = "Changed"
        response = self.upload(changed)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.get("/api/buildings/fixture").json()["building"], original["building"])

    def test_entity_ids_can_be_reused_in_another_building(self) -> None:
        self.upload(fixture_building())
        other = fixture_building()
        other["building"]["id"] = "other"
        self.assertEqual(self.upload(other).status_code, 201)
        self.assertEqual(len(self.client.get("/api/buildings").json()), 2)

    def test_malformed_json_and_wrong_root_types_leave_no_rows(self) -> None:
        for content in (b"", b" ", b"{", b"null", b"[]", b"42", b'"building"', b"\xff", b"{} {}", b"[" * 2000):
            with self.subTest(content=content[:30]):
                response = self.client.post(
                    "/api/buildings/import", content=content, headers={"Content-Type": "application/json"}
                )
                self.assertEqual(response.status_code, 422)
                self.assertIsInstance(response.json()["detail"], str)
                self.assert_empty_database()

    def test_duplicate_json_keys_are_rejected(self) -> None:
        content = json.dumps(fixture_building()).replace('"name": "Fixture"', '"name": "First", "name": "Second"')
        response = self.client.post(
            "/api/buildings/import", content=content, headers={"Content-Type": "application/json"}
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("duplicate JSON key", response.json()["detail"])
        self.assert_empty_database()

    def test_utf8_bom_is_accepted(self) -> None:
        content = b"\xef\xbb\xbf" + json.dumps(fixture_building()).encode()
        response = self.client.post(
            "/api/buildings/import", content=content, headers={"Content-Type": "application/json"}
        )
        self.assertEqual(response.status_code, 201)

    def test_missing_and_unknown_fields_are_rejected(self) -> None:
        for field in ("building", "floors", "spaces", "openings", "vertical_connectors", "assets"):
            with self.subTest(field=field):
                content = fixture_building()
                del content[field]
                self.assertEqual(self.upload(content).status_code, 422)
        content = fixture_building()
        content["questions"] = [{"answer": "must never enter the database"}]
        self.assertEqual(self.upload(content).status_code, 422)
        self.assert_empty_database()

    def test_empty_floor_or_space_lists_cannot_break_the_previewer(self) -> None:
        for field in ("floors", "spaces"):
            with self.subTest(field=field):
                content = fixture_building()
                content[field] = []
                self.assertEqual(self.upload(content).status_code, 422)
        self.assert_empty_database()

    def test_bad_ids_types_units_numbers_and_dimensions_are_rejected(self) -> None:
        cases = (
            ("building", "id", ""),
            ("building", "id", "  "),
            ("building", "id", "../file"),
            ("building", "id", "."),
            ("building", "id", ".."),
            ("building", "id", "a\\b"),
            ("building", "id", "a\x00b"),
            ("building", "id", 1),
            ("building", "units", "ft"),
            ("floors", "level", "0"),
            ("floors", "height_m", 0),
            ("floors", "elevation_m", float("inf")),
            ("openings", "step_free", "true"),
            ("openings", "width_m", -1),
            ("spaces", "polygon", [[0, 0], [1, 0]]),
            ("spaces", "polygon", [[0, 0], [1, 0], [0, float("nan")]]),
        )
        for section, field, value in cases:
            with self.subTest(section=section, field=field, value=value):
                content = fixture_building()
                owner = content[section] if section == "building" else content[section][0]
                owner[field] = value
                self.assertEqual(self.upload(content).status_code, 422)
        self.assert_empty_database()

    def test_bad_geometry_and_references_report_reasons_without_partial_writes(self) -> None:
        content = fixture_building()
        content["spaces"][0]["polygon"] = [[0, 0], [1, 1], [1, 0], [0, 1]]
        content["assets"][0]["space_id"] = "missing-room"
        response = self.upload(content)
        self.assertEqual(response.status_code, 422)
        self.assertIn("invalid polygon", response.json()["detail"])
        self.assertIn("missing-room", response.json()["detail"])
        self.assert_empty_database()

    def test_duplicate_entity_ids_floor_levels_and_connector_stops_are_rejected(self) -> None:
        cases = (
            ("assets", "id", "S-office"),
            ("floors", "level", 1),
            ("vertical_connectors", "floor_ids", ["F0", "F0"]),
            ("vertical_connectors", "space_ids", ["S-lift-0"]),
            ("spaces", "id", "outside"),
        )
        for section, field, value in cases:
            with self.subTest(section=section, field=field):
                content = fixture_building()
                content[section][0][field] = value
                self.assertEqual(self.upload(content).status_code, 422)
        self.assert_empty_database()

    def test_wrong_floor_references_and_entrances_are_rejected(self) -> None:
        for section in ("spaces", "openings", "assets"):
            with self.subTest(section=section):
                content = fixture_building()
                content[section][0]["floor_id"] = "missing-floor"
                self.assertEqual(self.upload(content).status_code, 422)
        content = fixture_building()
        content["openings"][1]["kind"] = "door"
        self.assertEqual(self.upload(content).status_code, 422)
        content = fixture_building()
        content["assets"][0]["floor_id"] = "F1"
        self.assertEqual(self.upload(content).status_code, 422)
        self.assert_empty_database()

    def test_non_json_requests_are_rejected(self) -> None:
        for content_type in ("", "text/plain", "multipart/form-data", "application/zip"):
            with self.subTest(content_type=content_type):
                response = self.client.post(
                    "/api/buildings/import",
                    content=json.dumps(fixture_building()),
                    headers={"Content-Type": content_type},
                )
                self.assertEqual(response.status_code, 415)
        self.assert_empty_database()

    def test_exact_size_limit_is_accepted_but_extra_bytes_are_rejected(self) -> None:
        content = json.dumps(fixture_building()).encode()
        with patch("building_api.imports.MAX_UPLOAD_BYTES", len(content)):
            response = self.client.post(
                "/api/buildings/import",
                content=content + b" ",
                headers={"Content-Type": "application/json", "Content-Length": "1"},
            )
            self.assertEqual(response.status_code, 413)
            self.assert_empty_database()
            response = self.client.post(
                "/api/buildings/import",
                content=iter([content[:10], content[10:]]),
                headers={"Content-Type": "application/json"},
            )
            self.assertEqual(response.status_code, 201)

    def test_simultaneous_identical_uploads_are_safe(self) -> None:
        barrier = Barrier(2)

        def upload_after_barrier():
            barrier.wait()
            return self.upload(fixture_building()).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(lambda _: upload_after_barrier(), range(2)))
        self.assertEqual(sorted(statuses), [200, 201])
        self.assertEqual(len(self.client.get("/api/buildings").json()), 1)

    def test_simultaneous_different_uploads_do_not_overwrite_each_other(self) -> None:
        barrier = Barrier(2)

        def upload_after_barrier(name: str):
            content = fixture_building()
            content["building"]["name"] = name
            barrier.wait()
            return name, self.upload(content).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(upload_after_barrier, ("First", "Second")))
        self.assertEqual(sorted(status for _, status in results), [201, 409])
        winner = next(name for name, status in results if status == 201)
        self.assertEqual(self.client.get("/api/buildings/fixture").json()["building"]["name"], winner)

    def test_database_failure_rolls_back_every_table_and_hides_internal_details(self) -> None:
        with closing(connect(self.database)) as db, db:
            db.execute(
                "CREATE TRIGGER fail_assets BEFORE INSERT ON assets BEGIN SELECT RAISE(ABORT, 'private path'); END"
            )
        response = self.upload(fixture_building())
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private path", response.text)
        self.assert_empty_database()

    def test_upload_never_creates_a_missing_database(self) -> None:
        self.database.unlink()
        self.assertEqual(self.upload(fixture_building()).status_code, 503)
        self.assertFalse(self.database.exists())

    def test_incompatible_database_returns_a_storage_error_without_migration(self) -> None:
        with closing(connect(self.database)) as db:
            db.execute("PRAGMA user_version = 99")
        response = self.upload(fixture_building())
        self.assertEqual(response.status_code, 503)
        with closing(sqlite3.connect(self.database)) as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 99)

    def test_corrupt_database_returns_a_storage_error(self) -> None:
        self.database.write_bytes(b"not a database")
        self.assertEqual(self.upload(fixture_building()).status_code, 503)
        self.assertEqual(self.database.read_bytes(), b"not a database")

    def test_all_official_buildings_still_pass_the_shared_validator(self) -> None:
        for path in sorted((REPO / "data").glob("*/*/building.json")):
            with self.subTest(path=path):
                read_building(path)


if __name__ == "__main__":
    unittest.main()
