"""Forward camera images to the localization service. Its URL and token stay on this server.

The contract is in docs/localization.md ("Localization service"). The response body passes through unchanged.
"""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Annotated
from urllib.parse import quote

import httpx
from fastapi import APIRouter, FastAPI, HTTPException, Query, Request, Response

MAX_IMAGE_BYTES = 4 * 1024 * 1024
TIMEOUT_S = 5.0
PASSED_THROUGH = {200, 404, 413, 422}
"""Upstream answers the phone can act on. Other failures become 502 or 503."""


@dataclass
class Localization:
    """Where the localization service runs. One HTTP client keeps the TLS connection open between frames."""

    url: str
    token: str
    transport: httpx.AsyncBaseTransport | None = None
    client: httpx.AsyncClient | None = field(default=None, init=False)

    @classmethod
    def from_environment(cls) -> "Localization | None":
        url, token = os.environ.get("LOCALIZATION_URL"), os.environ.get("LOCALIZATION_TOKEN")
        return cls(url.rstrip("/"), token) if url and token else None

    @asynccontextmanager
    async def connected(self) -> AsyncIterator[None]:
        async with httpx.AsyncClient(timeout=TIMEOUT_S, transport=self.transport) as client:
            self.client = client
            try:
                yield
            finally:
                self.client = None


def localization_router(localization: Localization | None) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/api/buildings/{building_id}/localize",
        responses={
            404: {"description": "Building without a localization map"},
            413: {"description": "Image larger than 4 MB"},
            415: {"description": "Body is not image/jpeg"},
            422: {"description": "Body is not a readable image"},
            502: {"description": "Localization service failed or rejected the server's token"},
            503: {"description": "Localization not configured or not reachable"},
        },
    )
    async def localize(
        building_id: str,
        request: Request,
        focal_px: Annotated[float | None, Query(gt=0, description="Camera focal length in pixels, if known")] = None,
    ) -> Response:
        """Find where an upright JPEG photo was taken. Only results with `reliable: true` should be used."""
        if localization is None or localization.client is None:
            raise HTTPException(503, "localization not configured")
        if request.headers.get("content-type", "").split(";")[0].strip().lower() != "image/jpeg":
            raise HTTPException(415, "send the photo as image/jpeg")
        image = await read_limited(request)
        try:
            upstream = await localization.client.post(
                f"{localization.url}/v1/buildings/{quote(building_id, safe='')}/localize",
                content=image,
                params={"focal_px": focal_px} if focal_px is not None else None,
                headers={"Authorization": f"Bearer {localization.token}", "Content-Type": "image/jpeg"},
            )
        except httpx.HTTPError:
            raise HTTPException(503, "localization service not reachable") from None
        if upstream.status_code == 401:
            raise HTTPException(502, "localization service rejected the server's token")
        if upstream.status_code not in PASSED_THROUGH:
            raise HTTPException(502, f"localization service failed ({upstream.status_code})")
        return Response(upstream.content, upstream.status_code, media_type="application/json")

    return router


async def read_limited(request: Request) -> bytes:
    """The request body, or 413 as soon as it passes the size limit."""
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "image larger than 4 MB")
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_IMAGE_BYTES:
            raise HTTPException(413, "image larger than 4 MB")
    return bytes(body)


def lifespan(localization: Localization | None):
    @asynccontextmanager
    async def run(_: FastAPI) -> AsyncIterator[None]:
        if localization is None:
            yield
            return
        async with localization.connected():
            yield

    return run
