"""Offline checks for reading Stray Scanner captures and turning frames upright."""

import tempfile
import unittest
from pathlib import Path

import numpy as np

from localization.capture import (
    WORLD_UP,
    Frame,
    load_capture,
    select_keyframes,
    turn_clockwise,
    upright_turns,
)


def project(frame: Frame, point: np.ndarray) -> np.ndarray:
    cam_from_world = np.linalg.inv(frame.world_from_cam)
    p = cam_from_world[:3, :3] @ point + cam_from_world[:3, 3]
    uv = frame.K @ (p / p[2])
    return uv[:2]


def sideways_frame(center=(0.0, 0.0, 0.0)) -> Frame:
    """A phone held upright, so the landscape sensor's x axis points down. It looks along world +x."""
    rotation = np.column_stack([-WORLD_UP, [0.0, 0.0, -1.0], [1.0, 0.0, 0.0]])
    pose = np.eye(4)
    pose[:3, :3] = rotation
    pose[:3, 3] = center
    K = np.array([[1450.0, 0.0, 930.0], [0.0, 1460.0, 715.0], [0.0, 0.0, 1.0]])
    return Frame(0, 0.0, pose, K, width=1920, height=1440)


class TurnTests(unittest.TestCase):
    def test_turned_frame_projects_like_the_turned_image(self) -> None:
        frame = sideways_frame()
        point = np.array([4.0, 0.7, -0.3])
        u, v = project(frame, point)

        # The pixel at (u, v) moves to (height - 1 - v, u) when the image turns clockwise.
        image = np.zeros((frame.height, frame.width))
        image[round(v), round(u)] = 1
        row, col = np.argwhere(np.rot90(image, k=-1) == 1)[0]

        turned = turn_clockwise(frame, 1)
        np.testing.assert_allclose(project(turned, point), [col, row], atol=0.5)
        self.assertEqual((turned.width, turned.height), (1440, 1920))
        np.testing.assert_allclose(turned.center, frame.center)

    def test_four_turns_restore_the_frame(self) -> None:
        frame = sideways_frame()
        turned = turn_clockwise(frame, 4)
        np.testing.assert_allclose(turned.world_from_cam, frame.world_from_cam)
        np.testing.assert_allclose(turned.K, frame.K)

    def test_upright_turns_make_image_down_follow_gravity(self) -> None:
        frames = [sideways_frame()]
        turns = upright_turns(frames)
        self.assertEqual(turns, 1)
        image_down_in_world = turn_clockwise(frames[0], turns).world_from_cam[:3, 1]
        np.testing.assert_allclose(image_down_in_world, -WORLD_UP, atol=1e-9)


class CaptureTests(unittest.TestCase):
    def test_reads_poses_and_per_frame_intrinsics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "odometry.csv").write_text(
                "timestamp, frame, x, y, z, qx, qy, qz, qw, fx, fy, cx, cy, "
                "distortion_center_x, distortion_center_y\n"
                "10.0, 000000, 1.0, 2.0, 3.0, 0.0, 0.0, 0.0, 1.0, 1457.5, 1457.6, 928.5, 714.6, , \n"
                "10.1, 000001, 1.5, 2.0, 3.0, 0.0, 0.0, 0.7071068, 0.7071068, 1458.0, 1458.0, 929.0, 715.0, , \n"
            )
            capture = load_capture(root, width=1920, height=1440)

        self.assertEqual([f.index for f in capture.frames], [0, 1])
        np.testing.assert_allclose(capture.frames[0].center, [1.0, 2.0, 3.0])
        np.testing.assert_allclose(capture.frames[0].K[0], [1457.5, 0.0, 928.5])
        # A quarter turn about z sends the camera's x axis to world +y.
        np.testing.assert_allclose(capture.frames[1].world_from_cam[:3, 0], [0.0, 1.0, 0.0], atol=1e-6)

    def test_keyframes_follow_distance_and_rotation(self) -> None:
        frames = [sideways_frame(center=(0.1 * i, 0.0, 0.0)) for i in range(10)]
        self.assertEqual(select_keyframes(frames, min_step_m=0.25, min_turn_deg=10), [0, 3, 6, 9])

        still = sideways_frame()
        turned_pose = still.world_from_cam.copy()
        angle = np.radians(15)
        about_up = np.array(
            [[np.cos(angle), 0, np.sin(angle)], [0, 1, 0], [-np.sin(angle), 0, np.cos(angle)]]
        )
        turned_pose[:3, :3] = about_up @ turned_pose[:3, :3]
        turned = Frame(1, 0.1, turned_pose, still.K, still.width, still.height)
        self.assertEqual(select_keyframes([still, turned], min_step_m=0.3, min_turn_deg=10), [0, 1])


if __name__ == "__main__":
    unittest.main()
