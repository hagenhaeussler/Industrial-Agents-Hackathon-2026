"""The web app is served next to the API without hiding API errors or files outside the build."""

import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from building_api.web import add_web_app


class WebAppTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        dist = root / "dist"
        (dist / "assets").mkdir(parents=True)
        (dist / "index.html").write_text("<html>app</html>")
        (dist / "assets" / "app.js").write_text("console.log(1)")
        (root / "secret.txt").write_text("outside")
        app = FastAPI()

        @app.get("/api/ping")
        def ping() -> dict[str, bool]:
            return {"ok": True}

        add_web_app(app, dist)
        self.client = TestClient(app)

    def test_client_routes_load_the_app(self) -> None:
        for path in ("/", "/b/building-1?from=a&to=b", "/admin/building-1"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn("app", response.text)

    def test_assets_and_api_keep_working(self) -> None:
        self.assertEqual(self.client.get("/assets/app.js").text, "console.log(1)")
        self.assertEqual(self.client.get("/api/ping").json(), {"ok": True})

    def test_unknown_api_paths_are_not_the_app(self) -> None:
        self.assertEqual(self.client.get("/api/missing").status_code, 404)

    def test_files_outside_the_build_are_not_served(self) -> None:
        response = self.client.get("/../secret.txt")
        self.assertNotIn("outside", response.text)


if __name__ == "__main__":
    unittest.main()
