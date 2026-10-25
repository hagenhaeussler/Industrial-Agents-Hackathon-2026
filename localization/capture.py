"""Read Stray Scanner captures as upright, posed frames.

Stray Scanner stores one row per video frame in `odometry.csv`: the camera position in metres and its
rotation as a quaternion. The pose maps camera to world. Camera axes follow OpenCV (x right, y down,
z forward). The world frame is ARKit's, so +y points against gravity.

The video is always stored in the sensor's landscape orientation, even when the phone was held upright.
Live queries from the web app arrive upright, and SuperPoint is not rotation invariant, so frames are
turned until the image's down axis follows gravity.
"""

import csv
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

WORLD_UP = np.array([0.0, 1.0, 0.0])

# One clockwise quarter turn of the image, as new camera axes expressed in old camera axes (columns).
# New x is old -y, new y is old x, z is unchanged.
_QUARTER_TURN = np.array([[0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])


@dataclass(frozen=True)
class Frame:
    index: int
    timestamp: float
    world_from_cam: np.ndarray  # 4x4
    K: np.ndarray  # 3x3, pixel centres at integer coordinates
    width: int
    height: int

    @property
    def center(self) -> np.ndarray:
        return self.world_from_cam[:3, 3]

    @property
    def view_direction(self) -> np.ndarray:
        return self.world_from_cam[:3, 2]


@dataclass(frozen=True)
class Capture:
    root: Path
    frames: list[Frame]

    @property
    def video(self) -> Path:
        return self.root / "rgb.mp4"


def quaternion_to_matrix(qx: float, qy: float, qz: float, qw: float) -> np.ndarray:
    q = np.array([qx, qy, qz, qw]) / np.linalg.norm([qx, qy, qz, qw])
    x, y, z, w = q
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ]
    )


def load_capture(root: Path, width: int, height: int) -> Capture:
    """Read poses and per-frame intrinsics. `width` and `height` are the stored video size."""
    frames = []
    with open(root / "odometry.csv", newline="") as f:
        reader = csv.reader(f, skipinitialspace=True)
        next(reader)
        for row in reader:
            timestamp, index = float(row[0]), int(row[1])
            x, y, z, qx, qy, qz, qw, fx, fy, cx, cy = map(float, row[2:13])
            pose = np.eye(4)
            pose[:3, :3] = quaternion_to_matrix(qx, qy, qz, qw)
            pose[:3, 3] = (x, y, z)
            K = np.array([[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]])
            frames.append(Frame(index, timestamp, pose, K, width, height))
    if not frames:
        raise ValueError(f"{root / 'odometry.csv'} contains no poses")
    return Capture(root, frames)


def upright_turns(frames: list[Frame]) -> int:
    """Return the number of clockwise quarter turns that make the image's down axis follow gravity."""
    down_in_cam = np.median([f.world_from_cam[:3, :3].T @ -WORLD_UP for f in frames], axis=0)
    # Image down axis after k clockwise turns, in the original camera axes.
    candidates = [np.array(v) for v in ((0, 1, 0), (1, 0, 0), (0, -1, 0), (-1, 0, 0))]
    return int(np.argmax([down_in_cam @ c for c in candidates]))


def turn_clockwise(frame: Frame, turns: int) -> Frame:
    """Describe the same view after rotating its image clockwise by `turns` quarter turns."""
    for _ in range(turns % 4):
        (fx, _, cx), (_, fy, cy) = frame.K[:2]
        K = np.array([[fy, 0.0, frame.height - 1 - cy], [0.0, fx, cx], [0.0, 0.0, 1.0]])
        pose = frame.world_from_cam.copy()
        pose[:3, :3] = pose[:3, :3] @ _QUARTER_TURN
        frame = replace(frame, world_from_cam=pose, K=K, width=frame.height, height=frame.width)
    return frame


def rotation_angle_deg(a: np.ndarray, b: np.ndarray) -> float:
    """Angle between two rotation matrices."""
    cos = (np.trace(a.T @ b) - 1) / 2
    return float(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))))


def select_keyframes(frames: list[Frame], min_step_m: float, min_turn_deg: float) -> list[int]:
    """Pick a frame each time the camera has moved or turned enough since the last pick."""
    picked = [0]
    for i in range(1, len(frames)):
        last = frames[picked[-1]]
        moved = np.linalg.norm(frames[i].center - last.center) >= min_step_m
        turned = rotation_angle_deg(frames[i].world_from_cam[:3, :3], last.world_from_cam[:3, :3]) >= min_turn_deg
        if moved or turned:
            picked.append(i)
    return picked
