# Main deployment

## Target

- Repository: `hagenhaeussler/Industrial-Agents-Hackathon-2026`, branch `main`.
- Railway project: `talk-to-your-building`, environment `production`.
- Web service: `web`, Dockerfile `web/deploy/Dockerfile`.
- Voice service: `voice-agent`, Dockerfile `voice_agent/Dockerfile`.
- Existing URLs and service variables stay in use.

Both services will use the GitHub source on `main`. The web build uses the repository root. The shared
`.dockerignore` excludes evaluation questions, answers, submissions, results, secrets and local build output.
Only `building.json` files enter from `data/`. Each Dockerfile copies only its runtime code into the image.
The voice service keeps its existing pre-deploy sync and health check.

## Integration

The rewrite at `02a6795` has a separate Git history from the old main at `dc289ba`. The merge preserves both
histories and uses the rewrite's file tree. Old application files are removed by this replacement. Open
follow-up pull requests are separate work and are not part of this merge.

## Checks

- `scripts/check.sh`: passed on 25 October 2026. Python: 105 tests. Ruff: clean. Building view: 22 tests and
  TypeScript/build passed. Web app: 12 tests and TypeScript/build passed. No paid provider calls.
- Vite reports bundles above 500 kB. This does not stop either build.
- Git whitespace checks accept the rewrite's existing CSV files with Windows line endings.
- Pending: Railway source configuration, builds and live HTTP checks.

Local Docker verification is unavailable because the Docker daemon is not running. Railway will build both
images. No paid model or voice conversations are part of verification.
