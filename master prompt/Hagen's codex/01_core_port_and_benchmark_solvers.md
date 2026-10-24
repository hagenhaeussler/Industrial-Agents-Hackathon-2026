# H01: Core port and benchmark solvers (target G1, 23:00 CEST)

## 1. Outcome and user value

After this stage the repository has a `core/` package that loads any kit-format building, answers all nine benchmark kinds and the six warm-up kinds deterministically, resolves names to IDs, and publishes real-data fixtures. Lenard's codex can produce the test submission from it (55 points), and Manuel's Claude can render a real building instead of demo data.

## 2. Starting state

- Base: `BASE_SHA` (README). Kit 1.1.0: `starter_agent/building_map.py` reproduces the graded model; kit oracle 369/369 on dev (measured 20:25 CEST).
- **Delivered elsewhere, not yet in `core/`:** the sibling solver code, committed by the humans (H1) as reference copies in `research/sibling-repo-2026-10-24/core/spatial.py` (284 lines, solvers) and `questions.py` (121 lines, template parser, owned by Lenard for porting), `evaluate.py` (86 lines), `tests/test_spatial.py` (261 lines). It was written against kit **1.0.0**.
- Measured during planning (scratch copy, not committed): unported it scores errand 3/19 and what-if 0/2 on 1.1.0 answers and crashes with `KeyError: 'via'` on the 1.1.0 graph; with the patch below, dev 138/138 from text and gold inputs, train 517/517 gold inputs, train 510/517 text (7 ambiguous labels).
- Read: CONTRACTS §1–§5, §14, §15; kit README §3–§4.

## 3. Scope and ownership

Create and own: `core/__init__.py`, `core/building.py`, `core/spatial.py`, `core/resolve.py`, `core/errors.py`, `core/profiles.py`, `core/schemas.py` (Pydantic models for CONTRACTS §5 shapes; can start minimal), `core/evaluate.py`, `core/export_fixtures.py`, `tests/core/`, `fixtures/building_proc-factory-dev-003.json`, `fixtures/tour_proc-factory-dev-003.json`, `fixtures/tool_responses.json`.
Do not touch: kit files, `bench/` (Lenard ports the template parser into `bench/templates.py`; your `core.evaluate --check text` may import it once Lenard pushes, and until then imports the reference copy through a small adapter you delete afterwards), `pyproject.toml` (Manuel's codex adds `rapidfuzz`, `pydantic`, `pytest` in M01; if you need them before M01 lands, use them and note it in STATUS).

## 4. Implementation obligations

1. **`core/building.py`:** `load_building(path_or_dict) -> Building`. `Building` subclasses `starter_agent.building_map.BuildingMap` (import, do not copy) and adds `id`, `content_hash` (CONTRACTS §1), `version` (0), cached polygons. Repair invalid polygons with the kit's `outline()` (`buffer(0)`) and record a warning instead of raising (the sibling raised; none of the 22,725 kit polygons are invalid, but an unseen building could contain one and must not kill every answer). Per-process cache keyed by `(content_hash, version)` reusing the kit `load_cached` walks idea.
2. **`core/spatial.py`:** port `research/sibling-repo-2026-10-24/core/spatial.py` into `core/spatial.py` with these changes (all three are required for kit 1.1.0):
   - In `constrained_graph`: walking edges no longer carry `via`. Replace `if data["via"] in constraints.closed` with `if data.get("via") in constraints.closed`.
   - In `constrained_route`: build `element_path` with the rule in CONTRACTS §5 (connector ID for every stair/lift edge, opening ID for every door node), and `space_path` with `spaces_passed`. Do not use the old `["via"]` lookup or `groupby` deduplication.
   - In `compare_exit_distances_with_door` (what-if door): the free `outside` node is gone. Keep the sibling's wall-midpoint placement, then:
     ```python
     graph = self.constrained_graph()
     entrances = [DOOR_PREFIX + oid for oid, o in self.openings.items()
                  if OUTSIDE in o["space_ids"] and DOOR_PREFIX + oid in graph]
     if not entrances: raise MapError("Building has no entrance.")
     before = nx.multi_source_dijkstra_path_length(graph, entrances, weight="weight")
     hypo = type(self)(copy.deepcopy(self.data)); hypo.walks = dict(self.walks); hypo.closed = set(self.closed)
     hypo.add_door(first, second, position=point)          # kit 1.1.0 add_door: walked like any door, invalidates both walks
     after = nx.multi_source_dijkstra_path_length(hypo.constrained_graph(), entrances, weight="weight")
     ```
     The count rule stays: rooms on `floor_id` (types room and hall, as in the sibling's `floor_rooms`) reachable after, and either unreachable before or improved by **more than 1 m**.
   - Keep the class name `SpatialCore` (the reference `questions.py` imports `from core.spatial import SpatialCore`), so Lenard's port and the temporary adapter work unchanged. The reference folder is named `core` too: load reference files by path with `importlib.util.spec_from_file_location`, never by putting `research/...` on `sys.path`.
   - Expose `solve(b, kind, inputs)` as a module function (CONTRACTS §4 table), keep the sibling's input validation, add the warm-up kinds (`locate`, `count`, `route*`, `tour`). `tour` with `keep_order: true` is the kit tour: legs in the given order, unreachable leg → `reachable: false`.
   - Keep `format_answer` only as a reference; the official serializer is Lenard's `bench/serialize.py` (CONTRACTS §13).
3. **`core/resolve.py`:** CONTRACTS §4 order. Full rendered label `"<name> (<floor name>)"` first (this is how benchmark questions name rooms), then ref, name, normalized forms (casefold, strip leading zeros in numeric tokens, EN/DE synonyms such as WC/toilet, lift/elevator/Aufzug, stairs/Treppe), then RapidFuzz `token_set_ratio` ≥ 85 for the rest. Numbers in the query must appear exactly in the candidate. Return `ambiguous` with ≤ 8 candidates when the best scores tie. Assets resolve by name, then by `type` (`"3d printer"` → type `3d_printer`); a type with several instances is `ambiguous` for routing but valid for `count`.
4. **`core/profiles.py`:** `KIT_1_1_0` constants re-exported from the kit module; `current_profile()` reads `TYB_PROFILE` (default `kit_1_1_0`); unknown value → error at startup.
5. **`core/evaluate.py`:** port the sibling evaluator: `--check structured` (gold `inputs`, tool-level) and `--check text` (question text → template parser → solve → official `benchmark.score.score_reply`), per-kind table, report JSONL under `agent_output/reports/core/` (git-ignored). Answers are read only after the prediction is complete (keep the sibling's separation).
6. **`core/export_fixtures.py`:** writes the three fixture files from real data (`proc-factory-dev-003`: snapshot per CONTRACTS §7 shape including `derived.anchors` and `derived.areas_m2`; a 3-stop tour with real legs; tool responses for `find` unique/ambiguous/not found and `plan_tour`). Until H02 lands, tour `segments` are anchor → door → anchor straight lines and the fixture says `"_fixture": {..., "geometry": "provisional"}`.
7. Edge cases to test (in `tests/core/`, fast, a handful of buildings): parallel connectors (stair + lift between the same spaces), two doors between the same rooms, closure of a connector/opening/space, unreachable destination returns `reachable: false` (never an exception to the caller), step-free route through a lift, what-if symmetry (A,B) = (B,A), errand with stairs allowed, an asset as a route endpoint. Port the relevant sibling tests; delete the ones that encode kit 1.0 behaviour (outside node, 12 m per floor) and say so in the commit message.

## 5. Interfaces and fixtures

- Produce: CONTRACTS §4 functions `load_building`, `solve`, `resolve`; §15 fixtures. Consumers: Lenard's codex (`bench`), Manuel's codex (server snapshot), Manuel's Claude (fixtures).
- The fixture files carry the `_fixture` header; Claude replaces them with live endpoints in C02.

## 6. Execution order

1. (10 min) Skeleton `core/` + `load_building` + content hash + `tests/core/test_building.py`; push. Tell Lenard the import path.
2. (25 min) Port `spatial.py` with the three changes; `solve` dispatch; run `core.evaluate data/dev --check structured` until 138/138; push.
3. (15 min) Warm-up kinds in `solve`; check them against `questions_basic.jsonl` answers in a test (routes: length within 1 cm of `optimal_length_m`, `space_path` and `element_path` equal; unreachable cases `reachable: false`). Push.
4. (15 min) `resolve.py` + tests ("Press 4" vs "Press 14" synthetic case; duplicate OSM labels return `ambiguous`).
5. (10 min) `export_fixtures.py`, push fixtures, notify Manuel's Claude and Manuel's codex.
6. (5 min) `core.evaluate --check text` once Lenard's `bench/templates.py` (or the reference adapter) is available; record numbers; run train structured.
Timebox: if step 2 is not at 138/138 by 22:45 CEST, push what you have, write the failing IDs and diagnosis in STATUS, and ask Lenard's codex for a second pair of eyes; do not start H02 polishing before G1 is green.

## 7. Acceptance

- `uv run python -m core.evaluate data/dev --check structured` → 138/138; `data/train` → 517/517.
- `uv run python -m core.evaluate data/dev --check text` → 138/138 (with the template parser).
- `PYTHONDONTWRITEBYTECODE=1 uv run python -m starter_agent.evaluate data/dev --oracle` → 369/369 (unchanged kit).
- Warm-up test: all dev warm-up route answers reproduced (length ±0.01 m, `space_path`, `element_path` exact; measured 161/161 for reachable non-tour routes during planning).
- `uv run pytest -q tests/core` green, < 30 s.
- Evidence: paste the per-kind tables into STATUS; report files under `agent_output/reports/core/`.
- Review: ask Lenard's codex to run `core.evaluate --check text` on its own checkout.

## 8. Collaboration and Git

Branch `hagen/core`. Push after steps 1, 2, 3, 5. Ask the captain (Manuel's codex) to merge at G1. If you change a CONTRACTS §4 signature, follow the change-request protocol and tell Lenard and Manuel's codex through your human before they build against it.

## 9. Completion report (write in STATUS.md, then tell your human)

SHA; delivered functions; per-kind tables (dev text, dev/train structured, oracle); fixture paths; known limits (ambiguous labels, invalid-polygon handling); next dependency (H02 for Claude's map geometry).

## 10. Blocked-work behaviour

- **H1 reference copies missing:** do not wait. Reimplement the solvers from the kit README §4 definitions and CONTRACTS §4 (largest/total area over room and hall spaces of a `room_type` on a floor; shared walls: first boundary ∩ second boundary buffered 0.35 m, length ≥ 1 m, other rooms on the same floor excluding corridor/stair/lift types; stacked: max intersection area with spaces on the nearest floor above/below; 3D distance: polygon centroids at floor elevations; reachability counts only `type == "room"`; errand: nearest room containing the asset type by route length from start, then to the largest room of the type on the floor; what-if as above). Acceptance is identical.
- **`pyproject` deps missing:** do not edit `pyproject.toml`; run locally with `uv run --with rapidfuzz --with pydantic --with pytest ...` and note the requirement in STATUS for Manuel's codex.
- **A kind will not reach 100 %:** push the rest, list failing IDs with diagnosis, and continue; never tune to IDs.
