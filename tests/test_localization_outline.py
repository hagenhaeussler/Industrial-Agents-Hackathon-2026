"""Offline checks for turning a scanned raster plan into a clean outline."""

import unittest

import numpy as np
from shapely.geometry import Polygon

from localization.outline import rectilinear_outline, wall_angle

CELL = 0.05


def cells(metres: float) -> int:
    return round(metres / CELL)


def fill(raster: np.ndarray, x0: float, x1: float, y0: float, y1: float) -> None:
    raster[cells(y0) : cells(y1), cells(x0) : cells(x1)] = True


class OutlineTests(unittest.TestCase):
    def test_draws_straight_outer_walls_and_cuts_space_seen_through_glass(self) -> None:
        interior = np.zeros((cells(12), cells(14)), bool)
        wall = np.zeros_like(interior)
        fill(interior, 1, 11, 1, 5)  # bottom wing
        fill(interior, 1.3, 4, 5, 10)  # left wing, its left wall 30 cm further in
        fill(interior, 5, 7, 0.2, 1)  # seen through a glass part of the bottom wall
        for x0, x1, y0, y1 in [
            (1, 1.05, 1, 5),
            (1.3, 1.35, 5, 10),  # left facade, not quite straight
            (10.95, 11, 1, 5),
            (3.95, 4, 5, 10),  # right walls
            (1, 5, 1, 1.05),
            (7, 11, 1, 1.05),  # bottom wall with glass between 5 and 7 m
            (4, 11, 4.95, 5),
            (1.3, 4, 9.95, 10),  # top walls
            (7, 7.05, 1, 4),  # interior partition
        ]:
            fill(wall, x0, x1, y0, y1)

        outline = rectilinear_outline(interior, wall, np.zeros(2), CELL)

        expected = Polygon([(1, 1), (11, 1), (11, 5), (4, 5), (4, 10), (1, 10)])
        self.assertEqual(len(outline.exterior.coords) - 1, 6)
        self.assertLess(outline.hausdorff_distance(expected), 0.1)

    def test_closes_an_open_end_at_the_edge_of_the_scan(self) -> None:
        interior = np.zeros((cells(6), cells(20)), bool)
        wall = np.zeros_like(interior)
        fill(interior, 1, 18, 2, 4)  # corridor whose far end was not scanned
        fill(wall, 1, 18, 1.95, 2)
        fill(wall, 1, 18, 4, 4.05)
        fill(wall, 1, 1.05, 2, 4)

        outline = rectilinear_outline(interior, wall, np.array([10.0, 20.0]), CELL)

        expected = Polygon([(11, 22), (28, 22), (28, 24), (11, 24)])
        self.assertLess(outline.hausdorff_distance(expected), 0.1)

    def test_finds_the_turn_that_aligns_walls_with_the_axes(self) -> None:
        along, across = np.linspace(0, 10, 400), np.linspace(0, 6, 240)
        points = np.concatenate(
            [
                np.stack([along, np.zeros(400)], 1),
                np.stack([along, np.full(400, 6.0)], 1),
                np.stack([np.zeros(240), across], 1),
            ]
        )  # three walls of a 10 x 6 m room
        turn = np.radians(5.0)
        rotation = np.array([[np.cos(turn), -np.sin(turn)], [np.sin(turn), np.cos(turn)]])

        angle = wall_angle(points @ rotation.T, CELL)

        self.assertAlmostEqual(np.degrees(angle), -5.0, delta=0.3)


if __name__ == "__main__":
    unittest.main()
