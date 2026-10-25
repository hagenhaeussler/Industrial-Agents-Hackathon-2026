"""Offline checks for placing a localized camera in a building."""

import unittest

import numpy as np

from localization.placement import BuildingFrame

# Map frame (ARKit, y up) to plan: the map's x and -z axes become the plan's x and y, the floor is at map y -1.4.
BUILDING_FROM_MAP = [[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 1.4], [0, 0, 0, 1]]
SQUARE = [[0, 0], [10, 0], [10, 10], [0, 10]]


def building() -> dict:
    return {
        "building": {"id": "b", "source_ref": {"building_from_map": BUILDING_FROM_MAP}},
        "floors": [{"id": "F1", "elevation_m": 3.5}, {"id": "F0", "elevation_m": 0.0}],
        "spaces": [
            {"id": "F0-hall", "floor_id": "F0", "polygon": SQUARE},
            {"id": "F0-office", "floor_id": "F0", "polygon": [[10, 0], [14, 0], [14, 10], [10, 10]]},
            {"id": "F1-hall", "floor_id": "F1", "polygon": SQUARE},
        ],
    }


def camera(plan_x: float, plan_y: float, height_m: float, look_map: tuple[float, float, float]) -> np.ndarray:
    """A camera at a plan position, looking along a map direction."""
    world_from_cam = np.eye(4)
    world_from_cam[:3, 3] = [plan_x, height_m - 1.4, -plan_y]
    world_from_cam[:3, 2] = look_map
    return world_from_cam


class PlacementTests(unittest.TestCase):
    def test_places_a_phone_in_the_space_it_stands_in(self) -> None:
        placement = BuildingFrame(building()).place(camera(12, 4, 1.5, (0, 0, -1)))

        self.assertEqual(placement.floor_id, "F0")
        self.assertEqual(placement.space_id, "F0-office")
        self.assertEqual(placement.position, (12, 4))
        self.assertAlmostEqual(placement.height_m, 1.5)
        self.assertAlmostEqual(placement.heading_deg, 90)  # map -z is plan +y

    def test_picks_the_floor_from_the_camera_height(self) -> None:
        placement = BuildingFrame(building()).place(camera(5, 5, 3.5 + 1.4, (1, 0, 0)))

        self.assertEqual((placement.floor_id, placement.space_id), ("F1", "F1-hall"))
        self.assertAlmostEqual(placement.height_m, 1.4)
        self.assertAlmostEqual(placement.heading_deg, 0)

    def test_counts_a_position_in_a_wall_but_not_far_outside(self) -> None:
        frame = BuildingFrame(building())

        self.assertEqual(frame.place(camera(-0.3, 5, 1.5, (1, 0, 0))).space_id, "F0-hall")
        self.assertIsNone(frame.place(camera(-2.0, 5, 1.5, (1, 0, 0))).space_id)


if __name__ == "__main__":
    unittest.main()
