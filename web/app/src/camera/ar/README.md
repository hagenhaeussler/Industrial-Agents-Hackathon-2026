# Marker frames and the device gate (CONTRACTS C1)

`buildingToXr(point, marker, floorY?)` implements CONTRACTS §11 exactly, in metres. The XR origin must be created while standing on the marker footprint facing `heading_deg`. Default `floorY` is −1.4 m; a caller may supply the floor height measured in the same local frame. A decoded QR supplies a declared point and heading under that standing protocol; it is not a measured camera pose.

`arrowBearing({position, headingDeg, deviceAlpha, nextWaypoint})` returns CSS clockwise degrees from straight ahead, or `null` at the waypoint/invalid input. `deviceAlpha` means **change since the marker scan**: call `orientationDelta(latestAlpha, alphaAtScan)` first. It is a relative rotation, not an absolute compass heading. With no motion permission pass `null` and keep the marker-relative arrow. Label the UI **Direction only**; there is no step counting or continuous localization.

The capability-only `DeviceGate` helper owns its camera/microphone streams and its test XR session. It stops media before requesting XR, requests required `local` and optional `hit-test`, `dom-overlay`, `local-floor`, and cleans up delayed camera permissions.

## Experimental current-floor AR line

`startAr({route, marker, container, overlay, stopCamera, onLost, signal?, floorY?})` returns a promise for `{stopAr()}`. Import this small module statically, then call it directly from the user's tap: it calls `stopCamera()` and requests the immersive session synchronously, before its first await. Three.js loads only after the session is granted. Do not await a capability check or dynamic import in the same tap before calling it. The UI should check support in advance and keep camera-arrow/2D guidance as its fallback.

Before starting, ask the user to stand on the scanned marker footprint facing its code direction again. The renderer calibrates that declared marker frame to the first actual WebXR viewer pose, including its origin and yaw. Default camera-relative floor height is −1.4 m; pass a measured negative `floorY` when available. The 16 cm ribbon sits 2 cm above that floor and draws only the supplied current-floor walking points, ending at the first stair/lift or floor change. It does not invent a line through a connector or across gaps. Provisional geometry, a different building, missing current-floor walking points, and invalid coordinates fail before permissions are requested.

Keep an `AbortController` per start and abort on unmount, route/marker change or exit; this also closes a session granted after cancellation and disposes a renderer that finishes loading late. Call `stopAr()` on the returned handle for an explicit exit. Native exit, page hide, hidden tab, renderer setup failure and sustained tracking loss release the session, animation loop, canvas and GPU resources. Native exit or tracking loss calls `onLost` with a fixed map/re-anchor message. To re-anchor, leave AR, scan the next marker, then start again while standing on it. No camera frames are accessed, saved or uploaded by this renderer.

This is an experimental implementation, not measured localization. No hit-test floor estimate, drift correction, automatic position update or physical corridor-alignment result is claimed. The requested optional hit-test/local-floor capabilities do not imply that either is used to measure the floor. The device gate and the 10 m / one-turn corridor check still require real Android/iPhone operators before showing AR in the live demo.

## Running the device gate

After the normal Vite build run from the repository root:

```sh
bun scripts/build-device-gate.ts
```

This bundles the installed `jsqr` dependency into `web/app/dist/devtest.js` and copies the standalone `public/devtest.html`. It needs no CDN, vendored source, package changes, or production SPA entrypoint changes. Serve `/devtest.html` through FastAPI (the integration captain aliases `/devtest`); open on both phones over HTTPS, or on Android through USB localhost forwarding.

For a local Vite-only check, build once as above and copy the generated bundle to `public/devtest.js` temporarily, or serve the built dist through FastAPI. Do not commit the generated bundle. Normal dev work on the SPA does not load the gate module.

Enter phone model/OS; press camera, microphone, both together, local QR scanning, test tone, AR support/session, and motion buttons. Copy the text log. The page never records, stores, or uploads frames/audio. QR payloads are displayed as text only. It releases streams/XR when hidden or closed. An operator must confirm whether the tone was audible with camera+microphone active; use headphones if needed.

Automated evidence: unit tests cover four frame headings, relative arrow maths, exact ribbon segments and connector boundaries, media cleanup/cancellation, XR feature request shape and ordering, delayed grant/renderer cancellation, native exit and tracking-loss cleanup, unsupported paths, and gesture-preserving motion permission. Renderer lifecycle tests use labelled offline browser/renderer doubles; they do not render on a real WebXR device. **Real Android/iPhone capability results, audio quality and AR alignment are pending H8. No live-device success is claimed.**

Primary references checked 24 October 2026: [WebXR requestSession](https://developer.mozilla.org/en-US/docs/Web/API/XRSystem/requestSession), [WebXR specification](https://www.w3.org/TR/webxr/), [Three.js AR renderer example](https://github.com/mrdoob/three.js/blob/master/examples/webxr_ar_hittest.html), [DeviceOrientationEvent](https://developer.mozilla.org/en-US/docs/Web/API/DeviceOrientationEvent), [Apple relative orientation guidance](https://developer.apple.com/documentation/webkitjs/deviceorientationevent), [jsQR usage](https://github.com/cozmo/jsQR).
