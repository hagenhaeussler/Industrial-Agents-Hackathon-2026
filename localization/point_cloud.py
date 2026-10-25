"""Turn the LiDAR depth of a Stray Scanner capture into a point cloud in the map frame.

The map keeps the ARKit poses fixed, so depth back-projected with those poses lands in the same frame
as localization results. Stray Scanner stores one 256x192 depth image in millimetres per video frame,
plus a confidence image (0 low, 1 medium, 2 high).
"""

from collections.abc import Iterable
from dataclasses import dataclass

import cv2
import numpy as np

from .capture import Capture, Frame
from .video import read_frames

HIGH_CONFIDENCE = 2
VOXEL_SPLAT_M = 0.03  # size of a drawn point in `render`
MAX_SPLAT_PX = 4


@dataclass(frozen=True)
class DepthView:
    """Depth points of one frame and the camera centre they were seen from."""

    index: int
    center: np.ndarray
    points: np.ndarray  # N x 3, world frame
    pixels: np.ndarray  # N x 2 (row, column) in the depth image


def depth_intrinsics(frame: Frame, depth_width: int, depth_height: int) -> np.ndarray:
    """Scale the RGB intrinsics to the depth image, which covers the same field of view."""
    sx, sy = depth_width / frame.width, depth_height / frame.height
    K = frame.K.copy()
    K[0, 0] *= sx
    K[1, 1] *= sy
    K[0, 2] = (K[0, 2] + 0.5) * sx - 0.5
    K[1, 2] = (K[1, 2] + 0.5) * sy - 0.5
    return K


def back_project(
    depth_m: np.ndarray, mask: np.ndarray, K: np.ndarray, world_from_cam: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Pixels where `mask` is true, as world points and as (row, column). Camera axes are OpenCV:
    x right, y down, z forward."""
    v, u = np.nonzero(mask)
    z = depth_m[v, u]
    cam = np.stack([(u - K[0, 2]) * z / K[0, 0], (v - K[1, 2]) * z / K[1, 1], z], axis=1)
    return cam @ world_from_cam[:3, :3].T + world_from_cam[:3, 3], np.stack([v, u], axis=1)


def depth_views(
    capture: Capture, indices: Iterable[int], stride: int = 2, max_depth_m: float = 5.0
) -> Iterable[DepthView]:
    """High-confidence depth points of the given frames. `stride` skips pixels to save time."""
    for index in indices:
        name = f"{index:06d}.png"
        depth = cv2.imread(str(capture.root / "depth" / name), cv2.IMREAD_UNCHANGED)
        confidence = cv2.imread(str(capture.root / "confidence" / name), cv2.IMREAD_UNCHANGED)
        if depth is None or confidence is None:
            continue
        depth_m = depth.astype(np.float32) / 1000
        mask = (confidence >= HIGH_CONFIDENCE) & (depth_m > 0.1) & (depth_m <= max_depth_m)
        sparse = np.zeros_like(mask)
        sparse[::stride, ::stride] = True
        frame = capture.frames[index]
        K = depth_intrinsics(frame, depth.shape[1], depth.shape[0])
        points, pixels = back_project(depth_m, mask & sparse, K, frame.world_from_cam)
        yield DepthView(index, frame.center, points, pixels)


def voxel_counts(points: np.ndarray, voxel_m: float) -> tuple[np.ndarray, np.ndarray]:
    """Voxel indices of the points and how many points fell into each voxel."""
    keys = np.floor(points / voxel_m).astype(np.int32)
    return np.unique(keys, axis=0, return_counts=True)


def colored_cloud(capture: Capture, indices: list[int], voxel_m: float) -> tuple[np.ndarray, np.ndarray]:
    """Depth points of the given frames, coloured from the video and averaged per voxel.

    Returns voxel centres (N x 3, world frame) and BGR colours (N x 3, uint8). The depth image covers the
    same view as the video frame, so a frame shrunk to the depth size gives each depth pixel its colour.
    """
    views = {view.index: view for view in depth_views(capture, indices)}
    depth_height, depth_width = cv2.imread(
        str(capture.root / "depth" / f"{next(iter(views)):06d}.png"), cv2.IMREAD_UNCHANGED
    ).shape
    keys, colors = [], []
    for index, frame in read_frames(capture.video, views):
        view = views[index]
        small = cv2.resize(frame.bgr(), (depth_width, depth_height), interpolation=cv2.INTER_AREA)
        keys.append(np.floor(view.points / voxel_m).astype(np.int64))
        colors.append(small[view.pixels[:, 0], view.pixels[:, 1]])
    keys, inverse = np.unique(np.concatenate(keys), axis=0, return_inverse=True)
    colors = np.concatenate(colors).astype(np.float64)
    counts = np.bincount(inverse.ravel())
    mean = np.stack([np.bincount(inverse.ravel(), weights=colors[:, c]) / counts for c in range(3)], axis=1)
    return (keys + 0.5) * voxel_m, mean.round().astype(np.uint8)


def render(
    points: np.ndarray, colors: np.ndarray, K: np.ndarray, world_from_cam: np.ndarray, width: int, height: int
) -> np.ndarray:
    """Draw coloured points as seen by a camera. Each point covers a square that shrinks with distance."""
    cam_from_world = np.linalg.inv(world_from_cam)
    cam = points @ cam_from_world[:3, :3].T + cam_from_world[:3, 3]
    ahead = cam[:, 2] > 0.1
    cam, colors = cam[ahead], colors[ahead]
    u = np.round(K[0, 0] * cam[:, 0] / cam[:, 2] + K[0, 2]).astype(int)
    v = np.round(K[1, 1] * cam[:, 1] / cam[:, 2] + K[1, 2]).astype(int)
    radius = np.clip(np.round(0.5 * K[0, 0] * VOXEL_SPLAT_M / cam[:, 2]).astype(int), 0, MAX_SPLAT_PX)
    visible = (u >= -MAX_SPLAT_PX) & (u < width + MAX_SPLAT_PX) & (v >= -MAX_SPLAT_PX) & (v < height + MAX_SPLAT_PX)
    order = np.argsort(-cam[visible, 2])  # far to near, so nearer points are written last and win
    u, v, z, radius, colors = (a[visible][order] for a in (u, v, cam[:, 2], radius, colors))

    image = np.full((height, width, 3), 255, np.uint8)
    depth = np.full((height, width), np.inf)
    for dv in range(-MAX_SPLAT_PX, MAX_SPLAT_PX + 1):
        for du in range(-MAX_SPLAT_PX, MAX_SPLAT_PX + 1):
            sel = radius >= max(abs(dv), abs(du))
            uu, vv = u[sel] + du, v[sel] + dv
            inside = (uu >= 0) & (uu < width) & (vv >= 0) & (vv < height)
            uu, vv, zz, cc = uu[inside], vv[inside], z[sel][inside], colors[sel][inside]
            nearer = zz < depth[vv, uu]
            depth[vv[nearer], uu[nearer]] = zz[nearer]
            image[vv[nearer], uu[nearer]] = cc[nearer]
    return image
