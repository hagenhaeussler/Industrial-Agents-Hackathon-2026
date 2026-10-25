"""Offline checks for aligning two gravity-aligned trajectories."""

import unittest

import numpy as np

from localization.alignment import apply, ransac_yaw_translation


def yaw_transform(degrees: float, shift: tuple[float, float, float]) -> np.ndarray:
    angle = np.radians(degrees)
    transform = np.eye(4)
    transform[:3, :3] = [[np.cos(angle), 0, np.sin(angle)], [0, 1, 0], [-np.sin(angle), 0, np.cos(angle)]]
    transform[:3, 3] = shift
    return transform


class AlignmentTests(unittest.TestCase):
    def test_recovers_turn_and_shift_despite_wrong_points(self) -> None:
        rng = np.random.default_rng(1)
        source = rng.uniform(-20, 20, size=(60, 3))
        source[:, 1] = rng.uniform(1.0, 1.6, size=60)
        truth = yaw_transform(137.0, (4.0, -0.3, 12.0))
        target = apply(truth, source) + rng.normal(0, 0.03, size=source.shape)
        target[:10] += rng.uniform(3, 10, size=(10, 3))  # wrong localizations

        transform, inliers = ransac_yaw_translation(source, target, threshold_m=0.5)

        np.testing.assert_allclose(transform, truth, atol=0.05)
        self.assertFalse(inliers[:10].any())
        self.assertTrue(inliers[10:].all())

    def test_never_tilts_the_vertical_axis(self) -> None:
        rng = np.random.default_rng(2)
        source = rng.uniform(-5, 5, size=(20, 3))
        target = apply(yaw_transform(-40.0, (1.0, 0.0, 2.0)), source)
        target[:, 1] += 0.1 * target[:, 0]  # a tilt the fit must not follow

        transform, _ = ransac_yaw_translation(source, target, threshold_m=5.0)

        np.testing.assert_allclose(transform[:3, 1], [0.0, 1.0, 0.0])


if __name__ == "__main__":
    unittest.main()
