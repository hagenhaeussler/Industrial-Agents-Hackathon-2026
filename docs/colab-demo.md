# Munich Urban Colab showcase

This extension adds `/colab` to the existing SPA and one kit-compatible building
at `demo/colab/building.json`. The original desk, phone journeys, voice agents,
benchmark inference and immutable kit files keep their existing contracts.

## What the model represents

The supplied evacuation-plan photographs guide floors 3 and 4. Ground, floors
1 and 2, unmeasured dimensions and furniture are illustrative. Read the model's
`metadata.json` and `README.md` for per-feature provenance. This is a schematic
demo model, not a measured digital twin or evacuation guide. It has a lift and
stairs across levels and can also be selected in the regular building catalog.

The dedicated view offers focused and exploded floor views, furniture selection,
shared visitor markers, uncertainty styling, and an explicitly simulated walk.
Only a few furniture pieces are eligible for automatic movement. The first
movement starts after about 35 seconds of viewing, subsequent movements are
spaced about 80 seconds apart and take seven seconds. All clients see the same
server-generated event. Pausing freezes the overlay. Reduced-motion settings
skip interpolation. The overlay never edits building geometry or claims that
objects are being physically tracked.

## Positioning: live connection versus a measured position

Mobile data and Wi-Fi can both carry the HTTPS requests. Neither connection
automatically gives this application an indoor coordinate or floor number.
Browser geolocation is an OS estimate and cannot by itself establish this model's
local coordinate frame or floor. The report in
[`research/2026-10-25-colab-wifi-positioning.md`](../research/2026-10-25-colab-wifi-positioning.md)
compares cellular, Wi-Fi, RTT, GNSS, Bluetooth and marker approaches, with primary
sources and the device restrictions.

For the available Android and iPhone, the practical experiment is:

1. Use Android, or a supported laptop, as an **explicitly paired native Wi-Fi
   collector**. The web browser cannot scan neighboring BSSIDs/RSSI values.
2. On floors 3 and 4, stand at known locations and save fresh fingerprints against
   corresponding map points. Router coordinates are unnecessary for this method.
3. Collect new scans. The server compares them to the survey and publishes a
   low-confidence nearest-reference estimate only when the pattern is sufficiently
   distinct. It refuses stale, synthetic, incomplete and ambiguous measurements.
4. Open the same `/colab` view on the phone and desktop. Both show that device's
   shared estimate. An iPhone viewing an Android estimate is **not an independently
   localized iPhone**.
5. Validate at held-out points, on both floors and while carrying the phone in
   different orientations. Until that is done, the uncertainty radius is a
   display heuristic, not measured positioning accuracy.

No real venue Wi-Fi readings, AP survey or on-device accuracy measurements are
included with this implementation. Fake AP readings are never automatically
enabled. Manual placement and simulated visitors have separate visible sources.

## API and calibration workflow

`GET /api/colab/model` returns the building and provenance sidecar.
`GET /api/colab/state` returns shared furniture/visitor positions, active
movements and server time; clients poll this feed. Positions include source,
confidence, update time, staleness and an optional heuristic radius.

Public demo controls affect this showcase overlay only:

- `POST /api/colab/demo` with `{ "running": true }` toggles furniture movement.
- `POST /api/colab/demo/walk` toggles the labelled simulated visitor.
- `POST /api/colab/positions` accepts a manual or simulated marker inside a room.
  It does not accept `wifi_fingerprint` as a caller-declared source.

Real scan ingestion is separate:

- `POST /api/colab/pair`, with the existing private admin code in
  `X-Admin-Token`, returns a random receive-only collector token and device ID.
  The token is valid for 12 hours, is bound to the device ID and is stored hashed.
  The response uses `Cache-Control: no-store`. Never put this token or the admin
  code in a URL, QR code, Git commit or shell history.
- `POST /api/colab/wifi/scans`, with the pairing token in `X-Colab-Token`, accepts
  `{ "device_id": "...", "label": "Survey Android", "scan": { ... } }`.
- `GET /api/colab/wifi/status` reports survey counts and recent collector
  heartbeats without exposing raw radio identifiers or measurements.
- `POST /api/colab/wifi/capture`, with `X-Admin-Token`, binds a device's latest
  fresh scan to `{ "device_id", "floor_id", "x", "y", "label" }`. The room is
  derived from the model. A point outside the selected floor's rooms is rejected.
- Alternatively `POST /api/colab/wifi/calibration`, with `X-Admin-Token`, replaces
  the survey using the schema documented in `core/localization.py`. Every point
  is validated against its claimed room and floor. Replacing the survey clears
  previous Wi-Fi fixes so they must be reacquired.

The native bridge is `scripts/colab_wifi_collector.py`. Its default is finite,
local capture only. Upload is opt-in through `--endpoint` and the environment
variable `COLAB_TRACKING_TOKEN`. Its `--device-id` must match the paired device.
For example, after installing Termux and the matching Termux:API companion and
granting the required permissions:

```sh
python scripts/colab_wifi_collector.py --source termux --count 1
```

The Android bridge reads cached OS scan results and checks their native monotonic
timestamps. Repeated reads do not force a new radio scan or bypass Android's scan
throttling. If results are stale or unavailable, the demo must show no current fix.
The report gives installation, survey and troubleshooting steps. The same bridge
has a Linux `iw` source, an optional permission-dependent macOS CoreWLAN source,
and a JSON input seam for other native collectors.

## Persistence and operation

Production configuration loads `demo/colab` by default through
`COLAB_MODEL_DIR`. Explicitly constructed test settings leave this extension
unconfigured unless a model directory is supplied. Shared demo state, private
fingerprints and hashed receive tokens use `STATE_DIR/colab.sqlite3` on the
existing Railway volume. No extra service or paid provider call is required.

Run the repository's normal `scripts/check.sh` before merging. Additional
focused coverage lives in `tests/core/test_colab_building.py`,
`tests/core/test_localization.py`, `tests/server/test_colab.py` and the frontend
Colab tests. Automated sensor tests use explicitly synthetic test fixtures; they
do not establish real venue accuracy or native-phone acceptance.
