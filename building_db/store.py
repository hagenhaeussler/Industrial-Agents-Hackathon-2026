"""SQLite storage for buildings: connection setup, import and read-back."""

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Literal

from shapely.geometry import Polygon

from building_db.source import (
    Asset,
    BuildingDocument,
    BuildingInfo,
    BuildingSourceError,
    Floor,
    Footprint,
    Opening,
    Space,
    VerticalConnector,
    read_building,
)

SCHEMA_VERSION = 1
CALCULATION_VERSION = 1
"""Bump when a derived-value function such as polygon_area changes, and recompute stored values."""


def polygon_area(polygon_json: str) -> float:
    """Area in m² of a polygon stored as a JSON list of [x, y] points. Handles irregular rooms."""
    return Polygon(json.loads(polygon_json)).area


def connect(path: Path | str) -> sqlite3.Connection:
    """Open the building database, creating the schema if the file is new."""
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.create_function("polygon_area", 1, polygon_area, deterministic=True)
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version == 0:
        connection.executescript(resources.files("building_db").joinpath("schema.sql").read_text())
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    elif version != SCHEMA_VERSION:
        connection.close()
        raise RuntimeError(f"{path} has schema version {version}; this code expects {SCHEMA_VERSION}")
    return connection


def connect_readonly(path: Path | str) -> sqlite3.Connection:
    """Open an existing building database for reading only. Never creates or changes the file.

    The connection may be used from a different thread than the one that opened it, as web frameworks do,
    but not from two threads at once.
    """
    connection = sqlite3.connect(f"{Path(path).resolve().as_uri()}?mode=ro", uri=True, check_same_thread=False)
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version != SCHEMA_VERSION:
        connection.close()
        raise RuntimeError(f"{path} has schema version {version}; this code expects {SCHEMA_VERSION}")
    return connection


ImportStatus = Literal["imported", "unchanged", "conflict", "failed"]


@dataclass(frozen=True)
class ImportResult:
    path: Path
    status: ImportStatus
    building_id: str | None = None
    message: str = ""


def import_building(connection: sqlite3.Connection, path: Path) -> ImportResult:
    """Import one building.json atomically. Never overwrites a stored building with different content."""
    try:
        document = read_building(path)
    except BuildingSourceError as error:
        return ImportResult(path, "failed", message="; ".join(error.problems))

    building_id = document.building.id
    content_sha256 = content_identity(path)
    stored = connection.execute("SELECT content_sha256 FROM buildings WHERE id = ?", (building_id,)).fetchone()
    if stored is not None:
        if stored[0] == content_sha256:
            return ImportResult(path, "unchanged", building_id)
        return ImportResult(path, "conflict", building_id, "a building with this id and different content is stored")

    with connection:
        insert_building(connection, document, path, content_sha256)
    return ImportResult(path, "imported", building_id)


def content_identity(path: Path) -> str:
    """Hash of the JSON content, independent of whitespace and key order."""
    canonical = json.dumps(json.loads(path.read_bytes()), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def insert_building(
    connection: sqlite3.Connection, document: BuildingDocument, path: Path, content_sha256: str
) -> None:
    info = document.building
    building_id = info.id
    connection.execute(
        "INSERT INTO buildings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            building_id,
            info.name,
            info.source,
            json.dumps(info.source_ref),
            info.license,
            info.attribution,
            info.split,
            info.units,
            content_sha256,
            str(path.resolve()),
            CALCULATION_VERSION,
        ),
    )
    connection.executemany(
        "INSERT INTO floors VALUES (?, ?, ?, ?, ?, ?)",
        [(building_id, f.id, f.level, f.name, f.elevation_m, f.height_m) for f in document.floors],
    )
    connection.executemany(
        "INSERT INTO spaces (building_id, id, floor_id, type, room_type, name, ref, polygon, synthetic)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (building_id, s.id, s.floor_id, s.type, s.room_type, s.name, s.ref, json.dumps(s.polygon), s.synthetic)
            for s in document.spaces
        ],
    )
    connection.executemany(
        "INSERT INTO openings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (building_id, o.id, o.floor_id, o.kind, *o.space_ids, *o.position, o.width_m, o.step_free, o.synthetic)
            for o in document.openings
        ],
    )
    connection.executemany(
        "INSERT INTO vertical_connectors VALUES (?, ?, ?, ?, ?, ?)",
        [(building_id, v.id, v.kind, v.name, v.step_free, v.synthetic) for v in document.vertical_connectors],
    )
    connection.executemany(
        "INSERT INTO connector_stops VALUES (?, ?, ?, ?, ?)",
        [
            (building_id, v.id, index, floor_id, space_id)
            for v in document.vertical_connectors
            for index, (floor_id, space_id) in enumerate(zip(v.floor_ids, v.space_ids, strict=True))
        ],
    )
    connection.executemany(
        "INSERT INTO assets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                building_id,
                a.id,
                a.floor_id,
                a.space_id,
                a.name,
                a.category,
                a.type,
                *a.position,
                a.footprint.width_m,
                a.footprint.depth_m,
                a.footprint.rotation_deg,
                a.source,
            )
            for a in document.assets
        ],
    )


def load_building(connection: sqlite3.Connection, building_id: str) -> BuildingDocument:
    """Read a stored building back in the source format. Each list is ordered by entity id."""

    def rows(sql: str) -> list[tuple]:
        return connection.execute(sql, (building_id,)).fetchall()

    building = rows(
        "SELECT id, name, source, source_ref, license, attribution, split, units FROM buildings WHERE id = ?"
    )
    if not building:
        raise KeyError(f"building {building_id} is not stored")
    id_, name, source, source_ref, license_, attribution, split, units = building[0]

    stops: dict[str, list[tuple[str, str]]] = {}
    for connector_id, floor_id, space_id in rows(
        "SELECT connector_id, floor_id, space_id FROM connector_stops WHERE building_id = ?"
        " ORDER BY connector_id, stop_index"
    ):
        stops.setdefault(connector_id, []).append((floor_id, space_id))

    return BuildingDocument(
        building=BuildingInfo(
            id=id_,
            name=name,
            source=source,
            source_ref=json.loads(source_ref),
            license=license_,
            attribution=attribution,
            split=split,
            units=units,
        ),
        floors=[
            Floor(id=i, level=level, name=n, elevation_m=elevation, height_m=height)
            for i, level, n, elevation, height in rows(
                "SELECT id, level, name, elevation_m, height_m FROM floors WHERE building_id = ? ORDER BY id"
            )
        ],
        spaces=[
            Space(
                id=i,
                floor_id=floor_id,
                type=type_,
                room_type=room_type,
                name=n,
                ref=ref,
                polygon=[(x, y) for x, y in json.loads(polygon)],
                synthetic=bool(synthetic),
            )
            for i, floor_id, type_, room_type, n, ref, polygon, synthetic in rows(
                "SELECT id, floor_id, type, room_type, name, ref, polygon, synthetic"
                " FROM spaces WHERE building_id = ? ORDER BY id"
            )
        ],
        openings=[
            Opening(
                id=i,
                floor_id=floor_id,
                space_ids=(space_a, space_b),
                kind=kind,
                position=(x, y),
                width_m=width,
                step_free=bool(step_free),
                synthetic=bool(synthetic),
            )
            for i, floor_id, kind, space_a, space_b, x, y, width, step_free, synthetic in rows(
                "SELECT id, floor_id, kind, space_a_id, space_b_id, x, y, width_m, step_free, synthetic"
                " FROM openings WHERE building_id = ? ORDER BY id"
            )
        ],
        vertical_connectors=[
            VerticalConnector(
                id=i,
                kind=kind,
                name=n,
                floor_ids=[floor_id for floor_id, _ in stops[i]],
                space_ids=[space_id for _, space_id in stops[i]],
                step_free=bool(step_free),
                synthetic=bool(synthetic),
            )
            for i, kind, n, step_free, synthetic in rows(
                "SELECT id, kind, name, step_free, synthetic FROM vertical_connectors WHERE building_id = ? ORDER BY id"
            )
        ],
        assets=[
            Asset(
                id=i,
                name=n,
                category=category,
                type=type_,
                space_id=space_id,
                floor_id=floor_id,
                position=(x, y),
                footprint=Footprint(width_m=width, depth_m=depth, rotation_deg=rotation),
                source=source_,
            )
            for i, floor_id, space_id, n, category, type_, x, y, width, depth, rotation, source_ in rows(
                "SELECT id, floor_id, space_id, name, category, type, x, y, width_m, depth_m, rotation_deg, source"
                " FROM assets WHERE building_id = ? ORDER BY id"
            )
        ],
    )
