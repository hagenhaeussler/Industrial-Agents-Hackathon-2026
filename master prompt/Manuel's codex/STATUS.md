# STATUS: Manuel's codex (Platform & Live Integration Lead, integration captain)
Last update: 2026-10-24 22:02 CEST · Branch: `manuel-codex/platform` · HEAD: C5 checkpoint (this revision) · Last verified main: `0e892435d7a37e2b201bccc0f26e22c40358833c`

Single writer: Manuel's codex. Structure follows OWNERSHIP_AND_DEPENDENCIES §7.

## Current task
G1 and G2 passed, pushed to main and tagged. Continuing M02: reconcile concurrent core/platform C4 changes as C5, unblock L02 exact item lookup, and consume newly published C02 phone/C03 admin UI. G3/G4 still need integrated journey and chat/voice acceptance. Work remains repository-only per human steering.

## Delivered (newest first)
- C5 / CR-L-3: find compares resolution stage before numeric score across assets/spaces. Exact ID, name/ref/label and normalized matches beat fuzzy scores; true ambiguity and number safety remain. The CNC exact/fuzzy collision was reproduced before the fix;16 actual-core/kit regressions pass.
- C5 / CR-L-2: consumed Hagenb57d39f (codeb2b8ddd) closure-list compatibility and fixed-order recovery. Spatial transport passes all validated live/session/explicit closures, including []; original benchmark string inputs remain supported. Reopened fixed stops regain their prescribed sequence in both engines; collected identity remains.28 mobility/closure tests and4 HTTP recovery tests pass.
- G2 pushed/tagged at0e89243: verified145-row submission, platform1a5c491, core6452bda, benche1c2dfd; integrated checks passed. G1 remains8baa2c6. Normal HEAD:main pushes from the clean detached integration worktree; human checkout untouched.
- C4 / CR-L-1: affirmative step-free mobility and route width persist atomically in shared sessions, including valid no_route outcomes. Invalid/ambiguous requests do not mutate state; concurrent tools preserve each other's constraints.
- d55d0ac / CR-H-2: core.replan and labelled kit fallback retarget moved pending parts by identity, split/merge destinations without losing stop IDs and preserve collected stops. Eight HTTP regressions cover both engines. Blocked optional end destinations report honestly and recover after reopening.
- 1a5c491 / CR-H-3: production Docker context excludes evaluation questions/answers/templates and submissions; retains building JSON/equipment/manifest. Docker web stage includes demo/scenario.json.
- M02 (5f63287 and follow-ups): durable SQLite schema2, sessions/tour revisions/proposals/events/markers/cache; idempotency/conflicts/expiry/undo, per-building WS, phone handoff/progress/replan, eleven tools, voice token/hook, chat adapter, marker sheets, validated JSON upload, opt-in reset; OpenAPI/labelled fixtures published.
- M03 prerequisites (d187ce5): /devtest with bundled QR scanner, camera/mic/motion/XR probes/cleanup, four-heading frame transform and arrow math. AR rendering stays after G4/device evidence.
- M01:53eb592 server/Docker/checks/README;682441a root rules/environment;917980c dependency/lockfile handoff within ten minutes. Runtime httpx included after production smoke exposed its dev-only omission.

## Interfaces exposed / changed
- Contract **C5** reconciles concurrent C4 core/platform changes, preserving C2 transport/C3 geometry. Eleven names/required arguments unchanged. server/README.md describes mobility, closure lists and match precedence; server/openapi.json exported as C5.
- Python registry: `from server.tools import registry`; json_schemas() and call(name,session_id,args), bound at startup. Chat constructor: ChatAgent(registry,store.get_session).
- HTTP: health/buildings/snapshots/events, sessions, tools, tours/progress/replan, markers/sheets, voice token, chat, opt-in demo reset. Admin and optional phone progress use X-Session-ID. Plan import remains explicit not_available.
- WS /ws/buildings/{id}: hello, building_changed/reset, tour_opened/updated,20s heartbeat; subscription before version fetch prevents handshake loss.
- Voice hook useBuildingVoice({agent,sessionId,onDisplay}), status/isSpeaking/error/start/stop/sendContext, valid JSON <=1500chars and stable commit UUIDs. Claude mounts ConversationProvider/visible UI.
- Local: `uv run uvicorn server.app:app --port 8000`; `curl localhost:8000/health`; /api/buildings/proc-factory-dev-003. Catalog280buildings. Claude runs `bun run gen:api`.

## Merge log (captain)
| Window | Merged branches / main SHA | Checks | Tag | Deployment |
|---|---|---|---|---|
| G2 | platform1a5c491 + core6452bda + benche1c2dfd -> **0e892435d7a37e2b201bccc0f26e22c40358833c** |250Python,oracle369/369,devtext138/138,39Bun,build; independent officialdev138/138 and CSVvalidator|gate-G2|repository-only|
| G1 | core4e6f956 (platformd187ce5/bench4d93bdb) + webe29fc43 -> **8baa2c65b1bda13b1596e28c652aaa6f41a00e99** |214Python,oracle369/369,devtext138/138,structureddev138/138/train517/517,39Bun,build,health/fixtures|gate-G1|repository-only|

## Evidence
- C5 fullcheck exit0:275Python tests (27.22s),oracle369/369,coredevtext138/138,39Bun,strictTS/Vite/device-gate build. All113server tests pass;44find/mobility pass. CNC stage precedence and two kit reopening cases failed before their fixes. Log /private/tmp/tyb-c5-platform-check.log. Read-only independent review found no actionable issues.
- G2 exactmain0e89243: `env -u ANTHROPIC_API_KEY scripts/check.sh` exit0;250Python,oracle369/369,coredevtext138/138,39Bun,strictTS/Vite/device-gate build. Log /private/tmp/tyb-g2-main-check.log.
- G2 CSV:145uniqueIDs/145rows,exact question_id/answer columns,6337bytes, validatorpasses; SHA256 d3b026e88822e9697b9b02b724f29bef08c5e01129afe5c3e7b3e2467231e89f. Independent officialdev138/138; per-kind counts match BENCHMARK.md. Hidden test accuracy unknown. Reports agent_output/reports/g2/{summary.json,official-dev.log,csv-integrity.json}.
- Production C4 image tyb-g2 sha256:c1c6db70b7d3c43b32885c9292215e7862d10ba6db927c17815a2be34b0bc381 (129937751bytes,linux/arm64): frozen build/empty-volume smoke pass. Runtime280buildingJSON+280equipmentCSV+manifest; zero evaluationJSON/JSONL/answer/templateCSV/PNG/SVG, submissions absent. API/SPA/devtest200, actualcore geometry/pointarrays. Closure/replan77.6/80.2/91.4ms; doublecommitoneevent; mobilitypersists on no_route; restartretainsphone/tour/collected/events. Reports agent_output/reports/g2/{production-smoke.json,docker-build.log,runtime-check.log,container.log}. Container/tempstate removed, image retained. LocalAPI timings only.
- Earlier C01 browserQA (actualcore,no mocks):3parts->108.87mtour,83ms to routeDOM; renderedQR decoded exactly; phone-emulated tab same3stops165ms; desk Opened on phone; desktop1280x800/mobile390x844 nooverflow. /private/tmp/tyb-live-journey-report.json. C01 lacked phoneprogress/reroute; new C02 needs separate proof.
- G1 exact8baa2c6: frozen uv/Bun installs/fullcheck, independent structureddev138/138/train517/517; health exactSHA/280buildings, factory79spaces/505assets, requiredfixtures. Logs ../tyb-main/agent_output/reports/g1/.
- Remote main/gate-G2 verified at0e89243; gate-G1 remains8baa2c6. No forcepushes, paid/provider calls or kit edits.
- M03 helpers:15Bun tests,strictTS/bundle,desktop/mobile-emulated smoke pass; unsupportedXR honest; Stopcleanup passes. Actual device camera/mic/motion, models and AR accuracy unverified.

## Blockers and resource requests
- Human steering: “just do all in the repo — elevenlabs agents will be implemented.” No external setup/access follow-ups. This captain has not deployed externally or verified voice/physical phones.
- Latest fetched/read: Hagenb57d39f consumed (closure-list/fixed-order); Lenardee38da7 consumed (L02 exactlookupCR; ChatAgent not published); Claude11a2962 published (C02phone/C03admin/desk localsearch), held for integration verification of blocked-stop/reconnect/mobility cases.
- G3 chat/voice find awaits Lenard's published ChatAgent/provider configuration. G4 needs integrated phone reroute trials and physical acceptance. G5/device/AR/Sundayrelease remain future gates.
- Venue H6 measurements absent; validated factory fallback available. No invented venue/measurement claims.

## Change requests
- CR-L-3 accepted C5: stage precedence across kinds; realCNC,ambiguity,number-safety regressions.
- CR-L-2 accepted C5: complete live closure lists consume core owner's §4support. Replaces C4 isolated-copy/singular-string bridge; benchmark inputs preserved.
- CR-L-1 accepted C4: atomic affirmative mobility/width persistence; no invalid-request mutation.
- CR-H-2 accepted d55d0ac: core replan delegation/moved-part recovery;8HTTP regressions.
- CR-H-3 accepted1a5c491: production data whitelist inspected in runtime image.
- CR-M-1 accepted C2 at5f63287 (§7/14): explicit X-Session-ID admin/phone transport and mobility_profile. Claude regenerates types; eleven tool names unchanged.

## Next handoff
- Lenard: fetch C5 platform for CR-L-1/2/3; publish L02 against registry.call/json_schemas(). No provider calls without authorization.
- Claude: consume C5 OpenAPI and regenerate types. Captain integrating published C02/C03, then checks phone confirmation/progress/reconnect/reroute and admin confirm/undo against actualcore.
- Captain: finish C5fullcheck, push platform, merge ready dependencies/web in clean integration worktree, check and pushmain. Preserve G1/G2 tags; do not tag G3/G4 until demonstrated.
- Physical devices/realvoice/Railwayrelease/ARaccuracy/Sundayrehearsal/finalsubmission remain outstanding acceptance work.
