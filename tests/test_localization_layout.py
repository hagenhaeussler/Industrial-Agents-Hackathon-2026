"""Offline checks for adding a room layout to a scanned building."""

import copy
import json
import unittest
from pathlib import Path

from shapely.geometry import Polygon

from building_db.source import BuildingDocument, consistency_problems
from building_tools.building import Building
from building_tools.routes import reachable_spaces
from localization.layout import LayoutError, apply_layout

SQUARE_METRE = {"width_m": 1.0, "depth_m": 1.0, "rotation_deg": 0.0}
SCAN = Path(__file__).parents[1] / "data/scan/scan-233fe5f22a"


def rect(x0: float, y0: float, x1: float, y1: float) -> list[list[float]]:
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def scanned_building() -> dict:
    """A 10 x 4 m scan with one table, as floor_plan writes it."""
    return {
        "building": {"id": "b", "source_ref": {}},
        "floors": [{"id": "b-F0"}],
        "spaces": [{"id": "b-F0-S001", "polygon": rect(0, 0, 10, 4), "synthetic": False}],
        "assets": [
            {"id": "b-A001", "name": "Table 1", "category": "furniture", "type": "table", "position": [2, 2]}
            | {"footprint": SQUARE_METRE, "source": "dataset"}
        ],
    }


def layout() -> dict:
    """Two rooms that split the scan, a synthetic room behind its right wall, and doors between them."""

    def space(ref: str, polygon: list[list[float]], synthetic: bool = False) -> dict:
        return {"ref": ref, "name": ref, "type": "room", "room_type": "office"} | {
            "polygon": polygon,
            "synthetic": synthetic,
        }

    return {
        "spaces": [space("1", rect(0, 0, 5, 4)), space("2", rect(5, 0, 10, 4)), space("3", rect(10, 0, 14, 4), True)],
        "openings": [
            {"spaces": ["1", "2"], "kind": "opening", "position": [5, 2], "width_m": 3.8},
            {"spaces": ["2", "3"], "kind": "door", "position": [10, 2], "width_m": 0.9},
        ],
        "assets": [
            {"name": "Desk 3", "category": "furniture", "type": "desk", "position": [12, 2], "footprint": SQUARE_METRE}
        ],
    }


class LayoutTests(unittest.TestCase):
    def test_splits_the_scan_and_keeps_its_tables(self) -> None:
        building = apply_layout(scanned_building(), layout(), "layout.json")

        self.assertEqual([space["id"] for space in building["spaces"]], ["b-F0-S001", "b-F0-S002", "b-F0-S003"])
        self.assertEqual(building["openings"][1]["space_ids"], ["b-F0-S002", "b-F0-S003"])
        table, desk = building["assets"]
        self.assertEqual((table["name"], table["space_id"], table["source"]), ("Table 1", "b-F0-S001", "dataset"))
        self.assertEqual((desk["space_id"], desk["source"]), ("b-F0-S003", "generated"))
        self.assertEqual(apply_layout(building, layout(), "layout.json"), building)  # a second run changes nothing

    def test_refuses_rooms_that_leave_part_of_the_scan_uncovered(self) -> None:
        broken = layout()
        broken["spaces"][1]["polygon"] = rect(5, 0, 9, 4)

        with self.assertRaisesRegex(LayoutError, "do not cover"):
            apply_layout(scanned_building(), broken, "layout.json")

    def test_refuses_a_synthetic_room_that_reaches_into_the_scan(self) -> None:
        broken = layout()
        broken["spaces"][2]["polygon"] = rect(9, 0, 14, 4)

        with self.assertRaisesRegex(LayoutError, "spaces 2 and 3 overlap"):
            apply_layout(scanned_building(), broken, "layout.json")

    def test_refuses_an_opening_away_from_the_shared_wall(self) -> None:
        broken = layout()
        broken["openings"][1]["position"] = [11, 2]

        with self.assertRaisesRegex(LayoutError, "not on the wall of space 2"):
            apply_layout(scanned_building(), broken, "layout.json")

    def test_committed_scan_building_matches_its_layout_and_is_connected(self) -> None:
        stored = json.loads((SCAN / "building.json").read_text())
        layout_ref = stored["building"]["source_ref"]["layout"]

        rebuilt = apply_layout(copy.deepcopy(stored), json.loads((SCAN / "layout.json").read_text()), layout_ref)

        self.assertEqual(rebuilt, stored)
        document = BuildingDocument.model_validate_json(json.dumps(stored))
        self.assertEqual(consistency_problems(document), [])
        building = Building(document, {space.id: Polygon(space.polygon).area for space in document.spaces})
        for entrance in (opening for opening in document.openings if opening.kind == "entrance"):
            start = next(space_id for space_id in entrance.space_ids if space_id != "outside")
            self.assertEqual(reachable_spaces(building, start, limit=0).count, len(document.spaces))


if __name__ == "__main__":
    unittest.main()
