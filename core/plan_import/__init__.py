"""Plan bytes → an explicitly incomplete, validated draft; never a saved edit."""

import hashlib

from core.errors import CoreError
from core.validate import validate_building
from .calibrate import calibration, to_metres
from .svg import associate_markers, extract_svg


def import_plan(file_bytes, kind, floor_level, scale=None):
    """Import a vector plan using only its bytes and a user's known distance.

    ``scale`` points are SVG viewBox/user coordinates, not CSS screen pixels.
    The caller must preview the draft, collect ``needs`` corrections, revalidate,
    and obtain confirmation before persisting it. No source plan is executed.
    """
    if not isinstance(floor_level, int) or isinstance(floor_level, bool):
        raise CoreError("invalid_args", "floor_level must be an integer.")
    if kind == "png":
        from .raster import extract_raster
        return extract_raster(file_bytes)
    if kind != "svg":
        raise CoreError("invalid_args", "Plan kind must be svg or png.")
    extracted = extract_svg(file_bytes)
    calibrated = calibration(scale) if scale is not None else None
    convert = (lambda point: to_metres(point, calibrated)) if calibrated else (lambda point: list(point))
    rooms = [{**room, "polygon": [convert(point) for point in room["polygon"]]} for room in extracted["rooms"]]
    markers = [{**marker, "position": convert(marker["position"])} for marker in extracted["markers"]]
    tolerance = .02 if calibrated else .1
    connected, unresolved = associate_markers(rooms, markers, tolerance)
    slug = hashlib.sha256(file_bytes).hexdigest()[:6]
    building_id = f"upl-plan-{slug}"
    floor_id = f"{building_id}-F{floor_level}"
    ids = [f"{floor_id}-S{i+1:03}" for i in range(len(rooms))]
    spaces = [{"id": sid, "floor_id": floor_id, "name": f"Unlabelled room {i+1}", "ref": None,
               "type": "room", "room_type": "generic_room", "polygon": room["polygon"],
               "source": "svg_draft", "import_fill": room["fill"]}
              for i, (sid, room) in enumerate(zip(ids, rooms))]
    openings = []
    for index, marker in enumerate(connected):
        opening_ids = [ids[i] for i in marker["room_indices"]]
        if marker["kind"] == "entrance":
            opening_ids.append("outside")
        openings.append({"id": f"{floor_id}-O{index+1:04}", "floor_id": floor_id,
                         "space_ids": opening_ids, "kind": marker["kind"], "position": marker["position"],
                         "width_m": .9, "step_free": False, "synthetic": False,
                         "import_requires_confirmation": ["width_m", "step_free"]})
    draft = {"building": {"id": building_id, "name": "Imported plan draft", "source": "svg_draft",
                          "units": "m" if calibrated else "svg_user_units", "draft": True},
             "floors": [{"id": floor_id, "level": floor_level, "name": f"Floor {floor_level}",
                         "elevation_m": 0, "height_m": 3, "import_requires_confirmation": ["height_m", "elevation_m"]}],
             "spaces": spaces, "openings": openings, "assets": [], "vertical_connectors": []}
    needs = ([] if calibrated else ["scale"]) + ["labels", "room_types", "door_widths", "step_free_checks", "floor_height"]
    if unresolved or not openings or not any(o["kind"] == "entrance" for o in openings):
        needs.append("doors")
    if floor_level != 0:
        needs.append("floor_elevation")
    if extracted["skipped_polygons"]:
        needs.append("rooms")
    return {"draft": draft, "validation": validate_building(draft), "needs": needs, "ready_to_commit": False,
            "source_frame": {"units": "svg_user_units", "y_down": True, "viewbox": extracted["viewbox"], "calibration": calibrated},
            "diagnostics": {"rooms_recovered": len(rooms), "markers_recovered": len(markers),
                            "openings_associated": len(openings), "unresolved_markers": unresolved,
                            "skipped_polygons": extracted["skipped_polygons"], "vision_calls": 0,
                            "labels_recovered": 0, "room_types_recovered": 0,
                            "notes": ["Room colours are preserved as hints; semantic room types are unconfirmed.",
                                      "Glyph text is not decoded.", "Widths, accessibility and floor height are draft defaults awaiting confirmation."]}}
