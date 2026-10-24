# M01: Scaffold, server skeleton, Docker and first Railway deploy (target G1, 23:00 CEST)

## 1. Outcome and user value

Every builder can install the same dependencies, the repository has its working rules (`AGENTS.md`), one command checks the integrated tree, and a public HTTPS URL serves `/health`, the building list and a real building snapshot. Phones can reach the app from the first hour.

## 2. Starting state

- `pyproject.toml` (kit) has `anthropic`, `matplotlib`, `networkx`, `shapely`; wheel packages `starter_agent`, `benchmark`. No `server/`, `core/`, `bench/`, `agent/` yet. Root `agent.py` is an empty kit file (leave it).
- `web/mobile/` is Lenard's prototype; Manuel's Claude moves it to `web/app/` early in C01 (`git mv`). Until the move lands on `main`, the Docker build stage must tolerate either path (see below).
- `data/` is 208 MB; `building.json` + `equipment.csv` total 62 MB, PNGs 90 MB. Bun is not guaranteed on every machine (it was not installed where this plan was written).
- Read: MASTER_PLAN §2; CONTRACTS §7; INTEGRATION §1–§2.

## 3. Scope and ownership

Create/own: `pyproject.toml`/`uv.lock` changes, `AGENTS.md` (root), `.env.example` (update), `server/__init__.py`, `server/app.py`, `server/config.py`, `tests/server/test_health.py`, `Dockerfile`, `.dockerignore`, `scripts/check.sh`, root README section "Run it locally" (append; do not rewrite the kit README).

## 4. Implementation obligations

1. **Dependencies (one commit, first 10 minutes, push immediately):** add `fastapi`, `uvicorn[standard]`, `pydantic>=2`, `rapidfuzz`, `qrcode`, `svgelements`; dev group: `pytest`, `httpx`. Add `core`, `server`, `bench`, `agent` to `[tool.hatch.build.targets.wheel] packages`. `uv lock` and verify `uv sync` + `uv run python -c "import fastapi, rapidfuzz"`. Tell all builders via your human.
2. **Root `AGENTS.md`** (short): source precedence (`master prompt/` → its CONTRACTS → `docs/elevenlabs-agent-config.md` → kit README/CHANGELOG; `PLAN.md` and older plans are history); `data/`, `starter_agent/`, `benchmark/` are read-only; labels from `questions*.jsonl` only in tests; no hard-coded IDs; run `scripts/check.sh` before asking for a merge; Claude API rules (no `temperature`/`top_p`/`top_k`, no forced `tool_choice` on Sonnet/Opus 5.5, no `thinking: disabled`, effort via `output_config`); `Answer:` line rules (CONTRACTS §13); no secrets; English UI text; `web/app/AGENTS.md` and `DESIGN.md` apply inside `web/app/`.
3. **`.env.example`:** `ANTHROPIC_API_KEY=`, `ELEVENLABS_API_KEY=`, `ELEVENLABS_AGENT_ID_NAVIGATOR=`, `ELEVENLABS_AGENT_ID_ADMIN=`, `STATE_DIR=./.state`, `TYB_PROFILE=kit_1_1_0`, `PUBLIC_BASE_URL=http://localhost:8000`, `DATA_DIR=./data`. Add `.state/` and `web/app/dist/` to `.gitignore` (you own these one-line additions; announce them).
4. **Server skeleton (`server/app.py`):** FastAPI app; `GET /health` (CONTRACTS §7, includes `commit` from `RAILWAY_GIT_COMMIT_SHA` or `git rev-parse`, profile, `state_dir_writable`, building count); `GET /api/buildings` from `data/manifest.csv` plus `demo/hero/` and uploads; `GET /api/buildings/{id}` snapshot (use `core.load_building` when Hagen's H01 lands; until then load the raw JSON and compute anchors/areas with the kit `outline()`); GZip middleware; CORS for `localhost:5173` in dev; static SPA from `web/app/dist` with history fallback **after** `/api`, `/ws`, `/health`; synchronous `def` handlers for geometry. One uvicorn worker.
5. **Dockerfile (multi-stage):**
   - Stage `web`: `oven/bun:1` image, `WORKDIR /web`, copy `web/` and build the app directory that exists (`web/app` preferred, else `web/mobile`) with `bun install --frozen-lockfile && bun run build`; copy the `dist` to `/web-dist`.
   - Stage `app`: `python:3.12-slim`; copy `uv` from `ghcr.io/astral-sh/uv` image; copy `pyproject.toml uv.lock` and run `uv sync --frozen --no-dev --no-install-project` (layer cache), then copy the sources and run `uv sync --frozen --no-dev` again; sources: `core server bench agent starter_agent benchmark demo fixtures` and `data/` **without PNG/SVG** (`.dockerignore`: `data/**/*.png`, `data/**/*.svg`, `agent_output`, `.venv`, `**/node_modules`, `.state`, `research/`); copy `/web-dist` to `/app/web/app/dist`; `ENV STATE_DIR=/state`; `CMD uv run --no-sync uvicorn server.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1`.
   - State initialisation at startup (create SQLite file and folders in `STATE_DIR`), never at build time; the volume is mounted at `/state`, not over `/app/data`.
6. **`scripts/check.sh`:** `set -euo pipefail`; `uv run pytest -q`; kit oracle; `uv run python -m core.evaluate data/dev --check text` (skip with a warning until H01 lands); `bun run build` in `web/app` if Bun exists, else a warning. Exit code reflects failures.
7. **Railway (with H3):** service from the GitHub repo using the Dockerfile; volume at `/state`; variables per `.env.example` (`STATE_DIR=/state`); app sleeping off; public domain; healthcheck path `/health`. Deploy policy: you deploy only merged `main` at merge windows. If you get a Railway token, keep it in your local environment only.
8. **README "Run it locally":** `uv sync`, `cp .env.example .env`, `uv run uvicorn server.app:app --reload --port 8000`, `cd web/app && bun install && bun run dev`, Docker commands, benchmark commands (link to `BENCHMARK.md`).

## 5. Interfaces and fixtures

- Publish the base URL (local and Railway) and `curl` examples in STATUS.
- `fixtures/session.json` and `fixtures/events_close_lift.json` (CONTRACTS §15) by 23:30 CEST so Claude can build the admin and reroute UI before M02 lands.

## 6. Execution order

deps (10 min, push) → `AGENTS.md` + `.env.example` (10 min) → server skeleton + test (20 min) → Dockerfile + local `docker build` (20 min) → `scripts/check.sh` (10 min) → Railway deploy (as soon as H3 allows) → G1 merges (core, deps) and first tag `gate-G1`.

## 7. Acceptance

- `uv run pytest -q tests/server` green; `curl localhost:8000/health` ok; `curl localhost:8000/api/buildings/proc-factory-dev-003 | head -c 300` returns the snapshot.
- `docker build -t tyb .` succeeds; `docker run --rm -p 8000:8000 -v "$PWD/.state:/state" tyb` serves `/health` and the SPA index.
- Railway URL `/health` ok over HTTPS (record the URL and SHA); if H3 is late, record "pending H3".
- Image size recorded.

## 8. Collaboration and Git

Branch `manuel-codex/platform`. Merge your M01 into `main` at G1 together with Hagen's H01 (core first). Tag `gate-G1`.

## 9. Completion report

SHA; URL(s); image size; commands and outputs; deps added; what is still pending (H3/H4).

## 10. Blocked-work behaviour

No Railway access: keep everything working locally, set up Android USB port forwarding (`chrome://inspect` → Port forwarding 8000 → localhost:8000) for phone tests, and chase H3 through your human every 30 minutes. Bun missing locally: build the web stage only inside Docker.
