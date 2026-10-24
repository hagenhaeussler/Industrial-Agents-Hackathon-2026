---
name: Talk to Your Building
description: Desk planning and phone guidance for finding parts in an unfamiliar building; white floating controls, an architectural floor map and a living Blobatar.
---

## Overview

The camera owns the screen. Compact controls sit above it to keep the route visible. The visual language is quiet, architectural and friendly. This is a phone-first tool for visitors finding equipment and rooms. The camera icon starts camera access. An illustration fills the view while the camera is off.

References: the user's approved navigation mockups set the full-screen composition. The [Blobatar editor](https://blobatar.dev/editor) supplies the exact name-based identity. Its [React source](https://github.com/Alain00/blobatar/blob/main/packages/blobatar/src/react.tsx) and motion styles establish the inline SVG animation. The identity comes only from `alain00`.

## Colors

- Primary ink: `#191c16`. Text, buttons and route symbols.
- Surface: `#ffffff`. Floating controls and dialogs.
- Background: `#f4f3ee`. Camera-off fallback.
- Route accent: `#dcff58`. Visible path and current step.
- Secondary text: `#64685f`. Supporting labels on white.
- Divider: `#e9eae3`.
- Camera off: `#c83432`, with a white icon.

## Typography

Use locally served Manrope Variable. Route instructions use 17–21px, weight 750, tight spacing. Dialog titles use 26px. Normal interactive text uses 12–16px. Small map labels are secondary information. Inputs use 16px to avoid mobile browser zoom. All actionable controls have explicit accessible names.

## Layout

Use the full small viewport height and safe-area insets. The floating route sits 14px from the phone screen edge, with a 620px maximum width. Desktop offsets use 20px. The minimap aligns to the route's right edge below it. Its width is 144px on phones, with 6px padding and a tightly cropped map. The bottom agent dock has a 440px maximum width. The central route overlay has a 560px maximum width and scales vertically with the viewport. Dialogs scroll independently and use native modal focus behavior.

## Elevation & Depth

White controls use a restrained shadow: `0 6px 28px #20251b12, 0 1px 3px #20251b0a`. Do not blur camera content. A dimmed backdrop separates dialogs from the navigation view.

## Shapes

The route panel uses a 20px radius. The minimap uses 14px. Buttons use 12–15px. Modal sheets have 30px top corners on mobile and 28px corners on desktop.

## Components

- Route banner: large turn symbol, current instruction, destination and meters. Opens route details.
- Minimap: current floor, schematic route and position marker. Opens destination selection.
- Camera control: one 44px icon button. Red while off, white while live. Its accessible name explains the action.
- Camera: rear-facing preferred, no audio, no recording, no upload. Handle denied, missing, busy and interrupted cameras. Cancel late requests and stop tracks on teardown.
- Agent: exact `alain00`, `animate="always"`, built-in idle expression. Use the happy expression on arrival. Respect the library's reduced-motion setting. Do not animate the rest of the interface continuously.
- Chat: live screens show replies and tool displays from the server, with text fallback when voice fails. The separate prototype keeps clearly marked scripted replies. Position comes from confirmation, codes and manual steps.

## Desk and map

- Home shows only the product name and the shared voice orb, centered with a gentle idle animation. Clicking the orb opens team selection; selecting a team slides in its building list. A new building uses two upload boxes: equipment CSV and a structured JSON floor plan. Creation retains the private access-code gate. Teams organize the shared preview catalog; they are not access-control boundaries.
- The desk is a plan table: conversation, start, mobility and searchable parts share the left white panel (392px, 20px inset, 20px radius). The planning action stays at its bottom. The rest of the desktop belongs to the map. At widths up to 1100px, stack map → controls and independently scrolling parts → planning action.
- The left panel reads "What do you need?" (26px, 750) → start chip ("You are at …") → mobility → parts grouped by floor and room. Planning uses optimized order and finishes at the last collected part. After planning, the existing tour summary opens on the left: policy label, stops and metres (30px), numbered stops, "Send to phone". "Change parts" restores the list and focuses its search. Calculation explanations and diagnostic timing are omitted; the server does not build explanation traces. Keep-order and finish-location controls, the repeated product caption and floating equipment cards are omitted.
- Desktop maps show roofless isometric slabs built from actual room polygons, with a shared 30° affine projection after `toSvg`. Routes, doors, parts and positions share the same transform. Slab thickness and floor separation are diagram spacing, not measured heights. Adjacent floors sit slightly closer; the active floor is substantially enlarged and centered while other floors recede as context. Selecting a small floor button, slab or keyboard-focusable plane moves focus to that floor and clears any equipment framing. Compact floor controls show 36px circular bubbles within 44px hit targets. Repeated floor-name pills, upright room-reference labels and floating asset-name labels are omitted from the desk. Reduced motion disables transitions. Phone widths, phone guidance, single-floor buildings and admin retain the flat map.
- Map: building metres, y flipped by `toSvg`. Rooms are quiet tints by type (circulation lightest, halls and zones a shade darker, stairs and lifts a soft green-grey), hairline walls, door gaps, other floors as faint dashed outlines. Parts are small grey dots; chosen parts are ink dots. Closed elements are hatched red. Flat phone/admin maps retain their useful labels.
- The route is the one bold element: ink outline under the accent line, drawn in 1.2s (instant with reduced motion). Stops are ink discs with accent numbers; collected stops turn grey with a tick. "You" is a white disc with an ink centre. Lift and stair pills on the route switch floors.
- The floor switch sits top right, highest level first, as separate round number bubbles with no enclosing card, floor-name text or stop-count badges. Use the building's numeric level (0 for ground; negative levels for basements). The active circle is ink with an accent number. Full floor names remain accessible to screen readers. Zoom and fit controls sit bottom right.
- The handoff dialog shows a large QR, the short link and a status line that turns accent when the phone opens the tour.

## Phone journey and admin

- Phone: route banner on top (turn symbol, instruction, next stop, metres to the next step), the map in the middle with the current leg bold and later legs as a quiet dashed line, the guidance dock at the thumb: avatar and status, progress dots (ink done, accent now, hatched red unreachable), one big primary action ("Next step", "Got it", "I have arrived"). Changes arrive as an accent notice that says what happened and what it means for this tour.
- Start: "Are you at …?" first, with "Yes", "Scan a position code" and "Choose my room". Position is never claimed without one of them.
- Camera mode: a direction-only arrow over live camera frames; a scanned code supplies the standing point and facing direction. Without a code or after a floor change, ask for the next code. Denied access keeps a clear return to the map.
- Admin: same plan-table layout as the desk. Every change shows an ink-bordered preview card first; Confirm is the only primary action. The admin code card appears before anything else when the server asks for it.

## Do's and Don'ts

Keep the camera visible and floating surfaces white, except for the red camera-off control. Keep text black or readable dark gray. Use the accent for navigation. Explain example data in route details and scripted replies in chat. Keep the main view free of repeated demo labels. Do not randomize the avatar name, pin its shape or palette, simulate live location as real data, or add decorative dashboard chrome.
