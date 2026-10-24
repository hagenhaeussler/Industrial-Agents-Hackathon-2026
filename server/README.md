# Platform integration (C5)

Run `uv sync`, copy `.env.example` to `.env`, then run:

```sh
uv run uvicorn server.app:app --reload --port 8000
```

The server loads `.env` without overriding existing environment variables. One production uvicorn worker owns WebSocket fan-out. SQLite, uploads and derived walking caches live in `STATE_DIR`; kit files remain immutable. Schema migrations run at startup. Production images include building geometry/inventory and the catalog; evaluation questions, answer CSVs and submissions are excluded.

## Client handoff

1. `POST /api/sessions` with `building_id`, `device: "desk"`, `role: "navigator"` and mobility `profile: "walk"` (or `wheelchair`, `pram`, `trolley`). Persist the returned `session_id` in localStorage.
2. `PATCH /api/sessions/{id}` with `position: {space_id, source: "desk"}`. The server derives the floor/anchor and checks supplied coordinates.
3. `POST /api/tours` with `{session_id, items: ["asset or space ID"], keep_order: false}`. The same operation is available through `plan_tour` in the tool registry.
4. The QR encodes only `PUBLIC_BASE_URL/go/{tour_id}`. On the phone create a `phone` session for the tour's building, then PATCH `active_tour_id`. This copies the mobility constraints and gives a low-confidence `tour_start` position. Ask the person to confirm it.
5. Send `X-Session-ID: <phone session_id>` with progress requests so "Got it" advances the phone position. Replan with `{session_id, from: <current position>, reason}`; ignore stale responses by revision.
6. Subscribe to `/ws/buildings/{building_id}`. On reconnect refetch the building snapshot and active tour. Refetch/replan after `building_changed` or `building_reset`. `hello` follows subscriber registration, so a concurrent commit cannot fall through a subscription gap.

The server emits `tour_opened` when a phone opens the handoff, and `tour_updated` after progress/replan/instruction advancement. WebSocket heartbeats occur every 20 seconds. UI reconnect backoff (0.5–5 seconds) belongs to the frontend.

## Shared tools and chat

`POST /api/tools/{name}` takes `{session_id, args}`. Eleven tool names and required arguments remain the C1 names. Domain failures return HTTP 200 with `ok:false`; transport failures use 4xx/5xx. Never treat a failed result as success. Valid affirmative `step_free` route/tour requests persist session mobility, and route width persists atomically across concurrent tools. A valid no-route result keeps that mobility need; invalid/ambiguous inputs do not mutate it. Explicit profile changes use the session PATCH API.

```python
from server.tools import registry  # bound by the FastAPI lifespan
schemas = registry.json_schemas()
# registry.call("find", session_id, {"query": "CNC mill"})
```

For `spatial_query(kind="step_free_reachable_count")`, `second_target` can name the closed element. All existing session/building closures are included; an empty set returns the count without closures. The live core accepts a closure list while preserving its original single-string benchmark input. Exact item matches precede normalized/fuzzy matches across entity kinds, so a perfect fuzzy score cannot displace an exact name.

An independent process can instantiate `ToolRegistry(PlatformService(catalog, store))` after initializing `StateStore`. `/api/chat` constructs `agent.chat.ChatAgent(registry, store.get_session)` and calls `reply(session_id, message)` when Lenard's agent and an Anthropic key are installed. Otherwise it returns explicit `not_available`.

The voice hook is documented in [the browser bridge README](../web/app/src/voice/README.md). The token endpoint returns a short-lived WebRTC token; missing provider configuration returns 503 `voice_unavailable`. This implementation does not configure the external ElevenLabs agents.

## Admin and markers

Create an admin session in the admin view. Tools use its body `session_id`; raw upload/marker/reset endpoints use `X-Session-ID`. Propose before commit. A proposal expires after ten minutes; version conflicts require a new preview. Repeat `proposal_id` or `op_id` commits return the original event. Undo appends an event.

Uploads use the core validator and get a server-assigned `upl-…` building ID. When the core validator is unavailable the endpoint returns `not_available`, rather than accepting unchecked data. Marker standing points must be in their rooms; marker sheets escape labels and print 12 cm QR codes. A scanned marker is a known point/heading under the standing protocol, not a camera pose.

Demo reset is disabled unless `TYB_DEMO_MODE=true`. It archives events, clears proposals, broadcasts `building_reset`, and retains separate session/tour state for a subsequent replan. Do not expose it outside the rehearsed demo environment.

## Verification and handoff files

```sh
scripts/check.sh
uv run python -m server.export_openapi
uv run python scripts/generate_server_fixtures.py
```

`server/openapi.json` is committed; Claude regenerates client types with `bun run gen:api`. `fixtures/session.json` and `fixtures/events_close_lift.json` are labelled examples with real kit geometry, not live state. `/devtest` is an unlinked device gate after the app build; its local jsQR bundle is built with `bun scripts/build-device-gate.ts`.

Until Hagen's core is integrated, the server uses the kit adapter for available routes/tours/edits. Every such route has `geometry: "provisional"`, and tool traces identify `_adapter: "kit"`. Anchor-to-door segments must not be represented as H02's exact wall-safe polylines. Spatial queries wait for the core. Physical-phone, live voice and Railway acceptance require separate evidence.
