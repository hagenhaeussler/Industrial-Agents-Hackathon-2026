#!/usr/bin/env bash
# Deploy the committed web app and building API to the Railway service "web".
# Only code and building.json files are uploaded. Question, answer and result files never leave this machine.
set -euo pipefail

repo=$(git rev-parse --show-toplevel)
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT

cd "$repo"
git archive HEAD -- building_api building_db building_tools packages/building-view web pyproject.toml uv.lock \
  ':(glob)data/*/*/building.json' | tar -x -C "$stage"
cp web/deploy/Dockerfile "$stage/Dockerfile"

if find "$stage/data" -type f ! -name building.json | grep -q .; then
  echo "refusing to deploy: a file other than building.json is staged in data/" >&2
  exit 1
fi

railway up "$stage" --path-as-root --service web --detach
