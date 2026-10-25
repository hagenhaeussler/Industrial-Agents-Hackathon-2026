# Locora web app

One React app with two routes:

| Route | For | What it does |
|---|---|---|
| `/` | Everyone | Pick a building by collection and floor plan |
| `/b/:buildingId?from=…&to=…&step_free=1` | Phone, QR target | Map, step list or camera view, with the avatar and the voice assistant in every view |
| `/admin/:buildingId` | Desktop | 3D building and floor plans, search, position by click, routes, QR code to a phone, team sidebar |

## Run

```sh
uv run python -m building_db import buildings.sqlite3 data/*/*/building.json   # once
uv run python -m building_api serve buildings.sqlite3 --port 8010
pnpm --dir packages/building-view install                                       # once
cd web && pnpm install && pnpm dev
```

The dev server proxies `/api/voice` to the voice server on Railway and every other `/api` path to the building
API. Set `VOICE_SERVER` or `BUILDING_API` to use other servers. Camera and microphone need HTTPS or localhost.

```sh
pnpm check   # TypeScript
pnpm test    # unit tests
pnpm build
```

Clicking **Workspace** on Home briefly flies from Earth to the real footprint for any of the 17 mapped
OSM buildings, then reveals the existing workspace. Other buildings, direct workspace links and phone
guides open as before. The entrance is capped at three seconds including loading, can be skipped, and
respects reduced motion. If the map or WebGL is unavailable the workspace still opens. Only the entrance
loads MapLibre; it reuses the geographic metadata and Earth treatment from `feature/campus-explorer`.

## Deploy

The Railway service `web` (project `talk-to-your-building`) runs the building API and serves the built app from
one container. `web/deploy/deploy.sh` uploads the committed code and the `building.json` files only, and refuses
to deploy if any other file from `data/` is staged. The image imports the buildings into SQLite at build time.

```sh
web/deploy/deploy.sh
```

The service variable `VITE_VOICE_SERVER` holds the voice server's public URL. The voice server must list the web
app's origin in `VOICE_CORS_ORIGINS`.

## How the parts fit

```mermaid
flowchart LR
  UI[Web app] -- "building, route with points" --> API[building_api]
  UI -- "conversation token" --> V[voice server on Railway]
  UI <-- "voice, WebRTC" --> EL[ElevenLabs agent]
  EL -- "tool calls" --> V
  EL -. "route tool call: stops and rules" .-> UI
```

- The UI calculates no routes. It draws the route and points from `GET /api/buildings/{id}/route`.
- When the voice agent calls `route`, the UI reads the stops and rules from the tool call and loads the same route
  from the API. So the screen shows what the agent says.
- The conversation gets `building_id`, the current space and the destination as dynamic variables. A change on
  screen during a conversation goes to the agent as a contextual update.
- The avatar (Blobatar `alain00` from the phone prototype) follows the conversation: idle, connecting, listening,
  speaking with the voice level, and happy on arrival.
- A QR code holds only the phone link. The phone loads the route itself.

## Camera localization

In the camera view the phone sends about one frame per second (JPEG, long side 1024 px, one request at a time) to
`POST /api/buildings/{id}/localize`. The building API forwards it to the GPU localization service with the token
from `LOCALIZATION_TOKEN`; the browser never sees the token or the service URL. See `docs/localization.md`.

- Only results with `reliable: true` count. `position` and `heading_deg` draw the marker on the mini map.
- When two fixes in a row agree on a new `space_id`, it becomes the start. The route is planned again with the
  stops still ahead, so passed waypoints are dropped. In the destination nothing changes.
- After 404 (no map for the building) or 503 (localization not configured on the server) the phone stops sending
  until the page reloads. After other failures, such as a timeout (502), the wait doubles up to 16 s.
- The service does not store images. Settings tell the user that frames are sent.

## Preview parts

Settings in the workspace name these. The main view does not.

- Team members, channels, messages and presence are sample content in `src/admin/team.ts`.
- Moving equipment changes only the browser's copy of the building.
- The camera view draws the next turn over the camera image.

## Building import

Use **Import building** on the home page to choose a file named `building.json`, up to 20 MiB.
After validation and saving, the app opens the building in the workspace. An identical file opens the
existing building. A changed file with the same ID is rejected without overwriting data. Validation and
storage errors stay on the home page so the file can be corrected or retried.

The upload uses the dataset schema. Extra metadata in the current `building_local/` examples is not
accepted by the strict importer. It must be normalized before those examples can be imported.
