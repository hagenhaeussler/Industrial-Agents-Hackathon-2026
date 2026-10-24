# STATUS: Manuel's Claude (Experience & Frontend Lead)
Last update: 2026-10-24 21:50 CEST · Branch: `manuel-claude/web` · HEAD: see `git log origin/manuel-claude/web -1` (this push) · Last sync with origin/main: `d46775f` (21:15 CEST)

Single writer: Manuel's Claude. Keep this structure (OWNERSHIP_AND_DEPENDENCIES §7).

## Current task
C01 done on fixtures; waiting for the live API to switch (G3). Meanwhile starting C02 (phone journey) on fixtures.

## Delivered (newest first)
- (this push) default start = room by a ground-floor entrance; dev-only `?mock=1` reads any kit building from `data/` (perf testing); AGENTS/DESIGN/README for desk + live data · checks: `bun run build` ok, `bun test` 15 pass · contract C1
- `de81877` **C01 desk on fixtures**: English app shell and router (`/`, `/desk`, `/admin`, `/go/:tourId`, `/m/:markerId`); `src/api` (C1 types, client with `?mock=1`, `useLatest` request guard, building WebSocket with 0.5→5 s backoff); `src/map` floor-map renderer (`toSvg`, rooms by type, doors, ghosted floors, parts, closures hatched, route drawn exactly as returned with 1.2 s draw, stop numbers, You pin, pan/zoom, floor switch with stop counts, fit route); desk (ask → `/api/chat` with candidate chips, parts list by floor/room with search, multi-select, keep-order, start picker → `PATCH /api/sessions`, `POST /api/tours`, tour summary with policy label/legs/unreachable, QR handoff with `tour_opened` status); `/go/:tourId` slice (loads tour, phone session at tour start, same stops on map); `demo/scenario.json` · checks: build ok, `bun test` 15 pass (incl. QR decodes to the exact URL via jsQR, late-response guard, routes, stop marks) · contract C1
- `78b0fde` dependency commit (exact versions in `web/app/bun.lock`): `@elevenlabs/react@1.19.1`, `qrcode@1.5.4` (+ `@types/qrcode@1.5.6`), `jsqr@1.4.0`, `react-zoom-pan-pinch@4.2.0`, `three@0.186.1` (+ `@types/three@0.186.0`), dev `openapi-typescript@7.13.0`; script `gen:api`; package renamed `talk-to-your-building`. Consumers: Manuel's codex.
- `c59b924` `git mv web/mobile web/app` (history preserved). Consumers: Manuel's codex (Dockerfile builds `web/app`).

## Interfaces exposed / changed
- `web/app/` is the SPA root. `bun install --frozen-lockfile && bun run build` → `web/app/dist`. Dev: `bun run dev` proxies `/api`, `/ws`, `/health` to `TYB_API` (default `http://127.0.0.1:8000`).
- Calls used (CONTRACTS §7): `GET /api/buildings`, `GET /api/buildings/{id}`, `POST /api/sessions`, `GET`/`PATCH /api/sessions/{id}` (`position`, `active_tour_id`), `POST /api/tours` (`session_id`, `items`, `keep_order`), `GET /api/tours/{id}`, `POST /api/chat`, `WS /ws/buildings/{id}` (`building_changed`, `building_reset`, `tour_updated`, `tour_opened`).
- `/api/chat` `display` handling: `{kind: "tour", tour_id}` loads and draws the tour; any display with `asset_ids` (and optional `space_id`, `floor_id`) highlights them; failed tool calls with `error.candidates` become chips (≤ 4). **Manuel's codex/Lenard's codex:** please use these shapes for `find` (e.g. `{kind: "highlight", asset_ids: [...], space_id, floor_id}`).
- Session `position` PATCH body: `{space_id, floor_id, point, source: "desk", confidence: "medium", heading_deg: null, marker_id: null}`.
- Phone handoff URL: `PUBLIC_BASE_URL/go/<tour_id>` where the base is `VITE_PUBLIC_BASE_URL` at build time, else `location.origin` (the dialog warns when it is localhost).
- `demo/scenario.json` (repo root): `building_id`, `start.space_id`, `say`, `items` (asset IDs), `admin.target`/`element_id`. Loaded via `import.meta.glob`, so a build that sees only `web/` still works (falls back to the factory without preselection).
- Voice mount point for Manuel's codex: `<div id="desk-voice-slot">` inside the desk ask field (CSS hides it while empty). I will import `src/voice/useBuildingVoice` directly once it exists; tell me the hook's return shape.

## Evidence
- Screenshots: `master prompt/Manuel's Claude/evidence/c01-desk-tour-mock.jpg` (factory dev-003, 3 stops on two floors, provisional geometry), `.../evidence/c01-qr-handoff-mock.jpg`.
- Plan → route visible in mock mode: 156 ms (console `[timing]`); live timings pending G3.
- Largest building (`osm-way27917482`, 1,623 spaces, 5 floors) in the dev build: floor switch 40–136 ms, ~380 room polygons per floor.
- `bun run build`: ok (JS 337.8 kB / 107.4 kB gzip; mocks split into a lazy 206 kB chunk loaded only with `?mock=1`). `bun test`: 15 pass, 0 fail.

## Design tooling
- Claude Design: **not available** in this environment (no Claude Design tool or connector is exposed to this session; O-1). Working from `web/app/DESIGN.md` plus the frontend-design skill.

## Blockers and resource requests
- O-2 resolved: Bun 1.3.14 on this machine (official npm package; Homebrew needs a CLT update).
- Live API (Manuel's codex) for G3; fixtures from Hagen's codex (~23:00) to replace my interim mock tour (kit route model, straight provisional segments).
- **Request to Manuel's codex (Dockerfile web stage):** please also `COPY demo /demo` into the `web` stage (one line), so `demo/scenario.json` is in the bundle; without it the build still succeeds but `?demo=hero` loses its preselection.

## Change requests
- none

## Next handoff
- Manuel's codex: merge `manuel-claude/web` for G3; tell me when `/api/buildings/{id}`, sessions, tours and chat are live so I remove `?mock=1` from my test path and record three live timings.
- Hagen's codex: once `fixtures/tour_proc-factory-dev-003.json` lands I replace `web/app/src/mocks/data/` with it and check the polylines visually.
