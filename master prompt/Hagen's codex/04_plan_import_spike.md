# H04: Plan import spike (timebox: starts after G5 at 02:15 CEST, hard stop 03:00 CET; ≈ 1 h 45 min real time)

## 1. Outcome and user value

Hagen's journey ends with "a new building is built, I upload the floor plan, and the building appears". The rubric names "correct buildings built from plans". This spike either produces a **measured** draft-import path (plan file → draft building → scale → validate → overlay → save → tools work), or a clear "not good enough" result that keeps it out of the pitch. JSON upload (H03) remains the reliable path.

## 2. Starting state

- H03 validator and JSON upload exist; Manuel's codex has `POST /api/buildings` (and adds `POST /api/buildings/{id}/plan-import` only if this spike delivers).
- Kit plans: `floor_<level>.svg` / `.png` / `_plain.png` per building. Claims to verify first (plan review A.2, not re-checked): SVGs are Matplotlib exports with room polygons as `<path>` filled by room type, text as glyphs; PNGs have no scale or axes; doors are drawn as points, entrances as red triangles.
- Read: UX_REQUIREMENTS J8; CONTRACTS §6 (preview before save); decision D-22.

## 3. Scope and ownership

Own `core/plan_import/` (`svg.py`, `raster.py`, `calibrate.py`, `measure.py`) and its tests. Uses `svgelements` (Manuel's codex adds it in M01) and, for raster, the Anthropic SDK with `claude-sonnet-5-5` vision (no `temperature`; structured output or a strict tool for the JSON). The UI (upload, overlay, scale points) is Claude's and is only built if this spike passes.

## 4. Implementation obligations

1. **Check the SVG assumption (15 min):** parse `data/dev/proc-factory-dev-003/floor_0.svg`; find the room fill paths; compute the affine transform to building metres by matching path bounding boxes to `building.json` polygons for that floor (this is evaluation only: at import time a user provides scale with two points and one known length). Report what is recoverable: room polygons, room types by fill colour, doors, labels.
2. **SVG draft importer:** polygons from paths → spaces (`type` from fill colour mapping learned from the kit legend or colour table, `room_type` when unambiguous, else `generic_room`), doors only if present as marks; IDs `upl-<slug>-F<level>-S<nnn>`. Scale: from two picked points and their real distance, or from one known room width. Output a kit-format draft and run `validate_building`.
3. **Raster draft importer (only if time remains after 2):** send `floor_<level>_plain.png` to `claude-sonnet-5-5` with a strict JSON schema (rooms as pixel polygons with labels, door points, entrance points); convert with the user scale. Treat the model output as untrusted data: validate geometry and IDs; never execute anything from it.
4. **Measurement on three dev floors** (one procedural factory, one campus, one OSM): room count recall, mean IoU of matched room polygons after the scale step, door-graph agreement (fraction of true room adjacencies via doors recovered). Record numbers and failure modes in STATUS and in `core/plan_import/README.md`.

## 5. Interfaces

Function `import_plan(file_bytes, kind: "svg|png", floor_level: int, scale: {"p1": [px,py], "p2": [px,py], "length_m": float} | None) -> {"draft": <kit building dict>, "validation": <report>, "needs": ["scale", "doors", ...]}`. If it passes, send this signature to Manuel's codex for the endpoint and to Claude for the UI.

## 6. Execution order

SVG check (15 min) → SVG importer (40 min) → measurement (20 min) → raster only if ≥ 30 min remain → write results. Stop at 03:00 CET regardless.

## 7. Acceptance

A table in STATUS with the three floors and metrics, the command that produced it, and a recommendation: **show** (mean IoU ≥ 0.8 and doors usable after one correction step), **mention only** (rooms good, doors not), or **cut**. The pitch only claims what this table supports.

## 8. Collaboration and Git

Branch `hagen/core`; merge only if tests pass and nothing in the benchmark or journey paths changes. Merge window: Sunday 07:30 CET.

## 9. Completion report

SHA, metrics table, recommendation, what the UI would need, cost of vision calls.

## 10. Blocked-work behaviour

If SVGs turn out not to contain room geometry and raster extraction is poor, stop, record the evidence, and spend remaining time on core robustness (e.g. resolving more naming variants for the Sunday building) instead.
