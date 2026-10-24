# STATUS: Manuel's codex (Platform & Live Integration Lead, integration captain)
Last update: 2026-10-24 22:06 CEST · Branch: `manuel-codex/platform` · HEAD: C6 checkpoint (this revision) · Last verified main: `a8be9ec54bdb2514e98776f9449484735af44f81`

Single writer: Manuel's codex. Structure follows OWNERSHIP_AND_DEPENDENCIES §7.

## Current task
G1 and G2 passed, pushed to main and tagged. The C5 follow-up is also on main at `a8be9ec`. Continuing M02 with C6 explicit replan constraints for the deliberate stairs action. The latest web branch is held for proved blocked-route and reconnect failures; precise handoff requests are below. G3/G4 remain pending the integrated journey and chat/voice acceptance. Work is repository-only per human steering.

## Delivered (newest first)
- C6 / CR-M-4: optional partial replan constraints replace only explicitly supplied fields. Deliberate stairs choice retains tour identity, collected stops, order, widths and exclusions. Missing/null/empty overrides preserve existing behavior; wheelchair/pram/trolley profiles still enforce step-free routing. Invalid overrides return 422 without mutation. **30 new core/kit HTTP tests and all 143 server tests pass.**
- C5 / CR-L-3 at `4d48930`: exact ID, name/ref/label and normalized find matches precede fuzzy scores across assets/spaces. The reported CNC collision was reproduced before fixing it. Sixteen actual-core/kit tests preserve true ambiguity and number safety.
- C5 / CR-L-2: consumed core `b57d39f` (code `b2b8ddd`). Spatial transport passes the complete validated live/session/explicit closure list, including []; benchmark strings remain supported. Reopened fixed stops regain their prescribed sequence in both engines, with collected identity retained. Platform published at `e40e780`; main at `a8be9ec`.
- G2: verified 145-row submission, platform `1a5c491`, core `6452bda`, bench `e1c2dfd`; green integrated main `0e89243` pushed and tagged. G1 stays at `8baa2c6`. All pushes use the clean detached integration worktree; the human checkout remains untouched.
- C4 / CR-L-1: affirmative step-free mobility and route width persist atomically in shared sessions, including valid no_route outcomes. Invalid/ambiguous requests do not mutate state; concurrent tools preserve each other's constraints.
- `d55d0ac` / CR-H-2: core.replan and labelled kit fallback retarget moved pending parts by identity, split/merge destinations without losing stop IDs, and preserve collected stops. Eight HTTP regressions cover both engines. Blocked optional end destinations report honestly and recover after reopening.
- `1a5c491` / CR-H-3: production context excludes evaluation questions, answer/template CSVs and submissions; retains building JSON, equipment and manifest. Docker web stage includes demo/scenario.json.
- M02 (`5f63287` and follow-ups): durable SQLite schema 2; sessions, tour revisions, proposals, events, markers/cache; idempotency, conflicts, expiry and undo; per-building WS; phone handoff/progress/replan; eleven tools; voice token/hook; chat adapter; marker sheets; validated JSON upload; opt-in reset; exported OpenAPI and labelled fixtures.
- M03 prerequisites (`d187ce5`): /devtest with local QR scanner, camera/mic/motion/XR probes and cleanup; four-heading frame transform and arrow math. AR rendering remains after G4 and device evidence.
- M01: `53eb592` server/Docker/checks/README; `682441a` root rules/environment; `917980c` dependency handoff within ten minutes. Production smoke also led to including httpx as a runtime dependency.

## Interfaces exposed / changed
- Contract **C6** adds optional partial `constraints` to POST tour replan. It preserves C2 transport, C3 geometry, C4 mobility and C5 resolution/closure semantics. Eleven tool names and required arguments are unchanged. See server/README.md and exported server/openapi.json.
- To deliberately allow stairs: PATCH the session to profile=walk with existing constraints plus step_free=false, then replan with constraints:{step_free:false}. Check both responses. Replan changes the saved tour, preserves unspecified constraints, and does not mutate session mobility.
- Python registry: `from server.tools import registry`; json_schemas() and call(name, session_id, args), bound at startup. Chat constructor: ChatAgent(registry, store.get_session).
- HTTP covers health/catalog/snapshots/events, sessions, tools, tours/progress/replan, markers/sheets, voice token/chat and opt-in demo reset. Admin and phone progress use X-Session-ID. Plan import remains explicit not_available.
- WS /ws/buildings/{id}: hello, building_changed/reset, tour_opened/updated, 20 s heartbeat; subscription precedes version fetch. Reconnect must compare snapshot/tour building versions and replan if stale; GET tour returns stored state.
- Voice hook useBuildingVoice({agent, sessionId, onDisplay}) exposes status/isSpeaking/error/start/stop/sendContext, valid JSON <=1500 chars and stable commit UUIDs. Claude mounts ConversationProvider and visible controls.
- Local: `uv run uvicorn server.app:app --port 8000`; `curl localhost:8000/health`; /api/buildings/proc-factory-dev-003. Catalog has 280 buildings. Claude regenerates types with `bun run gen:api`.

## Merge log (captain)
| Window | Merged branches / main SHA | Checks | Tag | Deployment |
|---|---|---|---|---|
| C5 follow-up | core b57d39f + platform e40e780 + bench ee38da7 -> **a8be9ec54bdb2514e98776f9449484735af44f81** | 275 Python; oracle 369/369; dev text 138/138; 39 Bun; production build | G1/G2 preserved | repository-only |
| G2 | platform 1a5c491 + core 6452bda + bench e1c2dfd -> **0e892435d7a37e2b201bccc0f26e22c40358833c** | 250 Python; oracle 369/369; dev text 138/138; 39 Bun; build; official dev and CSV validation | gate-G2 | repository-only |
| G1 | core 4e6f956 (platform d187ce5, bench 4d93bdb) + web e29fc43 -> **8baa2c65b1bda13b1596e28c652aaa6f41a00e99** | 214 Python; oracle 369/369; dev text 138/138; structured dev 138/138, train 517/517; 39 Bun; build/health/fixtures | gate-G1 | repository-only |

## Evidence
- C6 full check exit 0: **305 Python tests** (33.32 s), oracle **369/369**, core dev text **138/138**, **39 Bun**, strict TS/Vite/device-gate build. All 143 server tests pass, including 30 new replan tests. The original HTTP regression rejected constraints with 422 before the fix. Independent review found no actionable issue. Log: /private/tmp/tyb-c6-platform-check.log.
- C5 exact main `a8be9ec`: `env -u ANTHROPIC_API_KEY scripts/check.sh` exit 0: **275 Python tests** (27.19 s), oracle **369/369**, core dev text **138/138**, **39 Bun**, strict TS/Vite/device-gate build. Log /private/tmp/tyb-c5-main-check.log. Independent source review found no actionable issues.
- Web review at `11a2962`: actual factory/core payloads and the remote guidance module prove the failures below. Reports in agent_output/reports/c02-review/ include review.md, payloads.json, reconnect.json and the rerunnable guidance proof. These are real local API/module checks; no providers or physical phones.
- G2 exact main `0e89243`: full check passed (250 Python, 39 Bun and evaluations/build above); /private/tmp/tyb-g2-main-check.log. CSV has 145 unique IDs/rows, exact question_id/answer columns, 6337 bytes; validator passes; SHA256 `d3b026e88822e9697b9b02b724f29bef08c5e01129afe5c3e7b3e2467231e89f`. Independent official dev: 138/138, per-kind counts match BENCHMARK.md. Hidden test accuracy unknown. Reports: agent_output/reports/g2/{summary.json,official-dev.log,csv-integrity.json}.
- Production C4 image tyb-g2 `sha256:c1c6db70b7d3c43b32885c9292215e7862d10ba6db927c17815a2be34b0bc381` (129937751 bytes, linux/arm64): frozen build and empty-volume smoke pass. Runtime has 280 building JSONs, 280 equipment CSVs and manifest; zero evaluation JSON/JSONL, answer/template CSVs, PNG/SVG or submissions. API/SPA/devtest return 200; actual geometry/point arrays verified. Local closure/replan trials: 77.6/80.2/91.4 ms. Duplicate commit produces one event; mobility persists on no_route; restart retains phone/tour/collected/events. Reports: agent_output/reports/g2/{production-smoke.json,docker-build.log,runtime-check.log,container.log}. Container/temp state removed; image retained.
- Earlier C01 browser QA: actual core, three parts -> 108.87 m tour, 83 ms to route DOM; rendered QR decoded exactly; phone-emulated tab showed the same three stops in 165 ms; desk showed Opened on phone; desktop/mobile had no overflow. /private/tmp/tyb-live-journey-report.json. C01 lacks the newly published C02 behaviors, which require separate acceptance.
- G1 exact `8baa2c6`: frozen installs and full check; structured dev 138/138 and train 517/517; health reports exact SHA and 280 buildings; factory has 79 spaces/505 assets; required fixtures verified. Logs: ../tyb-main/agent_output/reports/g1/.
- Remote main verified at `a8be9ec`, gate-G2 at `0e89243`, gate-G1 at `8baa2c6`. No force pushes, paid/provider calls or kit edits.
- M03 helpers: 15 Bun tests, strict TS/bundle and desktop/mobile-emulated smoke pass. Unsupported XR is reported honestly; Stop cleans up. Actual device camera/mic/motion, device models and AR accuracy remain unverified.

## Blockers and resource requests
- Human steering: “just do all in the repo — elevenlabs agents will be implemented.” No external setup/access follow-ups. This captain has not deployed externally or verified live voice/physical phones.
- Latest consumed owner checkpoints: Hagen `b57d39f` and Lenard `ee38da7`. Lenard's ChatAgent is not published. Web `11a2962` is held for the proved C02 issues below; its owner STATUS also needs the current tip/contract/evidence.
- G3 find via chat/voice awaits L02/provider configuration. G4 needs the corrected integrated phone reroute journey and physical acceptance. Venue H6 measurements remain absent; use the validated factory fallback.

## Change requests
- **CR-M-2 to Manuel's Claude — blocked routes/reconnect, web11a2962:** guidance.ts:6–8,29–33 derives pending only from reachable tour.order. Actual wheelchair A00021→A00325 lift closure returns status=blocked, order=[], pending UPS retained in stops and blocked_by_closure in unreachable_stops; the real module says “Office lift is closed. New route (-80 m).” Include unreachable pending stops/reasons. Journey.tsx:155–157 only GETs snapshot/stored tour on reconnect; proved snapshot version1 alongside stored tour version0 still using the closed lift. Replan from the latest position when snapshot version exceeds tour version; preserve request/revision guards. Needed before C02 merge/G4.
- **CR-M-3 to Manuel's Claude — voice display:** Journey.tsx:37 omits onDisplay; the callback at206–209 reaches only text ChatSheet. Wire voice find/route/plan display through the shared handler. Admin voice slot remains empty. Update owner STATUS to the actual C02/C03/desk-search tip and tested contract.
- **CR-M-4 accepted C6 (§7), to Manuel's Claude:** explicit stairs action must PATCH profile=walk with existing constraints plus step_free=false, then replan with constraints:{step_free:false}; check both responses. Omitted overrides preserve mobility; non-walk profiles still force step-free routing. Consume only after this C6 increment is pushed.
- CR-L-3 accepted C5: stage precedence across kinds; real CNC, ambiguity and number-safety regressions.
- CR-L-2 accepted C5: complete closure lists consume the core owner's §4 support. Replaces C4 singular-string bridge; benchmark strings remain valid.
- CR-L-1 accepted C4: atomic affirmative mobility/width persistence; invalid requests do not mutate state.
- CR-H-2 accepted `d55d0ac`: core replan delegation/moved-part recovery; eight HTTP regressions.
- CR-H-3 accepted `1a5c491`: production whitelist inspected inside runtime image.
- CR-M-1 accepted C2 at `5f63287` (§7/14): explicit admin/phone X-Session-ID and mobility_profile; eleven tool names unchanged.

## Next handoff
- Lenard: fetch C5/C6 platform for CR-L-1/2/3; publish L02 against registry.call/json_schemas(). No provider calls without authorization.
- Claude: fix CR-M-2/3 and consume C6 CR-M-4; regenerate API types. Captain will recheck phone confirmation/progress/reconnect/reroute and admin confirm/undo against the actual core.
- Captain: finish C6 full check and production verification, push the platform increment, merge/check/push main. Keep G1/G2 tags; do not tag G3/G4 until demonstrated.
- Physical devices, real voice, Railway release, AR accuracy, Sunday rehearsal and final submission remain outstanding acceptance work.
