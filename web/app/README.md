# Talk to Your Building: web app

One SPA for desk planning (`/desk`), the phone journey (`/go/:tourId`) and admin (`/admin`). React, TypeScript, Vite and Bun.

- Live API: run the FastAPI server on port 8000 (`TYB_API` overrides); Vite proxies `/api`, `/ws` and `/health`.
- Without a server: add `?mock=1` (bundled kit data; in `bun run dev` every kit building is readable from `data/`).
- Demo: `/desk?demo=hero` preloads `demo/scenario.json`.

The phone prototype below is reachable at `/go/demo` until the live journey replaces it.

```sh
bun install
bun run dev
```

Open the printed localhost URL. For a phone, use the private HTTPS deployment and sign in with the owner account. Camera access needs HTTPS or localhost. A plain HTTP LAN address can show the demo, but cannot start the camera.

```sh
bun run build
bun test
```

## What works

- Live device camera with a preference for the rear camera. Explicit start/stop, permission and device errors, stream cleanup. No frames leave the browser.
- White floating route panel, floor minimap, demo path and route-step controls.
- Destination selection and a locally scripted agent chat that can switch destinations.
- Exact `alain00` identity using matching `blobatar` and `@blobatar/react` 2.7.0 packages. Always-on inline SVG motion, blinking and idle gaze. Built-in reduced-motion support. Happy expression at arrival.
- Mobile and desktop layouts, native modal focus handling, Escape to close.

## Prototype limits

The route, floor map, distances and position are example data. The line is a screen-space illustration, not a tracked physical-world anchor. No Gaussian Splat, visual localization, route backend, building-document retrieval, microphone or language model is connected. Chat replies are local templates. The corridor is an SVG illustration shown while the camera is off.

## Where things live

- `src/camera`: camera lifecycle and the demo corridor illustration.
- `src/navigation`: typed demo routes, floor map and camera overlay.
- `src/agent`: Blobatar, chat and demo answers.
- `src/styles.css`: layout and visual tokens.
- `DESIGN.md`: design rules.

## Blobatar findings

The name is hashed into stable visual traits. Keep the name and package major stable to preserve identity. `animate="always"` uses inline SVG so the imported motion CSS can animate its parts. `animate="hover"` does not provide continuous motion on a phone. Motion includes breathing, bobbing, blinking and gaze changes. Expressions alter the face without changing the name. The library disables movement for `prefers-reduced-motion`.

Sources: [repository](https://github.com/Alain00/blobatar), [React adapter](https://github.com/Alain00/blobatar/tree/main/packages/react), [motion styles](https://github.com/Alain00/blobatar/blob/main/packages/blobatar/src/motion.css).
