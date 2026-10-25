"""Align two gravity-aligned, metric trajectories.

ARKit frames have +y against gravity and use metres, so two captures differ only by a turn about the
vertical axis and a shift. Fitting those four degrees of freedom needs fewer points and cannot tilt
the result.
"""

import numpy as np


def fit_yaw_translation(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Least-squares 4x4 transform, a turn about +y plus a shift, that maps source points onto target."""
    source_mean, target_mean = source.mean(axis=0), target.mean(axis=0)
    a = (source - source_mean)[:, [0, 2]]
    b = (target - target_mean)[:, [0, 2]]
    u, _, vt = np.linalg.svd(a.T @ b)
    flat = (u @ vt).T
    if np.linalg.det(flat) < 0:
        vt[-1] *= -1
        flat = (u @ vt).T
    transform = np.eye(4)
    transform[np.ix_([0, 2], [0, 2])] = flat
    transform[:3, 3] = target_mean - transform[:3, :3] @ source_mean
    return transform


def apply(transform: np.ndarray, points: np.ndarray) -> np.ndarray:
    return points @ transform[:3, :3].T + transform[:3, 3]


def ransac_yaw_translation(
    source: np.ndarray, target: np.ndarray, threshold_m: float, iterations: int = 2000, seed: int = 0
) -> tuple[np.ndarray, np.ndarray]:
    """Robust fit that ignores wrong correspondences. Returns the transform and the inlier mask."""
    if len(source) < 2:
        raise ValueError("Need at least two corresponding points")
    rng = np.random.default_rng(seed)
    best = np.zeros(len(source), dtype=bool)
    for _ in range(iterations):
        sample = rng.choice(len(source), size=2, replace=False)
        transform = fit_yaw_translation(source[sample], target[sample])
        inliers = np.linalg.norm(apply(transform, source) - target, axis=1) <= threshold_m
        if inliers.sum() > best.sum():
            best = inliers
    transform = fit_yaw_translation(source[best], target[best])
    inliers = np.linalg.norm(apply(transform, source) - target, axis=1) <= threshold_m
    return transform, inliers
