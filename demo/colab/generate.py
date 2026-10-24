"""Reproducible, schematic Colab demo model; all unmeasured dimensions are estimates.

Run from the repository root: python demo/colab/generate.py --photos ../Fluchtplaene
The source photographs are inspected manually, never treated as scale drawings.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

BUILDING_ID = "munich-urban-colab-demo"
HERE = Path(__file__).resolve().parent
PHOTO_BASE = "WhatsApp Image 2026-10-25 at 00.46.58"
PHOTO_NAMES = [PHOTO_BASE + ".jpeg"] + [f"{PHOTO_BASE} ({i}).jpeg" for i in range(1, 7)]
SOURCE_NAMES = ["photo-00-central-core-crop.jpeg", "photo-01-floor-3-central.jpeg",
                "photo-02-floor-3-office-wing.jpeg", "photo-03-floor-4-office-wing.jpeg",
                "photo-04-floor-4-core-side.jpeg", "photo-05-floor-4-central.jpeg",
                "photo-06-floor-4-other-side.jpeg"]
PHOTO_FLOORS = [None, 3, 3, 4, 4, 4, 4]
PHOTO_NOTES = [
    "Cropped central service core; floor heading missing. Corroborates floor-3 arrangement; not independent floor evidence.",
    "Heading 3. Obergeschoss. Five Besprechung rooms, Küche, lift, WC, ELT-Verteiler, EDV, Putzraum, central stair flights, open offices.",
    "Heading 3. Obergeschoss. Side wing: five Büro labels, a stair, open office, Think Tank pods, terrace and atrium.",
    "Heading 4. Obergeschoss. Side wing: five Büro labels, a stair, Think Tank pods, atria, terrace, Küche, Aktivraum/Bib.",
    "Heading 4. Obergeschoss. Rotated central-core view: meeting rooms, kitchen, lift, WC, EDV, terraces, Aktivraum/Bib.",
    "Heading 4. Obergeschoss. Four Besprechung rooms, Aktivraum/Bib, Küche, WC, lift, EDV, ELT-Verteiler, two side terraces and stair flights.",
    "Heading 4. Obergeschoss. Another rotated partial view: meeting rooms, WC/lift, open office, Think Tank pods, terrace and atrium.",
]


def rect(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def build_model(source_photos):
    raw = {
        "building": {
            "id": BUILDING_ID,
            "name": "Munich Urban Colab · schematic demo",
            "source": "user_photos_and_synthetic_demo",
            "source_ref": {"metadata": "demo/colab/metadata.json", "photo_count": 7},
            "license": "User-supplied reference photos; model for hackathon demonstration",
            "attribution": "Venue plan features traced from user-supplied photographs; unmeasured demo geometry and furniture by the team.",
            "split": "demo",
            "units": "m",
            "description": "Photo-derived schematic of floors 3–4; floors 0–2 and all metric dimensions are illustrative. Not surveyed and not an evacuation plan.",
            "geometry_accuracy": "unmeasured schematic",
        },
        "floors": [], "spaces": [], "openings": [], "vertical_connectors": [], "assets": [],
    }
    metadata = {
        "schema_version": 1,
        "building_id": BUILDING_ID,
        "title": "Munich Urban Colab",
        "subtitle": "Photo-inspired upper floors · illustrative dimensions",
        "source_photos": source_photos,
        "source_date": "2026-10-25",
        "default_floor_level": 3,
        "floor_provenance": {}, "space_provenance": {}, "opening_provenance": {},
        "asset_provenance": {}, "connector_provenance": {},
        "dimensions": {
            "status": "estimated_not_measured", "units": "m",
            "main_core_extent": [56, 28], "combined_demo_extent": [56, 36],
            "floor_to_floor_m": 4.0, "floor_clear_height_m": 3.5,
            "door_width_m": 1.0, "lift_door_width_m": 1.2,
            "corridor_opening_width_m": 2.4,
            "method": "Manual orthogonal schematic of visible adjacency and labels; no scale bar, measured reference, perspective calibration or site survey was available.",
            "confidence": "No defensible metric accuracy bound; distances are demo-model distances only.",
        },
        "coordinate_frame": {
            "origin": "South-west corner of schematic central block", "x": "right", "y": "up",
            "north": "Not georeferenced. Photo orientation arrows vary with the posted-plan viewing direction.",
            "alignment": "Floors share an illustrative XY frame. Side-wing registration and correspondence of stair stops are inferred.",
        },
        "notes": [
            "Floor-3 and floor-4 room categories and broad service-core adjacency are visible in photos. Absolute coordinates, room sizes, door widths, heights and wing registration are inferred.",
            "The source plans are partial and differently rotated. The combined model is a deliberately simplified central block plus side office wing, not a complete or rectified whole-building trace.",
            "The photos show lift and stair symbols. Their modeled continuity across all five floors and accessibility are demo assumptions, not verified on site.",
            "Ground-floor reception is mentioned in the plan legend; its layout and entrance are synthetic. Floors 1 and 2 are wholly synthetic at the user's request.",
            "Atrium/void regions are omitted from walkable spaces. Terrace geometry is modeled only where recognizable in the chosen upper-floor view.",
            "No room numbers are legible: refs such as 3.01 are generated demo labels, not observed venue signage.",
            "Furniture, coffee machines and movable equipment are illustrative additions. A visible kitchen label does not establish exact furniture inventory or placement.",
            "Use for software demonstration only: not surveyed, not verified accessibility guidance and not an evacuation plan. Follow venue signage for actual movement.",
        ],
        "movable_assets": [], "walk_path": [],
    }
    spaces = {}

    def fid(level):
        return f"{BUILDING_ID}-F{level}"

    def sid(level, key):
        return f"{fid(level)}-S-{key}"

    def add_space(level, key, name, room_type, polygon, *, kind="room", label=None, observed=True, notes=""):
        identifier = sid(level, key)
        number = 1 + sum(s["floor_id"] == fid(level) for s in raw["spaces"])
        entry = {"id": identifier, "floor_id": fid(level), "type": kind, "room_type": room_type,
                 "name": f"{name} {level}.{number:02}", "ref": f"{level}.{number:02}",
                 "polygon": polygon, "synthetic": True}
        if label:
            entry["source_label"] = label
        raw["spaces"].append(entry)
        spaces[identifier] = entry
        is_photo = level in (3, 4) and observed
        photo_indices = ([1, 2] if level == 3 else [3, 4, 5, 6]) if is_photo else []
        metadata["space_provenance"][identifier] = {
            "basis": "photo-derived" if is_photo else "synthetic",
            "label_basis": "observed_category" if is_photo and label else "demo_label",
            "observed_label": label if is_photo else None,
            "source_photo_ids": [source_photos[i]["id"] for i in photo_indices],
            "geometry": "inferred_schematic", "dimensions": "estimated_not_measured",
            "room_ref": "generated_demo_ref", "notes": notes,
        }
        return identifier

    def opening(level, key, first, second, xy, *, width=1.0, kind="door", observed=True):
        identifier = f"{fid(level)}-O-{key}"
        refs = [sid(level, first) if first != "outside" else first,
                sid(level, second) if second != "outside" else second]
        raw["openings"].append({"id": identifier, "floor_id": fid(level), "space_ids": refs,
                                "kind": kind, "position": list(xy), "width_m": width,
                                "step_free": True, "synthetic": True})
        metadata["opening_provenance"][identifier] = {
            "basis": "photo-informed_adjacency" if level in (3, 4) and observed else "synthetic",
            "position": "inferred_boundary_position", "width": "estimated_not_measured",
            "step_free": "demo_assumption_not_accessibility_survey",
        }

    def asset(level, key, name, kind, room, xy, size=(0.8, 0.6), *, category="furniture", visible_pod=False):
        identifier = f"{fid(level)}-A-{key}"
        raw["assets"].append({"id": identifier, "name": f"{name} · floor {level}",
                              "type": kind, "category": category, "floor_id": fid(level),
                              "space_id": sid(level, room), "position": list(xy),
                              "footprint": {"width_m": size[0], "depth_m": size[1], "rotation_deg": 0},
                              "source": "demo_illustration"})
        metadata["asset_provenance"][identifier] = {
            "basis": "photo_category_inferred_position" if visible_pod and level in (3, 4) else "synthetic",
            "position": "illustrative_not_observed", "dimensions": "estimated_not_measured",
        }
        return identifier

    for level in range(5):
        photo = level in (3, 4)
        floor_id = fid(level)
        raw["floors"].append({"id": floor_id, "level": level,
                              "name": "Ground floor (illustrative)" if level == 0 else f"Floor {level}" + (" (illustrative)" if not photo else ""),
                              "elevation_m": level * 4.0, "height_m": 3.5})
        metadata["floor_provenance"][floor_id] = {
            "basis": "photo-derived" if photo else "synthetic",
            "label": f"{level}. Obergeschoss" if photo else "Illustrative ground floor" if level == 0 else f"Synthetic floor {level}",
            "notes": "Observed room categories and core arrangement; estimated coordinates, heights and wing registration." if photo else "No floor-plan photograph supplied; illustrative layout for the cross-floor demo.",
            "source_photo_ids": ([source_photos[i]["id"] for i in ([1, 2] if level == 3 else [3, 4, 5, 6])] if photo else []),
            "geometry": "schematic_not_surveyed", "elevation": "estimated",
        }

        for key, name, box in [
            ("south-corridor", "Meeting corridor", (8, 6, 48, 9)),
            ("west-corridor", "West core corridor", (12, 9, 16, 22)),
            ("east-corridor", "East core corridor", (40, 9, 44, 22)),
            ("north-corridor", "Stair lobby", (16, 14, 40, 17)),
        ]:
            add_space(level, key, name, "corridor", rect(*box), kind="corridor", label="Fluchtweg", notes="Green highlighted movement zone simplified to connected corridor rectangles; not asserted as an approved escape route.")

        if level == 4:
            west = [[0, 20], [8, 20], [8, 9], [12, 9], [12, 22], [19, 22], [19, 28], [0, 28]]
            east = [[44, 9], [48, 9], [48, 20], [56, 20], [56, 28], [40, 28], [40, 22], [44, 22]]
        else:
            west = [[0, 0], [8, 0], [8, 9], [12, 9], [12, 22], [19, 22], [19, 28], [0, 28]]
            east = [[48, 0], [56, 0], [56, 28], [40, 28], [40, 22], [44, 22], [44, 9], [48, 9]]
        add_space(level, "open-west", "Reception and coworking" if level == 0 else "Open office west", "lobby" if level == 0 else "office", west, kind="hall", label="offener Bürobereich")
        add_space(level, "open-east", "Open office east", "office", east, kind="hall", label="offener Bürobereich")

        for index, (x0, x1) in enumerate([(8, 14), (14, 20), (20, 26), (26, 32), (32, 40)], start=1):
            active = level == 4 and index == 5
            name, room_type, label = ("Activity room / library", "library", "Aktivraum/Bib") if active else (f"Meeting room {index}", "meeting_room", "Besprechung")
            add_space(level, f"meeting-{index}", name, room_type, rect(x0, 0, x1, 6), label=label)
            opening(level, f"meeting-{index}", f"meeting-{index}", "south-corridor", ((x0 + x1) / 2, 6))
            asset(level, f"table-{index}", f"Meeting table {index}", "meeting_table", f"meeting-{index}", ((x0 + x1) / 2, 3), (2.4, 1.2))
            for side, dy in [("north", 1.1), ("south", -1.1)]:
                asset(level, f"chair-{index}-{side}", f"Meeting chair {index} {side}", "chair", f"meeting-{index}", ((x0 + x1) / 2, 3 + dy), (0.5, 0.5))
        add_space(level, "kitchen", "Kitchen", "kitchen", rect(40, 0, 48, 6), label="Küche")
        opening(level, "kitchen", "kitchen", "south-corridor", (44, 6))

        service = [
            ("lift", "Central lift", "lift", (16, 9, 20, 14), "Aufzug", "lift"),
            ("wc-west", "Toilets west", "toilet", (20, 9, 26, 14), "WC", "room"),
            ("wc-east", "Toilets east", "toilet", (26, 9, 31, 14), "WC", "room"),
            (("wc-small", "Internal stair landing", "stairwell", (31, 9, 34, 14), "Treppe", "stair") if level == 4
             else ("wc-small", "Small toilet", "toilet", (31, 9, 34, 14), "WC", "room")),
            ("electrical", "Electrical distribution", "technical_room", (34, 9, 37, 14), "ELT-Verteiler", "room"),
            ("it", "IT room", "server_room", (37, 9, 40, 14), "EDV", "room"),
        ]
        for key, name, typ, box, label, kind in service:
            add_space(level, key, name, typ, rect(*box), kind=kind, label=label,
                      notes="Small internal stair symbol visible on floor 4; no unobserved vertical destination is invented for it." if level == 4 and key == "wc-small" else "")
            opening(level, key, key, "south-corridor", ((box[0] + box[2]) / 2, 9), width=1.2 if key == "lift" else 1.0)

        for key, name, box in [("stairs-west", "Central stairs west", (20, 17, 28, 21)), ("stairs-east", "Central stairs east", (32, 17, 40, 21))]:
            add_space(level, key, name, "stairwell", rect(*box), kind="stair", label="Treppe", notes="Visible stair-flight arrangement reduced to an independent demo stair stop; cross-floor correspondence inferred.")
            opening(level, key, key, "north-corridor", ((box[0] + box[2]) / 2, 17), width=1.4)

        for key, first, second, xy in [
            ("south-west", "south-corridor", "west-corridor", (14, 9)),
            ("south-east", "south-corridor", "east-corridor", (42, 9)),
            ("west-north", "west-corridor", "north-corridor", (16, 15.5)),
            ("east-north", "east-corridor", "north-corridor", (40, 15.5)),
            ("open-west", "west-corridor", "open-west", (12, 12)),
            ("open-east", "east-corridor", "open-east", (44, 12)),
        ]:
            opening(level, key, first, second, xy, width=2.4, kind="opening")

        add_space(level, "office-wing-corridor", "Office wing corridor", "corridor", rect(0, 28, 30, 30), kind="corridor", label="Fluchtweg", notes="Wing-to-central-block registration and this joining position are inferred from separate, rotated partial views.")
        opening(level, "wing-link", "open-west", "office-wing-corridor", (8, 28), width=2.4, kind="opening", observed=False)
        for i, (x0, x1) in enumerate([(0, 8), (8, 13), (17, 21), (21, 25), (25, 30)], 1):
            add_space(level, f"office-{i}", f"Office {i}", "office", rect(x0, 30, x1, 36), label="Büro", notes="Five offices and a stair bay are visible; dimensions and placement of this wing in the shared XY frame are inferred.")
            opening(level, f"office-{i}", f"office-{i}", "office-wing-corridor", ((x0 + x1) / 2, 30))
            asset(level, f"desk-{i}", f"Office desk {i}", "desk", f"office-{i}", ((x0 + x1) / 2, 33), (1.6, 0.8))
        add_space(level, "stairs-wing", "Office wing stairs", "stairwell", rect(13, 30, 17, 36), kind="stair", label="Treppe")
        opening(level, "stairs-wing", "stairs-wing", "office-wing-corridor", (15, 30), width=1.4)

        if level == 4:
            for side, box, xy in [("west", (0, 0, 8, 20), (8, 12)), ("east", (48, 0, 56, 20), (48, 12))]:
                add_space(level, f"terrace-{side}", f"Terrace {side}", "balcony", rect(*box), kind="outdoor", label="Terrasse", notes="Side terraces visible in the frontal floor-4 plan; exact size and step-free threshold unverified.")
                opening(level, f"terrace-{side}", f"terrace-{side}", f"open-{side}", xy)
        elif level == 3:
            add_space(level, "terrace-wing", "Office wing terrace", "balcony", rect(19, 22, 29, 28), kind="outdoor", label="Terrasse", notes="Terrace is visible in the side-wing view; placement against this schematic open office is inferred.")
            opening(level, "terrace-wing", "terrace-wing", "open-west", (19, 25), observed=False)

        asset(level, "coffee", "Coffee machine", "coffee_machine", "kitchen", (46, 1.2), (0.6, 0.55), category="equipment")
        asset(level, "kitchen-table", "Kitchen table", "meeting_table", "kitchen", (43, 3), (2.0, 1.0))
        asset(level, "fridge", "Kitchen refrigerator", "refrigerator", "kitchen", (40.7, 1), (0.7, 0.7), category="equipment")
        asset(level, "think-tank-west", "Think Tank west", "think_tank", "open-west", (4, 24), (2, 2), visible_pod=True)
        asset(level, "think-tank-east", "Think Tank east", "think_tank", "open-east", (52, 24), (2, 2), visible_pod=True)
        asset(level, "sofa", "Office lounge sofa", "sofa", "open-east", (52, 21.5), (2.4, 1.0))
        asset(level, "mobile-display", "Mobile presentation display", "mobile_display", "open-west", (10, 16), (0.9, 0.6), category="equipment")
        asset(level, "tool-cart", "Demo tool cart", "tool_cart", "open-east", (46, 16), (0.9, 0.6), category="equipment")

    opening(0, "entry", "outside", "open-west", (0, 4), width=1.8, kind="entrance", observed=False)
    for key, kind, name in [("lift", "lift", "Central lift"), ("stairs-west", "stairs", "Central stairs west"), ("stairs-east", "stairs", "Central stairs east"), ("stairs-wing", "stairs", "Office wing stairs")]:
        identifier = f"{BUILDING_ID}-V-{key}"
        raw["vertical_connectors"].append({"id": identifier, "kind": kind, "name": name,
                                            "floor_ids": [fid(level) for level in range(5)],
                                            "space_ids": [sid(level, key) for level in range(5)],
                                            "step_free": kind == "lift", "synthetic": True})
        metadata["connector_provenance"][identifier] = {
            "basis": "visible_upper_floor_symbol_with_inferred_continuity",
            "notes": "Cross-floor stop correspondence, operation and accessibility are illustrative; no on-site verification.",
        }

    metadata["movable_assets"] = [
        {"asset_id": f"{fid(4)}-A-coffee", "from": [46, 1.2], "to": [44.8, 1.2], "floor_id": fid(4), "space_id": sid(4, "kitchen"), "duration_s": 6, "purpose": "Illustrative furniture move; not observed live tracking."},
        {"asset_id": f"{fid(3)}-A-mobile-display", "from": [10, 16], "to": [10, 19], "floor_id": fid(3), "space_id": sid(3, "open-west"), "duration_s": 8, "purpose": "Illustrative equipment move within one valid space."},
        {"asset_id": f"{fid(4)}-A-kitchen-table", "from": [43, 3], "to": [43, 4], "floor_id": fid(4), "space_id": sid(4, "kitchen"), "duration_s": 7, "purpose": "Illustrative table rearrangement."},
    ]
    # A hand-placed illustrative walk, checked against the polygon union and doors.
    # It stays on floor 4; a real cross-floor route is available through the core.
    for key, x, y in [("kitchen", 44, 3), ("kitchen", 44, 5.5), ("kitchen", 44, 6),
                      ("south-corridor", 44, 7.5), ("south-corridor", 42, 7.5), ("south-corridor", 42, 9),
                      ("east-corridor", 42, 15.5), ("east-corridor", 40, 15.5),
                      ("north-corridor", 36, 15.5), ("north-corridor", 36, 17), ("stairs-east", 36, 19)]:
        metadata["walk_path"].append({"floor_id": fid(4), "space_id": sid(4, key), "x": x, "y": y})
    metadata["walk_path_basis"] = "Illustrative floor-4 kitchen-to-stairs walk; hand-placed inside modeled spaces. Not measured pedestrian tracking. No vertical teleport animation."
    metadata["demo_routes"] = [
        {"name": "Coffee across floors, step-free", "from": f"{fid(3)}-A-coffee", "to": f"{fid(4)}-A-coffee", "constraints": {"step_free": True}},
        {"name": "Cross-floor stairs while lift is closed", "from": f"{fid(3)}-A-coffee", "to": f"{fid(4)}-A-coffee", "constraints": {"closed": [f"{BUILDING_ID}-V-lift"]}},
    ]
    return raw, metadata


def photo_manifest(folder):
    result = []
    for index, (name, level, notes) in enumerate(zip(PHOTO_NAMES, PHOTO_FLOORS, PHOTO_NOTES)):
        path = folder / name
        if not path.exists():
            path = folder / SOURCE_NAMES[index]
        result.append({"id": f"photo-{index:02}", "filename": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                       "stored_path": f"sources/{SOURCE_NAMES[index]}",
                       "heading_floor_level": level, "observed": notes, "metric_calibration": None,
                       "rights": "User-supplied photograph; source poster copyright not assessed. The source file is copied byte-for-byte, preserving its original metadata."})
    return result


def write_model(output, raw, metadata):
    output.mkdir(parents=True, exist_ok=True)
    for filename, value in [("building.json", raw), ("metadata.json", metadata)]:
        (output / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    spaces = {s["id"]: s for s in raw["spaces"]}
    floors = {f["id"]: f for f in raw["floors"]}
    fields = ["asset_id", "name", "type", "category", "source", "building_id", "floor_level", "floor_name", "space_id", "space_name", "room_ref", "room_type", "x_m", "y_m", "width_m", "depth_m", "rotation_deg"]
    with (output / "equipment.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        for a in raw["assets"]:
            s, f = spaces[a["space_id"]], floors[a["floor_id"]]
            writer.writerow({"asset_id": a["id"], **{k: a[k] for k in ("name", "type", "category", "source")},
                             "building_id": BUILDING_ID, "floor_level": f["level"], "floor_name": f["name"],
                             "space_id": s["id"], "space_name": s["name"], "room_ref": s["ref"], "room_type": s["room_type"],
                             "x_m": a["position"][0], "y_m": a["position"][1], **a["footprint"]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--photos", type=Path)
    parser.add_argument("--output", type=Path, default=HERE)
    args = parser.parse_args()
    # Prefer the checked-in, byte-identical sources; no user-specific path needed.
    sources = photo_manifest(args.photos or HERE / "sources")
    raw, metadata = build_model(sources)
    write_model(args.output, raw, metadata)
    print(f"Wrote {len(raw['floors'])} floors, {len(raw['spaces'])} spaces, {len(raw['assets'])} assets to {args.output}")


if __name__ == "__main__":
    main()
