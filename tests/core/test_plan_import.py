from pathlib import Path

import pytest

from core.errors import CoreError
from core.plan_import import import_plan
from core.plan_import.measure import DEFAULT_FLOORS, measure_floor


SIMPLE = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
<g transform="translate(5 10)"><path d="M 0 0 L 10 0 L 10 10 L 0 10 z" style="fill:#f3efe6;stroke:#333333"/>
<path d="M 0 5" style="fill:none;stroke:#d32f2f"/></g></svg>'''


def test_no_scale_never_claims_metres_or_commit_readiness():
    result = import_plan(SIMPLE, "svg", 0)
    assert result["draft"]["building"]["units"] == "svg_user_units"
    assert "scale" in result["needs"]
    assert not result["validation"]["ok"]
    assert not result["ready_to_commit"]


def test_user_scale_flips_y_and_preserves_draft_corrections():
    result = import_plan(SIMPLE, "svg", 0, {"p1": [5,20], "p2": [15,20], "length_m": 20})
    room = result["draft"]["spaces"][0]
    assert room["polygon"] == [[0,20],[20,20],[20,0],[0,0]]
    assert result["validation"]["ok"]
    assert result["draft"]["openings"][0]["position"] == [0,10]
    assert not result["ready_to_commit"]
    assert "labels" in result["needs"]
    assert "door_widths" in result["needs"]
    assert "step_free_checks" in result["needs"]


@pytest.mark.parametrize("scale", [{"p1":[0,0],"p2":[0,0],"length_m":1},
                                  {"p1":[0,0],"p2":[1,0],"length_m":-1},
                                  {"p1":[0,0],"p2":[1,float('nan')],"length_m":1}])
def test_invalid_calibration_rejected(scale):
    with pytest.raises(CoreError):
        import_plan(SIMPLE, "svg", 0, scale)


def test_wall_contact_is_not_invented_as_a_door():
    source = b'''<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0L1 0L1 1L0 1z" style="fill:#f3efe6;stroke:#333333"/>
    <path d="M1 0L2 0L2 1L1 1z" style="fill:#f3efe6;stroke:#333333"/></svg>'''
    result = import_plan(source, "svg", 0, {"p1":[0,0],"p2":[1,0],"length_m":1})
    assert len(result["draft"]["spaces"]) == 2
    assert result["draft"]["openings"] == []
    assert "doors" in result["needs"]
    assert not result["validation"]["ok"]


def test_png_is_honestly_unavailable_without_paid_vision():
    result = import_plan(b"\x89PNG\r\n\x1a\n", "png", 0)
    assert result["draft"] is None
    assert not result["ready_to_commit"]
    assert "raster_extraction" in result["needs"]
    assert result["diagnostics"]["vision_calls"] == 0


def test_entity_payload_cannot_be_interpreted():
    with pytest.raises(CoreError):
        import_plan(b'<!DOCTYPE svg [<!ENTITY test "expanded">]><svg>&test;</svg>', "svg", 0)


@pytest.mark.parametrize("building_id,level", DEFAULT_FLOORS)
def test_svg_spike_metrics_on_three_distinct_dev_sources(building_id, level):
    result = measure_floor(Path("data/dev")/building_id, level)
    assert result["room_recall"] >= .8
    assert result["mean_matched_iou"] >= .8
    assert result["door_graph_recall"] >= .8
    assert result["validation_ok"]
