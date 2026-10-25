"""HTTP service that localizes one camera image in a building. It runs on the GPU machine.

    POST /v1/buildings/{building_id}/localize
    Authorization: Bearer <LOCALIZATION_TOKEN>
    Content-Type: image/jpeg, an upright photo, ideally 1024 px on the long side

The optional query `focal_px` gives the focal length of the sent image in pixels. Browsers do not know it, so
without it the server estimates it with the pose, starting from a typical phone camera.

Each building needs a `building.json` from `floor_plan`. Its `source_ref.map` names the map folder.

Run on the GPU machine:
    LOCALIZATION_TOKEN=... python -m localization.server --maps ~/data/maps \\
        --building ~/data/buildings/<capture>/building.json
"""

import argparse
import hmac
import json
import os
import threading
import time
from pathlib import Path
from typing import Annotated

import cv2
import numpy as np
import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from .localizer import Localizer, phone_camera
from .placement import BuildingFrame

MIN_RELIABLE_INLIERS = 30  # below this the median error was 4.3 m in the spike
MAX_IMAGE_BYTES = 4 * 1024 * 1024
TYPICAL_FOCAL_PER_LONG_SIDE = 0.75  # main cameras of recent phones: 0.7 to 0.8


class LocalizeResponse(BaseModel):
    building_id: str
    located: bool
    reliable: bool  # enough matches to trust the position; show unreliable results only as a hint
    floor_id: str | None = None
    space_id: str | None = None
    position: tuple[float, float] | None = None  # plan metres, as in building.json
    height_m: float | None = None  # camera height above its floor
    heading_deg: float | None = None  # viewing direction, counterclockwise from +x
    num_inliers: int
    focal_px: float | None = None
    timings_ms: dict[str, float]


class Site:
    """One building with its localization map. The GPU models are not thread-safe, so calls take a lock."""

    def __init__(self, building_path: Path, maps: Path):
        building = json.loads(building_path.read_text())
        self.frame = BuildingFrame(building)
        map_dir = maps / building["building"]["source_ref"]["map"]
        self.localizer = Localizer(map_dir)
        self.lock = threading.Lock()
        # The first GPU call compiles kernels and takes about a second; pay it before the first user does.
        self.localize((map_dir / "images" / self.localizer.names[0]).read_bytes(), None)

    def localize(self, jpeg: bytes, focal_px: float | None) -> LocalizeResponse:
        start = time.perf_counter()
        image = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise HTTPException(422, "the body is not a JPEG or PNG image")
        height, width = image.shape[:2]
        camera = phone_camera(focal_px or TYPICAL_FOCAL_PER_LONG_SIDE * max(width, height), width, height)
        decode_ms = (time.perf_counter() - start) * 1000
        with self.lock:
            result = self.localizer.localize(image, camera, estimate_focal=focal_px is None)
        timings = {"decode": round(decode_ms, 1)} | {k: round(v, 1) for k, v in result.timings_ms.items()}
        response = LocalizeResponse(
            building_id=self.frame.building_id,
            located=result.world_from_cam is not None,
            reliable=result.num_inliers >= MIN_RELIABLE_INLIERS,
            num_inliers=result.num_inliers,
            timings_ms=timings,
        )
        if result.world_from_cam is None:
            return response
        placement = self.frame.place(result.world_from_cam)
        return response.model_copy(
            update={
                "floor_id": placement.floor_id,
                "space_id": placement.space_id,
                "position": placement.position,
                "height_m": placement.height_m,
                "heading_deg": placement.heading_deg,
                "focal_px": round(result.focal_px, 1),
            }
        )


def create_app(sites: dict[str, Site], token: str) -> FastAPI:
    app = FastAPI(title="Locora localization service")

    def authorized(authorization: Annotated[str, Header()] = "") -> None:
        if not hmac.compare_digest(authorization.encode(), f"Bearer {token}".encode()):
            raise HTTPException(401, "missing or wrong token")

    @app.get("/health")
    def health() -> dict[str, list[str]]:
        return {"buildings": sorted(sites)}

    @app.post(
        "/v1/buildings/{building_id}/localize",
        dependencies=[Depends(authorized)],
        responses={404: {"description": "No map for this building"}, 413: {"description": "Image too large"}},
    )
    async def localize(
        building_id: str, request: Request, focal_px: Annotated[float | None, Query(gt=0)] = None
    ) -> LocalizeResponse:
        site = sites.get(building_id)
        if site is None:
            raise HTTPException(404, f"no localization map for building {building_id}")
        body = await request.body()
        if len(body) > MAX_IMAGE_BYTES:
            raise HTTPException(413, f"images must be smaller than {MAX_IMAGE_BYTES // 1024 // 1024} MB")
        return await run_in_threadpool(site.localize, body, focal_px)

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--maps", type=Path, required=True, help="folder that holds the map folders")
    parser.add_argument("--building", type=Path, action="append", required=True, help="building.json, repeatable")
    parser.add_argument("--host", default="127.0.0.1", help="a reverse proxy adds HTTPS in front")
    parser.add_argument("--port", type=int, default=8020)
    args = parser.parse_args()
    token = os.environ.get("LOCALIZATION_TOKEN", "")
    if len(token) < 32:
        parser.error("set LOCALIZATION_TOKEN to a random secret of at least 32 characters")
    sites = [Site(path, args.maps) for path in args.building]
    uvicorn.run(create_app({site.frame.building_id: site for site in sites}, token), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
