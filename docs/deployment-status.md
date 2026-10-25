# Locora deployment

## Target

Locora uses the existing repository, Railway project and service addresses listed below.
The Railway project still has its original infrastructure name, `talk-to-your-building`.

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

The equipment selection follow-up from PR #28 (`0dd4dd7`) is now merged into the release branch for `main`.
Its release check passed: 112 Python tests, 22 building-view tests, 33 web tests, Ruff and both TypeScript builds.

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

Local Docker verification is unavailable because the Docker daemon is not running. Railway built both
images successfully. No paid model or voice conversations are part of verification.

## JSON building upload release — 25 October 2026

- Integrates `t3/embed-equipment-rename-building-local` at `7dfb520`, including the local-data consolidation at
  `81633ff`, onto main at `ef73058`. The merge was conflict-free.
- The concurrent home-collections release (PR #40, main at `00f4d09`) is retained. Import sits on the new home
  page without duplicating its search or discarding its collections. API types were regenerated from the combined
  backend schema, retaining both import and isometric-preview endpoints.
- Remote recovery branch: `backup/main-before-building-json-upload-20261025-00f4d09` points to
  `00f4d09b82098e653097a94cae5a86cb21c0916f`, main immediately before this integration. The earlier
  `backup/main-before-building-json-upload-20261025-ef73058` recovery point is also retained.
- Home now offers **Import building**. A valid dataset-format file named `building.json` (maximum 20 MiB)
  is saved before opening its desktop workspace. It is available through the building API and route tools;
  identical uploads are idempotent and changed content with an existing ID is rejected without overwriting it.
- Release checks: 146 Python tests, 66 web tests and 22 building-view tests passed. Ruff and both production
  frontend builds passed. All provider API keys were disabled during the Python checks.
- Added coverage for importing from the collections home and for an uploaded building's SVG thumbnail. The
  empty-preview fixture uses an outdoor-only building, respecting the upload schema's nonempty-space requirement.
- Push main to use the existing GitHub-triggered Railway deployment. This release does not reconnect or deploy
  the retired `hagen-core-test` service.

Deployment limits to retain: the default web Dockerfile stores its SQLite database in the container filesystem,
so uploads require a persistent mount and the corresponding database path to survive a container replacement.
The separate voice service loads its own building catalog at startup; a web upload does not automatically add
that building to the voice catalog. The import feature therefore establishes preview and HTTP routing support,
not cross-service voice synchronization. Local `building_local/` examples with additional metadata also need
normalization to the strict dataset schema before upload. These limits are not changed by this merge.

The T3 browser snapshot timed out twice. The alternate browser had no available browser. A fresh visual,
microphone or phone-device check was not completed. A container filesystem check through Railway SSH was also
unavailable because no SSH key is registered; no key or account access was added. Build logs confirm the intended
Dockerfiles and their runtime COPY steps, but do not replace a container filesystem audit.
