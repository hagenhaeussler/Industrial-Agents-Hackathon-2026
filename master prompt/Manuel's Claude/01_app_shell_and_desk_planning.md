# C01: App shell and desk planning (target G3, 00:30 CEST; fixtures first, live API when Manuel's codex lands M02)

## 1. Outcome and user value

Aha 1, "Say what you need, not where it is": on the laptop Manfred sees the building and a parts list, clicks or says what he needs, the parts light up, the optimal order and total distance appear, the route draws itself, and a QR code sends the tour to his phone. One SPA hosts desk, phone and admin.

## 2. Starting state

- `web/mobile/` (`b411e05`): React 19, Vite 8, TypeScript (strict, `verbatimModuleSyntax`), Bun, `lucide-react`, Manrope, Blobatar `alain00`; modules `camera/useCamera.ts` (+ test), `navigation/` (demo routes in German, SVG minimap and overlay), `agent/` (scripted German chat). Rules in its `AGENTS.md`/`DESIGN.md`. Build/tests were not run during planning (no Bun on that machine).
- Real data: `fixtures/building_proc-factory-dev-003.json` and `fixtures/tour_proc-factory-dev-003.json` from Hagen's codex around 23:00 CEST (geometry provisional until ~00:30). Before that, write against the CONTRACTS §5/§7 examples.
- Live API from Manuel's codex: buildings ~23:00, tools/tours ~00:15–00:30.
- Read: UX_REQUIREMENTS J1–J4, §2; CONTRACTS §5, §7, §8 (ToolResponse, `display`, `trace`), §10, §11 (2D), §15.

## 3. Scope and ownership

Own: the move `git mv web/mobile web/app`, then all of `web/app/` except `src/voice/` and `src/camera/ar/`; `package.json`/`bun.lock`; `web/app/AGENTS.md`/`DESIGN.md` (update for desk + live data); `demo/scenario.json`.

## 4. Implementation obligations

1. **Move and baseline (first 15 minutes, push immediately and tell Manuel's codex, whose Dockerfile builds `web/app`):** `git mv web/mobile web/app`; `bun install`; `bun run build`; `bun test`; record results. Add, in one dependency commit with exact versions in `bun.lock`: `@elevenlabs/react` (for Manuel's codex's voice hook), `qrcode` (+ types), `jsqr`, `react-zoom-pan-pinch`, `three` (+ `@types/three`, lazy-loaded later), dev `openapi-typescript`; add script `"gen:api": "openapi-typescript ../../server/openapi.json -o src/api/schema.gen.ts"`. Router: your choice (a tiny history router is fine).
2. **English and honesty:** translate every German string; `index.html` `lang="en"`, title and description in English (product name from human input Q-7, working title "Talk to Your Building"); keep the prototype's honesty: anything still simulated carries the small "demo data" badge.
3. **API layer (`src/api/`):** typed client (generated types once `server/openapi.json` exists), `request_id` tracking per view so late responses never overwrite newer ones, `building_version` awareness, a mock switch (`?mock=1` → `src/mocks/` serving the fixtures).
4. **Floor map renderer (`src/map/`), shared by desk, phone minimap and admin:** SVG in building metres with `toSvg` (CONTRACTS §11, `scale(1,-1)`), rooms filled by type with readable labels in an unflipped layer, doors as small gaps/marks, active floor solid with other floors ghosted, floor switcher, assets as dots (selected ones large and labelled), route `segments` drawn exactly as returned (accent `#dcff58` with dark outline per DESIGN.md, animated dash draw ≤ 1.2 s, respects reduced motion), stop numbers, "You" pin, closed elements hatched red. Pan/zoom with `react-zoom-pan-pinch`, fit-to-route button. Must stay fast on the largest building (1,623 spaces): memoise per floor, avoid re-rendering rooms on route changes.
5. **Desk view (`/desk`, `/desk?demo=hero`):** left panel "What do you need?" input (sends to text chat `/api/chat`; voice button mounted when the voice hook is ready), parts list grouped by room and floor with search (client-side over the snapshot assets: name, type), checkboxes for multi-select, "Plan collection tour" button (calls `POST /api/tours`), "Keep my order" toggle, start position chip ("You are at …", change via room picker; the desk creates its `desk` session with `POST /api/sessions` on load and stores the position with `PATCH`); right: map. After planning: numbered stops, total metres, "Optimal order" (or "Good order · heuristic" when `order_policy` says so), per-leg list, unreachable stops listed with the reason. Clarifying questions from tool responses appear as tappable candidate chips.
6. **Handoff QR:** "Send to phone" opens a dialog with a large QR of `PUBLIC_BASE_URL/go/<tour_id>` (`qrcode` to SVG), the short URL as text, and a status line that turns to "Opened on phone" on the `tour_opened` WebSocket event (CONTRACTS §9).
7. **Quality bar:** keyboard path for search → select → plan → QR; visible focus; 44 px targets; no layout shift when the route animates; works at 1280×800 (projector) and larger.

## 5. Interfaces and fixtures

Consumes CONTRACTS §5 TourResult/RouteResult, §7 endpoints, §8 ToolResponse. Fixture mode until the endpoints are live; switch each screen to live data as soon as Manuel's codex announces it, and remove the fixture from the default path.

## 6. Execution order

Move + deps + baseline (15 min) → English pass and app shell with routes `/`, `/desk`, `/go/:tourId`, `/m/:markerId`, `/admin` (20 min) → map renderer on the building fixture (40 min) → parts list + selection + tour drawing on the tour fixture (30 min) → QR dialog (10 min) → switch to live API and test with Manuel's codex (15 min, G3).

## 7. Acceptance

- `bun run build` and `bun test` pass (record output); app served by the FastAPI server from `web/app/dist` (Manuel's codex confirms).
- G3 checklist items for the desk (INTEGRATION §3) on integrated `main`.
- Timed: click "Plan" → route visible < 3 s on the live API (record three timings).
- Screenshots of desk (factory building, three stops on two floors) in STATUS.

## 8. Collaboration and Git

Branch `manuel-claude/web`. Push after the move (Manuel's codex needs it for Docker), after the map, after the desk. Merge window G3. Ask Hagen's codex in STATUS if any route looks wrong on the map (you draw; he fixes geometry).

## 9. Completion report

SHA; screenshots; timings; build/test output; what is still on fixtures and when it switches; next: C02.

## 10. Blocked-work behaviour

API late: keep building on fixtures (real data) and mark the screen in STATUS as "fixture"; never fake success states that the API cannot produce. Bun unavailable: ask your human for O-2 immediately; meanwhile write code and let Manuel's codex build it in Docker.
