---
name: Alain building guide
description: A camera-first indoor navigation prototype with white floating controls and a living Blobatar.
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
- Chat: locally scripted, clearly marked demo replies. Named destinations switch the demo route. Do not claim a connected language model or real localization.

## Do's and Don'ts

Keep the camera visible and floating surfaces white, except for the red camera-off control. Keep text black or readable dark gray. Use the accent for navigation. Explain example data in route details and scripted replies in chat. Keep the main view free of repeated demo labels. Do not randomize the avatar name, pin its shape or palette, simulate live location as real data, or add decorative dashboard chrome.
