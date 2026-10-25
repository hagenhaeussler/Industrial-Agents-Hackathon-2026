"""Read selected frames of a capture video with the GPU video decoder (NVDEC).

OpenCV decodes HEVC on the CPU, which takes longer than the whole GPU part of a map build. ffmpeg's
`*_cuvid` decoders run on the GPU and stream raw NV12 frames. Python converts only the frames it needs.
Needs an ffmpeg build with the CUVID decoders, such as Ubuntu's, and an NVIDIA driver.
"""

import json
import logging
import subprocess
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# OpenCV's NV12 conversion expects the limited range (luma 16-235, chroma 16-240). iPhone videos use the
# full range 0-255, so their values are squeezed into the limited range first.
_LIMITED_LUMA = np.round(16 + np.arange(256) * 219 / 255).astype(np.uint8)
_LIMITED_CHROMA = np.round(128 + (np.arange(256) - 128) * 224 / 255).astype(np.uint8)


@dataclass(frozen=True)
class VideoInfo:
    codec: str
    width: int
    height: int
    full_range: bool


def probe(path: Path) -> VideoInfo:
    command = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height,color_range", "-of", "json", str(path),
    ]
    stream = json.loads(subprocess.run(command, capture_output=True, check=True, text=True).stdout)
    stream = stream["streams"][0]
    return VideoInfo(
        stream["codec_name"], int(stream["width"]), int(stream["height"]), stream.get("color_range") == "pc"
    )


@dataclass(frozen=True)
class VideoFrame:
    """One decoded NV12 frame. `luma` is free; `bgr()` pays for the color conversion."""

    nv12: np.ndarray
    full_range: bool

    @property
    def luma(self) -> np.ndarray:
        return self.nv12[: self.nv12.shape[0] * 2 // 3]

    def bgr(self) -> np.ndarray:
        nv12 = self.nv12
        if self.full_range:
            height = nv12.shape[0] * 2 // 3
            nv12 = np.concatenate([_LIMITED_LUMA[nv12[:height]], _LIMITED_CHROMA[nv12[height:]]])
        return cv2.cvtColor(nv12, cv2.COLOR_YUV2BGR_NV12)


def read_frames(path: Path, indices: Iterable[int]) -> Iterator[tuple[int, VideoFrame]]:
    """Yield (index, frame) for the wanted frame indices, in video order.

    Stops early when the video has fewer frames than the largest index.
    """
    wanted = set(indices)
    if not wanted:
        return
    info = probe(path)
    shape = (info.height * 3 // 2, info.width)  # NV12: full-size luma, then quarter-size chroma
    command = [
        "ffmpeg", "-nostdin", "-loglevel", "error", "-noautorotate",
        "-c:v", f"{info.codec}_cuvid", "-i", str(path),
        "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "nv12", "pipe:",
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    skipped = np.empty(shape, np.uint8)
    last = max(wanted)
    try:
        for index in range(last + 1):
            target = np.empty(shape, np.uint8) if index in wanted else skipped
            if not _read_exactly(process.stdout, memoryview(target).cast("B")):
                if process.wait() != 0:
                    raise RuntimeError(f"ffmpeg failed at frame {index}, see its error output above")
                logger.warning("Video ended at frame %d, wanted frames up to %d", index, last)
                return
            if index in wanted:
                yield index, VideoFrame(target, info.full_range)
    finally:
        process.kill()
        process.wait()


def _read_exactly(stream, view: memoryview) -> bool:
    filled = 0
    while filled < len(view):
        count = stream.readinto(view[filled:])
        if not count:
            return False
        filled += count
    return True
