"""Structured regression oracle for all 369 published dev warm-up cases.

Only this test converts reference-answer fields to inputs. Application inference
uses text/entity tools and never reads questions_basic.jsonl.
"""

import json
from pathlib import Path

import pytest

from core.building import load_building
from core.spatial import solve

ROOT = Path(__file__).resolve().parents[2]


def _check_route(actual, expected):
    assert actual["reachable"] is not False
    assert actual["length_m"] == pytest.approx(expected["optimal_length_m"], abs=.010000001)
    assert actual["space_path"] == expected["space_path"]
    assert actual["element_path"] == expected["element_path"]


def test_all_dev_warmup_structured_regressions():
    count = 0
    for path in sorted((ROOT / "data/dev").glob("*/questions_basic.jsonl")):
        building = load_building(path.parent)
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            question = json.loads(line)
            expected, kind = question["answer"], question["kind"]
            if kind == "locate":
                result = solve(building, kind, {"asset": expected["asset_id"]})
                assert {key: result[key] for key in ("asset_id", "space_id", "floor_level", "position")} == {
                    key: expected[key] for key in ("asset_id", "space_id", "floor_level", "position")}
            elif kind == "count":
                floor_id = next(fid for fid, floor in building.floors.items() if floor["level"] == expected["floor_level"])
                assert solve(building, kind, {"asset_type": expected["asset_type"], "floor_id": floor_id})["value"] == expected["count"]
            elif kind == "tour":
                result = solve(building, kind, {"stops": expected["stops"], "keep_order": True})
                if expected.get("reachable") is False:
                    assert result["reachable"] is False
                else:
                    assert result["length_m"] == pytest.approx(expected["optimal_length_m"], abs=.010000001)
                    assert len(result["legs"]) == len(expected["legs"])
                    for actual_leg, expected_leg in zip(result["legs"], expected["legs"], strict=True):
                        _check_route(actual_leg, expected_leg)
            else:
                inputs = {"start": expected["from_space_id"], "destination": expected["to_space_id"]}
                if "closed_element_id" in expected:
                    inputs["closed"] = [expected["closed_element_id"]]
                result = solve(building, kind, inputs)["route"]
                if expected.get("reachable") is False:
                    assert result["reachable"] is False
                else:
                    _check_route(result, expected)
            assert building.last_route is None
            assert building.closed == set()
            assert building.version == 0
            count += 1
    assert count == 369
