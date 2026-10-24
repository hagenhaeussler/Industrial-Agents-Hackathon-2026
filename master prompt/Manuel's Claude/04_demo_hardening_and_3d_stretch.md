# C04: Demo hardening, videos and the 3D stretch (after G5; Sunday 07:00–11:30 CET)

## 1. Outcome and user value

The live demo works twice in a row without a restart, the two 1-minute videos show the real product, and, if time allows, a stacked 3D view and a polished camera mode add the "wow" without risking the core journey.

## 2. Starting state

G5 passed (or its misses are listed). M03 decided the camera path. H04 recommended show/mention/cut for plan import.

## 3. Scope and ownership

`demo/SCRIPT.md` (pitch and video script with timings), video storyboard, `web/app/src/three/` (3D, lazy-loaded), camera mode UI around Manuel's codex's AR/overlay modules, plan-import UI only if H04 says "show".

## 4. Obligations

1. **Fix first:** every G5 miss in your area before any new feature.
2. **Demo script** (`demo/SCRIPT.md`): the MASTER_PLAN §7 demo (60 s), technical video (60 s) and 3-minute final, with exact spoken lines, who clicks what, fallbacks per step (MASTER_PLAN §6), and the Q&A answers. Ask the humans for the product name and closing line (Q-7) by 08:00 CET.
3. **Rehearsal support (G7 08:00 CET):** run the script with a timer; note every second over target; mirror phones (Android `scrcpy`, iPhone QuickTime) on the laptop layout you designed for the projector.
4. **Recording (08:30–09:30 CET):** desk at 1280×800 or 1920×1080, phone mirrored, daylight for camera scenes; capture raw clips; keep a backup clip of each aha moment.
5. **3D stretch (only after G5, lazy-loaded, behind a toggle):** react-three-fiber or plain three.js: floors extruded from polygons (`height_m`, `elevation_m`), exploded stack, active floor opaque and others translucent, route as a tube, stops as pins; must not slow the 2D path. Stop if not convincing by 03:00 CET.
6. **Camera mode UI:** "Start navigation" gesture → permissions → AR (Android) or overlay arrow (iPhone) from M03 modules; "Direction only" label on the overlay; "Scan the next code" when tracking is lost; denial → back to the map with a clear message.
7. **Labelled flourishes only:** simulated part movement or presence indicators carry "Simulated"; never shown as real tracking.

## 5. Interfaces

M03 `startAr/stopAr`, `arrowBearing`; H04 `import_plan` endpoint if shown.

## 6. Execution order

G5 fixes → script → (sleep) → 07:00 polish from rehearsal notes → 08:00 G7 → 08:30 recording → 09:30 edit support → 10:00 freeze (bug fixes only) → 11:30 final cut handed to the humans for upload.

## 7. Acceptance

Two consecutive full demo runs within target timings; both videos exported; the 3D view either works on the demo laptop at ≥ 30 fps or stays hidden.

## 8. Collaboration and Git

Branch `manuel-claude/web`; merges at Sunday windows; after 10:00 CET only fixes the captain approves.

## 9. Completion report

SHA; rehearsal timings; video file locations; what was cut.

## 10. Blocked-work behaviour

If the live phone path is unreliable at G7, switch the final to the recorded clips for Aha 2/3 and keep Aha 1 live.
