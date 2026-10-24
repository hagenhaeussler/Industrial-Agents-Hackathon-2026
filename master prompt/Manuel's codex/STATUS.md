# STATUS: Manuel's codex (Platform & Live Integration Lead, integration captain)
Last update: 2026-10-24 21:36 CEST · Branch: `manuel-codex/platform` · HEAD: M03 prerequisite checkpoint (this revision); M02 `5f63287` · Last sync with origin/main: `d46775f`

Single writer: Manuel's codex. Keep this structure (OWNERSHIP_AND_DEPENDENCIES §7).

## Current task
M02 repository implementation verified, awaiting integration gate with the complete core and frontend. External Railway/ElevenLabs setup is deferred by the human's repository-only instruction. M03 device-gate page and frame/arrow maths verified; AR rendering remains gated on G4 and physical-device results. Repository increments are ready for consumer integration.

## Delivered (newest first)
- M03 prerequisites: standalone /devtest page with local jsQR bundle; simultaneous camera/mic, QR, motion and XR probes with cleanup/cancellation; exact four-heading frame transform and direction-only arrow maths; Docker/check hooks. No AR route rendering or physical-device pass is claimed.
- `5f63287`: M02 implementation, C2 contracts, OpenAPI, voice bridge and labelled server fixtures.
- M02: SQLite schema 2 + v1 migration, durable sessions/tour revisions/proposals/events/markers/cache; idempotent commits, expiry/version checks, safe undo, immutable base replay, restart tests, per-building WebSocket events, phone handoff/progress/replan, all eleven shared tools, voice token + browser hook, chat adapter, marker sheets and opt-in demo reset. OpenAPI and server fixtures published with C2.
- Kit fallback is explicitly labelled in tool traces and provisional route geometry. Real H01 loader/resolver integration verified; exact H02 route/edit functions are consumed when published. Spatial queries and validated JSON upload return not_available until the needed core modules exist.
- `53eb592` (pushed): M01 server/Docker/checks/local README; `682441a`: root rules, environment and ignores.
- `917980c` (pushed within the initial dependency handoff): shared dependencies/lockfile and package exports. Added runtime httpx in M02 after production-only smoke exposed its dev-only omission.

## Interfaces exposed / changed
- Contract **C2**, additive CR-M-1: raw admin endpoints use `X-Session-ID`; phone progress accepts the same header to advance the caller; tours expose `mobility_profile` separately from cost profile. Tool names/required arguments unchanged. `server/README.md` contains integration details.
- HTTP: health/buildings/snapshots/events; sessions create/get/patch; tools; tours create/get/progress/replan; markers create/get/sheet; voice token; chat; demo reset. Plan import remains explicit not_available. `TYB_DEMO_MODE=true` required for reset (default off).
- `WS /ws/buildings/{id}`: hello, building_changed/reset, tour_opened/updated, 20 s heartbeat. Subscriber registration precedes version fetch; concurrent commits cannot fall through the handshake gap.
- `from server.tools import registry`: `json_schemas()` and `call(name, session_id, args)`; bound during app startup. Chat constructor is `ChatAgent(registry, session_provider)`.
- `web/app/src/voice/useBuildingVoice.ts`: agent/sessionId/onDisplay, status/isSpeaking/start/stop/sendContext, valid JSON result <=1500 chars and stable commit UUIDs. Claude mounts ConversationProvider and visible UI.
- `server/openapi.json` exported; Claude runs `bun run gen:api`. `fixtures/session.json`, `fixtures/events_close_lift.json` are explicitly labelled examples with real building IDs/geometry.
- Local: `uv run uvicorn server.app:app --port 8000`; `curl localhost:8000/health`; `curl localhost:8000/api/buildings/proc-factory-dev-003`; catalog dynamically reports 280 kit buildings.

## Merge log (captain)
| Window | Merged branches @ SHA | Checks | Tag | Deployed |
|---|---|---|---|---|
| Pre-G1 readiness | No main merge: complete core/evaluation gate pending | Platform green; partial H01 compatible | none | repository-only scope |

## Evidence
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
- Gate G1 remains pending Hagen's full evaluator/fixtures; do not mark it green from the partial 49a7e6b checkpoint. Exact route geometry/edit semantics require H02/H03; chat conversations require Lenard's ChatAgent.
- Latest fetch/read: Hagen 49a7e6b partial H01, Lenard 4db2d92 serializer/validator (30 owner-reported tests), Claude 78b0fde move/deps (STATUS still initial). Main remains d46775f. No gate tag or deployment claimed.

## Change requests
### CR-M-1: Explicit admin/phone session transport
- Contract sections: 7, 14; C1 -> C2 (additive).
- Change: X-Session-ID for raw admin endpoints and optional phone progress; mobility_profile handoff; demo opt-in; existing voice_unavailable token code documented.
- Why: prevent phone progress from advancing only the desk session, and make admin transport/types unambiguous.
- Migration: Claude sends phone progress header and regenerates API types. Eleven tool names unchanged.
- Status: accepted in C2 at `5f63287` (captain owns these sections); relay to Claude/Lenard before consumption.

## Next handoff
- Consumers Hagen, Lenard, Manuel's Claude: fetch platform branch; `5f63287` M02 live endpoints/OpenAPI/registry/voice hook/server fixtures are ready for integration.
- Next captain action at G1: read all four published STATUS files, merge ready increments in core -> server -> bench/agent -> web order, run scripts/check.sh and G1 acceptance, push main only when green; never force-push. No merge/deploy during recordings or sleep window.
- Physical G3/G4/G5, Railway release, real voice, phone device table, AR accuracy, Sunday rehearsal and submission remain future acceptance work, not completed claims.
