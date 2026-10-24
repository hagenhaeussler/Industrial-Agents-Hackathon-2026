# Deterministic building core

The core extends the immutable kit 1.1.0 implementation without editing the kit.
It reads building data only; labels and question files are used solely by the
evaluation commands and tests. `TYB_PROFILE` defaults to `kit_1_1_0` and rejects
unknown profiles.

```python
from core.building import load_building
from core.resolve import resolve
from core.routing import route
from core.tour import plan_tour, replan
from core.spatial import solve
from core.edits import resolve_edit, preview_edit, apply_events
from core.validate import validate_building

b = load_building(building_directory_or_dict)
answer = solve(b, 'largest_room', {'floor_id': floor_id, 'room_type': 'office'})
found = resolve(b, 'printer', 'asset')  # unique / ambiguous / none
walk = route(b, start_space_id, target_asset_id, {'step_free': True})
tour = plan_tour(b, start_space_id, [{'target': asset_id}], keep_order=False)
preview = preview_edit(b, {'action': 'close', 'target': lift_id}, [tour])
```

Core functions do not persist changes or authorize users. The server owns
proposal expiry, admin permissions, atomic/idempotent commit, session/tour IDs,
SQLite and realtime transport. `apply_events` deterministically materializes an
event log; `what_if` and previews work on isolated copies. See canonical C3
contracts in `master prompt/CONTRACTS.md`.

Routes retain selected door and connector identities, raw walk polylines,
rounded kit graph costs, English maneuvers and explicit unreachable reasons.
Physical point endpoints are supported. A flagged fallback drawing is not
claimed to be walkable. Tours use exact Held-Karp up to 12 pending stops and a
labelled nearest-neighbor/2-opt heuristic beyond that. Replans preserve collected
stops, relocate pending parts from the current inventory and apply current
closures without retaining a reopened lift as a stale request constraint.

## Checks

```sh
uv run pytest -q tests/core
uv run python -m core.evaluate data/dev --check text
uv run python -m core.evaluate data/dev data/train --check structured
uv run python -m core.check_geometry data/dev
uv run python -m core.export_fixtures
uv run python -m core.plan_import.measure --output core/plan_import/measurement.json
```

`core.evaluate` uses `bench.templates` when published. Its explicitly marked
temporary fallback loads the checked-in sibling parser by file path, without
changing `sys.path`. The fallback is evaluation tooling and is not included in
the deployment Docker context. Lenard owns its replacement and answer serializer.
Reports go to ignored `agent_output/reports/core/`.

Measured locally: dev text 138/138; dev structured 138/138; train structured
517/517. Train text is 510/517 because seven source labels are ambiguous; no
arbitrary entity is selected. All 369 dev warm-ups reproduce their expected
paths/lengths; geometry checks cover 269 legs and 1,232 walks with no failures
or kit fallbacks. These are local checks, not live voice/device results.

Cold geometry construction is the expensive operation: the largest building's
first graph took about 2.1 seconds, and another complex OSM example took about
11 seconds due to geometric visibility tests. Reused warm factory routes took
about 1.8 ms; a five-stop factory tour took 16.1 ms. Warm the selected demo
building before timed interaction; do not promise cold arbitrary-building
latency from those factory timings.

The SVG spike recovers measured kit-export geometry but deliberately returns an
incomplete draft requiring calibration and corrections. See
`plan_import/README.md`. PNG/vision import is not implemented and made no paid
calls. A measured real venue building awaits human dimensions;
`demo/hero/README.md` documents the factory fallback.
