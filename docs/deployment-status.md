# Main deployment

## Target

- Repository: `hagenhaeussler/Industrial-Agents-Hackathon-2026`, branch `main`.
- Railway project: `talk-to-your-building`, environment `production`.
- Web service: `web`, Dockerfile `web/deploy/Dockerfile`.
- Voice service: `voice-agent`, Dockerfile `voice_agent/Dockerfile`.
- Existing URLs and service variables stay in use.

Both services use the GitHub source on `main`. Railway's repository triggers were read back and both point to
that branch in `production`. New pushes build and deploy both services. The web build uses the repository root. The shared
`.dockerignore` excludes evaluation questions, answers, submissions, results, secrets and local build output.
Only `building.json` files enter from `data/`. Each Dockerfile copies only its runtime code into the image.
The voice service keeps its existing pre-deploy sync and health check. The web health check is `/api/buildings`.

- Web: https://web-production-99671.up.railway.app
- Voice: https://voice-agent-production-653b.up.railway.app

## Integration

The rewrite has a separate Git history from the old main at `dc289ba`. The merge preserves both histories and
uses the rewrite's file tree, including `898f35f` with phone camera localization and voice transcript feedback.
Old application files are removed by this replacement. Work not merged into that rewrite revision is separate.

## Checks

- `scripts/check.sh`: passed on 25 October 2026. Python: 112 tests. Ruff: clean. Building view: 22 tests and
  TypeScript/build passed. Web app: 23 tests and TypeScript/build passed. No paid provider calls.
- Vite reports bundles above 500 kB. This does not stop either build.
- Git whitespace checks accept the rewrite's existing CSV files with Windows line endings.
- Railway built and deployed `be6cc9d` from GitHub `main`. Both deployments reached `SUCCESS` and became active:
  web `b0829a2c-14b3-4ac1-9b89-57cbb6035eb0`, voice `822f770e-269c-451a-afa2-d5a8ddea0dc0`.
- Live HTTP checks passed: home, desktop and phone app entries; the main JavaScript asset; 281 buildings in each
  service; a reachable factory route of 130.25 m; voice token and allowed web origin; unauthenticated MCP returns 401.
- Voice pre-deploy sync completed. No paid conversation was started.

Local Docker verification is unavailable because the Docker daemon is not running. Railway will build both
images successfully. No paid model or voice conversations are part of verification.

The T3 browser snapshot timed out twice. The alternate browser had no available browser. A fresh visual,
microphone or phone-device check was not completed. A container filesystem check through Railway SSH was also
unavailable because no SSH key is registered; no key or account access was added. Build logs confirm the intended
Dockerfiles and their runtime COPY steps, but do not replace a container filesystem audit.
