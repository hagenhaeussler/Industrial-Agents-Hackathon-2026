# STATUS: Manuel's Claude (Experience & Frontend Lead)
Last update: 2026-10-24 22:15 CEST · Branch: `manuel-claude/web` · HEAD: `1ecbc7d` (+ this STATUS commit) · Last sync with origin/main: `d46775f` (main has not moved)

Single writer: Manuel's Claude. Keep this structure (OWNERSHIP_AND_DEPENDENCIES §7).

## Current task
C01, C02 and the C03 core (admin card, trace panel, upload) are done and verified locally against the integrated core + platform server (`hagen/core` @ `b57d39f`). Next: demo script (`demo/SCRIPT.md`), accessibility pass, then real-phone checks with the humans.

## Delivered (newest first)
- `1ecbc7d` U11: after a reconnect the phone compares `building_version`; if the building changed while offline it reads the missed events and replans from the current step (verified by stopping the server, committing a closure on restart: phone showed "Office staircase is closed. New route via Office lift (+20 m).").
- `6f65b96` **U6 wheelchair**: desk "How do you move?" (walk / wheelchair / pram / trolley → session profile, inherited by the phone); reroute notice names stops a closure makes unreachable and why ("UPS unit 1.05 can no longer be reached step-free: the Office lift was the only step-free way there. The other stops are replanned."); persistent banner for unreachable stops; **"Show the route with stairs" only on request** (see CR-C-1 for the server part; client fallback in place).
- `af3bcb6` **U8 upload**: admin drop/choose `building.json` → `POST /api/buildings` (X-Session-ID) → stats, errors, warnings → "Open in desk". Verified: `proc-campus-dev-000` uploaded as `upl-h-rsaalzentrum-024-…`, desk planned a 2-stop tour on it (104 m).
- `ff68d01` **"How I calculated this"** panel (desk tour + admin): route model, order policy, constraints, per-leg length/rooms/doors, version/revision, tool traces; mock data replaced by real core output (Hagen's C3 snapshot + a real-core tour for the scenario parts).
- `11a2962` desk ask box: when `/api/chat` is unavailable (503 today: no key / agent not merged) it searches the parts list itself and says so ("Text chat is not connected yet, so I searched the parts list. Selected 3D printer H-A3-A, Tool cabinet H-A1, UPS unit 1.05."); one phrase per item, ambiguous → chips, missing → named. The scenario sentence resolves to exactly the scenario parts (tested).
- `99ed118` **C03 admin view** (`/admin`, admin session): lifts/stairs list with Close…/Reopen…, clickable lifts, stairs, rooms and doors on the map, **preview card** (summary, affected tours before → after m or "no route", newly unreachable rooms), Confirm with a stable `op_id` (**double click → exactly one event**, verified), Cancel, event log with Undo, `version_conflict` → "Preview again", discreet "Reset demo" with `?demo=hero`.
- `693e05b` **C02 phone journey**; `e29fc43` desk on the live API (C2 types, `schema.check.ts`); `212bea6`; `de81877` **C01 desk**; `78b0fde` deps; `c59b924` `git mv web/mobile web/app`. Details in git log.
- checks at `1ecbc7d`: `bun run build` ok; `bun test` **26 pass, 0 fail**.

## Interfaces exposed / changed
- SPA routes: `/` (buildings), `/desk[?demo=hero|?building=<id>]`, `/admin[?demo=hero|?building=<id>]`, `/go/:tourId` (`/go/demo` = old prototype), `/m/:markerId`. `?mock=1` = bundled fixtures + "Demo data" badge.
- **Voice (Manuel's codex):** `src/phone/voice.tsx` mounts your `src/voice/useBuildingVoice.ts` lazily via `import.meta.glob` (my branch builds with or without it). **Trial merge** of `origin/manuel-codex/platform` into my HEAD (local only, not pushed): clean merge, `bun run build` ok, **49 Bun tests pass**, hook chunk 3.45 kB lazy; with the token endpoint returning 503 the phone opens the text chat sheet automatically (**U9 verified**). Desk/admin have `#desk-voice-slot` / `#admin-voice-slot` for a voice button (wiring on desk/admin is next once main has the hook).
- Calls used (CONTRACTS §7–§10): buildings, snapshot, sessions (create/get/patch incl. `profile`, `constraints`, `position`, `active_tour_id`), tours (create/get/progress with `X-Session-ID`/replan), tools (`propose_edit`, `commit_edit` with `op_id`, `undo` with `event_id`+`op_id`), events, markers (get), `POST /api/buildings` (upload), `POST /api/demo/reset`, `/api/chat`, WS events.
- `demo/scenario.json`: factory fallback (`proc-factory-dev-003`), start Hall access 0.19, parts 3D printer H-A3-A / Tool cabinet H-A1 / UPS unit 1.05 (two floors), admin target Office staircase (walk) or Office lift (wheelchair). Switch `building_id` to the hero building when it exists.

## Evidence (local: Vite dev + `hagen/core` @ `b57d39f` server from a detached worktree; Chrome in the app's browser pane, phone = 375×812 emulated tab)
- **Aha 1** plan → route visible: 76 ms, ~0.1 s, ~0.1 s; `POST /api/tours` 75 / 86 / 91 ms (platform adapter); real core similar ("planned in N ms" shown in the tour panel).
- **Aha 2** QR URL opened in the phone tab → tour shown; desk flipped to **"Opened on phone"** (`tour_opened`).
- **Aha 3** WS event → new route on the phone: **131 / 136 / 145 / 153 / 169 / 199 / 309 ms** (7 trials, local; 309 ms with the phone tab in the background); collected stops stay ticked; admin UI Confirm → phone banner "Office staircase is open again. New route via Office staircase (−10 m)."
- Real core maneuvers on the phone: "Go through the door into Office corridor 0.16." → "Take the Office staircase to Floor 1." (floor switches) → "After the Server rack 1.05-B, turn left." → arrival with happy avatar and "Got it".
- Largest building (1,623 spaces): floor switch 40–136 ms (dev build). Phone path ≈ 105 kB gzip.
- Screenshots `master prompt/Manuel's Claude/evidence/`: `c01-desk-tour-mock.jpg`, `c01-qr-handoff-mock.jpg`, `c01-desk-live-api.jpg`, `c02-phone-start-confirm.jpg`, `c02-phone-guidance.jpg`, `c02-phone-reroute-live.jpg`, `c02-phone-arrival-real-core.jpg`, `c02-u6-wheelchair-lift-closed.jpg`, `c03-admin-preview-card.jpg`, `c03-trace-panel.jpg`.
- **Not verified yet:** real Android/iPhone, Railway/HTTPS, live voice (no ElevenLabs agent/token), camera scanner on a device, `/m/<id>` with a printed marker, `/api/chat` with Lenard's agent.

## Design tooling
- Claude Design: **not available** in this environment (no Claude Design tool or connector is exposed to this session; O-1). Working from `web/app/DESIGN.md` plus the frontend-design skill.

## Blockers and resource requests
- **Humans (H8):** for U3/U10 on real phones I need the app on a URL the phones can reach. LAN works for the map (no camera without HTTPS): run the server + `bun run dev` and open `http://<laptop LAN IP>:5173/go/<tour>`; Railway (Hagen's test URL exists) for HTTPS/camera.
- **Manuel's codex / Hagen's codex (resolver):** with the platform kit adapter, `find "3D printer"` and `plan_tour "tool cabinet"` returned `not_found` though several match; with `hagen/core` they correctly return "Which of these did you mean?". Please make sure main uses the core resolver.
- **Request (Dockerfile web stage):** `COPY demo /demo` into the `web` stage so `demo/scenario.json` is bundled.

## Change requests
### CR-C-1: replan should follow the session's current mobility
- Contract section: CONTRACTS §5/§7 (replan), current version C4
- Requested change: `POST /api/tours/{id}/replan` (and progress replans) should use the session's current `profile`/`constraints` for `step_free` instead of the tour's stored constraints (today `service.replan_tour` passes `tour["constraints"]` as overrides, so `step_free: true` survives a PATCH to `profile: "walk"`).
- Why: J6b "Show the route with stairs" must work as an explicit, in-place replan of the same tour (the desk keeps tracking the tour id).
- Migration effect: server only. My client already PATCHes `profile: "walk"` + `constraints.step_free: false` and then replans; until the fix it falls back to planning the remaining parts as a new tour.
- Needed by: G4 (01:15 CEST) ideally; fallback works meanwhile.
- Status: open (owner Manuel's codex)

## Next handoff
- Manuel's codex (captain): `manuel-claude/web` @ `1ecbc7d` is ready to merge after core and platform; trial merge with platform is clean (49 Bun tests). It only touches `web/app/`, `demo/scenario.json` and my STATUS/evidence.
- Hagen's codex: route lines and maneuvers from the core look right on the map (doors, stair landings, no wall crossings seen on the factory); I will report any odd geometry.
- Lenard's codex: desk/phone/admin show chat replies, candidate chips (≤ 4, with floor) and react to `display` (`tour`, `asset_ids`, `instruction`, `edit_preview`/`edit_committed` via tool calls).
