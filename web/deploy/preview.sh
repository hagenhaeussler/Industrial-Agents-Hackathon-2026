#!/usr/bin/env bash
# Deploy committed code to the isolated AI coworker preview, including only building source files.
set -euo pipefail

repo=$(git rev-parse --show-toplevel)
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT

cd "$repo"
git archive HEAD -- building_api building_db building_tools packages/building-view web pyproject.toml uv.lock \
  ':(glob)data/*/*/building.json' | tar -x -C "$stage"
cp web/deploy/Dockerfile "$stage/Dockerfile"
cat > "$stage/railway.json" <<'JSON'
{
  "build": { "builder": "DOCKERFILE", "dockerfilePath": "Dockerfile" },
  "deploy": { "healthcheckPath": "/api/buildings", "healthcheckTimeout": 120 }
}
JSON

if find "$stage/data" -type f ! -name building.json | grep -q .; then
  echo "refusing to deploy: data contains a file other than building.json" >&2
  exit 1
fi

# Optional real app captures for the PR. They are hosted only on the preview.
if [[ -n "${COWORKER_PREVIEW_EVIDENCE:-}" ]]; then
  mkdir -p "$stage/web/public/preview-evidence"
  find "$COWORKER_PREVIEW_EVIDENCE" -maxdepth 1 -type f \( -name '*.png' -o -name '*.webm' \) \
    -exec cp {} "$stage/web/public/preview-evidence/" \;
fi

railway up "$stage" --path-as-root --project fb2812d2-9587-4b43-b647-1d0997386526 \
  --environment coworker-preview --service coworker-preview --detach \
  --message "AI coworkers preview $(git rev-parse --short HEAD)"
