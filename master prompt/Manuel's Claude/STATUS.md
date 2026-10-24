# STATUS: Manuel's Claude (Experience & Frontend Lead)
Last update: 2026-10-24 22:00 CEST · Branch: `manuel-claude/web` · HEAD: `693e05b` (+ this STATUS commit) · Last sync with origin/main: `d46775f` (21:15 CEST; main has not moved)

Single writer: Manuel's Claude. Keep this structure (OWNERSHIP_AND_DEPENDENCIES §7).

## Current task
C01 done (live API verified locally). C02 phone journey working on the live API locally; next: C02 robustness pass, then C03 admin preview card + demo mode (pulled forward, since G4 benefits from it).

## Delivered (newest first)
- `693e05b` **C02 phone journey (live API)**: `/go/:tourId` creates/reuses the phone session and PATCHes `active_tour_id` (server sends `tour_opened`); start sheet "Are you at <start>?" → **Yes** / **Scan a position code** (in-app jsQR, accepts only `/m/mk_…` links, frames never leave the canvas) / **Choose my room**; guidance banner from `maneuvers` (kind → icon, text, metres), current leg bold and later legs quiet on the map, steps sheet (text alternative), Next/Previous, **Got it** (`POST /progress` with `X-Session-ID`), progress dots, completion card with happy Blobatar; **live reroute**: `building_changed` → `POST /replan` from the step position → banner "Office staircase is closed. New route via Office lift (+10 m)." + voice context; wheelchair "Show the route with stairs" only on request; `/m/:markerId` (marker position, high confidence, continues the tour); voice bridge (see interfaces); text chat sheet fallback; route-level code splitting · checks: build ok, `bun test` **21 pass** · contract C2
- `e29fc43` desk on the live API: `schema.gen.ts` from `server/openapi.json` (C2) + compile-time `schema.check.ts`; `gen:api` via a pinned TS 5 tool dir (openapi-typescript cannot run on TS 7); `X-Session-ID` on progress; replan `from` is a Position; "Provisional route" badge for kit-adapter geometry
- `212bea6` ground-floor default start; dev-only `?mock=1` for every kit building; AGENTS/DESIGN/README
- `de81877` **C01 desk on fixtures**: app shell + router, `src/api`, `src/map` renderer, desk (ask, parts, plan, QR), `demo/scenario.json`
- `78b0fde` dependency commit (exact versions): `@elevenlabs/react@1.19.1`, `qrcode@1.5.4`, `jsqr@1.4.0`, `react-zoom-pan-pinch@4.2.0`, `three@0.186.1`, types, `openapi-typescript@7.13.0`
- `c59b924` `git mv web/mobile web/app`

## Interfaces exposed / changed
- `web/app/` SPA. `bun install --frozen-lockfile && bun run build` → `dist`. Dev: `bun run dev` proxies `/api`, `/ws`, `/health` to `TYB_API` (default `http://127.0.0.1:8000`).
- **Voice (Manuel's codex):** `src/phone/voice.tsx` loads `src/voice/useBuildingVoice.ts` through a lazy `import.meta.glob`, so my branch builds with or without it. After the merge it mounts `ConversationProvider` + your hook in a sibling bridge (no remount of the screen) ~0.6 s after the screen is up, and uses `status`, `isSpeaking`, `error`, `start`, `stop`, `sendContext` exactly as your README describes. Phone: mic button in the dock; `start()` failure opens the text chat sheet.
- `/api/chat` `display` handling: `{kind:"tour", tour_id}` draws the tour (desk); any display with `asset_ids` (+ `space_id`, `floor_id`) highlights them; `{kind:"instruction"}` on the phone refetches the tour (step follows `navigation_index`); failed tool calls with `error.candidates` become chips (≤ 4).
- Phone handoff URL `PUBLIC_BASE_URL/go/<tour_id>`: base = `VITE_PUBLIC_BASE_URL` at build time, else `location.origin` (dialog warns on localhost).
- `demo/scenario.json`: `building_id`, `start.space_id`, `say`, `items`, `admin.target`/`element_id` (factory: Office staircase `…-V01`).

## Evidence (local: Vite dev + platform server `d187ce5` from a detached worktree, Chrome in the app's browser pane)
- **Aha 1** plan → route visible on the live API: 76 ms, ~0.1 s, ~0.1 s (console `[timing]`); `POST /api/tours` 75 / 86 / 91 ms.
- **Aha 2** desk QR URL opened in a second (mobile-emulated) tab: tour visible, desk status flipped to **"Opened on phone"** via `tour_opened`.
- **Aha 3** admin `propose_edit` + `commit_edit` (close/open/undo Office staircase via `/api/tools`) → phone shows the new route **131 / 136 / 145 / 153 / 169 / 199 ms** after the WS event arrived (6 trials); collected stop stays ticked; closed stairwell hatched red.
- "Got it" → next stop on screen in 102 ms; reload mid-tour resumes at the same step (localStorage per tour revision).
- Largest building (`osm-way27917482`, 1,623 spaces) dev build: floor switch 40–136 ms.
- Screenshots in `master prompt/Manuel's Claude/evidence/`: `c01-desk-tour-mock.jpg`, `c01-qr-handoff-mock.jpg`, `c01-desk-live-api.jpg`, `c02-phone-start-confirm.jpg`, `c02-phone-guidance.jpg`, `c02-phone-reroute-live.jpg`.
- `bun run build` ok (phone path ≈ 105 kB gzip: index 69 + Journey 9 + map 20 + expression 6; ElevenLabs SDK 162 kB gzip in its own lazy chunk); `bun test` 21 pass, 0 fail.
- Not yet verified: real phones, Railway/HTTPS, voice (hook not on my branch), camera scanner on a device.

## Design tooling
- Claude Design: **not available** in this environment (no Claude Design tool or connector is exposed to this session; O-1). Working from `web/app/DESIGN.md` plus the frontend-design skill.

## Blockers and resource requests
- **Manuel's codex (kit adapter output, until H02):** maneuvers have `distance_m: 0`, stairs/lifts come as `kind: "straight"` (not `take_stairs`/`take_lift`), texts contain bracketed IDs (`… 0.19 [proc-factory-dev-003-F0-S019] …`) and are cut at 90 chars, and steps after a floor change keep the old `floor_id`. The UI copes (hides 0 m, strips `[…]`), but please check whether the adapter can fix these cheaply; otherwise they disappear with Hagen's H02.
- **Manuel's codex:** `propose_edit` summary is imperative ("Close Office staircase"); the phone turns it into "Office staircase is closed". If you change the summary style, tell me.
- **Request (Dockerfile web stage):** `COPY demo /demo` into the `web` stage so `demo/scenario.json` is bundled (without it the build still passes but `?demo=hero` loses its preselection).
- Hagen's codex: waiting for `fixtures/tour_proc-factory-dev-003.json` / H02 polylines to check them visually.

## Change requests
- none

## Next handoff
- Manuel's codex (captain): `manuel-claude/web` @ `693e05b` is ready to merge after `manuel-codex/platform` (it only adds files under `web/app/` and `demo/`; your `src/voice/`, `src/camera/ar/` and `public/devtest.html` do not overlap). After the merge, voice mounts automatically.
- Next pushes: C02 robustness (offline/U11 check, U10 permission paths), C03 admin view (map click → preview card → Confirm/Cancel → event log with Undo) and `?demo=hero` on admin.
