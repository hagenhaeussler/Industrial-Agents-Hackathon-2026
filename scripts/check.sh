#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

# This is an offline gate even on a developer machine with a live .env.
# Paid provider measurements use their separate explicitly budgeted runners.
export PYTHON_DOTENV_DISABLED=1
export ANTHROPIC_API_KEY='' ELEVENLABS_API_KEY='' OPENAI_API_KEY=''
export ELEVENLABS_AGENT_ID_NAVIGATOR='' ELEVENLABS_AGENT_ID_ADMIN=''
export TYB_CHAT_BUDGET_USD=0

uv run pytest -q
uv run python -m starter_agent.evaluate data/dev --oracle

if [[ -f core/evaluate.py ]]; then
    uv run python -m core.evaluate data/dev --check text
else
    echo 'WARNING: core.evaluate is not published yet; skipping the H01 text check.' >&2
fi

if ! command -v bun >/dev/null 2>&1; then
    echo 'WARNING: Bun is not installed; skipping the frontend build. Docker builds it with Bun.' >&2
elif [[ -f web/app/package.json ]]; then
    (cd web/app && bun test src && bun run build)
    if [[ -f web/app/src/camera/ar/deviceGatePage.ts ]]; then
        bun scripts/build-device-gate.ts
    fi
else
    if [[ -d web/app/src/voice && -d web/app/src/camera/ar ]]; then
        bun test web/app/src/voice web/app/src/camera/ar
    fi
    echo 'WARNING: web/app is not published yet; skipping the C01 frontend build.' >&2
fi
