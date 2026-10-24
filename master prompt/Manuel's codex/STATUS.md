# STATUS: Manuel's codex (Platform & Live Integration Lead, integration captain)
Last update: 2026-10-24 21:55 CEST · Branch: `manuel-codex/platform` · HEAD: G2/C4 checkpoint (this revision) · Last sync with origin/main: `8baa2c6` (G1 pushed)

Single writer: Manuel's codex. Keep this structure (OWNERSHIP_AND_DEPENDENCIES §7).

## Current task
G1 passed/pushed/tagged at `8baa2c6`. G2 benchmark verification is green; final integrated production check before main/tag. M02 C4 mobility/closure transport, moved-part recovery and optional-end recovery are implemented and verified. Local live desk/QR handoff passes; G3/G4 remain pending C02 phone journey and chat/voice/provider acceptance. No external deploy or AR rendering claimed.

## Delivered (newest first)
- C4/CR-L-1/2: persistent affirmative session mobility and route width, atomic merges across concurrent tools; zero/single/multiple closure handling without changing benchmark input schema; candidate names compatible with UI chips. **25 new mobility/tool tests pass**; existing eleven names/required arguments unchanged.
- Blocked optional end is reported as blocked even after collection finishes; core and kit HTTP closure/reopening recovery verified. Current **90 server tests**, **250 integrated Python tests**, **39 Bun tests** pass.
- CR-H-3: production Docker context excludes evaluation question JSON/JSONL, answer/template CSVs and submissions; keeps building JSON, equipment and manifest. Latest core `6452bda` and G2 bench `e1c2dfd` consumed.
- G1 captain integration: core `4e6f956` (already containing platform `d187ce5`, bench `4d93bdb`, web `de81877`) plus current web `e29fc43`; main and gate-G1 verified remotely at `8baa2c6`. Used a regular `HEAD:main` push from the prescribed detached clean integration worktree; the human checkout/main branch was not switched or overwritten.
- CR-H-2 fixed in this checkpoint: real-core and kit replan retarget moved pending parts by identity, preserve collected stops, split/merge rooms without losing stop IDs, and progress follows current inventory. Original HTTP400 regression reproduced before fix; 8 new HTTP tests + all63server tests pass.
- C3 OpenAPI now describes geometry_length_m, fallback, point endpoints as coordinate pairs, and building_closed; find display adds asset_ids/floor_id for Claude's live UI; Docker web stage includes demo/scenario.json.
- M03 prerequisites: standalone /devtest page with local jsQR bundle; simultaneous camera/mic, QR, motion and XR probes with cleanup/cancellation; exact four-heading frame transform and direction-only arrow maths; Docker/check hooks. No AR route rendering or physical-device pass is claimed.
- `5f63287`: M02 implementation, C2 contracts, OpenAPI, voice bridge and labelled server fixtures.
- M02: SQLite schema 2 + v1 migration, durable sessions/tour revisions/proposals/events/markers/cache; idempotent commits, expiry/version checks, safe undo, immutable base replay, restart tests, per-building WebSocket events, phone handoff/progress/replan, all eleven shared tools, voice token + browser hook, chat adapter, marker sheets and opt-in demo reset. OpenAPI and server fixtures published with C2.
- Kit fallback is explicitly labelled in tool traces and provisional route geometry. Real H01 loader/resolver integration verified; exact H02 route/edit functions are consumed when published. Spatial queries and validated JSON upload return not_available until the needed core modules exist.
- `53eb592` (pushed): M01 server/Docker/checks/local README; `682441a`: root rules, environment and ignores.
- `917980c` (pushed within the initial dependency handoff): shared dependencies/lockfile and package exports. Added runtime httpx in M02 after production-only smoke exposed its dev-only omission.

## Interfaces exposed / changed
- Contract **C4** (C2 transport/C3 core semantics preserved), additive CR-M-1: raw admin endpoints use `X-Session-ID`; phone progress accepts the same header to advance the caller; tours expose `mobility_profile` separately from cost profile. Tool names/required arguments unchanged. `server/README.md` contains integration details.
- HTTP: health/buildings/snapshots/events; sessions create/get/patch; tools; tours create/get/progress/replan; markers create/get/sheet; voice token; chat; demo reset. Plan import remains explicit not_available. `TYB_DEMO_MODE=true` required for reset (default off).
- `WS /ws/buildings/{id}`: hello, building_changed/reset, tour_opened/updated, 20 s heartbeat. Subscriber registration precedes version fetch; concurrent commits cannot fall through the handshake gap.
- `from server.tools import registry`: `json_schemas()` and `call(name, session_id, args)`; bound during app startup. Chat constructor is `ChatAgent(registry, session_provider)`.
- `web/app/src/voice/useBuildingVoice.ts`: agent/sessionId/onDisplay, status/isSpeaking/start/stop/sendContext, valid JSON result <=1500 chars and stable commit UUIDs. Claude mounts ConversationProvider and visible UI.
- `server/openapi.json` exported; Claude runs `bun run gen:api`. `fixtures/session.json`, `fixtures/events_close_lift.json` are explicitly labelled examples with real building IDs/geometry.
- Local: `uv run uvicorn server.app:app --port 8000`; `curl localhost:8000/health`; `curl localhost:8000/api/buildings/proc-factory-dev-003`; catalog dynamically reports 280 kit buildings.

## Merge log (captain)
| Window | Merged branches @ SHA | Checks | Tag | Deployed |
|---|---|---|---|---|
| G1 (early green integration) | core4e6f956 + platformd187ce5 + bench4d93bdb + webe29fc43 -> **8baa2c6** | 214 Python; oracle369/369; devtext138/138; structureddev138/138,train517/517;39Bun; productionbuild; health+fixtures | `gate-G1` @8baa2c6 | repository-only scope |

## Evidence
- Final production image `tyb-g2`, `sha256:c1c6db70b7d3c43b32885c9292215e7862d10ba6db927c17815a2be34b0bc381`,129937751bytes,linux/arm64: frozenbuild and empty-volume smoke passed. Actual runtime data:280buildingJSON+280equipmentCSV+manifest; ZERO evaluationJSON/JSONL,answer/templateCSV,PNG/SVG; submissions absent. OpenAPIC4,realcoretourpointarrays,desk/devtest200. Closure/replan3trials77.6/80.2/91.4ms; duplicatecommitoneevent; C4wheelchair/width persists on no_route; restartkeepsphone/tour/collectedstop/3events. Container/tempstate removed. Evidence `agent_output/reports/g2/production-smoke.json`,docker-build.log,runtime-check.log,container.log.
- G2: strict validator passes; CSV145uniqueIDs/145rows,exact question_id+answer columns,6337bytes, SHA256 `d3b026e88822e9697b9b02b724f29bef08c5e01129afe5c3e7b3e2467231e89f` matches owner. Independent `env -u ANTHROPIC_API_KEY uv run python -m benchmark.evaluate data/dev --agent bench.agent:answer --name captain-g2-dev`: **138/138**, every per-kind count matches BENCHMARK.md. No hidden test accuracy claim. Evidence `agent_output/reports/g2/summary.json`, official-dev.log, csv-integrity.json.
- Current `env -u ANTHROPIC_API_KEY scripts/check.sh` exit0: **250 Python tests** (25.24s), oracle369/369, core devtext138/138, **39 Bun**, strict TS/Vite/devicegate build. Log `/private/tmp/tyb-g2-full-check.log`. Full server90passed; source whitespace clean; no paid calls.
- Real browser QA (headless Chrome, actual core API, no mocks): 3parts ->108.87m tour,83ms to route DOM; exact rendered QR decoded; phone same3stops in165ms, tour_start/low confidence; desk shows Opened on phone. Desktop1280x800/mobile390x844 nooverflow/blank/overlay; screenshots/report `/private/tmp/tyb-live-journey-report.json` and tyb-live-{desk-tour,desk-qr,phone-tour}.png. These are desktop emulation timings, not physical phone/Railway evidence.
- The same QA proved the C02 gap: committing a lift closure produced **zero phone replan requests**; C01 GoTour is read-only (no start confirmation/Got it/voice). Chat503 fallback was visible with no provider call. Do not mark fullG3/G4 green until owner integration and physical acceptance.
- G1 exact HEAD `8baa2c65b1bda13b1596e28c652aaa6f41a00e99`: `scripts/check.sh` exit0, **214 Python tests**, **369/369 oracle**, **138/138 dev text**, **39 Bun**, strict TS/Vite/devicegate build. Separate dev structured138/138 and train structured517/517. Frozen uv/Bun installs succeeded. Health200 reports exact SHA,280 buildings; factory snapshot79spaces/505assets and both C3fixtures verified. Logs: `../tyb-main/agent_output/reports/g1/summary.json`, check.log, dev-structured.log, train-structured.log, health-fixtures.json.
- `git ls-remote origin refs/heads/main refs/tags/gate-G1` returned **8baa2c65b1bda13b1596e28c652aaa6f41a00e99** for both. No force push.
- Current platform follow-up: **63server tests pass** (including 8actualHTTP moved-part regressions core+kit); source regression confirmed failing against previous _plan before fix. C3 endpoint schema mismatch identified by real UI QA and fixed to actual [x,y] pairs; schema export verified.
- M03 helper verification: **15 Bun tests**, strict TS, standalone local bundle, desktop 1100x850 and mobile 390x844 Playwright smoke passed (no horizontal overflow/page errors; unsupported XR reported honestly; Stop cleanup works). Camera/QR/microphone/motion permission and AR accuracy on actual phones remain pending H8.
- Docker restart: persisted phone session/active tour, collected stop, 3 events and building_version 3; container stopped and temporary contexts cleaned. Local image retained for reuse; commit unknown locally without RAILWAY_GIT_COMMIT_SHA.
- Final `scripts/check.sh`: **55 Python tests**, kit oracle **369/369**, **24 Bun tests** passed. Core.evaluate and full C01 build explicitly skipped in platform checkout because those packages remain on their builder branches. Log: `/private/tmp/tyb-platform-final-check.log`.
- Fresh Python recheck after runtime dependency fix: `pytest -q tests/server` **55 passed in 2.88 s**; Bun **24 pass / 0 fail**. No paid/provider calls.
- Three local HTTP commit -> WebSocket -> replan trials: **82.6 / 67.0 / 68.2 ms**. These are server/local test results, not phone/Railway timings.
- Actual published H01 `49a7e6b` archived into /tmp, with current platform: **58 server+core tests passed in 3.38 s**. Verified real core.Building load/hash/resolve seam; no branch/worktree mutation.
- Production Docker combined validation: current platform + published C01 `78b0fde` overlaid only in temporary context. Frozen Bun install, strict TS/Vite, voice/AR helper compilation and local jsQR device-gate bundle passed. Corrected image `sha256:3b762f26670aa7ee9f013efde8314a2c2c8c8b04e5916142a76c2a6d37ac1ce0`, **129,869,967 bytes**, linux/arm64.
- Docker smoke: health/catalog/snapshot/SPA/device-gate 200; missing voice/chat configuration 503; marker creation/get/12 cm printable sheet; desk->phone->progress->three close/open/close commits->WS->replan, stable collected stop, duplicate commit one event. Docker timings **63.9 / 65.0 / 75.5 ms**; external acceptance not implied.
- Regression coverage: four simultaneous commits -> one event; concurrent preview/tour revision guards; expiry; stale preview; admin role from session; dependent undo rejected without mutation; archived reset can reuse evt-1 safely across buildings/cache; persisted walks avoid cold recompute; malformed uploads 422; concurrent WS handshake commit caught; restart sessions/tours/events retained.
- `uv lock`, `uv sync`, runtime imports, whitespace checks passed. Kit files untouched; isolated platform + integration worktrees preserve the human checkout.

## Blockers and resource requests
- Human steering: “just do all in the repo — elevenlabs agents will be implemented.” No external setup/access follow-ups required now. Railway deploy, live voice and physical devices remain unverified.
- G1 resolved; real H02/H03 core now available on main. Chat conversations still require Lenard's ChatAgent and authorized provider configuration. C02 phone confirmation/progress/reroute UI is still in Claude's milestone.
- Latest fetch/read: Hagen6452bda (additional explicit stop-position fix, queued); Lenarde1c2dfd (verified145-row submission/BENCHMARK, queuedG2); Claudee29fc43 (C01 liveAPI). No deployment claimed.

## Change requests
- **CR-H-2 accepted:** fixed at `d55d0ac`; server delegates core.replan and preserves canonical updated stops. 8HTTP regressions +63server tests green.
- **CR-H-3 accepted/implemented:** evaluation JSON/CSV and submissions excluded from production Docker context; runtime image inspection verifies the whitelist.
- **CR-L-1 / CR-L-2 accepted/implemented in C4 §8:** affirmative mobility/width persists atomically; closure bridge honors all current IDs on isolated core copy and passes one required solver string. 25 tool regressions green; core/benchmark schema untouched.
### CR-M-1: Explicit admin/phone session transport
- Contract sections: 7, 14; C1 -> C2 (additive).
- Change: X-Session-ID for raw admin endpoints and optional phone progress; mobility_profile handoff; demo opt-in; existing voice_unavailable token code documented.
- Why: prevent phone progress from advancing only the desk session, and make admin transport/types unambiguous.
- Migration: Claude sends phone progress header and regenerates API types. Eleven tool names unchanged.
- Status: accepted in C2 at `5f63287` (captain owns these sections); relay to Claude/Lenard before consumption.

## Next handoff
- Claude: consume C4 OpenAPI (`bun run gen:api`), voice hook and C01 display compatibility; complete C02 start confirmation/progress/reconnect/replan/voice UI. Backend and actual desk/QR handoff verified; UI gap evidence above. Only Claude edits those UI paths.
- Lenard: C4 mobility/closure CRs resolved and tested; `registry.call`/`json_schemas()` ready for ChatAgent. Publish L02 when ready; provider-free stub tests do not establish live spoken/chat acceptance.
- Consumers Hagen, Lenard, Manuel's Claude: fetch platform branch; `5f63287` M02 live endpoints/OpenAPI/registry/voice hook/server fixtures are ready for integration.
- Next captain action: push this checked platform increment, merge into clean integration worktree, run scripts/check.sh there, push main and gate-G2 once green; preserve gate-G1. Full G3/G4 remains pending the specific owner/provider/device dependencies above.
- Physical G3/G4/G5, Railway release, real voice, phone device table, AR accuracy, Sunday rehearsal and submission remain future acceptance work, not completed claims.
