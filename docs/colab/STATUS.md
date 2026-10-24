# Colab demo implementation status

Date: 25 October 2026, Europe/Berlin. Branch: `hagen/colab-demo-20261025`.
This status belongs to this user-requested extension; it does not replace other
builders' single-writer STATUS files or claim their acceptance gates.

## Delivered

- Photo-informed Colab model at `demo/colab/building.json`: five floors, 138
  spaces, 139 openings, 140 assets and four vertical connectors. Ground/1/2 and
  all unmeasured values are explicitly generated; floors 3/4 are schematics
  based on seven supplied photographs, preserved with hashes and provenance.
- Dedicated `/colab` frontend, desktop/phone layouts, interactive isometric
  floor/furniture views, public QR handoff, and occasional synchronized
  furniture movements. Explicitly simulated walk follows a validated path.
- Persistent shared state, manual markers, authenticated collector pairing,
  private Wi-Fi survey/capture, conservative fingerprint matching and stale/
  ambiguous-data handling. No browser scan or cellular indoor-location claim.
- Android/Termux, Linux and optional macOS native bridge; collector download,
  model download, setup documentation and positioning research.
- New survey/model revisions invalidate old calibration and fixes, retain a
  monotonic sequence and cause open clients to reload the new model. Delayed
  scans cannot overwrite or remove newer fixes; individual aged AP readings
  are excluded when capturing calibration.

## Checks actually run

- `.venv/bin/python -m pytest -q` during implementation: **522 passed** in
  77.79 seconds before the final ordering/model-revision regressions.
- `.venv/bin/python -m pytest tests/server/test_colab.py -q` after the first
  independent review fixes: **13 passed**.
- Independent model tests: **5 passed**; independent continuous-walker sample
  check: 600 half-second samples over five simulated minutes, no room errors
  or discontinuities.
- Pure localization and collector tests: **24 passed**, using synthetic test
  vectors. These do not measure real radio accuracy.
- Frontend `bun test src`: **182 passed** at the frontend handoff. Production
  TypeScript/Vite build passed again after updating the model-revision fixture.
- A full check found one stale frontend test fixture missing `model_revision`;
  the fixture was corrected and the production build passed. Final combined
  checks and integration with the latest teammate main are recorded below.
- Browser: actual DOM dimensions verified at 1280×800 and 390×844; no horizontal
  phone overflow, desktop controls fit the viewport. Floor switching, manual
  room placement, the same marker on two tabs, simulated walker labeling,
  admin collector pairing and no-scan calibration rejection were verified.
  A failed exact room-label locator was corrected to the observed selector;
  it was an automation selector mismatch, not a failed room-selection feature.

## Limits and next physical steps

No live Colab RSSI survey, phone native collector, held-out positioning accuracy,
independent iPhone localization, real AP coordinates or cellular indoor fix has
been demonstrated. The radius is an uncalibrated heuristic. User-provided
Android and iPhone are available; the next physical task is a fresh native scan
and 10–20 correctly labeled reference points on floors 3/4, then held-out tests.
The existing QR/manual sources remain available.

No paid provider calls were made for this extension. Immutable kit data,
benchmark labels and existing agent inference were not edited.

## Final integration and release

Pending final combined check and PR/release record. No new cloud deployment is
claimed by this status until a verified deployment ID and exact SHA are recorded.
