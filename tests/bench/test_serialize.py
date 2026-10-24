from types import SimpleNamespace

import pytest

from bench.serialize import serialize
from benchmark.score import score_reply


@pytest.fixture
def building():
    return SimpleNamespace(
        spaces={"sample-F1-S014": {"name": "Office 1.14", "ref": "1.14", "floor_id": "first"}},
        floors={"first": {"name": "Floor 1", "level": 1}},
        assets={"lectern": {"name": "Lectern"}},
    )


@pytest.mark.parametrize("kind", ["floor_area_total", "errand", "straight_line_3d"])
def test_numeric_answers_pass_the_official_scorer(building, kind):
    expected = {"type": "number", "value": 42.125, "relative_tolerance": 0, "absolute_tolerance": 0}
    assert score_reply(expected, serialize(building, kind, {"value": 42.125}))


@pytest.mark.parametrize("kind", ["shared_walls_count", "wide_delivery_count", "step_free_reachable_count", "what_if_door", "count"])
def test_counts_contain_one_integer(building, kind):
    assert serialize(building, kind, {"value": 3.0}) == "Answer: 3"


def test_room_reference_digits_do_not_replace_the_computed_area(building):
    expected = {"type": "space", "accept": ["1.14"], "reject": ["Office 1.15"],
                "area": {"value": 20.25, "relative_tolerance": 0, "absolute_tolerance": 0}}
    assert score_reply(expected, serialize(building, "largest_room", {"space_id": "sample-F1-S014", "area_m2": 20.25}))


def test_room_without_ref_uses_the_kit_fallback(building):
    del building.spaces["sample-F1-S014"]["ref"]
    assert serialize(building, "room_stacked", {"space_id": "sample-F1-S014"}) == "Answer: 1.14, Office 1.14"


@pytest.mark.parametrize("value", [True, float("inf"), float("nan"), "42"])
def test_invalid_numeric_results_are_not_committed(building, value):
    with pytest.raises(ValueError):
        serialize(building, "errand", {"value": value})


@pytest.mark.parametrize("value", [-1, 2.5])
def test_invalid_counts_are_not_committed(building, value):
    with pytest.raises(ValueError):
        serialize(building, "count", {"value": value})


def test_locate_names_the_asset_room_and_floor(building):
    assert serialize(building, "locate", {"asset_id": "lectern", "space_id": "sample-F1-S014"}) == "Answer: Lectern in Office 1.14 (Floor 1)"


@pytest.mark.parametrize("kind", ["route", "route_step_free", "route_with_closure"])
def test_unreachable_routes_are_explicit(building, kind):
    assert serialize(building, kind, {"route": {"reachable": False}}) == "Answer: no route"


def test_unreachable_tour_does_not_claim_a_length(building):
    assert serialize(building, "tour", {"reachable": False}) == "Answer: no route"
