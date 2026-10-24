# C02: Phone journey and live reroute (target G4, 01:15 CEST)

## 1. Outcome and user value

Aha 2, "From screen to hand", and Aha 3, "The building reacts": scanning the QR opens exactly this tour on the phone in under two seconds; Manfred confirms where he is, follows clear directions with landmarks and voice, ticks off parts, and when the lift closes mid-route he gets a notice, a spoken explanation and a new line without losing progress.

## 2. Starting state

- C01: app shell, map renderer, API layer.
- Manuel's codex M02: tours (`GET /api/tours/{id}`, progress, replan), sessions, WebSocket, voice hook `src/voice/useBuildingVoice` (CONTRACTS §8), markers (`GET /api/markers/{id}`).
- Hagen's codex H02: real maneuvers and polylines.
- Prototype pieces to keep: route banner, minimap position, camera toggle, agent dock with Blobatar (happy on arrival), dialogs.
- Read: UX_REQUIREMENTS J4b–J7, §3 (U3–U6, U9–U11); CONTRACTS §5, §8 (contextual updates), §9, §10.

## 3. Scope and ownership

`web/app/src/phone/` (or your structure), reuse `src/map/`; integrate `src/voice/` (Manuel's codex) and later `src/camera/ar/` (Manuel's codex, M03) behind Camera mode.

## 4. Implementation obligations

1. **`/go/:tourId`:** load the tour, create a phone session (store `session_id` in `localStorage`; reuse on reload), show the tour summary, then the start confirmation sheet: "Are you at <start label>?" **Yes** / **Scan a position code** (in-app jsQR scanner using the prototype camera hook; accepts `/m/<marker_id>` URLs only) / **Choose my room** (searchable list). `PATCH /api/sessions/{id}` with the position and source.
2. **`/m/:markerId`:** opened by the phone camera app: set position (source marker) for the stored session (or start a fresh one for the marker's building) and show "You are at <label>"; if a tour is active, continue it from here.
3. **Guidance screen** (prototype layout): route banner with the current maneuver (`kind` → icon, `text`, metres to it, destination stop label), minimap with the real floor and route, "Next step" control, step list in a sheet, per-stop "Got it" (`POST /api/tours/{id}/progress`), progress "k of n", completion screen ("All parts collected", total distance, happy avatar). Guidance modes: Map (default), Directions (large text list), Camera (C04/M03).
4. **Voice:** a "Start navigation" button (one user gesture) starts the navigator session via `useBuildingVoice` and requests the microphone; push contextual updates (CONTRACTS §8 phrasings) when the tour loads, a stop is collected, position changes, or the building changes. Show voice status (listening/speaking/off) and a text chat fallback (`/api/chat`) when the token endpoint returns 503 or the mic is denied.
5. **Live reroute:** subscribe `WS /ws/buildings/{id}`; on `building_changed` → `POST /api/tours/{id}/replan` from the current session position → apply only if `revision` is newer → banner "<summary>. New route via <landmark> (+N m)" (or "No step-free route any more: <reason>" with an explicit "Show route with stairs" option for wheelchair profiles) → contextual update to voice → map animates the new line. Collected stops stay ticked. Reconnect with backoff; on reconnect refetch tour and snapshot.
6. **Robustness:** reload mid-tour resumes; offline banner; denied camera/mic keep the 2D path; no stale route ever replaces a newer one.
7. **Phone layout:** the prototype's DESIGN.md rules (safe areas, 16 px inputs, white floating surfaces, route at top, minimap top right, agent at bottom), readable at arm's length, one-hand reachable "Got it".

## 5. Interfaces and fixtures

`fixtures/events_close_lift.json` and `fixtures/session.json` (Manuel's codex) let you build the reroute banner before the WebSocket is live.

## 6. Execution order

`/go` + session + start confirmation (30 min) → guidance with live maneuvers + progress (35 min) → WebSocket reroute (25 min, G4 with Manuel's codex) → voice integration (20 min, when the hook lands) → `/m/:markerId` + in-app scanner (15 min) → robustness pass (15 min).

## 7. Acceptance

- U3, U4, U6, U9, U10, U11 pass on Android and iPhone over HTTPS (record device + browser).
- Aha 2 timing: scan → tour visible < 2 s (three trials); Aha 3 timing: "Yes" on the laptop → phone banner + new line ≤ 2 s (three trials).
- Screenshots or a short screen recording path in STATUS.

## 8. Collaboration and Git

Branch `manuel-claude/web`; merge windows G4 and G5. Report contract mismatches as CRs to Manuel's codex (transport) or Hagen's codex (route content).

## 9. Completion report

SHA; device matrix; timings; what still uses fixtures; next: C03.

## 10. Blocked-work behaviour

No WebSocket yet: poll `GET /api/buildings/{id}` version every 2 s behind a flag so G4 can still be demonstrated; remove the poll when WS works. No voice: text chat sheet with the same suggestions.
