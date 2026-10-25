# Architecture image sources

These nine files support [Locora architecture and technical decisions](../../architecture-overview.md). They are unmodified copies. The source threads provide the context for the historical screenshots. Historical interface images are not fresh acceptance tests of the current deployment.

## Images supplied with the document request

| File | Original attachment basename | Content |
|---|---|---|
| [localization-frame-9983.png](localization-frame-9983.png) | `75d62475-0331-412d-b76f-68763758a820-ecf0ffd0-d10e-42e7-acf1-3f58c941089e.png` | Photo, point-cloud view, blend and plan; 161 inliers, 933 ms, 0.14 m to reference |
| [localization-frame-10927.png](localization-frame-10927.png) | `75d62475-0331-412d-b76f-68763758a820-b2484b69-a866-4e3f-bf1e-b2a814439a88.png` | Photo, point-cloud view, blend and plan; 511 inliers, 219 ms, 0.20 m to reference |
| [localization-frame-15090.png](localization-frame-15090.png) | `75d62475-0331-412d-b76f-68763758a820-037a3f9a-45b5-4bfd-881e-bbb70bab828c.png` | Photo, point-cloud view, blend and plan; 768 inliers, 207 ms, 0.46 m to reference |

The originals are in the local T3 attachment directory. The errors and timings above are read from each image, not inferred from the median results in the localization report.

## Images recovered from settled project threads

The source threads are [Build a Reusable 2D and 3D Visualization Engine](t3-thread://v1/d702769e-f87b-44f6-a112-b2cf91ed2af5) and [Plan Responsive Voice Agent Navigation UI](t3-thread://v1/d0237c5e-b2cd-498e-aeff-da9d1f859fa2). Both were settled when inspected on 25 October 2026.

| Local file | Original at a fixed Git revision | What it supports |
|---|---|---|
| [viewer-campus-route.png](viewer-campus-route.png) | [pr-campus-route.png](https://github.com/hagenhaeussler/Industrial-Agents-Hackathon-2026/blob/b7a7a8a37ac85f27d72e12b8e321ea3388ab7429/pr-campus-route.png) | Shared 2D and 3D scene; blue line is a test overlay |
| [viewer-floor-focus.png](viewer-floor-focus.png) | [pr-swiss-focus.png](https://github.com/hagenhaeussler/Industrial-Agents-Hackathon-2026/blob/b7a7a8a37ac85f27d72e12b8e321ea3388ab7429/pr-swiss-focus.png) | Focused floor with surrounding floors drawn as flat outlines |
| [desktop-voice-route.png](desktop-voice-route.png) | [voice1.png](https://github.com/hagenhaeussler/Industrial-Agents-Hackathon-2026/blob/a2749f6cec6001235983d4e6141b21f3ddccfeca/voice1.png) | Historical assistant response beside its route; team sidebar contains sample data |
| [phone-map.png](phone-map.png) | [phone-map.png](https://github.com/hagenhaeussler/Industrial-Agents-Hackathon-2026/blob/a2749f6cec6001235983d4e6141b21f3ddccfeca/phone-map.png) | Historical mobile map, route instruction and voice controls |
| [phone-camera.png](phone-camera.png) | [phone-camera.png](https://github.com/hagenhaeussler/Industrial-Agents-Hackathon-2026/blob/a2749f6cec6001235983d4e6141b21f3ddccfeca/phone-camera.png) | Camera layout with a simulated green background; no physical-camera localization evidence |
| [desktop-qr.png](desktop-qr.png) | [admin-qr.png](https://github.com/hagenhaeussler/Industrial-Agents-Hackathon-2026/blob/a2749f6cec6001235983d4e6141b21f3ddccfeca/admin-qr.png) | QR dialog with a localhost warning; no completed phone-handoff evidence |

The original asset branches were `assets/pr-14` and `assets/pr-23`. Local copies avoid dependence on those branches. These source links point to the fixed commits, rather than moving branch tips. The source repository requires access.

The localization photos show a real interior. This local documentation task does not publish them or change their access permissions.
