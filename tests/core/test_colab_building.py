"""Integration checks for the explicitly schematic, photo-informed Colab model."""
import csv
import hashlib
import importlib.util
import json
from itertools import combinations, pairwise
from pathlib import Path

import pytest
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from core.building import load_building
from core.routing import route
from core.validate import validate_building

DIRECTORY = Path(__file__).resolve().parents[2] / "demo" / "colab"
BUILDING_ID = "munich-urban-colab-demo"


@pytest.fixture(scope="module")
def documents():
    return tuple(json.loads((DIRECTORY / filename).read_text()) for filename in ("building.json", "metadata.json"))


def test_colab_validates_without_geometry_or_connectivity_warnings(documents):
    raw, metadata = documents
    report = validate_building(raw)
    assert report["ok"], report
    assert not report["warnings"], report
    assert {f["level"] for f in raw["floors"]} == {0, 1, 2, 3, 4}
    for floor in raw["floors"]:
        provenance = metadata["floor_provenance"][floor["id"]]
        assert provenance["basis"] == ("photo-derived" if floor["level"] in (3, 4) else "synthetic")
    assert metadata["dimensions"]["status"] == "estimated_not_measured"
    assert set(metadata["space_provenance"]) == {s["id"] for s in raw["spaces"]}
    assert set(metadata["opening_provenance"]) == {s["id"] for s in raw["openings"]}
    assert set(metadata["asset_provenance"]) == {s["id"] for s in raw["assets"]}


def test_colab_no_overlapping_spaces_or_unroutable_invented_atrium(documents):
    raw, _ = documents
    for floor in raw["floors"]:
        shapes = [(s["id"], Polygon(s["polygon"])) for s in raw["spaces"] if s["floor_id"] == floor["id"]]
        for (first_id, first), (second_id, second) in combinations(shapes, 2):
            assert first.intersection(second).area < 1e-8, (first_id, second_id)
    assert all(s["room_type"] != "atrium_void" for s in raw["spaces"])


def test_colab_source_copies_and_generator_are_reproducible(documents):
    raw, metadata = documents
    for photo in metadata["source_photos"]:
        assert hashlib.sha256((DIRECTORY / photo["stored_path"]).read_bytes()).hexdigest() == photo["sha256"]
    spec = importlib.util.spec_from_file_location("colab_generator_test", DIRECTORY / "generate.py")
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    generated = generator.build_model(generator.photo_manifest(DIRECTORY / "sources"))
    assert generated == (raw, metadata)
    with (DIRECTORY / "equipment.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert {r["asset_id"] for r in rows} == {a["id"] for a in raw["assets"]}


def test_colab_animation_is_contained_and_crosses_real_openings(documents):
    raw, metadata = documents
    spaces = {s["id"]: s for s in raw["spaces"]}
    polygons = {sid: Polygon(space["polygon"]) for sid, space in spaces.items()}
    for move in metadata["movable_assets"]:
        assert polygons[move["space_id"]].covers(LineString([move["from"], move["to"]]))
    for waypoint in metadata["walk_path"]:
        assert spaces[waypoint["space_id"]]["floor_id"] == waypoint["floor_id"]
        assert polygons[waypoint["space_id"]].covers(Point(waypoint["x"], waypoint["y"]))
    for first, second in pairwise(metadata["walk_path"]):
        assert first["floor_id"] == second["floor_id"]
        segment = LineString([(first["x"], first["y"]), (second["x"], second["y"])])
        assert unary_union([polygons[first["space_id"]], polygons[second["space_id"]]]).covers(segment)
        if first["space_id"] != second["space_id"]:
            doors = [o for o in raw["openings"] if set(o["space_ids"]) == {first["space_id"], second["space_id"]}]
            assert any(segment.distance(Point(o["position"])) < 1e-8 for o in doors)


def test_colab_floor3_to_floor4_routes_use_real_connectors(documents):
    raw, metadata = documents
    building = load_building(raw)
    for request in metadata["demo_routes"]:
        result = route(building, request["from"], request["to"], request["constraints"])
        assert result["reachable"], result
        assert result["length_m"] > 0
        assert not any(segment.get("fallback") for segment in result["segments"])
        vertical = [segment["kind"] for segment in result["segments"] if segment["kind"] != "walk"]
        assert vertical and set(vertical) == ({"lift"} if request["constraints"].get("step_free") else {"stairs"})
        for segment in result["segments"]:
            if segment["kind"] == "walk" and len(segment["points"]) > 1:
                assert building.polygons[segment["space_id"]].buffer(1e-6).covers(LineString(segment["points"]))
    inaccessible = route(building, f"{BUILDING_ID}-F3-A-coffee", f"{BUILDING_ID}-F4-A-coffee",
                         {"step_free": True, "closed": [f"{BUILDING_ID}-V-lift"]})
    assert not inaccessible["reachable"]
    assert inaccessible["reason"] == "blocked_by_closure"
