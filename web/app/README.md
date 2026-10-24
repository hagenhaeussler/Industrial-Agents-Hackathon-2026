# Talk to Your Building: web app

One React 19 / TypeScript / Vite SPA serves desk planning, phone guidance and facility administration.

[Open the shared preview](https://hagen-core-test-testing.up.railway.app/desk?demo=hero). Navigation is public; `/admin?demo=hero` asks for the private admin code. Coordinate closures and demo resets with coworkers because the preview shares persistent building state. Upload a separate JSON building for independent experiments.

```sh
bun install --frozen-lockfile
bun run dev
```

Run the FastAPI server on port 8000; Vite proxies `/api`, `/ws` and `/health` (`TYB_API` overrides the upstream). Camera and microphone require HTTPS or localhost. Plain HTTP on a LAN supports the map only. Provider keys remain in the server's private environment; never add them to a `VITE_` variable.

```sh
bun test
bun run build
```

## Live journey

- `/`: building list. `/desk?building=<id>`: search parts, select, plan, choose mobility and optional finish, inspect route/trace, send the exact saved tour to a phone with QR.
- `/desk?demo=hero`: factory scenario from `demo/scenario.json`; the factory is kit data, not a measured model of the venue.
- `/go/<tourId>`: confirm a start, scan a position code or choose a room; follow steps, collect stops and explicitly reach any final destination. Reload resumes progress. Building changes trigger replanning without losing collected parts; wheelchair profiles require an explicit choice before showing stairs.
- `/m/<markerId>`: use a printed position-code location. Codes supply a declared standing point and heading; they do not measure the camera pose.
- `/admin`: code-gated preview → confirm → commit once → undo; upload/validate kit-format `building.json`; demo reset when enabled on the server. The code and privileged session stay in tab-only `sessionStorage`.
- Desk and phone show standalone tool routes as a separate preview with exact server segments and textual directions. Closing it restores the collection tour without changing position/progress. Spatial answers can highlight multiple rooms; stale geometry from another building/version is ignored.
- Text and ElevenLabs voice tools share each screen's display handler. Voice is explicit opt-in; unavailable audio falls back to text and navigation buttons. Provider setup/test limits are described in `docs/live-provider-setup.md` at the repo root.

## Camera and AR

The phone's Camera button opens a rear-camera view with a **Direction only** arrow. Scan a position code while in camera mode to anchor its heading; without motion permission the arrow is explicitly relative to the code's direction. Floor changes ask for another code. Camera denial leaves a return to the map. Frames are neither recorded nor uploaded.

Compatible browsers may offer **Try experimental AR** after a new standing/facing confirmation. The optional, separately loaded Three.js module draws only the current floor's computed walking segments and stops before a lift/stair transition. Denial, cancellation, tracking loss, backgrounding and route changes return to a working map/camera path. Physical-device alignment, drift and simultaneous voice/camera performance still require Android/iPhone measurements; offline lifecycle tests do not establish those results.

## Fixtures and prototype

`?mock=1` explicitly enables labelled fixtures; it is never the default live path. `/go/demo` keeps the original scripted prototype for design reference only. Its illustrated corridor, demo routes and local chat are separate from the live screens. No continuous localization, live part tracking, Gaussian Splat or reliable image-to-building import is claimed. JSON import is the supported path; 3D exploded-building view is an unshipped stretch.

## Structure

`src/desk`, `src/phone` and `src/admin` own screens; `src/map` draws server geometry through `src/geo/transform.ts`; `src/api` owns transport/contracts; `src/voice` owns token/SDK/client tools; `src/camera/ar` owns frame transforms and XR lifecycle. `DESIGN.md` defines visual/accessibility rules. `demo/SCRIPT.md` at the repo root supplies the recording runbook.

Blobatar uses the stable `alain00` identity and the library's reduced-motion support. Sources: [repository](https://github.com/Alain00/blobatar), [React adapter](https://github.com/Alain00/blobatar/tree/main/packages/react).
