# M03: Device gate and camera navigation (device gate by 00:00 CEST with humans; AR implementation only after G4 is green; stop at 03:00 CET)

## 1. Outcome and user value

We know, from the real phones, what works: camera and microphone together, in-app QR scanning, WebXR on Android, motion permission on iPhone. Then, if time allows, the route appears as a line on the real floor (Android) or as a direction arrow over the camera (iPhone), anchored by the position marker. This is the Level-5 extension and the visual punch of Aha 2. It never blocks the 2D journey.

## 2. Starting state

- HTTPS URL from M01 (Railway) or Android USB port forwarding. Prototype camera hook `web/app/src/camera/useCamera.ts` (rear camera, no audio, no recording, robust cleanup) is Claude's and stays the camera lifecycle owner for the 2D/overlay view.
- Marker model and frame maths: CONTRACTS §10–§11. Polylines from H02.
- Research caveats: a decoded QR is not a camera pose; iOS Safari has no `immersive-ar`; `BarcodeDetector` is off by default on iOS (use jsQR); stop `getUserMedia` before starting an XR session.

## 3. Scope and ownership

Own `web/app/src/camera/ar/` (`frames.ts` + tests, `deviceGate.ts`, `ArSession.ts` (three.js + WebXR), `OverlayArrow.ts` (bearing maths), `README.md`) and `agent_output/reports/device-gate.md` (or the same content in STATUS). Claude owns the camera mode UI, permission prompts and fallbacks in the visible app; agree on a small interface: `startAr({route, marker, onLost}) / stopAr()` and `arrowBearing({position, headingDeg, deviceAlpha, nextWaypoint})`.

## 4. Implementation obligations

1. **Device gate page** `/devtest` (unlinked route, ask Claude to mount it or mount a plain HTML file under `web/app/public/devtest.html`): buttons to (a) start rear camera, (b) start mic + an ElevenLabs session (or `getUserMedia({audio:true})` if voice is not ready), both at once, (c) scan a QR with jsQR from the camera stream, (d) `navigator.xr?.isSessionSupported('immersive-ar')`, request a session with `requiredFeatures: ['local']`, `optionalFeatures: ['hit-test', 'dom-overlay', 'local-floor']`, (e) `DeviceOrientationEvent.requestPermission()` on iOS. Log results with device model and browser version. Run with the humans (H8) on both phones; write the results table.
2. **Decision from the gate** (record in STATUS): Android AR path yes/no; iPhone overlay yes/no; whether audio plays correctly with the camera running (if not: headphones in the demo).
3. **`frames.ts`:** CONTRACTS §11 transform with unit tests for headings 0°, 90°, 180°, 270° and a known point.
4. **Android AR (after G4):** three.js scene with the route polyline of the current floor as a flat ribbon 2 cm above `floorY`, starting at the marker standing point; next-maneuver label in `dom-overlay` if available; exit button. Re-anchor flow: exit AR → scan next marker → restart. Success criterion: standing on the start sticker facing the code, the line follows the corridor for 10 m and stays within ~0.5 m after one turn (measure with the humans; record honestly).
5. **iPhone overlay:** arrow angle = bearing to the next waypoint relative to the marker heading, corrected by device orientation alpha changes since the scan; no compass, no step counting; label "Direction only".
6. Respect the prototype rule: no recording, storing or uploading of camera frames.

## 5. Interfaces

Exported functions above, documented in `camera/ar/README.md`; Claude integrates them into Camera mode and handles permission/denial UI.

## 6. Execution order

Device-gate page (15 min of your time, as soon as an HTTPS URL exists; the humans run it on both phones while you continue M02 and paste the results to you) → decision → `frames.ts` + tests (15 min) → after G4: Android AR (60 min timebox) → iPhone arrow (30 min timebox) → hand over to Claude.

## 7. Acceptance

Device gate table with both phones; `frames.ts` tests green (`bun test`); AR success criterion measured or the feature marked "not shown live"; a 10–15 s screen recording of the Android line for the demo video if it works.

## 8. Collaboration and Git

Branch `manuel-codex/platform`. AR merges only if it cannot break the 2D path (feature behind Camera mode, lazy-loaded three.js chunk).

## 9. Completion report

Device table; decisions; measured AR quality; recording path; limits.

## 10. Blocked-work behaviour

XR unsupported or unstable: ship the iPhone-style overlay on both, or cut camera mode to "camera background + 2D directions". Never block integration duties for AR; at 03:00 CET stop.
