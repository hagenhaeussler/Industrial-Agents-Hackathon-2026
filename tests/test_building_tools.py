"""Building tool tests: lookup rules on a fixture, and the README definitions against train and dev answers."""

import json
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

from building_db.store import connect, import_building
from building_tools.building import Building, ToolInputError, load
from building_tools.lookup import building_overview, find_assets, find_spaces
from building_tools.spatial import distance_3d, shared_walls, stacked_spaces
from tests.test_building_db import fixture_building

REPO = Path(__file__).resolve().parents[1]
GOLD_KINDS = {"largest_room", "floor_area_total", "room_stacked", "shared_walls_count", "straight_line_3d"}


def fixture_with_floor_above() -> dict:
    """The fixture plus two rooms on floor 1: one over most of the office, one over a corner of it."""
    content = fixture_building()
    for space_id, name, polygon in (
        ("S-large", "Office 1.01", [[0.5, 0], [2, 0], [2, 2], [0.5, 2]]),
        ("S-small", "Office 1.02", [[0, 0], [0.5, 0], [0.5, 2], [0, 2]]),
    ):
        content["spaces"].append(
            {
                "id": space_id,
                "floor_id": "F1",
                "type": "room",
                "room_type": "office",
                "name": name,
                "ref": name.split()[1],
                "polygon": polygon,
                "synthetic": False,
            }
        )
    content["spaces"][2]["polygon"] = [[2.1, 0], [3, 0], [3, 1], [2.1, 1]]  # upper lift stop, 0.05 m offset
    return content


class FixtureToolTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "fixture" / "building.json"
        path.parent.mkdir()
        path.write_text(json.dumps(fixture_with_floor_above()))
        connection = connect(Path(directory.name) / "buildings.sqlite3")
        self.addCleanup(connection.close)
        import_building(connection, path)
        self.building = load(connection, "fixture")

    def test_overview_lists_floors_from_lowest_and_types(self) -> None:
        overview = building_overview(self.building)
        self.assertEqual([floor.name for floor in overview.floors], ["Ground floor", "Floor 1"])
        self.assertEqual(overview.room_types["office"], 3)
        self.assertEqual(overview.asset_types, {"desk": 1})
        self.assertEqual([(c.id, c.floors) for c in overview.connectors], [("V-lift", ["Ground floor", "Floor 1"])])

    def test_floor_in_brackets_filters_and_exact_names_win(self) -> None:
        matches = find_spaces(self.building, "Office 1.01 (Floor 1)")
        self.assertEqual((matches.match, [s.id for s in matches.spaces]), ("exact", ["S-large"]))

        partial = find_spaces(self.building, "office 1")
        self.assertEqual(partial.match, "partial")
        self.assertEqual({s.id for s in partial.spaces}, {"S-large", "S-small"})

    def test_room_type_filter_sums_every_match_and_ranks_by_area(self) -> None:
        matches = find_spaces(self.building, floor="1", room_type="Office", limit=1)
        self.assertEqual(matches.count, 2)
        self.assertAlmostEqual(matches.total_area_m2, 4.0)
        self.assertEqual([s.id for s in matches.spaces], ["S-large"])

    def test_unknown_references_are_explicit_errors(self) -> None:
        with self.assertRaisesRegex(ToolInputError, "Ground floor"):
            find_spaces(self.building, floor="Floor 9")
        with self.assertRaisesRegex(ToolInputError, "desk"):
            find_assets(self.building, asset_type="stove")
        # A plural or misspelled room type is refused with the known types, instead of matching nothing.
        with self.assertRaisesRegex(ToolInputError, "known room types: .*office"):
            find_spaces(self.building, room_type="offices")
        with self.assertRaisesRegex(ToolInputError, "find_spaces"):
            stacked_spaces(self.building, "S-missing", "above")

    def test_assets_by_type_report_their_space(self) -> None:
        matches = find_assets(self.building, asset_type="desk", floor="Ground floor")
        self.assertEqual([(a.id, a.space.id) for a in matches.assets], [("A-desk", "S-office")])

    def test_stacking_ranks_overlaps_and_rejects_missing_floors(self) -> None:
        above = stacked_spaces(self.building, "S-office", "above")
        self.assertEqual([o.space.id for o in above.overlaps], ["S-large", "S-small"])
        self.assertAlmostEqual(above.overlaps[0].share_of_start, 2 / 3, places=3)

        with self.assertRaisesRegex(ToolInputError, "no floor 2"):
            stacked_spaces(self.building, "S-office", "above", floors=2)

    def test_shared_walls_count_rooms_and_report_other_neighbours(self) -> None:
        # The office and the lift touch along 1 m; the lift is reported but not counted.
        walls = shared_walls(self.building, "S-office")
        self.assertEqual(walls.count, 0)
        self.assertEqual(walls.counted, [])
        self.assertEqual([n.space.id for n in walls.not_counted], ["S-lift-0"])
        self.assertEqual(shared_walls(self.building, "S-office", count_types=["lift"]).count, 1)

    def test_distance_uses_centroid_and_floor_elevation(self) -> None:
        distance = distance_3d(self.building, "S-lift-0", "S-lift-1")
        self.assertAlmostEqual(distance.vertical_m, 3.0)
        self.assertAlmostEqual(distance.horizontal_m, 0.05)


class GoldAnswerTests(unittest.TestCase):
    """The tools must reproduce every train and dev answer for these kinds. Answers and inputs are test data only."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.directory = tempfile.TemporaryDirectory()
        connection = connect(Path(cls.directory.name) / "buildings.sqlite3")
        cls.questions = defaultdict(list)
        cls.buildings: dict[str, Building] = {}
        for questions_path in sorted(REPO.glob("data/[dt][er][va]*/*/questions.jsonl")):
            questions = [json.loads(line) for line in questions_path.read_text().splitlines()]
            questions = [q for q in questions if q["kind"] in GOLD_KINDS]
            if not questions:
                continue
            building_path = questions_path.with_name("building.json")
            result = import_building(connection, building_path)
            assert result.building_id is not None, result.message
            cls.buildings[result.building_id] = load(connection, result.building_id)
            for question in questions:
                cls.questions[question["kind"]].append(question)
        connection.close()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.directory.cleanup()

    def check(self, kind: str, minimum: int, solve) -> None:
        """Run `solve(building, question)` on every question of a kind; it returns (got, expected)."""
        questions = self.questions[kind]
        self.assertGreaterEqual(len(questions), minimum)
        for question in questions:
            with self.subTest(question["id"]):
                got, expected = solve(self.buildings[question["building_id"]], question)
                if isinstance(expected, float):
                    self.assertAlmostEqual(got, expected, delta=0.01)
                else:
                    self.assertEqual(got, expected)

    def test_largest_room(self) -> None:
        def solve(building: Building, question: dict) -> tuple:
            inputs = question["inputs"]
            top = find_spaces(building, floor=inputs["floor_id"], room_type=inputs["room_type"], limit=1).spaces[0]
            return (top.id, top.area_m2), (question["answer"]["space_id"], question["answer"]["area"]["value"])

        self.check("largest_room", 96, solve)

    def test_floor_area_total(self) -> None:
        def solve(building: Building, question: dict) -> tuple:
            inputs = question["inputs"]
            total = find_spaces(building, floor=inputs["floor_id"], room_type=inputs["room_type"]).total_area_m2
            return total, float(question["answer"]["value"])

        self.check("floor_area_total", 150, solve)

    def test_room_stacked(self) -> None:
        def solve(building: Building, question: dict) -> tuple:
            inputs = question["inputs"]
            stacked = stacked_spaces(building, inputs["start"], inputs["direction"])
            return stacked.overlaps[0].space.id, question["answer"]["space_id"]

        self.check("room_stacked", 26, solve)

    def test_shared_walls_count(self) -> None:
        def solve(building: Building, question: dict) -> tuple:
            return shared_walls(building, question["inputs"]["start"]).count, question["answer"]["value"]

        self.check("shared_walls_count", 140, solve)

    def test_straight_line_3d(self) -> None:
        def solve(building: Building, question: dict) -> tuple:
            inputs = question["inputs"]
            distance = distance_3d(building, inputs["first"], inputs["second"]).distance_m
            return distance, float(question["answer"]["value"])

        self.check("straight_line_3d", 25, solve)

    def test_question_room_labels_resolve_to_their_space(self) -> None:
        # Questions name rooms as "<name> (<floor name>)". Every labelled space must be found that way.
        for building in self.buildings.values():
            for space in building.document.spaces:
                label = f"{space.name} ({building.floor_by_id[space.floor_id].name})"
                with self.subTest(label):
                    self.assertIn(space.id, [s.id for s in find_spaces(building, label, limit=1000).spaces])


if __name__ == "__main__":
    unittest.main()
