# STATUS: Manuel's codex (Platform & Live Integration Lead, integration captain)
Last update: 2026-10-24 21:26 CEST · Branch: `manuel-codex/platform` · HEAD: M01 checkpoint (this revision) · Last sync with origin/main: `d46775f`

Single writer: Manuel's codex. Keep this structure (OWNERSHIP_AND_DEPENDENCIES §7).

## Current task
M01 repository implementation verified; external Railway/ElevenLabs setup deferred by human. M02 state, tools, tours and realtime in progress.

## Delivered (newest first)
- M01: FastAPI health/catalog/snapshot + GZip/CORS/SPA fallback, runtime SQLite initialization, root rules/config, Docker image, check script, local-run README.
- `682441a`: root AGENTS.md, .env.example, `.state/` and `web/app/dist/` ignores.
- `917980c` (pushed): dependency handoff, consumers all four builders; installation and imports verified.
- M01 dependencies: fastapi, uvicorn[standard], pydantic>=2, rapidfuzz, qrcode, svgelements; pytest/httpx dev group; core/server/bench/agent wheel packages; generated uv.lock.

## Interfaces exposed / changed
- C1: `GET /health`, `GET /api/buildings`, `GET /api/buildings/{id}?version=0`; real catalog count 280 from manifest (281 in contract was an illustrative example).
- Local: `uv run uvicorn server.app:app --port 8000`; `curl localhost:8000/health`; `curl localhost:8000/api/buildings/proc-factory-dev-003`.

## Merge log (captain)
| Window | Merged branches @ SHA | Checks | Tag | Deployed |
|---|---|---|---|---|

## Evidence
- M01 working tree: `scripts/check.sh`: 21 Python tests passed; kit oracle 369/369. `core.evaluate` skipped with explicit warning because H01 has not been published; web/app build skipped because C01 move remains on its own branch.
- `docker build -t tyb .`: passed, frozen Bun install + TypeScript/Vite build from web/mobile fallback. Local linux/arm64 image 129,465,743 bytes; ID `sha256:15fae22469fb4966650c208aa58b1cfbe1586032f502000ff68c0d97faedf4b0`.
- Empty-volume Docker smoke on :18001: health/catalog/snapshot/desk/go 200, unknown API and WS 404; SQLite tables created at startup; container stopped. Image commit is unknown locally without Git/RAILWAY_GIT_COMMIT_SHA.
- SQLite tests include four simultaneous commits => one event, stale preview rejection, undo, persisted sessions/tours/events and tour revision conflict.
- `uv lock` and `uv sync`: success (54 resolved packages); `uv run python -c "import fastapi, rapidfuzz"`: success. No tests exist at this first dependency-only handoff.
- Isolated worktrees created from `origin/main` at `d46775f`; human checkout untouched.

## Blockers and resource requests
- Human steering: “just do all in the repo — elevenlabs agents will be implemented.” External Railway deploy and provider setup are pending outside this repository task; no access follow-ups required now.
- H3 Railway access (needed by 23:00 CEST), H4 ElevenLabs agents (needed by 00:30 CEST), H8 phones for the device gate.

## Change requests
- none

## Next handoff
- M01 checkpoint to all; next M02 OpenAPI + registry to Lenard and Claude. Fixtures `session.json`, `events_close_lift.json` to Manuel's Claude by 23:30 CEST.
