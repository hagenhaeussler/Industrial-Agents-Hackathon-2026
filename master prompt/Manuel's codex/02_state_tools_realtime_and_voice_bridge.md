# M02: State, tool registry, tours, edits, realtime and the voice bridge (targets: tools/tours by G3 00:30 CEST, edits/events by G4 01:15 CEST)

## 1. Outcome and user value

The desk and the phone share one truthful state: tours created on the desk open on the phone; an admin's committed lift closure is stored once, broadcast, and the phone replans from its position in ≤ 2 s; voice and text call the same tools and never get a fake success. This is the backbone of all three aha moments.

## 2. Starting state

- M01: server skeleton, deps, Docker, Railway (or pending H3).
- Hagen's codex: H01 (`load_building`, `resolve`, `solve`) by ~22:40; H02 step 0 (`resolve_edit`, `apply_events` for close/open/undo, minimal `preview_edit`) ~23:10; `route`/`plan_tour`/`replan` with polylines ~00:00–00:45. Build against the CONTRACTS shapes and swap in the functions as they land.
- Lenard's codex: `agent.chat.ChatAgent` ~00:15 (uses your registry).
- Humans: H4 ElevenLabs agents + key.
- Read: CONTRACTS §6–§10, §14; INTEGRATION §5.

## 3. Scope and ownership

Own `server/state.py`, `server/tools.py`, `server/schemas.py`, `server/ws.py`, `server/voice.py`, `server/markers.py`, `server/routes_*.py` (split as you like), `server/openapi.json` (export script `uv run python -m server.export_openapi`), `tests/server/`, `web/app/src/voice/` (inside Claude's app: `voice/useBuildingVoice.ts`, `voice/clientTools.ts`, `voice/README.md`), fixtures `fixtures/session.json`, `fixtures/events_close_lift.json`.

## 4. Implementation obligations

1. **SQLite (`server/state.py`)** at `STATE_DIR/tyb.sqlite3`, WAL mode, one connection per request or a small lock; tables: `buildings(id, source, path, content_hash, name, created_at)`, `events(building_id, building_version, event_id, kind, edit_json, undoes, op_id UNIQUE, proposal_id UNIQUE, session_id, summary, created_at, archived)`, `proposals(proposal_id, building_id, edit_json, base_version, op_id, session_id, created_at, expires_at, committed_event_id)`, `sessions(session_id, building_id, device, role, profile, constraints_json, position_json, active_tour_id, updated_at)`, `tours(tour_id, building_id, revision, session_id, body_json, updated_at)` (keep revisions), `markers(marker_id, building_id, body_json)`, `derived_cache(content_hash, key, blob)`. Migrations: create-if-missing at startup; schema version table.
2. **Materialisation:** `current_building(building_id)` = `core.edits.apply_events(base, events)` cached by `(content_hash, version)`; warm the hero and demo buildings at startup in a background thread; persist large walk caches in `derived_cache`.
3. **Tool registry (`server/tools.py`):** one dict `REGISTRY[name] = Tool(name, json_schema, handler, roles)` for the eleven tools in CONTRACTS §8 (the UI calls the same tools and the REST endpoints; no extra unlisted tool names). Each handler: load session → materialised building at current version → resolve (ambiguous → `ok: false` with candidates) → core call → `ToolResponse` with `speech` (≤ 2 sentences, landmarks first), `display`, `trace` (fn, args, ms), `request_id`, `building_version`. Admin tools require `role == "admin"` (`forbidden`). `commit_edit`: transaction; check `expected_version` (default proposal `base_version`); `version_conflict` on mismatch; idempotent by `proposal_id` and `op_id`; append event; broadcast. `undo`: latest non-undo event of the session unless an `event_id` is given. The registry exposes `json_schemas()` for Lenard's chat agent and the OpenAPI.
4. **HTTP endpoints (CONTRACTS §7):** buildings (incl. upload with `validate_building`), events, tools, sessions, tours (create via `plan_tour`, progress, replan via `replan`), markers (create from `demo/hero/markers.json`, sheet as printable HTML with QR SVGs from `qrcode`, ≥ 12 cm, sticker + heading arrow + label), voice token, chat (calls `ChatAgent.reply`), demo reset (demo mode only), health. Export `server/openapi.json` after every contract-relevant change and tell Claude to run `bun run gen:api`.
5. **WebSocket (`server/ws.py`):** per-building subscriber sets in process; `hello` on connect; `building_changed` after commit/undo; `building_reset`; `tour_updated` after replan/progress; `tour_opened` when a phone session sets `active_tour_id`. Heartbeat ping every 20 s. Broadcast happens after the DB transaction commits.
6. **Voice token (`server/voice.py`):** `GET /api/voice/token?agent=navigator|admin` → server-side `GET https://api.elevenlabs.io/v1/convai/conversation/token?agent_id=<id>` with header `xi-api-key`; return `{token, agent_id}`; 503 `voice_unavailable` without key/ID; never log the key.
7. **Voice bridge in the browser (`web/app/src/voice/`):** a hook `useBuildingVoice({agent, sessionId, onDisplay})` built on `@elevenlabs/react` (inside `ConversationProvider`; Claude adds the dependency in C01 and mounts the provider): fetch the token, `startSession({ conversationToken })`, register client tools by exact name (CONTRACTS §8) that `POST /api/tools/{name}` with `{session_id, args}` (adding a stable `op_id` per proposal for `commit_edit`), call `onDisplay(response.display)`, and return `JSON.stringify({ok, speech, result})` truncated to 1,500 characters; expose `status`, `isSpeaking`, `start()`, `stop()`, `sendContext(text)` (wraps `sendContextualUpdate` with the CONTRACTS §8 phrasings). Claude builds all visible UI around it. Document the hook in `voice/README.md`.
8. **Tests (`tests/server/`, no network):** create tour → get → progress → replan keeps collected; propose → commit twice → one event; stale `expected_version` → 409-equivalent `version_conflict`; undo; WebSocket receives `building_changed` after commit (TestClient websocket); restart (new app instance on the same `STATE_DIR`) keeps sessions/tours/events; admin tool from a navigator session → `forbidden`; voice token without key → 503.
9. **Latency:** measure commit → broadcast → replan response locally for the demo building; target ≤ 500 ms server-side, so the phone can meet ≤ 2 s.

## 5. Interfaces and fixtures

Fixtures by 23:30 CEST (`fixtures/session.json`, `fixtures/events_close_lift.json`). After each endpoint group lands: `curl` examples in STATUS, OpenAPI export, message to Claude and Lenard via your human.

## 6. Execution order

state + sessions + buildings (30 min) → registry with `find`/`route`/`plan_tour` + tours endpoints (40 min, G3) → voice token + `useBuildingVoice` (25 min, G3 if H4 ready) → chat wiring with Lenard's agent (10 min) → propose/commit/undo + WS + replan (40 min, G4) → markers + sheet + upload + demo reset (25 min) → restart and reconnect tests.

## 7. Acceptance

- `uv run pytest -q tests/server` green.
- G3 and G4 checklists in INTEGRATION §3 pass on integrated `main` (you run them with Claude and Hagen).
- Stopwatch: three trials of "Yes" → phone banner ≤ 2 s on Railway; record in STATUS.
- Voice: one spoken `find` on the desk returns and highlights; error path returns `ok: false` to the agent.

## 8. Collaboration and Git

Branch `manuel-codex/platform`. Merge windows G3 and G4 (you merge yourself after core). Announce any CONTRACTS §7–§10 change with a CR before Claude builds against it.

## 9. Completion report

SHA; endpoint list with `curl` examples; test list; latency numbers; voice status; known gaps.

## 10. Blocked-work behaviour

Core functions late: implement handlers against CONTRACTS shapes with the kit `BuildingMap` (`route` via `BuildingMap.route`, closures via `set_closed`) behind a clearly named adapter, mark responses `"_adapter": "kit"` in `trace`, and replace when Hagen pushes. ElevenLabs not configured: ship the token endpoint and hook with the 503 path; Claude shows text chat.
