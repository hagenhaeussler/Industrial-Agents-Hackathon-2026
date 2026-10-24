"""Discover immutable building data and materialise contract snapshots."""

import csv
from dataclasses import dataclass
import hashlib
import importlib
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from starter_agent.building_map import outline

from .config import Settings

logger = logging.getLogger(__name__)


class BuildingSummary(BaseModel):
    id: str
    name: str
    source: str
    split: str | None
    floors: int
    has_lift: bool
    has_stairs: bool


class DerivedGeometry(BaseModel):
    anchors: dict[str, tuple[float, float]]
    areas_m2: dict[str, float]


class BuildingSnapshot(BaseModel):
    building: dict[str, Any]
    building_version: int
    content_hash: str
    closed: list[str]
    derived: DerivedGeometry


@dataclass(frozen=True)
class BuildingRecord:
    path: Path
    summary: BuildingSummary


def _inside(path: Path, root: Path) -> bool:
    return path.resolve().is_relative_to(root.resolve())


class BuildingCatalog:
    def __init__(self, settings: Settings):
        self.settings = settings

    def records(self) -> dict[str, BuildingRecord]:
        records: dict[str, BuildingRecord] = {}
        manifest = self.settings.data_dir / "manifest.csv"
        if manifest.is_file():
            with manifest.open(encoding="utf-8", newline="") as stream:
                for row in csv.DictReader(stream):
                    path = self.settings.data_dir / row["path"] / "building.json"
                    if not _inside(path, self.settings.data_dir) or not path.is_file():
                        continue
                    summary = BuildingSummary(
                        id=row["building_id"], name=row["name"], source=row["source"],
                        split=row.get("split"), floors=int(row["floors"]),
                        has_lift=row["has_lift"].lower() == "true",
                        has_stairs=row["has_stairs"].lower() == "true",
                    )
                    records[summary.id] = BuildingRecord(path, summary)
        for root in (self.settings.hero_dir, self.settings.state_dir / "uploads"):
            if not root.is_dir():
                continue
            for path in sorted(root.rglob("*.json")):
                if not _inside(path, root):
                    continue
                try:
                    raw = json.loads(path.read_text(encoding="utf-8"))
                    info = raw["building"]
                    connectors = raw["vertical_connectors"]
                    summary = BuildingSummary(
                        id=info["id"], name=info["name"], source=info.get("source", "upload"),
                        split=info.get("split"), floors=len(raw["floors"]),
                        has_lift=any(c["kind"] == "lift" for c in connectors),
                        has_stairs=any(c["kind"] == "stairs" for c in connectors),
                    )
                except (ValueError, TypeError, KeyError):
                    logger.warning("Skipping non-building JSON in catalog: %s", path.name)
                    continue
                # Uploaded data cannot shadow an immutable kit/hero building.
                records.setdefault(summary.id, BuildingRecord(path, summary))
        return records

    def get(self, building_id: str) -> BuildingRecord:
        try:
            return self.records()[building_id]
        except KeyError:
            raise KeyError(f"Building '{building_id}' was not found.") from None

    def snapshot(self, building_id: str) -> BuildingSnapshot:
        record = self.get(building_id)
        raw = json.loads(record.path.read_text(encoding="utf-8"))
        version = 0
        closed: list[str] = []
        content_hash = "sha256:" + hashlib.sha256(
            json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()[:16]
        # H01 is published independently. Fall back only when the core package is
        # absent; errors inside an installed core must surface as real failures.
        try:
            module = importlib.import_module("core.building")
        except ModuleNotFoundError as exc:
            if exc.name not in ("core", "core.building"):
                raise
        else:
            building = module.load_building(raw)
            content_hash = building.content_hash
            version = building.version
            closed = sorted(getattr(building, "closed", []))
        anchors = {}
        areas = {}
        for space in raw["spaces"]:
            polygon = outline(space["polygon"])
            anchor = polygon.representative_point()
            anchors[space["id"]] = (anchor.x, anchor.y)
            areas[space["id"]] = polygon.area
        return BuildingSnapshot(
            building=raw, building_version=version, content_hash=content_hash,
            closed=closed, derived=DerivedGeometry(anchors=anchors, areas_m2=areas),
        )
