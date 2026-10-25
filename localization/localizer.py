"""Localize one image in a map built by `build_map`.

The pipeline follows hloc: MegaLoc finds the most similar map images, SuperPoint and LightGlue match the
query to them, and PnP + RANSAC estimates the 6DoF pose from the matched 3D points.
All models and map features stay on the GPU so a request only pays for inference.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import h5py
import numpy as np
import pycolmap
import torch
from hloc import extract_features, extractors
from hloc.utils.base_model import dynamic_load

from .matching import as_input, create_matcher, load_features

LOCAL_FEATURES = extract_features.confs["superpoint_aachen"]
# MegaLoc at 512 px instead of hloc's 1024 px: retrieval only needs the coarse place, and the
# smaller input makes it several times faster.
GLOBAL_FEATURES = {
    **extract_features.confs["megaloc"],
    "output": "global-feats-megaloc-r512",
    "preprocessing": {"resize_max": 512},
}
RANSAC_MAX_ERROR_PX = 12.0


def colmap_camera(K: np.ndarray, width: int, height: int) -> pycolmap.Camera:
    """COLMAP puts pixel centres at +0.5, OpenCV and ARKit at integer coordinates."""
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2] + 0.5, K[1, 2] + 0.5
    return pycolmap.Camera(model="PINHOLE", width=width, height=height, params=[fx, fy, cx, cy])


def phone_camera(focal_px: float, width: int, height: int) -> pycolmap.Camera:
    """A camera known only by its focal length, with the principal point in the image centre."""
    return pycolmap.Camera(model="SIMPLE_PINHOLE", width=width, height=height, params=[focal_px, width / 2, height / 2])


def resize_long_side(image: np.ndarray, long_side: int) -> tuple[np.ndarray, float]:
    """Shrink so the longer side is at most `long_side`. Returns the image and the scale used."""
    scale = long_side / max(image.shape[:2])
    if scale >= 1:
        return image, 1.0
    size = (round(image.shape[1] * scale), round(image.shape[0] * scale))
    return cv2.resize(image, size, interpolation=cv2.INTER_AREA), scale


@dataclass
class Localization:
    world_from_cam: np.ndarray | None
    num_inliers: int
    num_matches: int
    retrieved: list[str]
    focal_px: float  # as given, or as estimated when the focal length was unknown
    timings_ms: dict[str, float] = field(default_factory=dict)


class _Stopwatch:
    def __init__(self, device: str):
        self.device = device
        self.timings: dict[str, float] = {}
        self._last = time.perf_counter()

    def lap(self, name: str) -> None:
        if self.device == "cuda":
            torch.cuda.synchronize()
        now = time.perf_counter()
        self.timings[name] = (now - self._last) * 1000
        self._last = now


class Localizer:
    def __init__(self, map_dir: Path, num_retrieved: int = 5, device: str = "cuda"):
        self.device = device
        self.num_retrieved = num_retrieved
        self.reconstruction = pycolmap.Reconstruction(map_dir / "sfm")
        self.points3D = {pid: p.xyz for pid, p in self.reconstruction.points3D.items()}

        images = {im.name: im for im in self.reconstruction.images.values() if im.num_points3D > 0}
        self.names = sorted(images)
        self.point3D_ids = [
            np.array([p.point3D_id if p.has_point3D() else -1 for p in images[n].points2D]) for n in self.names
        ]

        with h5py.File(map_dir / "global.h5", "r") as f:
            descriptors = np.stack([f[n]["global_descriptor"][()] for n in self.names])
        self.global_descriptors = torch.from_numpy(descriptors).float().to(device)

        self.features = load_features(map_dir / "features.h5", self.names, device)
        self.superpoint = self._load(LOCAL_FEATURES)
        self.megaloc = self._load(GLOBAL_FEATURES)
        self.matcher = create_matcher(device)

    def _load(self, conf: dict) -> torch.nn.Module:
        model_class = dynamic_load(extractors, conf["model"]["name"])
        return model_class(conf["model"]).eval().to(self.device)

    def localize_jpeg(self, data: bytes, camera: pycolmap.Camera) -> Localization:
        start = time.perf_counter()
        image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        decode_ms = (time.perf_counter() - start) * 1000
        result = self.localize(image, camera)
        result.timings_ms = {"decode": decode_ms, **result.timings_ms}
        return result

    @torch.no_grad()
    def localize(self, image_bgr: np.ndarray, camera: pycolmap.Camera, estimate_focal: bool = False) -> Localization:
        """Pose of the camera that took `image_bgr`.

        Browsers do not report the focal length. With `estimate_focal`, the camera's focal length is only a
        starting value: RANSAC solves for it with the pose, and the refinement adjusts it.
        """
        clock = _Stopwatch(self.device)
        height, width = image_bgr.shape[:2]

        rgb, _ = resize_long_side(image_bgr[:, :, ::-1], GLOBAL_FEATURES["preprocessing"]["resize_max"])
        rgb = torch.from_numpy(np.ascontiguousarray(rgb)).to(self.device).permute(2, 0, 1)[None] / 255
        query_descriptor = self.megaloc({"image": rgb.float()})["global_descriptor"]
        scores = query_descriptor @ self.global_descriptors.T
        top = torch.topk(scores[0], min(self.num_retrieved, len(self.names))).indices.tolist()
        clock.lap("retrieval")

        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        gray, scale = resize_long_side(gray, LOCAL_FEATURES["preprocessing"]["resize_max"])
        gray = torch.from_numpy(gray).to(self.device)[None, None].float() / 255
        features = self.superpoint({"image": gray})
        keypoints = (features["keypoints"][0] + 0.5) / scale - 0.5
        descriptors = features["descriptors"][0].T
        clock.lap("features")

        query = {
            "keypoints": keypoints[None],
            "descriptors": descriptors[None],
            "image_size": torch.tensor([[width, height]], device=self.device).float(),
        }
        matched_2d, matched_3d = [], []
        for i in top:
            reference = as_input(self.features[i])
            matches = self.matcher({"image0": query, "image1": reference})["matches0"][0].cpu().numpy()
            query_idx = np.flatnonzero(matches >= 0)
            point_ids = self.point3D_ids[i][matches[query_idx]]
            keep = point_ids >= 0
            matched_2d.append(query_idx[keep])
            matched_3d.append(point_ids[keep])
        clock.lap("matching")

        pairs = {(int(q), int(p)) for q, p in zip(np.concatenate(matched_2d), np.concatenate(matched_3d))}
        world_from_cam, num_inliers = None, 0
        if len(pairs) >= 4:
            query_idx, point_ids = map(np.array, zip(*sorted(pairs)))
            points2D = keypoints.cpu().numpy()[query_idx].astype(np.float64) + 0.5
            points3D = np.array([self.points3D[p] for p in point_ids])
            estimate = pycolmap.estimate_and_refine_absolute_pose(
                points2D,
                points3D,
                camera,
                estimation_options={
                    "ransac": {"max_error": RANSAC_MAX_ERROR_PX},
                    "estimate_focal_length": estimate_focal,
                },
                refinement_options={"refine_focal_length": estimate_focal},
            )
            if estimate is not None:
                cam_from_world = estimate["cam_from_world"]
                world_from_cam = np.eye(4)
                world_from_cam[:3, :4] = cam_from_world.inverse().matrix()
                num_inliers = int(estimate["num_inliers"])
        clock.lap("pose")

        return Localization(
            world_from_cam=world_from_cam,
            num_inliers=num_inliers,
            num_matches=len(pairs),
            retrieved=[self.names[i] for i in top],
            focal_px=float(camera.mean_focal_length()),
            timings_ms=clock.timings,
        )
