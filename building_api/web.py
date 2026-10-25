"""Serve the built web app next to the API, for a single deployment."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def add_web_app(app: FastAPI, dist: Path) -> None:
    """Serve `dist` (the output of `pnpm build` in `web/`). Paths outside /api fall back to index.html, so the
    app's own routes such as /b/<id> load on a fresh request. Register this after the API routes."""
    root = dist.resolve()
    index = root / "index.html"
    if not index.is_file():
        raise FileNotFoundError(f"{index} does not exist; run pnpm build in web/ first")
    app.mount("/assets", StaticFiles(directory=root / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def page(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "not found")
        file = (root / path).resolve()
        if path and file.is_file() and file.is_relative_to(root):
            return FileResponse(file)
        return FileResponse(index)
