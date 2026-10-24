# Integrated project readiness

Scope: the four builder prompt folders under `master prompt/`, checked against
the integrated implementation. This is an evidence checklist, not a claim that
every physical-demo or submission gate has passed. The human selected the factory
fallback until venue measurements are available.

The [shared preview](https://hagen-core-test-testing.up.railway.app/desk?demo=hero)
is available for coworkers. [How to use it](team-preview.md) and the
[human steps for the remaining inputs](human-handoff.md) are separate guides.
The release PR records the exact final SHA, deployment ID and cloud smoke results.

## Prompt coverage

| Prompt | Integrated result | Remaining acceptance |
|---|---|---|
| H01 core port | All 15 question kinds; dev structured 138/138, train structured 517/517; dev text 138/138; unchanged kit oracle 369/369 | Unseen organizer data cannot be certified in advance |
| H02 geometry/tours | 269 dev routes and 1,232 walks checked, zero geometric failures/fallbacks; exact tour order through 12 stops, labelled heuristic above 12; profiles/closures/final leg | Physical directions/landmarks reviewed on the actual venue |
| H03 edits/validation/hero | Pure preview/commit/undo/what-if; authenticated upload; all 280 kit buildings validate with zero errors (242 warnings); factory closure scenario works | Venue measurements/objects/marker coordinates (factory fallback chosen) |
| H04 plan import spike | Measured SVG draft import on three dev floors, explicit scale/correction needs | “Mention only”; arbitrary raster/PDF reconstruction and a production plan-import UI are cut |
| L01 benchmark submission | Official dev 138/138; generated 145-row test CSV validates and matches committed output | Final release/unseen-file generation and organizer upload |
| L02 chat/voice | Real text chat, guarded edits, skills and two configured authenticated ElevenLabs agents; four provider tool-choice tests | Human microphone/client-tool roundtrip and three-model spoken A/B; tokens alone do not pass these |
| L03 robust fallback | Fixed live strict-grammar failure; small provider envelope with unchanged typed solver validation; all 77 live cases pass, cache reads observed | Controlled model A/B is not established by conditional escalation statistics |
| L04 Sunday adapter | 15-question dev-as-unseen rehearsal, zero errors; seven reference route legs match | Actual Sunday building, final organizer schema/runtime/output requirements |
| M01 scaffold/deploy | One-process FastAPI, production Dockerfile, persistent Railway volume, HTTPS preview; automated Linux/Docker rehearsal added | Exact release run recorded by CI and final deployment PR |
| M02 live integration | SQLite events/sessions/tours, shared tools, WebSockets, idempotence, conflicts, undo, restart/reset-safe state identity and voice bridge | Real rendered devices/audio remain separate |
| M03 camera/device gate | Device gate, direction-only camera UI, experimental marker-confirmed Android WebXR ribbon, denial/cancel/background fallbacks | Android/iPhone permission tests, real alignment/drift and 10 m walk; omit unproven AR from pitch |
| M04 release/submission | Integrated release checks, secret-free voice exports, attribution, local/run/deploy docs and Sunday commands | Final freeze, recordings and account-holder submission confirmation |
| C01 desk | Real buildings/parts, search and multi-select, profile/start/end, tour map, QR handoff, route previews, spatial highlights and calculation traces | Human usability/physical QR timings |
| C02 phone | Confirmed/manual/marker start, map/directions/progress/reload, replan, explicit final arrival, reset-aware freshness, voice fallback | Real Android/iPhone journey, network and timing checks |
| C03 admin/polish | Private-code gate, preview/confirm/undo, validation/upload, event/calculation traces, honest factory scenario | Human accessibility/device review and rehearsed spoken edit |
| C04 hardening/stretch | Camera integration, lifecycle regressions and updated honest demo script | Record the two required videos; optional 3D/simulated live tracking is cut |

## Evidence and limits

Final local combined check: **491 Python tests, 159 frontend tests / 614 assertions**, unchanged oracle369/369, dev text138/138, strict TypeScript/Vite production build and device bundle all pass. Real HTTP/WebSocket/restart/reset verification passes; three local commit-to-replan trials took102–158ms. These are local API timings, not physical-device measurements.

`scripts/check.sh` now enforces offline provider configuration even when a developer has a live `.env`.

Core checks were rerun on 24 October 2026: structured 655/655 across dev/train,
all 280 building validations, and 269 geometric route checks. Reports are in ignored
`agent_output/reports/core/swarm-*`.

Live fallback verification covers 48 authored paraphrases across all 15 kinds,
17 original benchmark questions and 12 warm-up questions: **77/77**. It cost
$0.14880213 by the application's conservative meter, plus a $0.000162525 schema
diagnostic. There were 681,072 cache-read input tokens. These are dev measurements,
not proof of unseen-building accuracy. Full commands, source hash, per-kind and
model results and the failed-before-generation diagnostic are in `BENCHMARK.md`.

The button-driven factory tour was observed on the public preview: three stops
across two floors, 97 m, planned in 369 ms. Prior live text lookup/route responses took
about 5–7 seconds. The less-than-three-second spoken-route target is **not certified**.
Token exchanges and mocked provider tool execution do not demonstrate microphone
audio or the browser's real tool roundtrip.

The shared smoke budget remains the human-authorized **$5 total** across all
turns. Previous cloud allocation is conservatively retained; no redeploy grants
a new allocation. The next preview process has a $0.50 chat cap. Voice agents have
60-second/two-per-day limits each. This is a bounded test configuration; unrestricted
coworker voice/chat usage needs a deliberate shared budget decision.

## What humans still need to do

1. Run the factory preview on an Android phone and an iPhone; record QR/progress,
   closure/undo, offline recovery and denied-permission outcomes and timings.
2. Verify a real microphone/client-tool exchange, then coordinate the spoken
   model comparison within the remaining budget.
3. If the demo should represent the venue, supply measured rooms/doors/connectors,
   floor elevations and actual objects; then calibrate and print matching markers.
4. Supply the organizers' actual unseen files and confirmed output/deadline rules.
5. Rehearse the pitch, record the demo/technical videos, upload the final artifacts
   and verify the submission remotely.

Follow [human-handoff.md](human-handoff.md) step by step. Until then, use the
factory on screen, Map/Directions as the reliable guidance path, JSON as the
reliable new-building import, and the validated deterministic benchmark path.
