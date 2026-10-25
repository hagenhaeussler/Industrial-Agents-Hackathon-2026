#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

export PYTHON_DOTENV_DISABLED=1
export ANTHROPIC_API_KEY='' ELEVENLABS_API_KEY='' OPENAI_API_KEY=''

uv run python -m unittest discover -s tests
uv tool run ruff check building_agent building_api building_db building_tools voice_agent localization tests

for project in packages/building-view web; do
  (
    cd "$project"
    pnpm install --frozen-lockfile
    pnpm test
    pnpm build
  )
done

git -c core.whitespace=cr-at-eol diff --check HEAD
