# STATUS: Manuel's codex (Platform & Live Integration Lead, integration captain)
Last update: 2026-10-24 21:22 CEST · Branch: `manuel-codex/platform` · HEAD: dependency commit (this revision) · Last sync with origin/main: `d46775f`

Single writer: Manuel's codex. Keep this structure (OWNERSHIP_AND_DEPENDENCIES §7).

## Current task
M01 step 1 verified; dependency handoff ready. Next: rules, server skeleton, local checks, deployment.

## Delivered (newest first)
- M01 dependencies: fastapi, uvicorn[standard], pydantic>=2, rapidfuzz, qrcode, svgelements; pytest/httpx dev group; core/server/bench/agent wheel packages; generated uv.lock.

## Interfaces exposed / changed
- none yet (planned: CONTRACTS §7–§10 endpoints, tool registry, WebSocket, voice token, `useBuildingVoice`)

## Merge log (captain)
| Window | Merged branches @ SHA | Checks | Tag | Deployed |
|---|---|---|---|---|

## Evidence
- `uv lock` and `uv sync`: success (54 resolved packages); `uv run python -c "import fastapi, rapidfuzz"`: success. No tests exist at this first dependency-only handoff.
- Isolated worktrees created from `origin/main` at `d46775f`; human checkout untouched.

## Blockers and resource requests
- H3/H4 requested from human at start; no access confirmation yet.
- H3 Railway access (needed by 23:00 CEST), H4 ElevenLabs agents (needed by 00:30 CEST), H8 phones for the device gate.

## Change requests
- none

## Next handoff
- dependency commit to everyone (consumers: Hagen, Lenard, Manuel's Claude); fixtures `session.json`, `events_close_lift.json` to Manuel's Claude by 23:30 CEST.
