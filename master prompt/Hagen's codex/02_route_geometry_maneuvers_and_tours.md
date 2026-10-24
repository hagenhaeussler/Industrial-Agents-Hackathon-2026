# H02: Route geometry, maneuvers and optimal tours (target 00:45 CEST, before G4; provisional geometry is acceptable at G3)

## 1. Outcome and user value

Routes come back as real walk polylines (15 cm off the walls, round corners, through the chosen doors), with turn-by-turn maneuvers that name landmarks, and multi-stop tours in a provably optimal order. This is what makes Aha 1 (route drawn on the desk), Aha 2 (phone directions, camera line) and Aha 3 (replan from the current position, collected stops kept) real instead of illustrated.

## 2. Starting state

- H01 merged or pushed: `core.spatial`, `core.resolve`, fixtures with provisional geometry.
- Kit facts: `walking_lengths()` computes lengths with a visibility graph over the landing points and the corners of `polygon.buffer(-0.15)` with `allowed = walkable.buffer(0.02)`, then Floyd–Warshall; it does **not** keep the path. `space_walks()` adds the door-to-landing distance at both ends; `graph()` rounds each edge to 3 decimals; unreachable pairs inside a space fall back to straight distance × 1.5.
- Read: CONTRACTS §3, §5; UX_REQUIREMENTS J3, J5, J6, J6b.

## 3. Scope and ownership

Create and own: `core/geometry.py` (walk polylines), `core/routing.py` (`route`), `core/maneuvers.py`, `core/tour.py` (`plan_tour`, `replan`), `core/check_geometry.py`, tests in `tests/core/`. Update `core/export_fixtures.py` to real geometry and drop the `provisional` flag. Do not modify the kit file; reimplement the same computation for paths and assert equality with the kit lengths.

## 4. Implementation obligations

1. **Walk polylines** (`core/geometry.py`): for a space and two members (anchor or door landing), rebuild the same node set the kit uses (points + shrunken corners), the same visibility matrix (reuse `starter_agent.building_map.visibility_matrix`), and run Dijkstra with predecessors (numpy or `networkx.from_numpy_array`) to recover the corner sequence. Full door-to-door polyline = door position → landing → corners → landing → door position. Cache per `(content_hash, version, space_id)` together with the kit walks. If the kit used the ×1.5 fallback for a pair, return the straight segment and mark `"fallback": true`.
2. **`route()`** (`core/routing.py`): builds the constrained graph (CONTRACTS §3; merge session closures), Dijkstra from the start space to the destination space, returns RouteResult §5 with `node_path`, `space_path` (`spaces_passed`), `element_path` (CONTRACTS rule, verified 161/161), `segments` per floor (walk polylines; stairs/lift segments as connector records with `to_floor_id`), `maneuvers`, `length_m` (2 decimals) and `length_m_exact`. Unreachable → `reachable: false` with `reason` (`no_step_free_path` if the unconstrained route exists but not step-free, `too_narrow` for width, `blocked_by_closure` if removing closures restores it, else `disconnected`) and best-effort `blocking_ids` (for closures: the closed IDs on the unconstrained route).
3. **Maneuvers** (`core/maneuvers.py`): one `depart`, then one maneuver per door crossing where the heading change between the last 1.5 m before and the first 1.5 m after the door exceeds 30° (`slight_*` 30–60°, `turn_*` 60–150°, `u_turn` > 150°), one `enter` for entering the destination room or a named hall, `take_lift`/`take_stairs` per connector use (merge consecutive flights into one "Take Stairs B up to Floor 2"), `arrive`. Straight door crossings are folded into the next maneuver's `distance_m`. Landmark: nearest asset of category `machine`, `equipment` or `fixture` within 3 m of the maneuver point and in the space being left or entered, else the entered space's name. Texts: "After the CNC mill, turn right.", "Go through the door into Corridor 0.01.", "Take the Office lift to Floor 1.", max 90 characters, English.
4. **Tours** (`core/tour.py`): `plan_tour(b, start, stops, constraints, keep_order=False, end=None)`. Stops are given as asset or space IDs; merge items in the same space into one stop (`stop_id` stable: `s1…` by first appearance). Distance matrix by one `single_source_dijkstra_path_length` per stop (start included). `keep_order` → fixed order. Otherwise Held–Karp over pending reachable stops (open path, optional `end`), exact up to 12 stops; above 12, nearest neighbour + 2-opt with `order_policy: "optimized_heuristic"`. Then route each leg (full RouteResult). Unreachable stops go to `unreachable_stops` with a reason and do not block the others.
5. **Replan** (`replan(b, tour, from_position, reason_event=None)`): keep `collected` stops, start from `from_position.space_id`, re-optimise remaining stops unless `keep_order`, increment `revision`, set `changed_because`. A wheelchair profile never falls back to stairs; if a stop becomes unreachable it is reported as such.
6. **Performance** (measure and record): warm `route` on `proc-factory-dev-003` < 150 ms; 5-stop tour < 1 s; first-touch walk computation of the largest building (1,623 spaces) measured and reported; Manuel's codex will warm the demo buildings at startup.
7. **`core/check_geometry.py`:** for every walk used by the dev warm-up routes: polyline inside `polygon.buffer(-0.15).buffer(0.02)` plus the door stubs, polyline length equals the kit edge length within 1e-3 m (the kit rounds to 3 decimals), route `length_m` equals the kit answer within 0.01 m; prints a summary and exits non-zero on failure.

## 5. Interfaces and fixtures

- Produces CONTRACTS §5 RouteResult and TourResult exactly; send Manuel's codex the call signatures and two example payloads in STATUS.
- Regenerate `fixtures/tour_proc-factory-dev-003.json` with real polylines and maneuvers; tell Manuel's Claude.

## 6. Execution order

0. (10 min, first thing, unblocks Manuel's codex) minimal `core/edits.py`: `resolve_edit` and `apply_events` for `close`/`open`/`undo` (materialise = base + closures), `preview_edit` returning `summary` and `effects.active_tours_affected` computed by re-routing the given tours. Push and tell Manuel's codex; H03 completes the other actions.
1. (40 min) Polylines + `check_geometry` on dev; push.
2. (20 min) `route()` with unreachable reasons; tests (L-shaped room never cut through; parallel doors keep the chosen door ID; step-free through lift; closed lift → stairs, wheelchair → `no_step_free_path`); push and notify Manuel's codex.
3. (25 min) Maneuvers + landmark texts; eyeball five routes in two buildings by printing the texts; push.
4. (20 min) `plan_tour` + `replan` + tests (Held-Karp equals brute force on random 6-stop cases; collected stops preserved); push.
5. (10 min) Real fixtures; notify Claude.
Timebox: if maneuvers are still poor at 00:30 CEST, ship door-level maneuvers with room names and improve later; polylines and tours are not optional.

## 7. Acceptance

- `uv run python -m core.check_geometry data/dev` exits 0 (record counts).
- `uv run pytest -q tests/core` green.
- A screenshot or SVG dump (your own quick matplotlib render is fine) of two routes in L-shaped rooms showing no wall crossing; attach paths in STATUS.
- Manuel's Claude confirms visually on the desk map once G3 is reached.

## 8. Collaboration and Git

Branch `hagen/core`; merge `origin/main` before step 2 and step 5. Request merge at 00:30 CEST (G3 window). Any change to RouteResult/TourResult fields after Claude started rendering needs a change request.

## 9. Completion report

SHA; `check_geometry` summary; timings; example payload paths; known limits (fallback walks, maneuver heuristics); next: H03.

## 10. Blocked-work behaviour

If polyline reconstruction disagrees with kit lengths in some spaces, keep the kit length as the truth, return the straight-line fallback for those walks with `"fallback": true`, list the spaces in STATUS, and continue. Never adjust lengths to match the drawing.
