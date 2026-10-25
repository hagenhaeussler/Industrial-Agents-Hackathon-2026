"""The localize route forwards photos to the localization service and maps its failures. No network is used."""

import json
import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from building_api.app import create_app
from building_api.localize import MAX_IMAGE_BYTES, Localization

RESULT = {
    "building_id": "b1",
    "located": True,
    "reliable": True,
    "floor_id": "F0",
    "space_id": "S1",
    "position": [1.5, 2.0],
    "height_m": 1.4,
    "heading_deg": 90.0,
    "num_inliers": 120,
    "focal_px": 900.0,
    "timings_ms": {"total": 170},
}


class LocalizeRouteTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.database = Path(directory.name) / "unused.sqlite3"
        self.requests: list[httpx.Request] = []
        self.answer = httpx.Response(200, json=RESULT)

    def client(self, localization: Localization | None) -> TestClient:
        client = TestClient(create_app(self.database, localization))
        client.__enter__()  # runs the lifespan, which opens the shared upstream client
        self.addCleanup(client.__exit__, None, None, None)
        return client

    def upstream(self) -> Localization:
        def handle(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return self.answer

        return Localization("https://gpu.example", "secret", transport=httpx.MockTransport(handle))

    def post(self, client: TestClient, body: bytes | Iterator[bytes] = b"\xff\xd8jpeg", **kwargs) -> httpx.Response:
        headers = kwargs.pop("headers", {"Content-Type": "image/jpeg"})
        return client.post("/api/buildings/b 1/localize", content=body, headers=headers, **kwargs)

    def test_forwards_the_photo_with_the_token_and_returns_the_result_unchanged(self) -> None:
        response = self.post(self.client(self.upstream()), params={"focal_px": 900})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), RESULT)
        (sent,) = self.requests
        self.assertEqual(str(sent.url), "https://gpu.example/v1/buildings/b%201/localize?focal_px=900.0")
        self.assertEqual(sent.headers["authorization"], "Bearer secret")
        self.assertEqual(sent.content, b"\xff\xd8jpeg")

    def test_without_configuration_the_route_is_unavailable(self) -> None:
        response = self.post(self.client(None))
        self.assertEqual(response.status_code, 503)
        self.assertIn("not configured", response.json()["detail"])

    def test_rejects_other_content_types_and_large_photos_before_forwarding(self) -> None:
        client = self.client(self.upstream())
        self.assertEqual(self.post(client, headers={"Content-Type": "image/png"}).status_code, 415)
        self.assertEqual(self.post(client, body=b"x" * (MAX_IMAGE_BYTES + 1)).status_code, 413)
        self.assertEqual(self.requests, [])

    def test_maps_upstream_failures(self) -> None:
        client = self.client(self.upstream())
        for upstream, expected in ((404, 404), (422, 422), (401, 502), (500, 502)):
            self.answer = httpx.Response(upstream, json={"detail": "x"})
            self.assertEqual(self.post(client).status_code, expected, f"upstream {upstream}")

    def test_unreachable_or_slow_service_is_a_temporary_failure(self) -> None:
        for error in (httpx.ConnectError, httpx.ReadTimeout):

            def fail(request: httpx.Request, error: type[httpx.TransportError] = error) -> httpx.Response:
                raise error("no answer", request=request)

            localization = Localization("https://gpu.example", "t", transport=httpx.MockTransport(fail))
            self.assertEqual(self.post(self.client(localization)).status_code, 502, error.__name__)

    def test_rejects_a_large_photo_sent_without_a_declared_length(self) -> None:
        chunks = iter([b"x" * MAX_IMAGE_BYTES, b"x"])
        response = self.post(self.client(self.upstream()), body=chunks)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.requests, [])

    def test_the_token_never_reaches_the_caller(self) -> None:
        self.answer = httpx.Response(401, json={"detail": "bad token"})
        response = self.post(self.client(self.upstream()))
        self.assertNotIn("secret", json.dumps(response.json()))


if __name__ == "__main__":
    unittest.main()
