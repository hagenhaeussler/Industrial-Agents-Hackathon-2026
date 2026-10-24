import json
from pathlib import Path

from core.schemas import TourResult


def test_real_fixture_satisfies_typed_contract():
    raw = json.loads(Path('fixtures/tour_proc-factory-dev-003.json').read_text())
    value = TourResult.model_validate(raw)
    assert value.legs
    assert value.order_policy == 'optimized_exact'
    assert all(leg.maneuvers for leg in value.legs)
    assert all(segment.geometry_length_m is not None for leg in value.legs
               for segment in leg.segments if segment.kind=='walk')
