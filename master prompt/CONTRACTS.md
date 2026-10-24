# Contracts: Talk to Your Building

This file is the single canonical place for shared interfaces. Builder prompts link here and do not copy the details. If a prompt and this file disagree, this file wins. To change a section, use the change-request protocol in [OWNERSHIP_AND_DEPENDENCIES.md](OWNERSHIP_AND_DEPENDENCIES.md#6-change-request-protocol). Only the section owner edits a section, and the owner appends one line to the [contract changelog](#16-contract-changelog).

Contract version: **C3** (24 Oct 2026; C2 HTTP clarifications by Manuel's codex preserved; C3 core result clarifications by Hagen's codex). Section owners:

| § | Section | Owner | Main consumers |
|---|---|---|---|
| 1 | Identifiers, units, frames | Hagen's codex | all |
| 2 | Evaluation and cost profiles | Hagen's codex | Lenard's codex |
| 3 | Mobility constraints | Hagen's codex | all |
| 4 | Core Python API | Hagen's codex | Lenard's codex, Manuel's codex |
| 5 | Route, tour and maneuver results | Hagen's codex | Manuel's Claude, Manuel's codex |
| 6 | Edits, proposals, events, versions | Hagen's codex (semantics), Manuel's codex (storage, HTTP) | all |
| 7 | HTTP API | Manuel's codex | Manuel's Claude, Lenard's codex |
| 8 | Tool API and voice client tools | Manuel's codex (transport), Lenard's codex (prompts) | Manuel's Claude |
| 9 | Realtime events | Manuel's codex | Manuel's Claude |
| 10 | Sessions, position, handoff, markers | Manuel's codex | Manuel's Claude |
| 11 | Coordinate transforms in the browser | Manuel's Claude (2D), Manuel's codex (WebXR) | each other |
| 12 | Benchmark interfaces and output schemas | Lenard's codex | humans, judges |
| 13 | Answer serialization rules | Lenard's codex | judges |
| 14 | Errors | Manuel's codex | all |
| 15 | Fixtures and mocks | each producer | consumers |

---

## 1. Identifiers, units and frames

- **Units:** metres and square metres everywhere. Angles in degrees. Times in ISO 8601 UTC in payloads; humans read Europe/Berlin.
- **Building frame:** the kit frame. x to the right, y up, one XY frame for all floors of a building (exception documented in the kit: some Swiss Dwellings floors are centred per floor; `room_stacked` is never asked for those). Height is the floor's `elevation_m`.
- **Kit IDs are used unchanged:** `building.id`, `floor.id`, `space.id`, `opening.id`, `vertical_connector.id`, `asset.id`. Never invent aliases for them in payloads.
- **Graph node IDs** (from `starter_agent/building_map.py`): a space node is its `space_id`; a door node is `"door:" + opening_id`.
- **Generated IDs:**

| ID | Format | Producer |
|---|---|---|
| uploaded building | `upl-<slug>-<6 hex>` | server |
| hero building | `hero-<slug>` | Hagen's codex (file in `demo/hero/`) |
| `content_hash` | `sha256:` + first 16 hex of SHA-256 over `json.dumps(building, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` | core |
| `building_version` | integer, `0` = unmodified base, +1 per committed event (undo is an event too) | server |
| new opening from an edit | `<floor_id>-O-evt<version>` | core (edit application) |
| `event_id` | `evt-<building_version>` (unique per building) | server |
| `proposal_id` | `prp_` + 12 base32 chars | server |
| `op_id` | client-generated UUID4, one per user intention, reused on retry | client |
| `request_id` | `req_` + 12 base32 chars | server, echoed by client |
| `session_id` | UUID4 hex | server |
| `tour_id` | 10 lowercase base32 chars (unguessable enough for a demo, never sequential) | server |
| `marker_id` | `mk_` + 8 base32 chars | server |

## 2. Evaluation and cost profiles

- **`kit_1_1_0`** is the default and only implemented profile: the README §3 route model exactly as `starter_agent/building_map.py` implements it (door-to-door walks on `buffer(-0.15)`, 30 cm door landing, stairs 2 m per metre of rise between consecutive stops, lift 15 m once per ride plus 1 m per metre with every stop pair joined, edge lengths rounded to 3 decimals, parallel edges kept, **no route round the outside**). The kit says the hidden test answers use this model.
- **`sunday_vN`** is reserved. It is created only if the organizers publish a different rule. It is a subclass or parameter set, never an edit of the kit constants.
- The profile is chosen by configuration (`TYB_PROFILE` env var, `--profile` CLI flag), recorded in every report, checkpoint and `/health` response. **An LLM never chooses it.**
- The live app uses the same profile for lengths. The polylines in §5 are the geometric realisation of the same walks, so map, camera and benchmark agree.

## 3. Mobility constraints

```json
{"step_free": false, "min_door_width_m": 0.0, "closed": [], "no_transit_room_types": []}
```

| Named profile | Constraints | Origin |
|---|---|---|
| `walk` | defaults | default |
| `wheelchair` | `step_free: true` | user says wheelchair, pram, crutches, "no stairs"; kept in the session |
| `trolley` | `step_free: true`, `min_door_width_m: <width>` | user states a load width; `wide_delivery_count` semantics |

- `step_free` drops every stair connector and every opening with `step_free: false` (kit rule). Lifts stay.
- `min_door_width_m` drops every opening narrower than the value (an opening exactly as wide passes).
- `closed` lists connector, opening or space IDs; they cannot be used at all. Session/building closures are merged with request closures.
- `no_transit_room_types` is implemented in core but **not used by any demo or benchmark path** (forklift and production-bay semantics are unconfirmed; see the decision register D-19).
- **A wheelchair profile never silently becomes a stairs route.** If no step-free route exists, the result is `reachable: false` with a reason. The UI and agent say so and may offer, as a separate explicit option, the route with stairs.

## 4. Core Python API

Package `core/` (owner Hagen's codex). Pure functions over an immutable building object; no network, no global mutable state except per-process caches keyed by `(content_hash, building_version, profile, constraints)`.

```python
from core.building import Building, load_building          # Building wraps starter_agent.building_map.BuildingMap (kit file unchanged)
b = load_building(Path("data/dev/proc-factory-dev-003"))   # or load_building(dict); b.id, b.content_hash, b.version (0)

from core.spatial import solve                             # benchmark solvers, ported from the sibling core (D-03)
solve(b, kind: str, inputs: dict) -> dict                  # kinds: the 9 benchmark kinds plus locate, count, route, route_step_free, route_with_closure, tour
                                                           # inputs use exactly the field names of the kit `inputs` (README §4, train/dev files)

from core.resolve import resolve
resolve(b, text: str, kind: str = "any") -> dict           # kind: any|space|asset|asset_type|room_type|floor|connector|opening
  # {"status": "unique|ambiguous|none", "candidates": [{"kind": "space", "id": "...", "label": "Office 0.30 (Ground floor)", "score": 1.0, "why": "exact ref"}]}
  # order: exact ID > exact ref/name > full rendered label "Name (Floor)" > normalized (case, leading zeros, EN/DE synonyms) > fuzzy (RapidFuzz)
  # numbers must match exactly: "Press 4" never resolves to "Press 14"; equal best scores -> "ambiguous"

from core.routing import route
route(b, start, destination, constraints: dict | None = None) -> dict      # RouteResult, §5
from core.tour import plan_tour
plan_tour(b, start, stops: list[dict], constraints=None, keep_order=False, end=None) -> dict   # TourResult, §5
from core.edits import resolve_edit, preview_edit, apply_events
resolve_edit(b, edit: dict) -> dict          # names -> IDs, validates, raises EditError
preview_edit(b, edit, active_tours: list[dict]) -> dict   # effects, never mutates
apply_events(base: Building, events: list[dict]) -> Building   # deterministic replay; result.version == len(events)
from core.whatif import what_if
what_if(b, edit, probe: dict) -> dict        # isolated copy; never persisted
from core.validate import validate_building
validate_building(raw: dict) -> dict         # {"ok": bool, "errors": [...], "warnings": [...], "stats": {...}}
```

**`solve` inputs per kind** (benchmark kinds use the kit field names exactly; warm-up kinds have no kit `inputs`, so these are ours):

| kind | inputs | result (besides `value`) |
|---|---|---|
| `largest_room`, `floor_area_total` | `floor_id`, `room_type` | `space_id`, `area_m2` / `value` (m²) |
| `errand` | `start`, `asset_type`, `floor_id`, `room_type` | `value` (m), `via`, `target` |
| `wide_delivery_count` | `start`, `floor_id`, `min_width` | `value`, `space_ids` |
| `step_free_reachable_count` | `start`, `floor_id`, `closed` | `value`, `space_ids` |
| `room_stacked` | `start`, `direction` (`above`/`below`) | `space_id`, `overlap_m2` |
| `shared_walls_count` | `start` | `value`, `space_ids` |
| `straight_line_3d` | `first`, `second` | `value` (m) |
| `what_if_door` | `first`, `second`, `floor_id`, optional `door_floor_id` | `value`, `improved_space_ids`, `door_position` |
| `locate` | `asset` (asset ID) | `asset_id`, `space_id`, `floor_level`, `position` |
| `count` | `asset_type`, `floor_id` | `value` |
| `route`, `route_step_free`, `route_with_closure` | `start`, `destination`, optional `step_free`, optional `closed` (list of IDs) | RouteResult §5 under `route` |
| `tour` | `stops` (list of space IDs, first = start), `keep_order: true` | TourResult-like `legs`, `length_m`, or `reachable: false` |

- `start`, `destination` and stop `target` accept a space ID, an asset ID (resolved to the asset's space, kit rule: a route to an item ends in its room) or a `{"space_id": "...", "point": [x, y]}` position. Free text is resolved **before** calling core (by `resolve`), never inside routing.
- Errors are raised as `core.errors.CoreError(code, message, candidates=None)` with `code` from §14.

## 5. Route, tour and maneuver results

**RouteResult** (reachable):

```json
{
  "reachable": true,
  "from_space_id": "proc-factory-dev-003-F0-S030",
  "to_space_id": "proc-factory-dev-003-F1-S012",
  "length_m": 57.41,
  "space_path": ["...-F0-S030", "...-F0-S016", "...-F1-S012"],
  "element_path": ["...-F0-O0035", "...-V02", "...-F1-O0101"],
  "node_path": ["...-F0-S030", "door:...-F0-O0035", "...-F0-S016", "...-F1-S012"],
  "segments": [
    {"floor_id": "...-F0", "kind": "walk", "space_id": "...-F0-S030", "points": [[3.1, 4.2], [5.0, 4.2], [12.4, -4.7]], "length_m": 14.2},
    {"floor_id": "...-F0", "kind": "lift", "element_id": "...-V02", "points": [[20.1, 3.0]], "to_floor_id": "...-F1", "length_m": 18.8}
  ],
  "maneuvers": [
    {"i": 0, "kind": "depart", "floor_id": "...-F0", "at": [3.1, 4.2], "distance_m": 0, "text": "Leave Office 0.30 through the door ahead.", "landmark": null, "element_id": null},
    {"i": 1, "kind": "turn_right", "floor_id": "...-F0", "at": [12.4, -4.7], "distance_m": 9.6, "text": "After the CNC mill, turn right.", "landmark": "CNC mill 0.16", "element_id": "...-F0-O0035"},
    {"i": 2, "kind": "take_lift", "floor_id": "...-F0", "at": [20.1, 3.0], "distance_m": 6.0, "text": "Take the Office lift to Floor 1.", "landmark": "Office lift", "element_id": "...-V02"},
    {"i": 3, "kind": "arrive", "floor_id": "...-F1", "at": [25.0, 7.5], "distance_m": 4.4, "text": "You have arrived at Tool crib 1.12.", "landmark": null, "element_id": null}
  ],
  "constraints": {"step_free": false, "min_door_width_m": 0.0, "closed": [], "no_transit_room_types": []},
  "profile": "kit_1_1_0",
  "building_id": "proc-factory-dev-003", "building_version": 0, "content_hash": "sha256:0123456789abcdef"
}
```

Rules, verified on 24 Oct 2026 against the kit answers (161/161 reachable dev routes, see the register):
- `space_path` is `BuildingMap.spaces_passed(graph, node_path)`: every space passed, corridors crossed door to door included.
- `element_path` lists, for each consecutive node pair: the connector ID when the cheapest edge is a stair/lift edge (**one entry per flight or ride edge**, so a two-flight stair appears twice), and the opening ID whenever the next node is a door node. This reproduces the kit `element_path` exactly.
- `length_m` is the Dijkstra length on the profile graph, rounded to 2 decimals for display; unrounded value kept in `length_m_exact`.
- `segments[].points` are the actual walk polylines inside each space: anchor or landing points plus the corners of the shrunken polygon chosen by the visibility-graph shortest path, then the door position. `segments[].length_m` is the authoritative graph cost (rounded to 0.001 m by the kit); additive `geometry_length_m` is the raw measured polyline length. Check the latter against unrounded kit walks within 1e-6 m, and against rounded graph costs within 0.001 m. Rounding makes equality at 1e-6 m to the rounded graph cost impossible in general. Explicit `fallback: true` means the kit used its inflated straight-line fallback: its drawing is not claimed to be a verified walkable route. The UI never chooses doors or straightens lines.
- Routes accept position objects and use their actual point, rather than silently replacing it with the room anchor. Additive `start_position` and `destination_position` record the actual endpoints.
- `maneuvers[].kind` ∈ `depart, straight, turn_left, turn_right, slight_left, slight_right, u_turn, enter, take_lift, take_stairs, arrive`. Turn kinds come from the polyline heading change at door crossings (> 30° slight, > 60° turn, > 150° u-turn). `landmark` is the nearest named asset within 3 m of the maneuver point that is not furniture of category `furniture`, else the space being entered, else null. `text` is plain English, at most 90 characters.

**RouteResult** (unreachable): `{"reachable": false, "from_space_id": ..., "to_space_id": ..., "reason": "no_step_free_path|blocked_by_closure|too_narrow|disconnected", "blocking_ids": [...], "constraints": ..., "profile": ..., "building_id": ..., "building_version": ..., "content_hash": ...}`. `blocking_ids` is best effort (for example the closed lift whose removal would make it reachable); it may be empty.

**TourResult:**

```json
{
  "tour_id": "k3j9q2m7xa", "revision": 2, "status": "active",
  "building_id": "...", "building_version": 3,
  "order_policy": "optimized_exact",
  "start": {"space_id": "...-F0-S004", "point": [3.0, 2.0], "floor_id": "...-F0", "source": "desk"},
  "end": null,
  "stops": [
    {"stop_id": "s1", "space_id": "...-F0-S021", "asset_ids": ["...-A00117"], "label": "Torque wrench · Tool crib 0.21", "status": "collected"},
    {"stop_id": "s2", "space_id": "...-F1-S012", "asset_ids": ["...-A00301", "...-A00302"], "label": "Filament, steel drum · Store 1.12", "status": "pending"}
  ],
  "order": ["s1", "s2"],
  "legs": ["<RouteResult from start to s1>", "<RouteResult s1 -> s2>"],
  "length_m": 112.6,
  "unreachable_stops": [],
  "changed_because": {"event_id": "evt-3", "summary": "East lift closed"},
  "profile": "kit_1_1_0", "constraints": {"step_free": false, "min_door_width_m": 0.0, "closed": [], "no_transit_room_types": []}
}
```

- **Stop identity:** items in the same space merge into one stop. `stop_id` is stable across revisions.
- **Meaning of "optimal":** minimal total profile length of an open path from `start` through all pending reachable stops, ending at `end` if given. `order_policy`: `optimized_exact` (Held-Karp dynamic programme over the stop distance matrix, used up to 12 stops), `optimized_heuristic` (nearest neighbour + 2-opt, above 12 stops, labelled as heuristic in the UI), `fixed` (`keep_order: true`; this is the kit `tour` kind, where order is prescribed).
- **Replan:** collected stops keep `status: "collected"` and are excluded from optimisation; the new start is the latest known position (§10); `revision` increments; `changed_because` names the event.
- **Unreachable stops** are listed with their reason and never silently dropped. The remaining stops are still planned.
- **Core/server boundary:** core returns `tour_id: null` until the server assigns the opaque ID. `constraints` retain requested mobility/closure constraints; current building closures are applied to every leg and recorded separately as additive `building_closed`. A later reopen must not be overridden by a stale copy of a building closure saved in the tour.
- **Moved parts:** replanning retargets pending asset stops from the current asset inventory. Collected stops stay collected. Existing stop IDs are retained, including when previously separate stops move into the same room; if one grouped stop splits across rooms, extra stops receive new IDs. New tours still merge items initially sharing a space.

## 6. Edits, proposals, events and versions

**Edit request** (same shape for `propose_edit` and `what_if`; matches `docs/elevenlabs-agent-config.md`):

```json
{"action": "close|open|add_door|move_asset|set_room_type", "target": "East lift", "second_target": null, "value": null}
```

| action | target | second_target | value | Effect |
|---|---|---|---|---|
| `close` | connector, opening or space | – | – | element unusable |
| `open` | a closed element | – | – | reopens |
| `add_door` | space A | space B (same floor, shared wall ≥ 1 m) | optional width in m, default 0.9 | new step-free opening at the midpoint of the longest shared wall run (same placement as `what_if_door`) |
| `move_asset` | asset | target space | optional `"x,y"` | asset moves; position defaults to the target space anchor |
| `set_room_type` | space | – | room type from the kit list | changes `room_type` |

**Lifecycle** (server owns storage; core owns semantics):
1. `propose_edit` → resolve names to IDs (ambiguous → error with candidates, nothing stored) → `preview_edit` → store proposal `{proposal_id, edit (resolved), base_version, op_id, created_at, expires_at = +10 min}` → return preview. **Nothing changes.**
2. Preview payload: `{"proposal_id", "edit", "summary": "Close East lift (lift, floors 0-3)", "base_version", "effects": {"active_tours_affected": 1, "tours": [{"tour_id", "before_m", "after_m"|null, "reachable_after": bool}], "newly_unreachable_spaces": 0}}`.
3. `commit_edit {proposal_id, expected_version?, op_id?}` → if `expected_version` (default: the proposal's `base_version`) differs from the current version → `version_conflict` with the current version and a fresh preview hint; nothing applied. Otherwise append event, version + 1, broadcast §9. **Idempotent:** committing the same `proposal_id` or `op_id` again returns the original event and does not apply twice.
4. `undo {event_id?, op_id}` → appends an `undo` event that reverts the given event (default: the latest non-undo event by the same session). Undo of an undone event is rejected.
5. `what_if` → isolated copy, returns effects only. Never stored, never broadcast.

**Event record:** `{"event_id": "evt-4", "building_id", "building_version": 4, "kind": "close|open|add_door|move_asset|set_room_type|undo", "edit": {...resolved IDs...}, "undoes": null, "op_id", "proposal_id", "session_id", "author_role": "admin", "summary", "created_at"}`.

- Base data is immutable. The materialised building at version *v* is `apply_events(base, events[:v])`.
- **Benchmark isolation:** benchmark and Sunday runs always load base files from disk and never read `/state`. Each question starts from the original building.
- Edits are permitted only for sessions with `role: "admin"`. An LLM-provided argument is not a permission.

## 7. HTTP API

FastAPI service, one process (owner Manuel's codex). All JSON. `/api`, `/ws` and `/health` are matched before the SPA fallback. Synchronous `def` handlers for geometry so the event loop stays free.

| Method and path | Request | Response |
|---|---|---|
| `GET /health` | – | `{"ok": true, "commit": "<sha>", "profile": "kit_1_1_0", "state_dir_writable": true, "buildings": 281}`; no LLM call |
| `GET /api/buildings` | – | `[{"id", "name", "source", "split", "floors", "has_lift", "has_stairs"}]` (kit buildings, hero, uploads) |
| `GET /api/buildings/{id}` | `?version=` optional | `{"building": <kit building.json materialised at version>, "building_version", "content_hash", "closed": [ids], "derived": {"anchors": {space_id: [x,y]}, "areas_m2": {space_id: a}}}` (gzip) |
| `POST /api/buildings` | `building.json` body (admin) | `{"building_id", "validation": <validate_building report>}`; 422 if invalid |
| `POST /api/buildings/{id}/plan-import` | multipart PNG/SVG + `floor_level` (admin, X5 only) | draft + validation, §6-style preview; nothing saved until confirmed |
| `GET /api/buildings/{id}/events` | `?since=` | `[event]` |
| `POST /api/tools/{name}` | `{"session_id", "args": {...}}` | ToolResponse §8 |
| `POST /api/sessions` | `{"building_id", "device": "desk|phone", "role": "navigator|admin", "profile": "walk"}` | session §10 |
| `GET /api/sessions/{id}` / `PATCH /api/sessions/{id}` | position, profile, active tour | session |
| `POST /api/tours` | `{"session_id", "start"?, "items": ["asset or space ids"], "keep_order": false, "end": null}` | TourResult with `tour_id` |
| `GET /api/tours/{id}` | – | TourResult (latest revision) |
| `POST /api/tours/{id}/progress` | `{"stop_id", "status": "collected|pending"}` | TourResult |
| `POST /api/tours/{id}/replan` | `{"session_id", "from": {"space_id", "point"?}, "reason"}` | TourResult revision + 1 |
| `GET /api/markers/{id}` | – | marker §10 |
| `POST /api/buildings/{id}/markers` | `{"markers": [{"space_id", "point", "heading_deg", "label"}]}` (admin) | `[marker]` |
| `GET /api/buildings/{id}/markers/sheet` | – | printable HTML with QR codes (URL form §10) |
| `GET /api/voice/token` | `?agent=navigator|admin` | `{"token", "agent_id"}`; 503 `voice_unavailable` when no key; the API key never leaves the server |
| `POST /api/chat` | `{"session_id", "message"}` | `{"reply", "tool_calls": [ToolResponse], "display": {...}}` |
| `POST /api/demo/reset` | `{"building_id"}` (admin; demo mode) | archives the building's event log, restarts it at version 0 and broadcasts `building_reset`; never available outside demo mode |

**Session header and handoff metadata (C2, additive):** Administrative raw-HTTP requests (building upload, marker creation, demo reset, plan import) carry `X-Session-ID: <admin session_id>`; tools already carry `session_id` in their JSON body. `POST /api/tours/{id}/progress` accepts optional `X-Session-ID` to advance the calling phone's position; include it on the phone. Without it, the stored tour session is used for compatibility. The caller must belong to the same building and have opened that tour. Server tours also carry `mobility_profile` (`walk|wheelchair|pram|trolley`) separately from the cost `profile`; the phone copies it and `constraints` when opening the handoff. `TYB_DEMO_MODE=true` is required to enable demo reset; it is disabled by default. `GET /devtest` serves the unlinked device-gate page after the frontend build.

Front-end routes served by the SPA: `/` (building picker), `/desk`, `/admin`, `/go/{tour_id}`, `/m/{marker_id}`. Query `?demo=hero` loads the demo scenario.

Types for TypeScript are generated from FastAPI's OpenAPI (`server/openapi.json`, committed by Manuel's codex; `web/app/src/api/schema.gen.ts`, regenerated by Manuel's Claude with `bun run gen:api`). No hand-written duplicate types for server payloads.

## 8. Tool API and voice client tools

**One tool registry** (`server/tools.py`, owner Manuel's codex) backs the HTTP tool endpoint, the text chat agent and the ElevenLabs client tools. Names and parameters below are frozen at C1. The ten tools from `docs/elevenlabs-agent-config.md` are unchanged; `spatial_query` is an addition.

**ToolResponse:**

```json
{
  "ok": true, "tool": "plan_tour", "request_id": "req_ab12cd34ef56",
  "building_id": "...", "building_version": 3,
  "result": {"tour_id": "k3j9q2m7xa", "order": ["s1", "s2"], "length_m": 112.6},
  "speech": "Three parts in two stops, about 113 metres. First the tool crib, then the store upstairs.",
  "display": {"kind": "tour", "tour_id": "k3j9q2m7xa"},
  "trace": [{"fn": "resolve", "args": {"text": "torque wrench"}, "ms": 2}, {"fn": "plan_tour", "args": {"stops": 2}, "ms": 41}]
}
```

Failure: `{"ok": false, "tool", "request_id", "building_version", "error": {"code", "message", "candidates": [...]}, "speech": "There are two presses: line 4 and line 7. Which one?"}`. Domain failures return HTTP 200 so the voice agent receives them; transport failures use 4xx/5xx. **A failed tool is never reported to the agent as success.**

| Agent | Tool | Arguments | Behaviour |
|---|---|---|---|
| navigator | `find` | `query` (string, required) | resolve over assets and spaces; unique → highlight and `speech` with place; ambiguous → candidates for one clarifying question; none → says so |
| navigator | `plan_tour` | `items` (comma-separated string, required), `keep_order` (bool), `step_free` (bool) | resolves each item (ambiguous item → error with candidates, nothing planned), plans from the session position, creates a tour, returns `tour_id` |
| navigator | `route` | `destination` (required), `step_free`, `min_door_width_m` | route from session position with session profile merged |
| navigator | `next_step` | – | next maneuver of the active tour; at a stop asks to confirm collection |
| navigator | `spatial_query` | `kind` (one of the nine benchmark kinds, required), `target`, `second_target`, `floor`, `room_type`, `asset_type`, `direction`, `min_width_m` (strings/number as applicable) | resolves names to IDs and calls `core.spatial.solve`; answers "what is above office 0.29", "largest meeting room on floor 1", "how many rooms share a wall with …"; **added by the master agent (not in `docs/elevenlabs-agent-config.md`)**: required for the text chat, optional for the ElevenLabs navigator (H4) |
| admin | `propose_edit` | `action`, `target` (required), `second_target`, `value` | §6 step 1–2 |
| admin | `commit_edit` | `proposal_id` (required) | §6 step 3; client adds `op_id` |
| admin | `undo` | – | §6 step 4 |
| admin | `what_if` | as `propose_edit` | §6 step 5 |
| admin | `set_scale` | `reference`, `length_m` | X5 import only; otherwise `not_available` |
| admin | `generate_markers` | – | creates markers for entrances and doors of the demo route; returns sheet URL |

- ElevenLabs tools are type **Client** with **"Wait for response"** enabled (verified in the ElevenLabs React docs on 24 Oct 2026: without blocking, the agent assumes success). The browser handler calls `POST /api/tools/{name}`, updates the view from `display`, and returns `JSON.stringify({ok, speech, result})` truncated to ≤ 1,500 characters.
- Position, building and profile come from the session, never from the conversation.
- Context the app pushes with `sendContextualUpdate` (no reply is triggered), exact phrasing:
  - `Position: <space name> (<floor name>), source <marker|manual|tour start>.`
  - `Tour <tour_id> loaded: <n> stops, next <label>.`
  - `Building changed: <summary>. The active tour was replanned: <new length> m, next <label>.` or `... No route is available any more: <reason>.`
  - `Stop collected: <label>. <k> of <n> done.`

## 9. Realtime events

`WS /ws/buildings/{building_id}`. Server messages:

```json
{"type": "hello", "building_id": "...", "building_version": 3}
{"type": "building_changed", "building_id": "...", "building_version": 4, "event": {"event_id": "evt-4", "kind": "close", "edit": {"action": "close", "target": "...-V02"}, "summary": "East lift closed"}, "at": "2026-10-24T23:10:00Z"}
{"type": "building_reset", "building_id": "...", "building_version": 0}
{"type": "tour_updated", "tour_id": "...", "revision": 3}
{"type": "tour_opened", "tour_id": "...", "session_id": "...", "device": "phone"}
```

- Clients reconnect with backoff 0.5 s → 5 s, then `GET /api/buildings/{id}` and the active tour. Messages with `building_version` ≤ the known version are ignored.
- On `building_changed`, the phone with an active tour calls `POST /api/tours/{id}/replan` from its current position. Only the newest response per tour is applied (compare `revision` and `request_id`).
- `tour_opened` is sent when a phone session sets `active_tour_id` (the desk shows "Opened on phone").
- Target: phone shows the new route ≤ 2 s after the admin says "Yes" (Aha 3).

## 10. Sessions, position, handoff and markers

**Session:** `{"session_id", "building_id", "device", "role", "profile", "constraints", "position": null | {"space_id", "floor_id", "point": [x, y], "heading_deg": null | 90, "source": "desk|tour_start|marker|manual", "marker_id": null, "confidence": "high|medium|low", "updated_at"}, "active_tour_id"}`. Session state is separate from building state. Sessions persist in SQLite so a reload or reconnect keeps them; the browser stores `session_id` in `localStorage`.

**Desktop start position:** the desk user picks or confirms "I am at …" (default in demo mode: the scenario start). Without a position, `plan_tour` asks for one.

**Handoff QR** (desktop → phone): encodes the URL `https://<host>/go/<tour_id>` and nothing else. The server stores the tour (§5). The phone loads it, creates its own `phone` session, copies the profile and sets position `source: "tour_start", confidence: "low"` to the tour start, then asks: *"Are you at <start label>?"* with **Yes**, **Scan a position code**, **Choose my room**. A handoff link alone never claims to locate the person.

**Position marker** (a different concept, printed on paper at doors): URL `https://<host>/m/<marker_id>`. Record: `{"marker_id", "building_id", "floor_id", "space_id", "point": [x, y], "heading_deg", "label"}`. `point` is a floor footprint sticker in front of the code; `heading_deg` is the direction the person faces when standing on the sticker looking at the code, counter-clockwise from the building +x axis. Scanning (camera app or in-app jsQR) sets `source: "marker", confidence: "high"`. A decoded QR is a known point and heading under that standing protocol, not a measured camera pose.

**Manual progress:** each stop has a "Got it" control (and voice "collected" / "next"). Position advances to the stop's space when a stop is collected.

## 11. Coordinate transforms in the browser

- **2D map** (`web/app/src/geo/transform.ts`, owner Manuel's Claude): SVG world group uses `transform="scale(1,-1)"` around building coordinates, i.e. `screen_y = -y`; one function `toSvg([x, y])` used for rooms, assets, routes and positions. Labels are rendered in an un-flipped layer.
- **WebXR** (`web/app/src/camera/ar/frames.ts`, owner Manuel's codex): XR `local` space, origin at the device pose when the session starts while the user stands on the marker facing `heading_deg` θ. For building point (bx, by) relative to marker point p: `d = (bx - px, by - py)`, forward `f = dx·cosθ + dy·sinθ`, right `r = dx·sinθ − dy·cosθ`; XR position `(x = r, y = floorY, z = −f)` with `floorY` from `local-floor` if granted, else −1.4 m. Unit-tested with four headings.

## 12. Benchmark interfaces and output schemas

Owner Lenard's codex.

- **Official evaluator entry point (unchanged contract):** `bench.agent:answer(building_directory: Path, question_text: str) -> str`, used as `uv run python -m benchmark.evaluate data/dev --agent bench.agent:answer`.
- **Run order inside `answer`:** (1) deterministic template parser → typed inputs → `core.spatial.solve` → serializer; (2) if parsing fails with "unsupported wording" or the parser finds an ambiguity, and `ANTHROPIC_API_KEY` is available, the LLM fallback ([MASTER_PLAN.md §4.2](MASTER_PLAN.md#42-benchmark-and-product-agent-harness)) produces validated inputs through tools; (3) otherwise an honest reply **without** an `Answer:` line. Never a placeholder answer.
- **Batch runner:** `uv run python -m bench.run <split_dir> --name <run> [--csv out.csv] [--workers 4] [--mode hybrid|template|llm]` with per-question checkpoints keyed by `(question_id, sha of question text, building content_hash, git commit, profile, model, prompt_version)`.
- **Sunday adapter (provisional until the organizers publish the schema):** `uv run python -m bench.run_benchmark <building_dir> <questions.json> <answers.json> [--csv answers.csv]`.
  - Input accepted: a JSON list or `{"questions": [...]}`; each entry has `id` and `text` (or `question`), optional `kind`, optional `constraints` (`step_free`, `closed`, `min_door_width_m`). Also accepts JSONL and the kit CSV `question_id,building_id,kind,question`.
  - Output `answers.json`: `{"profile": "kit_1_1_0", "commit": "<sha>", "building_id", "content_hash", "answers": [{"id", "kind", "answer_text": "<full reply ending with the Answer line>", "value": <number|null>, "item_id": <asset id|null>, "space_id": <space id|null>, "route": null | {"reachable": true, "space_path": [...], "node_path": [...], "element_path": [...], "length_m": 57.41}, "error": null}]}`. Unreachable: `"route": {"reachable": false, "space_path": [], "node_path": [], "element_path": [], "length_m": null}`. Tours: `route.legs` holds one entry per leg plus the summed `length_m`.
  - The adapter is the only component that changes if the organizers publish a different schema.
- **Submission CSV:** exactly the 145 IDs of `data/test/submission_template.csv`, columns `question_id,answer`, UTF-8, header, ≤ 5 MB, every row non-empty; validated by `uv run python -m bench.validate_submission <csv> data/test/submission_template.csv`.

## 13. Answer serialization rules

The serializer, not the LLM, writes the final line. Kit scorer facts verified locally: only the last line starting with `Answer:` counts; number answers need exactly one number; `²` is not matched as a digit and `m2` after a number is not a separate number, but any other number (a room ref, a floor) in a numeric answer line makes it wrong.

| Kind | Answer line |
|---|---|
| `largest_room` | `Answer: <ref>, <name>, <area> m²` (ref first, e.g. `Answer: 0.21, Quality lab 0.21, 20.250000 m²`); if a space has no ref use the kit fallback label |
| `room_stacked` | `Answer: <ref>, <name>` |
| `floor_area_total`, `errand`, `straight_line_3d` | `Answer: <number>` only |
| counts | `Answer: <integer>` only |
| warm-up `locate` | `Answer: <asset name> in <space name> (<floor name>)` |
| warm-up `count` | `Answer: <integer>` |
| warm-up routes and tours | `Answer: <length> m via <space names>` or `Answer: no route` |

One short explanatory sentence may precede the line. Never two `Answer:` lines with different content.

## 14. Errors

`code` values shared by core, server, tools and UI:

| code | meaning | user-facing behaviour |
|---|---|---|
| `ambiguous` | several equally good candidates | ask exactly one question listing ≤ 4 candidates with floor |
| `not_found` | nothing matches | say it does not exist; offer closest real matches |
| `no_route` | unreachable under constraints | say so, give the reason; offer an explicit alternative profile |
| `invalid_args` | schema or semantic validation failed | agent repairs once, else asks |
| `version_conflict` | building changed since preview | re-preview and ask again |
| `forbidden` | edit from a non-admin session | explain that changes need the admin view |
| `voice_unavailable` | voice token/provider configuration unavailable (HTTP 503) | show text chat fallback |
| `not_available` | feature not built or provider missing (voice, import) | fall back (text chat, JSON upload) |
| `internal` | bug | apologise briefly; logged with `request_id` |

HTTP transport errors use FastAPI's default `{"detail": ...}` plus `{"error": {"code", "message"}}`.

## 15. Fixtures and mocks

- Producers publish real-data fixtures early so consumers never wait: `fixtures/` at the repository root, each file with a top-level `"_fixture": {"producer", "contract": "C1", "generated_by": "<command>", "replace_by": "<live endpoint>"}` field.
  - `fixtures/building_proc-factory-dev-003.json` (snapshot §7), `fixtures/tour_proc-factory-dev-003.json` (TourResult with real polylines once H02 lands; straight anchor-to-door lines before, flagged `"_fixture": {"geometry": "provisional"}`), `fixtures/tool_responses.json` — producer Hagen's codex (`uv run python -m core.export_fixtures`).
  - `fixtures/events_close_lift.json`, `fixtures/session.json` — producer Manuel's codex.
- Frontend mocks live only in `web/app/src/mocks/` and are switched on by `?mock=1`; the UI shows a small "demo data" badge whenever a mock is active (prototype rule kept). Mocks are removed from default paths by the journey gate.

## 16. Contract changelog

| Version | Date/time | Section | Change | By |
|---|---|---|---|---|
| C1 | 24 Oct 2026 | all | initial (includes the `spatial_query` tool addition and `tour_opened` event) | master agent |

- **C2 — 24 Oct 2026, Manuel's codex, CR-M-1:** clarified §7 admin session header, optional phone progress header, mobility handoff metadata and demo opt-in; documented the existing voice token 503 code in §14. Endpoint paths, eleven tool names and their required arguments unchanged.

- **C3 — 24 Oct 2026, Hagen's codex, CR-H-1:** clarified §5 raw polyline length versus rounded kit cost, actual point endpoints, server-assigned tour IDs, current building closures and moved-part replanning. C2 HTTP/session transport preserved.
