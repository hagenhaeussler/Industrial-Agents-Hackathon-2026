"""Match SuperPoint features with LightGlue while all features stay in GPU memory.

The map build and the localizer use the same matcher settings. One pair takes about 6 ms of GPU time
but over 20 ms in total, because Python launches each GPU step in turn. `match_pairs` therefore runs
several worker processes on the same GPU. It writes hloc's file layout, so hloc's triangulation reads
the result unchanged.
"""

import logging
import os
from pathlib import Path

import h5py
import torch
import torch.multiprocessing as mp
from hloc.utils.parsers import names_to_pair
from lightglue import LightGlue
from tqdm import tqdm

logger = logging.getLogger(__name__)

Features = dict[str, torch.Tensor]


def load_features(path: Path, names: list[str], device: str) -> list[Features]:
    """Read SuperPoint features as LightGlue inputs. Descriptors stay half precision to save memory."""
    features = []
    with h5py.File(path, "r") as f:
        for name in names:
            group = f[name]
            features.append(
                {
                    "keypoints": torch.from_numpy(group["keypoints"][()]).float().to(device)[None],
                    "descriptors": torch.from_numpy(group["descriptors"][()].T).half().to(device)[None],
                    "image_size": torch.tensor(group["image_size"][()], device=device).float()[None],
                }
            )
    return features


def create_matcher(device: str) -> LightGlue:
    """LightGlue with early stopping and point pruning, in half precision on the GPU."""
    matcher = LightGlue(features="superpoint", depth_confidence=0.95, width_confidence=0.99, mp=device == "cuda")
    return matcher.eval().to(device)


def as_input(features: Features) -> Features:
    return {**features, "descriptors": features["descriptors"].float()}


def match_pairs(
    pairs: list[tuple[str, str]],
    features_path: Path,
    matches_path: Path,
    workers: int = max(1, (os.cpu_count() or 2) - 1),
    device: str = "cuda",
) -> None:
    """Match each pair and write `matches0` and `matching_scores0` per pair, as hloc does."""
    shards = [pairs[i::workers] for i in range(workers)]
    parts = [matches_path.with_name(f"{matches_path.stem}.part{i}.h5") for i in range(workers)]
    jobs = [(shard, features_path, part, device) for shard, part in zip(shards, parts)]
    with mp.get_context("spawn").Pool(workers) as pool:
        pool.starmap(_match_shard, jobs)
        pool.close()
        pool.join()  # let workers exit on their own; leaving the block would kill them

    with h5py.File(matches_path, "w") as out:
        for shard, part in zip(shards, parts):
            with h5py.File(part, "r") as f:
                for pair in shard:
                    key = names_to_pair(*pair)
                    for dataset in ("matches0", "matching_scores0"):
                        out.create_dataset(f"{key}/{dataset}", data=f[key][dataset][()])
            part.unlink()
    logger.info("Matched %d pairs with %d workers", len(pairs), workers)


@torch.no_grad()
def _match_shard(pairs: list[tuple[str, str]], features_path: Path, matches_path: Path, device: str) -> None:
    names = sorted({name for pair in pairs for name in pair})
    features = dict(zip(names, load_features(features_path, names, device)))
    matcher = create_matcher(device)
    with h5py.File(matches_path, "w") as out:
        for name0, name1 in tqdm(pairs, mininterval=30):
            result = matcher({"image0": as_input(features[name0]), "image1": as_input(features[name1])})
            group = out.create_group(names_to_pair(name0, name1))
            group.create_dataset("matches0", data=result["matches0"][0].short().cpu().numpy())
            group.create_dataset("matching_scores0", data=result["matching_scores0"][0].half().cpu().numpy())
