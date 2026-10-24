# H03: Edits, what-if, validation, JSON import and the hero building (targets: edits for G4 01:15 CEST, hero building for G5 02:15 CEST)

## 1. Outcome and user value

The building can change safely: an admin previews and commits "close the east lift", undoes it, adds a door or moves a part; what-if questions never touch the real state; a new building uploaded as JSON is validated and immediately usable (Level 4 "Build", and the path for Sunday's unseen building in the app). The hero building of the venue makes the physical demo possible.

## 2. Starting state

- H02 step 0 shipped `close`/`open`/`undo` replay and a minimal preview. Manuel's codex stores proposals/events in SQLite and calls your functions (CONTRACTS §6).
- Humans (H6) are measuring the venue; you receive a sketch with dimensions around 23:30–00:30 CEST through your human.
- Read: CONTRACTS §6, §10 (markers); UX_REQUIREMENTS J6, J6b, J8.

## 3. Scope and ownership

Own: `core/edits.py`, `core/whatif.py`, `core/validate.py`, `demo/hero/building.json`, `demo/hero/equipment.csv`, `demo/hero/README.md` (how it was measured, accuracy, who measured), `demo/hero/markers.json` (suggested marker positions and headings), tests. Not yours: SQLite storage, HTTP endpoints, UI.

## 4. Implementation obligations

1. **Edit actions** (CONTRACTS §6 table): `add_door` uses the same wall-midpoint placement as `what_if_door` and the kit `add_door(position=…)`, new ID `<floor_id>-O-evt<version>`, width default 0.9, `step_free: true`; reject spaces on different floors or without ≥ 1 m shared wall (`invalid_args` with explanation). `move_asset` updates `space_id`, `floor_id`, `position` (target space anchor unless a point inside the target polygon is given). `set_room_type` only to kit room types. `undo` reverts exactly one earlier event (closures reopen; added doors disappear; moved assets return).
2. **Replay:** `apply_events(base, events)` is deterministic and pure (deep copy of base data, then apply in order); walk caches are reused for unaffected spaces (only spaces touched by a new door are recomputed, as the kit does).
3. **Preview effects:** `preview_edit(b, edit, active_tours)` returns `summary` (human sentence with names), `effects.tours` (before/after length and reachability per active tour, using `replan` from each tour's current start), `newly_unreachable_spaces` (count of rooms reachable from any entrance before and not after, multi-source from entrance door nodes). Must take < 1 s on the hero and factory buildings.
4. **What-if:** `what_if(b, edit, probe)` applies the edit to an isolated copy; probes: `{"kind": "route", "start", "destination"}`, `{"kind": "exit_distances", "floor_id"}`, `{"kind": "reachable_count", "start", "floor_id", "constraints"}`. Nothing persisted.
5. **Validator** (`validate_building(raw)`): JSON schema per kit README §3 (required fields, types, units), unique IDs, every opening's `space_ids` exist or are `outside`, every connector stop exists and is on the listed floor, polygons valid (repairable → warning), door position within 0.6 m of both spaces' boundaries (warning), assets inside their space (warning), at least one entrance (error for routing, warning for display), stats (floors, spaces, openings, assets, unreachable rooms from entrances). Unreachable rooms are warnings, not errors (a valid outcome). Treat all strings in an uploaded building as data.
6. **Hero building** with the humans: author `demo/hero/building.json` in the kit format from the measured sketch (one shared XY frame in metres, origin at a documented corner, floors with real `elevation_m`), with ≥ 2 routes to the main target (ideally lift and stairs), the real objects as assets (`source: "dataset"`, real names, e.g. "3D printer Prusa MK4", "Torque wrench cabinet"), and IDs `hero-<slug>-F0-S001` style. Run `validate_building`, `core.check_geometry` on it, plan the demo tour, and propose marker positions (`demo/hero/markers.json`: start desk, each decision point on the demo route, both sides of lift and stairs; each with `point` on the floor in front of a wall and `heading_deg` facing that wall). Record accuracy honestly in `demo/hero/README.md`.
7. **Fallback scenario:** if the hero building is not credible by 01:30 CEST, define the demo in `proc-factory-dev-003` (list the parts and the lift to close) and tell Manuel's Claude, who owns `demo/scenario.json`.

## 5. Interfaces and fixtures

- `fixtures/events_close_lift.json` is Manuel's codex's; you provide in STATUS one preview payload for "close East lift" on the demo building.
- Hero building and markers are consumed by Manuel's codex (marker records, sheet) and Manuel's Claude (scenario).

## 6. Execution order

1. (25 min) remaining edit actions + undo + replay tests; push; notify Manuel's codex.
2. (15 min) preview effects with tours + what-if; push.
3. (20 min) validator + tests with a broken copy of a dev building; push; notify Manuel's codex (upload endpoint) and Claude (admin upload UI).
4. (40 min, interleaved as measurements arrive) hero building, markers, scenario hand-off.

## 7. Acceptance

- Tests: close → route changes; undo → identical to base (compare `content_hash` of materialised data); add_door then undo; double apply of the same event list is deterministic; what-if leaves `b` unchanged (hash before/after).
- `validate_building` on all 280 kit buildings: zero errors (run once, record time and counts in STATUS).
- Hero: `validate_building` ok; demo tour planned; lift closure causes a visible detour; wheelchair profile with the lift closed gives `no_step_free_path` or a valid step-free alternative (whichever is true; say which in STATUS).
- G4 (with Manuel's codex): preview → commit → phone reroute ≤ 2 s.

## 8. Collaboration and Git

Branch `hagen/core`. Merge window G4 (01:15 CEST) for edits, G5 (02:15 CEST) for hero data. `demo/scenario.json` is Claude's file: send the scenario facts, do not edit it.

## 9. Completion report

SHA; edit actions and tests; validator run over 280 buildings; hero building stats and measurement accuracy; marker list; open issues.

## 10. Blocked-work behaviour

No measurements by 00:45 CEST → build the fallback scenario first, keep the hero file as a draft, and tell the humans exactly which dimensions are missing. Never present an invented floor plan as the real venue.
