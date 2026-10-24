# STATUS: Manuel's codex (Platform & Live Integration Lead, integration captain)
Last update: 2026-10-24 21:50 CEST · Branch: `manuel-codex/platform` · HEAD: integration follow-up (this revision) · Last sync with origin/main: `8baa2c6` (G1 pushed)

Single writer: Manuel's codex. Keep this structure (OWNERSHIP_AND_DEPENDENCIES §7).

## Current task
G1 passed and pushed to main at `8baa2c65b1bda13b1596e28c652aaa6f41a00e99`; `gate-G1` points to that exact checked commit. Continuing M02/C3 integration hardening, G2 submission review and local G3 journey checks. Physical G4/device acceptance remains pending; no AR rendering or external deploy is claimed.

## Delivered (newest first)
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
- Contract **C3** (C2 transport preserved), additive CR-M-1: raw admin endpoints use `X-Session-ID`; phone progress accepts the same header to advance the caller; tours expose `mobility_profile` separately from cost profile. Tool names/required arguments unchanged. `server/README.md` contains integration details.
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
- **CR-H-2 accepted:** fixed in this checkpoint; server delegates core.replan and preserves canonical updated stops. 8HTTP regressions +63server tests green.
- **CR-H-3 accepted:** exclude evaluation question/answer files from production Docker context; implementation/check next.
- **CR-L-1 / CR-L-2 accepted for C4 §8:** persist affirmative tool mobility settings; explicitly bridge the benchmark's singular closure input while honoring all current session closures on an isolated materialization. Implementing with regression tests; no core/benchmark schema change.
### CR-M-1: Explicit admin/phone session transport
- Contract sections: 7, 14; C1 -> C2 (additive).
- Change: X-Session-ID for raw admin endpoints and optional phone progress; mobility_profile handoff; demo opt-in; existing voice_unavailable token code documented.
- Why: prevent phone progress from advancing only the desk session, and make admin transport/types unambiguous.
- Migration: Claude sends phone progress header and regenerates API types. Eleven tool names unchanged.
- Status: accepted in C2 at `5f63287` (captain owns these sections); relay to Claude/Lenard before consumption.

## Next handoff
- Consumers Hagen, Lenard, Manuel's Claude: fetch platform branch; `5f63287` M02 live endpoints/OpenAPI/registry/voice hook/server fixtures are ready for integration.
- Next captain action: merge/recheck the M02 fixes, latest core stop-position fix and G2 submission; run the validator and independent official dev score, then push main and gate-G2 only when green. Continue local G3 journey evidence and request C02/voice consumer integration through published STATUS (human relay).
- Physical G3/G4/G5, Railway release, real voice, phone device table, AR accuracy, Sunday rehearsal and submission remain future acceptance work, not completed claims.
