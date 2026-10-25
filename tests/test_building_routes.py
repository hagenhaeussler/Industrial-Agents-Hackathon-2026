"""Route tool tests: route model rules on a fixture, and every route-based train and dev answer."""

import json
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

from shapely.geometry import Polygon

from building_db.source import BuildingDocument
from building_db.store import connect, import_building
from building_tools.building import Building, ToolInputError, load
from building_tools.lookup import find_spaces
from building_tools.network import RouteConditions, shared_wall_midpoint
from building_tools.routes import exit_distance_change, reachable_spaces, route
from tests.test_building_db import fixture_building

REPO = Path(__file__).resolve().parents[1]
ROUTE_KINDS = {"route", "route_step_free", "route_with_closure", "tour"}
BENCHMARK_KINDS = {"errand", "wide_delivery_count", "step_free_reachable_count", "what_if_door"}


def fixture_with_second_wing() -> dict:
    """The fixture plus a ground-floor store with its own entrance and no door to the office."""
    content = fixture_building()
    content["spaces"].append(
        {
            "id": "S-store",
            "floor_id": "F0",
            "type": "room",
            "room_type": "storage",
            "name": "Store 0.02",
            "ref": "0.02",
            "polygon": [[5, 0], [7, 0], [7, 2], [5, 2]],
            "synthetic": False,
        }
    )
    content["openings"].append(
        {
            "id": "O-store-entrance",
            "floor_id": "F0",
            "space_ids": ["S-store", "outside"],
            "kind": "entrance",
            "position": [7.0, 1.0],
            "width_m": 1.2,
            "step_free": True,
            "synthetic": False,
        }
    )
    return content


class FixtureRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "fixture" / "building.json"
        path.parent.mkdir()
        path.write_text(json.dumps(fixture_with_second_wing()))
        connection = connect(Path(directory.name) / "buildings.sqlite3")
        self.addCleanup(connection.close)
        import_building(connection, path)
        self.building = load(connection, "fixture")

    def test_route_lists_spaces_and_elements_and_pays_for_the_lift(self) -> None:
        result = route(self.building, ["S-office", "S-lift-1"])
        (leg,) = result.legs
        self.assertEqual([space.id for space in leg.spaces], ["S-office", "S-lift-0", "S-lift-1"])
        self.assertEqual(
            [(element.id, element.kind) for element in leg.elements], [("O-door", "door"), ("V-lift", "lift")]
        )
        # The lift ride costs 15 m plus 1 m per metre climbed (3 m), on top of walking to and from the door.
        self.assertGreater(result.length_m or 0, 18.0)
        self.assertLess(result.length_m or 0, 21.0)

    def test_no_route_goes_round_the_outside(self) -> None:
        result = route(self.building, ["S-office", "S-store"])
        self.assertFalse(result.reachable)
        self.assertIsNone(result.length_m)
        self.assertEqual(result.legs[0].blocked_by, [])

    def test_unreachable_leg_names_the_blocking_conditions(self) -> None:
        narrow = route(self.building, ["S-office", "S-lift-1"], RouteConditions(min_door_width_m=1.0))
        self.assertEqual(narrow.legs[0].blocked_by, ["min_door_width_m"])
        closed = route(self.building, ["S-office", "S-lift-1"], RouteConditions(closed=["V-lift"]))
        self.assertEqual(closed.legs[0].blocked_by, ["closed"])

    def test_leg_conditions_apply_per_leg(self) -> None:
        result = route(
            self.building,
            ["S-lift-1", "S-office", "S-lift-0"],
            leg_conditions=[RouteConditions(), RouteConditions(closed=["O-door"])],
        )
        self.assertEqual([leg.reachable for leg in result.legs], [True, False])

    def test_reachable_spaces_filter_and_sort_by_distance(self) -> None:
        result = reachable_spaces(self.building, "S-office", asset_type="desk")
        self.assertEqual([(match.space.id, match.distance_m) for match in result.spaces], [("S-office", 0.0)])
        everything = reachable_spaces(self.building, "S-office")
        self.assertEqual([match.space.id for match in everything.spaces], ["S-office", "S-lift-0", "S-lift-1"])
        with self.assertRaisesRegex(ToolInputError, "known types: desk"):
            reachable_spaces(self.building, "S-office", asset_type="stove")

    def test_rooms_without_a_pass_through_can_still_be_reached(self) -> None:
        conditions = RouteConditions(no_pass_through_room_types=["lift"])
        result = reachable_spaces(self.building, "S-office", conditions)
        self.assertEqual([match.space.id for match in result.spaces], ["S-office", "S-lift-0"])

    def test_room_types_without_a_pass_through_match_in_plain_words(self) -> None:
        content = fixture_with_second_wing()
        for space in content["spaces"]:
            if space["type"] == "lift":
                space["room_type"] = "lift_shaft"
        document = BuildingDocument.model_validate_json(json.dumps(content))
        building = Building(document, {space.id: Polygon(space.polygon).area for space in document.spaces})
        conditions = RouteConditions(no_pass_through_room_types=["Lift shaft"])
        result = reachable_spaces(building, "S-office", conditions)
        self.assertEqual([match.space.id for match in result.spaces], ["S-office", "S-lift-0"])

    def test_exit_changes_report_lost_ways_out_and_refuse_doors_without_a_wall(self) -> None:
        # The fixture's lift and store do not touch, so a door between them is refused.
        with self.assertRaisesRegex(ToolInputError, "do not share a wall"):
            exit_distance_change(self.building, "Ground floor", RouteConditions(added_doors=[("S-lift-0", "S-store")]))
        unchanged = exit_distance_change(self.building, "Ground floor", RouteConditions(closed=["O-entrance"]))
        self.assertEqual([entry.space.id for entry in unchanged.longer], ["S-office"])
        self.assertIsNone(unchanged.longer[0].after_m)


class SharedWallMidpointTests(unittest.TestCase):
    def test_added_door_position_does_not_depend_on_where_the_outline_starts(self) -> None:
        east = Polygon([(4, 0), (8, 0), (8, 4), (4, 4)])
        # The same 4 m square, once starting at a corner and once in the middle of the shared wall at x = 4.
        for coordinates in ([(0, 0), (4, 0), (4, 4), (0, 4)], [(4, 3), (4, 4), (0, 4), (0, 0), (4, 0)]):
            for first, second in ((Polygon(coordinates), east), (east, Polygon(coordinates))):
                x, y = shared_wall_midpoint(first, second)
                self.assertAlmostEqual(x, 4.0)
                self.assertAlmostEqual(y, 2.0)


class GoldRouteTests(unittest.TestCase):
    """Route tools against train and dev answers. Answers and inputs are test data only."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.directory = tempfile.TemporaryDirectory()
        connection = connect(Path(cls.directory.name) / "buildings.sqlite3")
        cls.questions = defaultdict(list)
        cls.buildings: dict[str, Building] = {}
        files = [(path, BENCHMARK_KINDS) for path in sorted(REPO.glob("data/[dt][er][va]*/*/questions.jsonl"))]
        files += [(path, ROUTE_KINDS) for path in sorted(REPO.glob("data/dev/*/questions_basic.jsonl"))]
        for path, kinds in files:
            questions = [q for q in map(json.loads, path.read_text().splitlines()) if q["kind"] in kinds]
            if not questions:
                continue
            result = import_building(connection, path.with_name("building.json"))
            assert result.building_id is not None, result.message
            cls.buildings.setdefault(result.building_id, load(connection, result.building_id))
            for question in questions:
                cls.questions[question["kind"]].append(question)
        connection.close()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.directory.cleanup()

    def building(self, question: dict) -> Building:
        return self.buildings[question["building_id"]]

    def test_warm_up_routes_match_lengths_to_the_centimetre(self) -> None:
        checked = 0
        for kind in ("route", "route_step_free", "route_with_closure"):
            for question in self.questions[kind]:
                answer = question["answer"]
                conditions = RouteConditions(
                    step_free=kind == "route_step_free",
                    closed=[answer["closed_element_id"]] if answer.get("closed_element_id") else [],
                )
                with self.subTest(question["id"]):
                    result = route(
                        self.building(question), [answer["from_space_id"], answer["to_space_id"]], conditions
                    )
                    if "optimal_length_m" in answer:
                        self.assertAlmostEqual(result.length_m or -1, answer["optimal_length_m"], delta=0.011)
                    else:
                        self.assertFalse(result.reachable)
                checked += 1
        self.assertGreater(checked, 180)

    def test_warm_up_tours_match_total_lengths(self) -> None:
        for question in self.questions["tour"]:
            answer = question["answer"]
            with self.subTest(question["id"]):
                result = route(self.building(question), answer["stops"])
                if "optimal_length_m" in answer:
                    self.assertAlmostEqual(result.length_m or -1, answer["optimal_length_m"], delta=0.011)
                else:
                    self.assertFalse(result.reachable)

    def test_errand_totals(self) -> None:
        questions = [q for q in self.questions["errand"] if q.get("inputs")]
        self.assertGreaterEqual(len(questions), 90)
        for question in questions:
            inputs, building = question["inputs"], self.building(question)
            with self.subTest(question["id"]):
                nearest = reachable_spaces(building, inputs["start"], asset_type=inputs["asset_type"], limit=1)
                target = find_spaces(building, floor=inputs["floor_id"], room_type=inputs["room_type"], limit=1)
                result = route(building, [inputs["start"], nearest.spaces[0].space.id, target.spaces[0].id])
                expected = question["answer"]["value"]
                self.assertAlmostEqual(result.length_m or -1, expected, delta=max(0.01 * expected, 1.0))

    def test_reachable_room_counts(self) -> None:
        questions = self.questions["wide_delivery_count"] + self.questions["step_free_reachable_count"]
        self.assertGreaterEqual(len(questions), 80)
        for question in questions:
            inputs = question["inputs"]
            conditions = RouteConditions(
                step_free=True,
                min_door_width_m=inputs.get("min_width", 0.0),
                closed=[inputs.get("closed")] if "closed" in inputs else [],
            )
            with self.subTest(question["id"]):
                result = reachable_spaces(
                    self.building(question), inputs["start"], conditions, floor=inputs["floor_id"], space_types=["room"]
                )
                self.assertEqual(result.count, question["answer"]["value"])

    def test_what_if_door_counts(self) -> None:
        self.assertGreaterEqual(len(self.questions["what_if_door"]), 4)
        for question in self.questions["what_if_door"]:
            inputs = question["inputs"]
            with self.subTest(question["id"]):
                change = RouteConditions(added_doors=[(inputs["first"], inputs["second"])])
                result = exit_distance_change(self.building(question), inputs["floor_id"], change)
                self.assertEqual(result.shorter_count, question["answer"]["value"])


if __name__ == "__main__":
    unittest.main()
