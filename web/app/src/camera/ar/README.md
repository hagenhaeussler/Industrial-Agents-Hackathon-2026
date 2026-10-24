# Marker frames and the device gate (CONTRACTS C1)

`buildingToXr(point, marker, floorY?)` implements CONTRACTS §11 exactly, in metres. The XR origin must be created while standing on the marker footprint facing `heading_deg`. Default `floorY` is −1.4 m; a caller may supply the floor height measured in the same local frame. A decoded QR supplies a declared point and heading under that standing protocol; it is not a measured camera pose.

`arrowBearing({position, headingDeg, deviceAlpha, nextWaypoint})` returns CSS clockwise degrees from straight ahead, or `null` at the waypoint/invalid input. `deviceAlpha` means **change since the marker scan**: call `orientationDelta(latestAlpha, alphaAtScan)` first. It is a relative rotation, not an absolute compass heading. With no motion permission pass `null` and keep the marker-relative arrow. Label the UI **Direction only**; there is no step counting or continuous localization.

The capability-only `DeviceGate` helper owns its camera/microphone streams and its test XR session. It stops media before requesting XR, requests required `local` and optional `hit-test`, `dom-overlay`, `local-floor`, and cleans up delayed camera permissions. No scene or AR line is implemented before G4.

## Running the device gate

After the normal Vite build run from the repository root:

```sh
bun scripts/build-device-gate.ts
```

This bundles the installed `jsqr` dependency into `web/app/dist/devtest.js` and copies the standalone `public/devtest.html`. It needs no CDN, vendored source, package changes, or production SPA entrypoint changes. Serve `/devtest.html` through FastAPI (the integration captain aliases `/devtest`); open on both phones over HTTPS, or on Android through USB localhost forwarding.

For a local Vite-only check, build once as above and copy the generated bundle to `public/devtest.js` temporarily, or serve the built dist through FastAPI. Do not commit the generated bundle. Normal dev work on the SPA does not load the gate module.

Enter phone model/OS; press camera, microphone, both together, local QR scanning, test tone, AR support/session, and motion buttons. Copy the text log. The page never records, stores, or uploads frames/audio. QR payloads are displayed as text only. It releases streams/XR when hidden or closed. An operator must confirm whether the tone was audible with camera+microphone active; use headphones if needed.

Automated evidence: unit tests cover four frame headings, relative arrow maths, media cleanup/cancellation, XR feature request shape and ordering, unsupported paths, and gesture-preserving motion permission. **Real Android/iPhone capability results, audio quality and AR alignment are pending H8. No live-device or route-overlay success is claimed.**

Primary references checked 24 October 2026: [WebXR requestSession](https://developer.mozilla.org/en-US/docs/Web/API/XRSystem/requestSession), [WebXR specification](https://www.w3.org/TR/webxr/), [DeviceOrientationEvent](https://developer.mozilla.org/en-US/docs/Web/API/DeviceOrientationEvent), [Apple relative orientation guidance](https://developer.apple.com/documentation/webkitjs/deviceorientationevent), [jsQR usage](https://github.com/cozmo/jsQR).
