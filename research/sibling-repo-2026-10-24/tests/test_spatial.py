"""Offline regressions for geometry, graph constraints and public train/dev cases."""

import copy
import json
import math
import random
import tempfile
import unittest
from pathlib import Path

import networkx as nx

from benchmark.score import score_reply
from core.questions import answer, parse_question
from core.spatial import Constraints, SpatialCore
from starter_agent.building_map import MapError

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    def room(sid, floor, polygon, type="room", room_type="office"):
        return {"id": sid, "floor_id": floor, "type": type, "room_type": room_type,
                "name": sid, "ref": sid, "polygon": polygon}

    def rect(x, y, width=4, height=4):
        return [[x, y], [x + width, y], [x + width, y + height], [x, y + height]]

    def door(oid, floor, a, b, position, width=1.2):
        return {"id": oid, "floor_id": floor, "space_ids": [a, b], "position": position,
                "width_m": width, "step_free": True, "kind": "door"}

    return {
        "building": {"id": "unit", "name": "Unit building", "source": "procedural"},
        "floors": [{"id": "f0", "level": 0, "name": "Ground floor", "elevation_m": 0},
                   {"id": "f1", "level": 1, "name": "Floor 1", "elevation_m": 3},
                   {"id": "f3", "level": 3, "name": "Floor 3", "elevation_m": 10}],
        "spaces": [room("a", "f0", rect(0, 0)), room("b", "f0", rect(4.2, 0)),
                   room("h", "f0", rect(0, 4), "hall", "lobby"),
                   room("l0", "f0", rect(4.2, 4), "lift", "lift"),
                   room("c", "f1", rect(0, 0)), room("l1", "f1", rect(4.2, 4), "lift", "lift"),
                   room("d", "f3", rect(0, 0)), room("l3", "f3", rect(4.2, 4), "lift", "lift")],
        "openings": [door("entrance", "f0", "outside", "a", [0, 2]),
                     door("ab", "f0", "a", "b", [4.1, 2], .9),
                     door("ah", "f0", "a", "h", [2, 4]),
                     door("hl", "f0", "h", "l0", [4.1, 6], 1.1),
                     door("lc", "f1", "l1", "c", [4, 4]),
                     door("ld", "f3", "l3", "d", [4, 4])],
        "vertical_connectors": [{"id": "stairs", "name": "Stairs", "kind": "stairs", "step_free": False,
                                 "floor_ids": ["f3", "f0", "f1"], "space_ids": ["l3", "l0", "l1"]},
                                {"id": "lift", "name": "Lift", "kind": "lift", "step_free": True,
                                 "floor_ids": ["f0", "f1", "f3"], "space_ids": ["l0", "l1", "l3"]}],
        "assets": [{"id": "desk1", "type": "desk", "name": "Desk", "floor_id": "f0", "space_id": "b"}],
    }


class SpatialTests(unittest.TestCase):
    def setUp(self):
        self.core = SpatialCore(fixture())

    def test_wall_thickness_and_hall_neighbors(self):
        self.assertEqual(set(self.core.shared_wall_neighbors("a")), {"b", "h"})
        self.assertEqual(self.core.floor_area_total("f0", "lobby"), 16)
        self.assertEqual(self.core.largest_room("f0", "lobby")["space_id"], "h")

    def test_width_threshold_and_room_only_count(self):
        self.assertEqual(set(self.core.reachable_rooms("a", "f0", Constraints(True, .9))), {"a", "b"})
        self.assertEqual(self.core.reachable_rooms("a", "f0", Constraints(True, 1.0)), ["a"])

    def test_parallel_connectors_and_closures(self):
        g = self.core.constrained_graph()
        self.assertEqual(len(g["l0"]["l1"]), 2)
        self.assertEqual(nx.shortest_path_length(g, "l0", "l1", weight="weight"), 12)
        g = self.core.constrained_graph(Constraints(step_free=True))
        self.assertEqual(nx.shortest_path_length(g, "l0", "l1", weight="weight"), 21)
        self.assertEqual(nx.shortest_path_length(g, "l1", "l3", weight="weight"), 27)
        g = self.core.constrained_graph(Constraints(step_free=True, closed=frozenset({"lift"})))
        self.assertFalse(nx.has_path(g, "a", "c"))
        self.assertTrue(nx.has_path(self.core.constrained_graph(), "a", "c"))

    def test_existing_mutable_closure_is_respected(self):
        self.core.closed.add("lift")
        self.assertEqual(self.core.reachable_rooms("a", "f1", Constraints(step_free=True)), [])

    def test_closed_door_and_space(self):
        for element in ("ab", "b"):
            self.assertNotIn("b", self.core.reachable_rooms("a", "f0", Constraints(closed=frozenset({element}))))

    def test_centroid_elevation_distance_and_skipped_level(self):
        self.assertEqual(self.core.distance_3d("a", "d"), 10)
        self.assertEqual(self.core.stacked_room("c", "above")["space_id"], "d")
        self.assertEqual(self.core.stacked_room("d", "below")["space_id"], "c")
        # L shape: centroid (19/14, 19/14), distinct from representative_point.
        data = fixture()
        data["spaces"][0]["polygon"] = [[0, 0], [4, 0], [4, 1], [1, 1], [1, 4], [0, 4]]
        core = SpatialCore(data)
        self.assertAlmostEqual(core.distance_3d("a", "c"), math.sqrt(2 * (2 - 19/14)**2 + 9))

    def test_errand_uses_route_distance_to_pickup(self):
        result = self.core.errand("a", "desk", "f1", "office")
        self.assertEqual(result["via"], "b")
        self.assertEqual(result["target"], "c")
        expected = self.core.constrained_route("a", "b")["length_m"] + self.core.constrained_route("b", "c")["length_m"]
        self.assertAlmostEqual(result["length_m"], expected)

    def test_hypothetical_door_is_pure_and_connects_unreachable_room(self):
        data = fixture()
        data["openings"] = [o for o in data["openings"] if o["id"] != "ab"]
        core = SpatialCore(data)
        before = copy.deepcopy(core.data)
        first = core.compare_exit_distances_with_door("a", "b", "f0")
        second = core.compare_exit_distances_with_door("a", "b", "f0")
        self.assertEqual(first, second)
        self.assertEqual(first["improved_space_ids"], ["b"])
        self.assertEqual(core.data, before)
        self.assertEqual(core.closed, set())

    def test_door_midpoint_is_order_and_ring_start_independent(self):
        data = fixture()
        # Start the ring in the middle of the shared wall; this splits its intersection.
        data["spaces"][0]["polygon"] = [[4, 1], [4, 4], [0, 4], [0, 0], [4, 0]]
        core = SpatialCore(data)
        ab = core.compare_exit_distances_with_door("a", "b", "f0")
        ba = core.compare_exit_distances_with_door("b", "a", "f0")
        self.assertEqual(ab, ba)
        self.assertAlmostEqual(ab["door_position"][0], 4.1)
        self.assertAlmostEqual(ab["door_position"][1], 2)
        data["spaces"][0]["polygon"].insert(1, [4, 1])
        repeated = SpatialCore(data).compare_exit_distances_with_door("a", "b", "f0")
        self.assertEqual(repeated["door_position"], ab["door_position"])

    def test_errand_closed_start_or_destination_is_a_map_error(self):
        for closed in ("a", "c"):
            core = SpatialCore(fixture())
            core.closed.add(closed)
            with self.assertRaisesRegex(MapError, "closed"):
                core.errand("a", "desk", "f1", "office")

    def test_names_containing_and_and_floor_phrase(self):
        data = fixture()
        data["spaces"][0]["name"] = "Copy and Print on the floor 3"
        core = SpatialCore(data)
        question = "We're planning a wireless sensor link between Copy and Print on the floor 3 (Ground floor) and c (Floor 1). What is the straight-line distance in metres between the centres of the two rooms (each room's floor-plan centroid, at its floor's elevation)?"
        self.assertEqual(parse_question(core, question), ("straight_line_3d", {"first": "a", "second": "c"}))
        question = "I'm moving a 1.0 m wide trolley. It can't go on stairs or steps (lifts are fine), and every door it passes through must be at least 1.0 m wide. It arrives through the entrance into Copy and Print on the floor 3 (Ground floor). Into how many rooms on the floor 1 can it be delivered?"
        self.assertEqual(parse_question(core, question)[1]["floor_id"], "f1")

    def test_seeded_geometry_and_routing_invariants(self):
        rng = random.Random(20261024)
        for _ in range(100):
            data = fixture()
            scale, dx, dy = rng.uniform(.5, 5), rng.uniform(-1000, 1000), rng.uniform(-1000, 1000)
            for s in data["spaces"]:
                s["polygon"] = [[x * scale + dx, y * scale + dy] for x, y in s["polygon"]]
            for o in data["openings"]:
                x, y = o["position"]
                o["position"] = [x * scale + dx, y * scale + dy]
                o["width_m"] = rng.uniform(.7, 1.6)
            for floor in data["floors"]:
                floor["elevation_m"] *= scale
            core = SpatialCore(data)
            self.assertAlmostEqual(core.distance_3d("a", "c"), 3 * scale)
            self.assertAlmostEqual(core.floor_area_total("f0", "office"), 32 * scale**2)
            self.assertEqual(core.stacked_room("a", "above")["space_id"], "c")
            narrow = set(core.reachable_rooms("a", "f1", Constraints(True, .8)))
            wide = set(core.reachable_rooms("a", "f1", Constraints(True, 1.2)))
            self.assertLessEqual(wide, narrow)
            full = core.constrained_route("a", "c")["length_m"]
            step_free = core.constrained_route("a", "c", Constraints(True))["length_m"]
            self.assertGreaterEqual(step_free, full - 1e-9)

    def test_failures_are_explicit(self):
        for width in (-1, math.inf, math.nan):
            with self.assertRaises(MapError):
                Constraints(min_width=width)
        with self.assertRaises(MapError):
            self.core.constrained_graph(Constraints(closed=frozenset({"typo"})))
        with self.assertRaises(MapError):
            self.core.stacked_room("a", "sideways")
        with self.assertRaises(MapError):
            self.core.stacked_room("a", "below")
        with self.assertRaises(MapError):
            self.core.largest_room("f0", "bedroom")
        with self.assertRaises(MapError):
            self.core.compare_exit_distances_with_door("a", "c", "f0")
        for inputs in ({}, {"floor_id": "f0", "room_type": ["office"]},
                       {"floor_id": "f0", "room_type": "office", "typo": "x"}):
            with self.assertRaises(MapError):
                self.core.solve("largest_room", inputs)
        with self.assertRaises(MapError):
            self.core.solve("what_if_door", {"first": "a", "second": "b", "floor_id": "f1", "door_floor_id": "f1"})

    def test_non_benchmark_ids_can_be_formatted(self):
        self.assertIn("a", self.core.format_answer(self.core.largest_room("f0", "office")))
        self.core.spaces["a"].pop("ref")
        self.assertIn("a", self.core.format_answer({"space_id": "a"}))

    def test_ambiguous_label_requires_disambiguation(self):
        data = fixture()
        for s in data["spaces"][:2]:
            s["name"] = "Office"
        core = SpatialCore(data)
        with self.assertRaisesRegex(MapError, "Ambiguous"):
            parse_question(core, "There's water dripping from the ceiling in Office (Ground floor). Which room is directly above it?")

    def test_text_adapter_needs_no_question_file(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            (p / "building.json").write_text(json.dumps(fixture()))
            reply = answer(p, "Facilities want the total floor area of every office on the ground floor added together. How many square metres is that? Finish with a line 'Answer: <number>'.")
            self.assertEqual(reply, "Answer: 32.000000")
        with self.assertRaises(MapError):
            parse_question(self.core, "Invent a route through a wall")

    def test_agent_tool_reflects_current_closures_and_reports_errors(self):
        from anthropic.lib.tools import ToolError
        from starter_agent.tools import make_tools
        tools = {t.name: t for t in make_tools(self.core, Path("/tmp"))}
        query = {"kind": "step_free_reachable_count", "inputs": {"start": "a", "floor_id": "f1", "closed": "stairs"}}
        self.assertEqual(json.loads(tools["spatial_query"].call(query))["result"]["value"], 1)
        tools["set_closed"].call({"element": "lift", "closed": True})
        self.assertEqual(json.loads(tools["spatial_query"].call(query))["result"]["value"], 0)
        with self.assertRaises(ToolError):
            tools["spatial_query"].call({"kind": "largest_room", "inputs": {}})
        overview = json.loads(tools["building_overview"].call({}))
        self.assertEqual(overview["floor_ids"][0]["id"], "f0")


class DatasetRegressionTests(unittest.TestCase):
    def test_all_train_dev_tools_and_unambiguous_text(self):
        total = 0
        ambiguities = []
        for split in ("train", "dev"):
            paths = sorted((ROOT / "data" / split).glob("*/questions.jsonl"))
            self.assertEqual(len(paths), 200 if split == "train" else 40)
            for path in paths:
                core = SpatialCore.load(path.parent)
                for line in path.read_text().splitlines():
                    if not line.strip():
                        continue
                    q = json.loads(line)
                    total += 1
                    with self.subTest(id=q["id"], mode="structured"):
                        reply = core.format_answer(core.solve(q["kind"], q["inputs"]))
                        self.assertTrue(score_reply(q["answer"], reply), reply)
                    with self.subTest(id=q["id"], mode="text"):
                        try:
                            kind, inputs = parse_question(core, q["question"])
                        except MapError as error:
                            self.assertIn("Ambiguous room label", str(error))
                            self.assertEqual(split, "train")
                            ambiguities.append(q["id"])
                            continue
                        self.assertEqual((kind, inputs), (q["kind"], q["inputs"]))
                        self.assertTrue(score_reply(q["answer"], core.format_answer(core.solve(kind, inputs))))
        self.assertEqual(total, 655)
        self.assertEqual(len(ambiguities), 7)


if __name__ == "__main__":
    unittest.main()
