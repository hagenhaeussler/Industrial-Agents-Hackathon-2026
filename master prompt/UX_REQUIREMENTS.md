# UX requirements and traceability

Primary source: `Hagen UX explanation transcript.md` (recording 24 Oct 2026, 18:44, cleaned and non-verbatim; speaker attribution inferred by content). Timestamps below refer to that recording. Where the transcript is open, this file states a design decision and marks it as ours, not Hagen's.

**Persona:** Manfred, an assembler who is new to a building (or the building is new). He knows what he needs, not where it is, and does not know room numbers.

**Two experiences:** UX A on the laptop (desk planning; admin changes are a separate role on the same app), UX B on the phone (walking). Desk is not admin: edits require an admin session (CONTRACTS §6).

**The three aha moments** (human product focus) map to rows J2–J6: **Aha 1 "Say what you need, not where it is"** (J2–J3), **Aha 2 "From screen to hand"** (J4–J5), **Aha 3 "The building reacts"** (J6).

## 1. Traceability matrix

| ID | Source passage | User need | Interaction (decided here) | Data / tool / backend | Owner(s) | Acceptance evidence | Priority / fallback |
|---|---|---|---|---|---|---|---|
| J1 | 06:16–06:42, 08:33–09:08 "I am Manfred and come into a new building" | understand at once why the app helps; no room IDs needed | Landing `/` and `/desk?demo=hero` open the building with a one-line prompt "What do you need?" plus the parts list; demo mode preloads the scenario | `GET /api/buildings`, scenario file `demo/scenario.json` | Manuel's Claude | screenshot of first screen; a person unfamiliar with the app finds a part in < 20 s | P1 |
| J2 | 06:42–07:14 "model of the factory … parts list … select a part → model shows where it is" | see the building and the parts together; select → see location | Desk: 2D floor map (active floor solid, others ghosted, floor switcher) + searchable parts list grouped by room; clicking a part highlights it and its room, switches floor, shows "Torque wrench · Tool crib 0.21 · Ground floor" | snapshot `GET /api/buildings/{id}`; `find` tool; `resolve` | Claude (UI), Hagen (resolve), Manuel's codex (API) | Aha 1 timed: highlight < 1 s after click; voice/text "Where is the 3D printer?" highlights it | P1; 3D view only after G5 |
| J2b | 07:00–07:14 "parts may move a little … a small gimmick" | liveliness | Optional: a labelled "simulated" movement event moves an asset; the list updates | `move_asset` edit events | Claude, Manuel's codex | shown only with "Simulated" badge | P3 after G5; never claimed as tracking |
| J3 | 07:22–07:41 "several parts … like Amazon … optimal route for the whole task" | plan one collection task over many parts | Multi-select in the list (checkboxes) **or** say "I need the filament, the torque wrench and the steel drum"; stops appear numbered on the map; order and total length shown; "Optimal order" label (or "Good order (heuristic)" above 12 stops); "Keep my order" toggle; optional end destination | `plan_tour` (Held-Karp), TourResult §5; ambiguity → `ambiguous` with candidates | Claude (UI), Hagen (tour), Lenard (agent behaviour) | Aha 1: route drawn < 3 s after the request; ambiguous item ("the press") triggers exactly one question; unknown item ("coffee machine") is reported as not found, the rest still planned | P1; fallback click-only |
| J3b | (our decision) | know where the tour starts | Desk asks once "Where are you now?" (room picker, default the scenario start) and stores it in the session | session position `source: desk` | Claude, Manuel's codex | tour start shown as a "You" pin | P1 |
| J4 | 07:14–07:22 "a QR code appears, he scans it with the phone" | continue on the phone without retyping | "Send to phone" shows a QR of `https://<host>/go/<tour_id>`; the phone opens the same tour; the desk shows "Opened on phone" when the phone loads it | tour stored server-side; `GET /api/tours/{id}`; WS `tour_updated` | Claude, Manuel's codex | Aha 2: tour visible on the phone < 2 s after the scan, stops and order identical | P1; fallback: open the URL on a second laptop window |
| J4b | (our decision; prompt §4.4) | establish the phone's real starting position | Phone asks "Are you at Desk area 0.12?" → **Yes** / **Scan a position code** / **Choose my room**; the answer is spoken to the voice agent as context | session position `tour_start` (low) → `marker` (high) / `manual` (medium) | Claude, Manuel's codex | position source visible in the UI; no claim of automatic localization | P1 |
| J5 | 07:41–07:50 "map on the smartphone … to the first, second and third part" | follow understandable directions and see progress | Prototype layout kept: route banner (turn icon, instruction with landmark, metres), minimap with the real floor geometry and route, agent dock; step list; per-stop "Got it" (voice: "collected", "next"); progress "2 of 3 stops"; arrival state with the avatar's happy expression; guidance mode Map / Directions / Camera | RouteResult `maneuvers`, `segments`; `next_step`; `POST /api/tours/{id}/progress` | Claude (UI), Hagen (maneuvers), Lenard (navigator prompt) | instructions mention a landmark at least at every turn; route line never crosses a wall on the map (H02 check); progress survives a reload | P1 |
| J5b | prompt §4.5 | voice, map, camera and permissions interact predictably | One "Start navigation" button requests mic (+ camera/motion/XR only in Camera mode); voice speaks at most three steps then waits for "next"; any permission denial leaves the 2D map working with a clear message; losing tracking in AR shows "Scan the next position code" | voice bridge, camera module | Claude, Manuel's codex | permission-denied paths tested on both phones (M03 X0 log) | P1 for map/voice, P2 camera |
| J6 | 07:50–08:03 "a lift fails … the app notices … shows an alternative via the stairs … changes the route" | be told what happened and get a new way without losing progress | Admin on the laptop says "Close the east lift" (or clicks it on the map) → preview "Close East lift. 1 active tour affected: 84 m → 97 m via Stairs B" → "Yes" → phone mid-route: banner "East lift is closed. New route via Stairs B (+13 m)", spoken update, new line; collected stops stay ticked | `propose_edit` → `commit_edit` (idempotent) → event → WS → `replan` from current position | Hagen (edit semantics), Manuel's codex (events, WS), Claude (admin + phone UI), Lenard (admin prompt) | Aha 3: phone shows the new route ≤ 2 s after "Yes"; collected stops unchanged; double "Yes" commits once; undo restores and the phone replans again | P1; fallback: admin button instead of voice |
| J6b | prompt §4.6 | wheelchair must never silently get stairs | If the session profile is `wheelchair` and only stairs remain: "There is no step-free route to the store any more. The east lift was the only step-free way." Offer: "Show the route with stairs?" (explicit) | `reachable: false`, `reason`, `blocking_ids` | Hagen, Claude, Lenard | test scenario U6 below | P1 |
| J7 | 08:03 "he finds the part" | know the task is complete; handle exceptions | Completion screen "All 3 parts collected" with total distance; if a part is missing on arrival: "Not there" → admin can mark it moved (admin only) or skip; changed destination: tap another part → replan; interrupted session: reopening `/go/{id}` resumes at the next pending stop | tour progress, `move_asset`, replan | Claude, Manuel's codex | reload mid-tour resumes; "Not there" path ends in a clear state | P1 completion, P2 exceptions |
| J8 | 09:02–09:17 "new building … upload the floor plan … building appears with parts" | set up a new building quickly | **Stage 1 (mandatory):** admin uploads a `building.json` (+ optional `equipment.csv`), sees the validation report (rooms, doors, unreachable spaces as warnings), the building renders and every tool works — same path as the Sunday building. **Stage 2 (timeboxed):** upload a plan SVG/PNG → draft rooms/doors overlay → set scale (two points + known length) → correct → save; parts list added from CSV or by voice "add a 3D printer in room 0.21". A plan image never supplies asset identities or trustworthy scale by itself | `POST /api/buildings`, `validate_building`; `plan-import` (H04) | Hagen (validate, import), Manuel's codex (endpoints), Claude (admin UI) | Stage 1: a dev building uploaded as new answers `find` and `route`; Stage 2: measured on 3 dev floors (room count, area IoU, door graph) | Stage 1 P1; Stage 2 P3, cut if unmeasured |
| J9 | 05:39–06:03, 09:17–09:26 "UI details open, to be tried out" | the team iterates on the UI | Claude owns visual and interaction decisions within `DESIGN.md` | – | Claude | – | – |

## 2. Interaction quality requirements (25 interaction points)

| Need | Requirement | Evidence |
|---|---|---|
| Ask only what is needed | One clarifying question only when a required argument is missing or `resolve` is ambiguous; list ≤ 4 candidates with floor ("Which press: line 4 on the ground floor or line 7 on floor 1?") | voice/text regression utterances 4 and 6 |
| Show what was understood | Before routing: one line "From Lobby 0.01 to Tool crib 0.21, step-free"; before an edit: preview + explicit "yes" | utterances 3, 8, 9 |
| Directions people can follow | Landmarks and turn words first, room numbers second, floor changes explicit ("Take the Office lift to Floor 1"), distances rounded | maneuver texts reviewed on the hero building |
| Corrections and changed minds | "No, the other press" re-resolves without restart; "Actually skip the drum" removes a stop and replans | chat transcript in Lenard's STATUS |
| Honest failure | non-existent item, no route, voice unavailable, camera denied: each has a clear sentence and a working alternative | U5, U6, U9 |
| Edit safety | preview → confirm → commit once → undo; conflicts re-preview | M02 tests, U7 |
| Accessibility | keyboard access to list, map controls and dialogs; visible focus; 44 px targets; `prefers-reduced-motion` respected (Blobatar already does); text alternatives for the map (step list) | Claude's C03 checklist |
| Spoken interruption | user can interrupt the voice; a committed edit stays committed and is reported | utterance 7 |
| Readable maps | room labels at sensible zoom, active floor emphasis, route accent `#dcff58` with dark outline (DESIGN.md) | screenshots |

## 3. Acceptance scenarios (run at G3–G5 and G7)

| ID | Scenario | Pass |
|---|---|---|
| U1 | Desk: "Where is the 3D printer?" | part highlighted, floor switched, spoken/printed location |
| U2 | Desk: select three parts on two floors → plan | numbered stops, total length, "Optimal order", route animated < 3 s |
| U3 | Desk → QR → Android and iPhone open `/go/{id}` | same tour < 2 s; start confirmation shown |
| U4 | Phone: follow two steps, "Got it" at stop 1, reload the page | progress kept, next stop active |
| U5 | Phone: "Where is the coffee machine?" (absent) | clear "there is none", nothing invented |
| U6 | Phone in wheelchair profile; admin closes the only lift | "no step-free route" with reason; stairs offered only explicitly |
| U7 | Admin: "Close the east lift" → preview → "Yes" twice → "Undo" | one event, phone reroutes ≤ 2 s, undo reroutes back |
| U8 | Admin uploads a dev `building.json` as a new building | validation report; `find` and `route` work on it |
| U9 | Voice token endpoint returns 503 | text chat appears automatically with the same capabilities |
| U10 | Phone denies camera and microphone | 2D map and buttons still complete the tour |
| U11 | Network drop on the phone for 10 s during a reroute | reconnect, snapshot reload, latest route shown, no stale route applied |

## 4. Honest limits (say these in the pitch and README if asked)

- Position comes from confirmation, printed markers and manual progress. Between markers, only the Android AR session tracks motion; the iPhone overlay shows direction, not position.
- Part movement shown in the demo is simulated unless an admin moved the part.
- "Optimal" means shortest by the kit route model, exact up to 12 stops.
- Plan-image import, if shown, is a draft that needs scale and correction; JSON import is the reliable path.
- The voice agent's LLM runs inside ElevenLabs; every fact it states comes from our tools.
