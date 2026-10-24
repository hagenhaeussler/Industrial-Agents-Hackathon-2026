# STATUS: Hagen's codex (Core & Spatial Intelligence Lead)
Last update: 2026-10-24T21:42+02:00 · Branch: `hagen/core` · HEAD: this checkpoint · Last sync: `d46775f`; consumed platform `d187ce5`, bench `4d93bdb`, web `de81877`

Single writer: Hagen's codex.

## Current task
H01/H02 core delivered; H03 edits/validator delivered, measured venue data pending; H04 SVG spike measured (mention only). Integrated checks passed; final Railway test smoke and captain handoff.

## Delivered (newest first)
- All 15 deterministic solvers; current kit 1.1.0 walk/connector semantics, no kit edits.
- Actual walk polylines, selected door/connector IDs, actual point endpoints, English maneuvers, constraints/unreachable reasons.
- Exact collection tours up to 12 pending stops, explicit heuristic above 12, optional end, collected-stop and moved-part replanning.
- Pure preview/event replay/targeted undo/what-if; JSON validation and typed core payloads.
- Real snapshot/tour/tool fixtures under `fixtures/`; SVG L-room route examples.
- SVG draft importer and measurement report in `core/plan_import/`; no paid vision calls. JSON input remains reliable path.
- Consumed all three teammates' published checkpoints on this test branch without conflicts; main merges remain the captain's responsibility.

## Interfaces exposed / changed
- `core.building.load_building`, `core.spatial.solve`, `core.resolve.resolve`.
- `core.routing.route`, `core.tour.plan_tour` / `replan`.
- `core.edits.resolve_edit` / `preview_edit` / `apply_events`, `core.whatif.what_if`, `core.validate.validate_building`.
- `core.plan_import.import_plan(file_bytes,kind,floor_level,scale=None)` returns draft, validation, correction needs; never auto-commits.
- Pending-asset replanning also refreshes additive server `target` metadata; direct core regression passes.
- C3 adds geometry_length_m/start_position/destination_position/building_closed; preserves C2 HTTP/session transport. Core tour_id is null until server assigns one.

## Evidence
- `scripts/check.sh` on full core with M01: 113 Python tests passed in 21.69 s; kit oracle 369/369; dev text 138/138. Bun skip explicitly reported at that point.
- Latest combined Python check after consuming M02, Lenard parser and Claude app: **214 passed in 26.08 s**.
- Full integrated `scripts/check.sh` passed after consuming all three builder branches: 214 Python tests, oracle 369/369, dev text 138/138, 39 Bun tests and production frontend/device-gate build.
- `core.evaluate data/dev --check text`: **138/138**; dev structured **138/138**; train structured **517/517**. Train text **510/517**, seven genuinely ambiguous labels, no guessing. Reports: ignored `agent_output/reports/core/`.
- All **369** dev warm-up regressions pass, exact space/element paths, lengths within inclusive 1 cm. Cache correction reduced full warm-up regression 71.54 s -> 21.56 s.
- `core.check_geometry data/dev`: **40 buildings, 269 legs, 1,232 walks, zero fallbacks/failures** (22.47 s). Two synthetic L-room examples: `fixtures/route_geometry_l_examples.svg`.
- Validator over **280 buildings: zero errors**, 242 door-boundary warnings, 0.871 s; malformed-input checks covered 360 field mutations without uncaught exceptions.
- Warm factory route mean **1.795 ms**; 5-stop exact tour **16.064 ms**. Largest building first graph **2.096 s**; another complex OSM cold route ~11 s (Shapely visibility dominates), warm repeat ~0.002 s. Warm chosen demo buildings before timing; no universal cold latency claim.
- Factory wheelchair lift-close preview **16.6 ms**, 107.65 m -> unreachable, one active tour affected; normal walking still uses stairs.
- H04 three floor results: factory 47/47, campus 28/28, OSM 21/21 polygons; matched IoU 1.0; internal adjacency 50/50, 27/27, 25/25. Evaluation uses oracle bounds solely to simulate perfect user calibration. Recommendation **mention only**; labels/types/width/accessibility/height and arbitrary plans remain unproven.
- Railway plugin created isolated project `146f7fb5-46aa-42fb-a164-9f14159e2e23`, testing env `0eac3d7a-01e4-4c78-b401-9c55840f33f2`, service `6cead871-bd0b-4447-a182-92d8a03b40ec`, 500 MB `/state` volume. Public URL (human-approved): https://hagen-core-test-testing.up.railway.app . First pinned checkpoint `49a7e6b` deployed successfully; health + real 79-space factory snapshot verified. Current full checkpoint deployment follows after push.

## Blockers and resource requests
- Venue measurements H6 not supplied. No invented venue building; `demo/hero/README.md` records needed dimensions/objects/marker headings. Validated factory fallback is ready for Claude's scenario.
- No paid vision/model calls, live voice, physical phone tracking or complete UI journey acceptance claimed. Railway trial issue resolved by human enabling Hobby.

## Change requests
- **CR-H-1 accepted C3 (§5):** distinguish raw physical geometry from graph costs rounded to 0.001 m; documented additive result fields, current closures and pending moved-part semantics. C2 platform changes preserved.
- **CR-H-2 to Manuel's codex (§6/server seam):** `server.service._plan` restores old stops by old space after planning and `replan_tour` bypasses `core.tour.replan`. A pending asset moved to another room needs its server stop target/space updated before core planning (and ID-based reconciliation afterwards), or use core.replan. Reproduced against the real local API: move preview/commit succeeds, then POST tour replan returns HTTP 400 invalid_args because the pending stop still refers to the old room. Otherwise a stale canonical stop with asset_ids in its old room raises invalid_args. Core.replan itself retargets correctly and its regression passes. Please add server-level move-during-tour test; no platform files edited by Hagen.

## Next handoff
- PR handoff: https://github.com/hagenhaeussler/Industrial-Agents-Hackathon-2026/pull/1 .
- Captain: merge published Hagen branch, run integrated checks, expose new real core APIs through existing adapter. This branch consumes teammates' checkpoints for seam checks; do not duplicate their modules.
- Lenard: consume solve/resolve + real parser integration; run your own dev evaluation and test CSV. Temporary reference parser adapter automatically yields to `bench.templates` now present.
- Claude: real C3 snapshot/tour/tool fixtures ready; geometry is reconstructed, not provisional. Use factory fallback until venue data arrives.
- Manuel's codex: separate Railway test project/URL available; final production project ownership stays with captain. Resolve CR-H-2; missing venue dimensions remain human input.
