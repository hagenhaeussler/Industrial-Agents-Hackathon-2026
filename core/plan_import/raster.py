"""Raster extraction is deliberately unavailable without a funded vision spike."""

from core.errors import CoreError


def extract_raster(file_bytes):
    if not isinstance(file_bytes, bytes) or not file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        raise CoreError("invalid_args", "Expected PNG bytes.")
    return {"draft": None, "validation": {"ok": False, "errors": [{"code": "not_available", "path": "$", "message": "Raster geometry extraction has not been implemented or measured."}], "warnings": [], "stats": {}},
            "needs": ["raster_extraction", "scale", "rooms", "doors", "labels"],
            "ready_to_commit": False,
            "diagnostics": {"vision_calls": 0, "vision_cost": 0}}
