"""Add a room layout to a scanned building: rooms, openings and equipment, for navigation demos.

A scan gives the outline of one floor and a few tables. A `layout.json` next to the `building.json` splits the
outline into rooms, adds rooms behind walls that were not scanned (`synthetic`), and places openings and assets.
The scanned rooms must cover the scanned outline exactly, so the layout cannot move the area the camera
localizes in. Assets from the scan are kept; the layout's assets get `source: "generated"`.

Run after `floor_plan`, and again after every change of the layout. A second run gives the same file:
    python -m localization.layout data/scan/<building>/building.json data/scan/<building>/layout.json
"""

import argparse
import json
from pathlib import Path

from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from building_db.source import OUTSIDE

AREA_TOLERANCE_M2 = 0.01
ON_WALL_M = 0.05  # an opening must lie this close to the outline of each space it joins


class LayoutError(ValueError):
    pass


def apply_layout(building: dict, layout: dict, layout_ref: str) -> dict:
    """The building with the layout's spaces, openings and assets. Raises LayoutError on a layout that does not
    fit the scan."""
    if len(building["floors"]) != 1:
        raise LayoutError("a layout needs a building with exactly one floor")
    floor_id = building["floors"][0]["id"]
    scanned = unary_union([Polygon(space["polygon"]) for space in building["spaces"] if not space["synthetic"]])

    spaces, polygons = [], {}
    for number, entry in enumerate(layout["spaces"], start=1):
        polygon = Polygon(entry["polygon"])
        if not polygon.is_valid:
            raise LayoutError(f"space {entry['ref']} has an invalid outline")
        if entry["ref"] in polygons:
            raise LayoutError(f"space ref {entry['ref']} is used twice")
        polygons[entry["ref"]] = polygon
        spaces.append(
            {"id": f"{floor_id}-S{number:03d}", "floor_id": floor_id}
            | {key: entry[key] for key in ("type", "room_type", "name", "ref", "polygon", "synthetic")}
        )
    check_cover(scanned, [(entry["ref"], polygons[entry["ref"]], entry["synthetic"]) for entry in layout["spaces"]])
    space_ids = {space["ref"]: space["id"] for space in spaces} | {OUTSIDE: OUTSIDE}

    openings = []
    for number, entry in enumerate(layout["openings"], start=1):
        position = Point(entry["position"])
        for ref in entry["spaces"]:
            if ref not in space_ids:
                raise LayoutError(f"opening {number} joins unknown space {ref}")
            if ref != OUTSIDE and polygons[ref].exterior.distance(position) > ON_WALL_M:
                raise LayoutError(f"opening {number} at {entry['position']} is not on the wall of space {ref}")
        openings.append(
            {
                "id": f"{floor_id}-O{number:03d}",
                "floor_id": floor_id,
                "space_ids": [space_ids[ref] for ref in entry["spaces"]],
                "kind": entry["kind"],
                "position": entry["position"],
                "width_m": entry["width_m"],
                "step_free": True,
                "synthetic": True,  # the scan shows no doors
            }
        )

    scanned_assets = [asset for asset in building["assets"] if asset["source"] != "generated"]
    added = [entry | {"source": "generated"} for entry in layout["assets"]]
    assets = []
    for number, entry in enumerate(scanned_assets + added, start=1):
        ref = containing_space(polygons, entry)
        assets.append(
            {"id": f"{building['building']['id']}-A{number:03d}", "name": entry["name"]}
            | {key: entry[key] for key in ("category", "type")}
            | {"space_id": space_ids[ref], "floor_id": floor_id}
            | {key: entry[key] for key in ("position", "footprint", "source")}
        )
    names = [asset["name"] for asset in assets]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise LayoutError(f"asset names must be unique: {duplicates}")

    info = building["building"]
    return building | {
        "building": info | {"source_ref": info["source_ref"] | {"layout": layout_ref}},
        "spaces": spaces,
        "openings": openings,
        "vertical_connectors": [],
        "assets": assets,
    }


def check_cover(scanned, spaces: list[tuple[str, Polygon, bool]]) -> None:
    """Scanned spaces must cover the scanned outline exactly and no two spaces overlap, so synthetic spaces lie
    outside the scan."""
    for index, (ref, polygon, _) in enumerate(spaces):
        for other_ref, other, _ in spaces[index + 1 :]:
            if polygon.intersection(other).area > AREA_TOLERANCE_M2:
                raise LayoutError(f"spaces {ref} and {other_ref} overlap")
    covered = unary_union([polygon for _, polygon, synthetic in spaces if not synthetic])
    if covered.symmetric_difference(scanned).area > AREA_TOLERANCE_M2:
        raise LayoutError("the scanned spaces do not cover the scanned outline exactly")


def containing_space(polygons: dict[str, Polygon], asset: dict) -> str:
    point = Point(asset["position"])
    refs = [ref for ref, polygon in polygons.items() if polygon.contains(point)]
    if len(refs) != 1:
        raise LayoutError(f"asset {asset['name']} at {asset['position']} is not inside exactly one space")
    return refs[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("building", type=Path, help="building.json from floor_plan, changed in place")
    parser.add_argument("layout", type=Path)
    args = parser.parse_args()
    building = json.loads(args.building.read_text())
    result = apply_layout(building, json.loads(args.layout.read_text()), args.layout.as_posix())
    args.building.write_text(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
