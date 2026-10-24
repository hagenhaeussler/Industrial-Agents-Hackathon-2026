"""Explicit evaluation profile; never selected by a language model."""

import os
from starter_agent.building_map import (
    STAIRS_M_PER_RISE, LIFT_FIXED_M, LIFT_M_PER_RISE, WALL_CLEARANCE_M,
    DOOR_LANDING_M, COVER_TOLERANCE_M, LENGTH_DECIMALS,
)
from .errors import CoreError

KIT_1_1_0 = "kit_1_1_0"


def current_profile():
    value = os.environ.get("TYB_PROFILE", KIT_1_1_0)
    if value != KIT_1_1_0:
        raise CoreError("invalid_args", f"Unknown TYB_PROFILE: {value}")
    return value
