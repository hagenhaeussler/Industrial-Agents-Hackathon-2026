# Campus explorer

## Handoff for the main developer

This branch is a working feature prototype for review and selective reuse. It does not deploy or
replace the main branch. The routing choice is deliberate for the demo: the explorer occupies `/`,
and the previous building list moves to `/buildings`. If the main app should retain its existing
landing page, mount `CampusExplorer` at a separate route instead. The existing workspace and phone
guide remain separate entry points. Only CIT currently has calibrated indoor assets; its ID belongs
to the catalogue and generated data, not application branching logic.

Useful parts to reuse independently:

- `web/src/explore/CampusExplorer.tsx`: catalogue, arrival sequence and exterior/interior state.
- `GoogleExterior.tsx` and `GoogleIndoorLayer.ts`: optional Google scene, building replacement,
  room highlighting and restoration without recreating the map.
- `indoor-camera.ts`, `model-placement.ts` and `geography.ts`: camera framing and geographic transforms.
- `scripts/prepare_campus.py`, `scripts/prepare_google_models.mjs` and
  `packages/building-view/src/export/FloorGlb.ts`: reproducible, source-derived geometry pipeline.

From the repository root, install the existing Python environment and both frontend packages, then run:

```sh
uv sync
pnpm --dir packages/building-view install --frozen-lockfile
pnpm --dir web install --frozen-lockfile
uv run python -m building_db import buildings.sqlite3 data/*/*/building.json
uv run python -m building_api serve buildings.sqlite3 --host 127.0.0.1 --port 8011
# In a second terminal:
BUILDING_API=http://127.0.0.1:8011 pnpm --dir web dev --host 127.0.0.1 --port 8013
```

Open `http://127.0.0.1:8013/?building=osm-way27917482&map=photo`. Enter a Google browser key in the UI
and select **Open Google 3D**. Do not put it in source, an environment file, a commit or the PR.
For the demo, select **Go inside**, level 2, search for `02.06.011`, select the room, close its card,
show all floors, vary their separation, then use **Back to 3D**. Campus and Aerial also work without a key.

The checked-in map data and generated models total approximately 18.8 MiB. These are OSM metadata and
our own source-derived models; no Google imagery, tiles, browser captures or credentials are included.
Before production adoption, review the Google API version and billing/key restrictions, decide the
landing-page route, and verify Google rendering on target phones. The original live Google checks
are documented below; offline checks do not contact paid providers.

Model freshness is currently a build-time responsibility: runtime checks verify the building/floor
IDs, floor count, elevations, anchor and GLB structure, but do not compare `sourceSha256` or
`frameSha256` against the active source/calibration. Those hashes are provenance metadata. Regeneration
is mandatory after geometry or calibration edits, even when IDs and elevations stay unchanged.
Before production adoption, add source/frame freshness enforcement and a stale-model regression test.
The production build also reports large JavaScript chunks; review loading performance on target devices.

## Product and implementation plan

The entry page becomes a geographic building explorer. Selecting a building starts on a globe, flies to
its real OSM location, then tilts into an architectural campus view. The featured example is the TUM
Mathematics and Informatics building in Garching. Its five dataset levels include the basement.

1. Prepare a versioned catalogue of the 17 OSM buildings from their `source_ref.osm` references. Keep
   their outlines, addresses, source versions, and dataset counts. Do not import evaluation files.
2. Use MapLibre's globe, camera animations, vector basemap and building extrusions. Keep the existing
   workspace and phone routes. The map is loaded separately from the phone experience.
3. Offer Campus and Aerial styles, plus optional Google **3D Photo**. Campus follows the supplied university-campus references: ivory
   context buildings, green landscape, restrained blue-grey selection, lime emphasis, readable labels.
   Aerial uses the Bavarian Surveying Administration's public DOP20 orthophoto WMS. Both are real
   geographic data. Architectural facades are schematic, not a photographed 3D mesh.
4. Fit the featured building's local plan to OSM room geometry by matching room refs and floor levels.
   Store the affine transform and measured residuals as catalogue data, separately from `building.json`.
   A building without a verified transform still opens in the existing standalone workspace.
5. Draw the verified building's rooms, walls, equipment and stacked levels on the map. Support level
   selection, floor separation, room selection, return to the exterior and opening the full workspace.
6. Verify geometric alignment, flight cancellation, reduced motion, style switches, unavailable APIs,
   desktop and phone layouts, and the original workspace. Run TypeScript, frontend and focused Python
   checks. Inspect real browser screenshots against the concept and supplied references.

## Design inventory

The full-screen concept uses the existing Manrope font and app palette. Header: white, 68 px; desktop
building rail: white, 320 px; remaining space: live geographic canvas. Text is #191c16, muted text #64685f,
accent #dcff58, subtle borders #e9eae3. Controls use 12 px radii, 14 px text and Lucide outline icons.
The header contains the brand, Explore and Workspace. The rail contains search, building rows and the
selected building's address and counts. The map has Campus/Aerial, globe, north, zoom and level controls.
On phones the building rail becomes a compact bottom sheet with a searchable building picker.

The generated concept is a layout reference only. Its invented campus geometry, photographic thumbnails,
building placements and floor labels must not replace actual data. Preview thumbnails use real aerial
imagery. Attribution remains visible. Campus and Aerial do not require a paid provider or account.

## Data sources

- MapLibre GL JS, BSD-3-Clause: <https://maplibre.org/maplibre-gl-js/docs/>
- OpenFreeMap/OpenMapTiles, OSM-derived basemap: <https://openfreemap.org/>
- OSM API, building and room geometry, ODbL: <https://www.openstreetmap.org/copyright>
- Google 3D Maps, optional, proprietary imagery, runtime browser key:
  <https://developers.google.com/maps/documentation/javascript/3d/overview>
  <https://developers.google.com/maps/documentation/javascript/reference/3d-map>
- Bavarian DOP20, CC BY 4.0:
  <https://geodaten.bayern.de/opengeodata/OpenDataDetail.html?active=SERVICE&pn=dop20rgb>

The UI is implemented in this repository; no third-party demo application is copied. The experimental
`maplibre-indoor` demo informs the exterior-to-interior interaction. MapLibre handles Campus/Aerial and
their indoor geometry. In **3D Photo**, Google's renderer displays both the photographic surroundings
and our own floor models. The calibrated CIT building is replaced within that same Google scene.

## Current implementation and verification

The explorer is the home page; `/buildings` retains the full building list, `/admin/:id` the original
Three.js workspace and `/b/:id` the phone guide. `?building=<id>` starts the arrival sequence for a
specific catalogue entry. Only the featured building currently has a verified geographic indoor frame.
The other 16 buildings support exterior views and open their existing workspace for interior work.

The CIT calibration uses 1,541 matching OSM room centroids. Median residual is approximately 0.0013 m
and the 95th percentile approximately 0.0049 m in EPSG:3857 projected coordinates. This measures agreement
with the OSM snapshot, not physical survey accuracy. The scene uses the source elevations and room shapes.
The 88 landscape trees use actual OSM positions and schematic crowns; facade windows and exterior
heights are architectural display values. The aerial surface is an orthophoto, not a textured 3D mesh.

To regenerate the catalogue, use `scripts/prepare_campus.py --featured <id>`. For a calibrated interior,
also supply `--calibrate <id> --room-map <osm-map-api-json>`. The OSM map API export must cover that
building's footprint and contain room refs, levels and their nodes. `--raw` accepts the preparer's saved
building outlines and metadata for offline regeneration. Evaluation files are never read.

Verification on 25 October 2026:

- TypeScript and Vite production build pass; MapLibre's worker is bundled as an ES worker for deployment.
- 40 web tests, 22 existing building-view tests and 15 focused Python tests pass.
- Production build tested with the real API at 1440×1000 and 390×844. Eleven browser scenarios pass:
  globe, flight, aerial HTTP 200, five indoor levels, level filter/keyboard separation/top-down,
  rapid-selection cancellation, reduced motion, mobile picker, original workspace, provider outage
  and selecting/dismissing an actual ground-floor room (MI Magistrale, 00.01.001) on the map.
- No application console errors. Headless Chromium reports screenshot-related GPU readback warnings.
- IAB used for interactive checks. The Browser plugin was not available; isolated Playwright supplied
  repeatable viewport sizes because the IAB viewport follows the desktop app window.
- Concept and browser screenshots inspected with `view_image`: header, typography, rail width,
  lime selected/primary controls, map palette, controls, real thumbnail framing and mobile layout.
  Actual geography, source floor names and real aerial thumbnails intentionally replace invented
  details in the generated concept. Copy is the implemented inventory, with provider credits added.

## Photorealistic surroundings with our floor model

On 25 October 2026 the user's Demo Key successfully loaded Google Maps JavaScript `maps3d` at the CIT
coordinates. Browser inspection confirmed photographed roofs, facades and trees, beyond flat aerial imagery.
**3D Photo** loads Google only after explicitly entering a key. The SDK is loaded once per page and kept
in memory. No literal key is present in the repository; no environment variable, file or browser storage
is used to retain it. The browser sends this client-side key to Google for authentication, so it is visible
in that tab's network requests and must be restricted appropriately. Reloading loses the local session.

The exterior uses the catalogue's real center and bounds, with a terrain-relative camera target. A Google
`gmp-click` is checked against the selected OSM polygon, including any holes. Clicking a neighbour does not
open the selected plan. An accessible **Go inside** button provides the same transition.

For CIT, `GoogleIndoorLayer` appends a Google `FlattenerElement` scoped to the OSM footprint and one
`Model3DInteractiveElement` per source floor. This removes Google's building mesh while retaining the
terrain, surrounding buildings, trees and imagery. A generated 3 m ground-distance clearance around the
footprint removes photogrammetric facade spill seen in close-up testing. The Shapely buffer preserves
courtyard interiors wider than the clearance. This is a display mask, not a change to source geometry,
calibration, model scale or position. It is not a survey of Google's mesh.
**Back to 3D** removes the flattener and floor models, restoring the original photographic building. It
does not recreate the Google map. Floor selection and separation update those same model elements.
Google documents [mesh flattening](https://developers.google.com/maps/documentation/javascript/3d/mesh-flattening)
and [custom models](https://developers.google.com/maps/documentation/javascript/3d/models).

Opening floors animates closer to the actual footprint and aims at the vertical center of the visible
stack. The default separation is 8 m. Google switches from HYBRID to SATELLITE, removing its POI/road
labels while preserving the photographic mesh and required attribution. A selected level switches to a
16-degree, north-oriented view. `indoor-camera.ts` fits geographic outlines and floor heights to the
35-degree camera FOV with room for the controls; narrow canvases receive a larger distance.
The room rail lists actual source rooms, scoped to the chosen level, with a name/number search. Choosing
a room selects its floor, flies to its source polygon bounds and adds a lime GLB just above
the slab. The room highlight uses exactly the same geographic anchor, scale and root transform as its
floor. Using a terrain-draped Google polygon was rejected after live testing showed it below the flat
model slab. Closing the card returns to the floor overview. Changing level clears the room search;
**Refocus floors** restores the current detail view after manual camera movement. **Back to 3D** restores
the exterior camera and labels. Camera transitions respect reduced-motion preferences.

`scripts/prepare_google_models.mjs` compiles rooms, door-cut walls and equipment from `building.json`
through the existing scene compiler, then exports indexed GLBs using Three.js. The geographic calibration
maps plan points to WGS84, then to local east/north metres at the catalogue anchor. Geometry is glTF Y-up;
the exported root converts it to Google's Z-up map frame. Scale remains one. No guessed building rotation
or location offset is applied. Source elevations determine each floor's position; walls are cut down to
1.2 m for inspection. Separated view raises the stack enough to expose the basement above Google's terrain;
selecting B1 alone also raises it for inspection. With zero separation, source floor elevations are used
and underground geometry is occluded by terrain. All placements include a 0.3 m surface clearance.

Regenerate the catalogue/calibration first, then run from the repository root:

```sh
node scripts/prepare_google_models.mjs data/dev/osm-way27917482/building.json
pnpm --dir web build
```

The command requires the existing Python environment with Shapely (`.venv/bin/python`, or set
`MODEL_PYTHON` to its executable) to prepare the display mask. It reads only the supplied building geometry
and catalogue, uses no provider API or key, and
writes content-hashed GLBs plus a manifest under `web/public/maps/models/<building-id>/`. The preparer's
Vite cache is separate from the development server to prevent dependency-cache invalidation and page
reloads during regeneration. The manifest
records source and calibration SHA-256 hashes, anchor, floor IDs and elevations. It also registers the
manifest in that catalogue entry. Rerun this command after regenerating the catalogue or changing the
source geometry/calibration. No building IDs are hard-coded in application logic. Current CIT assets
include approximately 16 MiB of floor meshes, fetched on requesting its interior. The 1,305 room-highlight
GLBs total 3.07 MiB; only the selected room's small asset is loaded. Every floor GLB is checked for
availability and binary structure before the flattener is attached; a missing asset leaves Google's
building visible with an error. Aborted preparations cannot attach models to another building.

Buildings without a calibrated frame open the original workspace. A calibrated building without exported
Google models falls back to its Campus floor view with an explicit notice. Google load errors offer a
return to Campus. Phone styles keep Google attribution above the bottom sheet.

Verification on 25 October 2026: 59 frontend tests, 23 building-view tests, 4 focused Python geometry tests,
TypeScript checks and production
build pass. Offline coverage includes footprint hit testing, camera fit, key clearing, cancellation,
missing assets, room selection, model filtering/altitudes, restoration, and an independent GLB world-bounds
test that catches the initially observed vertical-floor orientation error. Camera tests cover closer
entry, portrait fitting, stack height, floor/room detail, reduced motion and restoration. A source-fixture
UI test exercises room search, selecting the correct level, clearing searches and returning outside.

The closer-view iteration was tested at 1100×853 through CUA in the in-app browser; the Browser plugin
was not available. Real Google DOM attributes confirmed SATELLITE mode, approximately 609 m exterior,
447 m stack, 419 m level-2 and 39 m room-detail camera distances. The source room 02.06.011 was found
through the search rail and the camera reached that room with only its level visible. The final live
check used the local Vite server at `127.0.0.1:8013`, proxying the existing API on `8011`. It verified the
aligned lime room highlight, closing the card, clearing the search by changing levels, 0/8/12 m
separation, exposed B1 inspection, top-down, refocusing, exterior restoration and re-entry. Returning
outside left one Google map, no flattener, no floor/highlight models and no key-entry field; HYBRID labels
returned outside and SATELLITE removed them again on entry. No warnings or errors were recorded.
The same source was production-built for the existing preview on `8011`. Hot reload reuses the already
loaded public Google SDK namespace without reading its key. A full page reload still requires entry.

The production preview at `127.0.0.1:8011` was tested with the user's runtime Demo Key. **Go inside** removed
the real CIT shell and displayed five aligned floor models within the same Google map. Level 2 selection,
6 m and 12 m separation, basement selection, top-down view and **Back to 3D** were exercised against the real API. Return left one Google map,
zero flatteners, zero floor models and no key field. No console errors or warnings were recorded. A scan
of app sources, generated data, docs and the production build found zero embedded Google API keys. Screenshots
are kept outside the repository. The direct click on Google's opaque surface could not be automated
(closed shadow root); the live flow used **Go inside**, while click hit testing is covered offline.
The IAB viewport override did not change the tab's reported 1100×853 viewport; live Google verification
at a fixed phone viewport remains unconfirmed. Narrow camera fitting is covered offline.
