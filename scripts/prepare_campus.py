"""Prepare map metadata from building.json and public OSM data; never reads evaluation files.

Fetch the OSM building references once, then run with --raw /tmp/campus-osm-buildings.json to rebuild
offline. --calibrate takes a building ID and --room-map a matching OSM map API JSON export.
"""

import argparse
import json
import math
import statistics
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from shapely.geometry import Polygon

RADIUS = 6378137.0


def mercator(lon, lat):
    return RADIUS * math.radians(lon), RADIUS * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def geographic(x, y):
    return math.degrees(x / RADIUS), math.degrees(2 * math.atan(math.exp(y / RADIUS)) - math.pi / 2)


def google_mask(outline, latitude, padding_m=3):
    """Display-only clearance for photogrammetric facade spill beyond the OSM outline."""
    rings = [[mercator(*point) for point in ring] for ring in outline["coordinates"]]
    polygon = Polygon(rings[0], rings[1:])
    if not polygon.is_valid:
        raise ValueError("A valid building footprint is required")
    buffered = polygon.buffer(padding_m / math.cos(math.radians(latitude)), join_style="mitre")
    return {"type": "Polygon", "coordinates": [
        [geographic(*point) for point in ring.coords] for ring in [buffered.exterior, *buffered.interiors]
    ]}


def fit_frame(document, raw):
    """Fit corresponding room centroids. Reject ambiguous refs and poorly matching geometry."""
    elements = raw["elements"]
    nodes = {e["id"]: e for e in elements if e["type"] == "node"}
    candidates = {}
    for way in elements:
        tags = way.get("tags", {})
        if way["type"] != "way" or not tags.get("ref") or not tags.get("level"):
            continue
        if not all(node in nodes for node in way["nodes"]):
            continue
        try:
            polygon = Polygon([mercator(nodes[n]["lon"], nodes[n]["lat"]) for n in way["nodes"]])
            if not polygon.is_valid or polygon.area <= 0:
                continue
            for level in tags["level"].split(";"):
                candidates.setdefault((tags["ref"], float(level)), []).append(polygon.centroid)
        except ValueError:
            continue
    levels = {f["id"]: f["level"] for f in document["floors"]}
    pairs = []
    for space in document["spaces"]:
        matches = candidates.get((space["ref"], levels[space["floor_id"]]), [])
        if len(matches) == 1:
            local = Polygon(space["polygon"]).centroid
            pairs.append((local.x, local.y, matches[0].x, matches[0].y))
    if len(pairs) < 10:
        raise ValueError("At least 10 unambiguous room correspondences are required")
    means = [statistics.mean(p[i] for p in pairs) for i in range(4)]
    centered = [[p[i] - means[i] for i in range(4)] for p in pairs]
    xx = sum(p[0] ** 2 for p in centered)
    yy = sum(p[1] ** 2 for p in centered)
    xy = sum(p[0] * p[1] for p in centered)
    determinant = xx * yy - xy * xy
    if determinant <= 0:
        raise ValueError("Room correspondences do not span a two-dimensional plan")
    columns = []
    for target in (2, 3):
        bx = sum(p[0] * p[target] for p in centered)
        by = sum(p[1] * p[target] for p in centered)
        a = (bx * yy - by * xy) / determinant
        b = (by * xx - bx * xy) / determinant
        columns.append([a, b, means[target] - a * means[0] - b * means[1]])
    errors = sorted(math.hypot(
        columns[0][0] * x + columns[0][1] * y + columns[0][2] - X,
        columns[1][0] * x + columns[1][1] * y + columns[1][2] - Y,
    ) for x, y, X, Y in pairs)
    p95 = errors[int(len(errors) * 0.95)]
    if p95 > 0.25:
        raise ValueError(f"Plan alignment failed: 95th percentile residual {p95:.3f} projected metres")
    return {
        "crs": "EPSG:3857",
        "matrix": columns,
        "matchedSpaces": len(pairs),
        "medianResidualM": statistics.median(errors),
        "p95ResidualM": p95,
        "method": "Affine least-squares fit of room centroids matched by ref and level; residuals are against OSM, not survey accuracy.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--raw", type=Path)
    parser.add_argument("--room-map", type=Path)
    parser.add_argument("--calibrate")
    parser.add_argument("--featured", required=True)
    parser.add_argument("--featured-label")
    parser.add_argument("--output", type=Path, default=Path("web/public/maps/buildings.json"))
    args = parser.parse_args()
    documents = {}
    for path in sorted(args.data.glob("*/*/building.json")):
        document = json.loads(path.read_text())
        if document["building"]["source"] == "osm_indoor":
            documents[document["building"]["id"]] = document
    if args.raw:
        raw_buildings = json.loads(args.raw.read_text())
    else:
        raw_buildings = []
        for document in documents.values():
            info = document["building"]
            way_id = info["source_ref"]["osm"].removeprefix("way")
            url = f"https://api.openstreetmap.org/api/0.6/way/{way_id}/full.json"
            request = urllib.request.Request(url, headers={"User-Agent": "TalkToYourBuilding/0.1"})
            with urllib.request.urlopen(request, timeout=40) as response:
                elements = json.load(response)["elements"]
            way = next(e for e in elements if e["type"] == "way" and str(e["id"]) == way_id)
            nodes = {e["id"]: e for e in elements if e["type"] == "node"}
            raw_buildings.append({
                "building": info, "tags": way["tags"], "osm_version": way["version"],
                "outline": [[nodes[n]["lon"], nodes[n]["lat"]] for n in way["nodes"]],
            })
    buildings = []
    for raw in raw_buildings:
        id_ = raw["building"]["id"]
        document = documents[id_]
        tags = raw["tags"]
        outline = raw["outline"]
        polygon = Polygon(outline)
        west, south, east, north = polygon.bounds
        address = " ".join(filter(None, [tags.get("addr:street"), tags.get("addr:housenumber")]))
        floors = document["floors"]
        # Elevations belong to the dataset; this is an explicitly schematic exterior height.
        height = max(f["elevation_m"] + f["height_m"] for f in floors)
        item = {
            "id": id_, "name": document["building"]["name"],
            "label": tags.get("short_name", document["building"]["name"]),
            "address": address or None, "city": tags.get("addr:city"),
            "postcode": tags.get("addr:postcode"), "center": [(west + east) / 2, (south + north) / 2],
            "bounds": list(polygon.bounds), "outline": {"type": "Polygon", "coordinates": [outline]},
            "levels": [f["level"] for f in floors], "floors": len(floors),
            "rooms": sum(s["type"] == "room" for s in document["spaces"]),
            "spaces": len(document["spaces"]), "assets": len(document["assets"]),
            "height": max(height, 3), "osmUrl": "https://www.openstreetmap.org/" + document["building"]["source_ref"]["osm"].replace("way", "way/"),
            "osmVersion": raw["osm_version"],
        }
        if id_ == args.featured and args.featured_label:
            item["label"] = args.featured_label
        if id_ == args.calibrate:
            if not args.room_map:
                raise ValueError("--room-map is required for calibration")
            item["localFrame"] = fit_frame(document, json.loads(args.room_map.read_text()))
        buildings.append(item)
    if args.featured not in documents:
        raise ValueError("Featured building must be present in the source data")
    result = {
        "generatedAt": datetime.now(timezone.utc).isoformat(), "featuredBuildingId": args.featured,
        "attribution": "© OpenStreetMap contributors · ODbL 1.0", "buildings": buildings,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
    if args.room_map:
        tree_features = []
        for node in json.loads(args.room_map.read_text())["elements"]:
            if node["type"] == "node" and node.get("tags", {}).get("natural") == "tree":
                tree_features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [node["lon"], node["lat"]]},
                                      "properties": {"osmId": node["id"]}})
        args.output.with_name("trees.json").write_text(json.dumps({"type": "FeatureCollection", "features": tree_features}, separators=(",", ":")) + "\n")
    print(f"Wrote {len(buildings)} buildings to {args.output}")


if __name__ == "__main__":
    main()
