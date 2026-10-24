# C03: Admin changes, "How I calculated this", demo mode and polish (admin card + demo mode by G5 02:15 CEST; the rest in the stretch window until 03:00 CET)

## 1. Outcome and user value

The facility side of Aha 3 is clear and safe: the admin says or clicks "close the east lift", sees what will change, confirms once, and can undo. A new building can be uploaded as JSON and used immediately. The "How I calculated this" panel shows that the LLM interprets and the rules decide. Demo mode makes the three aha moments repeatable on stage.

## 2. Starting state

- M02: `propose_edit`, `commit_edit`, `undo`, `what_if` via `/api/tools/*`, upload `POST /api/buildings`, markers sheet, demo reset; admin voice agent via the hook.
- H03: edit semantics, validator report shape, hero building and scenario facts (or the factory fallback).
- Read: UX_REQUIREMENTS J6, J6b, J8; CONTRACTS §6, §8, §14.

## 3. Scope and ownership

`web/app/src/admin/`, `src/trace/`, `demo/scenario.json`, `demo/SCRIPT.md`, accessibility fixes across the app.

## 4. Implementation obligations

1. **Admin view (`/admin`, session role admin):** map with clickable lifts, stairs and doors ("Close…"/"Reopen…"), voice/text admin agent, preview card from the `propose_edit` response (summary, affected tours with before/after metres or "no route", newly unreachable rooms), **Confirm** (sends `commit_edit` with the stable `op_id`) and **Cancel**, event log with **Undo**, version conflict message with "Preview again". Desk users are not admins: the admin role is chosen explicitly (demo: `/admin?demo=hero`).
2. **Upload a building:** drag-and-drop `building.json` (+ optional `equipment.csv` if Manuel's codex supports it), validation report (errors block, warnings listed, stats), "Open in desk" after success.
3. **"How I calculated this" panel** (desk and admin): renders the `trace` of the last ToolResponses (resolve → plan_tour → route …, with arguments, timing, result summary) and the chosen profile; collapsible; plain language headings.
4. **Demo mode (`demo/scenario.json`):** building ID, desk start position, the parts to pick (asset IDs), the lift to close, expected detour, marker IDs; `?demo=hero` preloads it on desk, admin and phone; a visible but discreet "Reset demo" in admin calls `POST /api/demo/reset` and resets local state.
5. **Accessibility and readability pass:** keyboard access everywhere, focus order, labels, contrast on the projector, reduced motion, text alternatives (step lists) for map content.
6. **Bonus moment (if time):** a desk question "Water is dripping from the ceiling in office 0.29. What's above it?" highlights the room above on the next floor (chat → `spatial_query` tool with `kind: room_stacked`; floor switch animation).

## 5. Interfaces

CONTRACTS §6 preview payload, §8 ToolResponse `trace`, §7 upload and reset endpoints.

## 6. Execution order

Admin close/undo with preview card (25 min; until it lands, the admin path at G4 runs through the chat panel in an admin session) → demo mode + scenario (20 min) → G5 → trace panel (15 min) → upload (15 min) → accessibility pass (15 min) → bonus moment if time.

## 7. Acceptance

- U7 and U8 pass; G4 and G5 checklists (INTEGRATION §3) with your timings.
- Demo reset twice in a row returns to the identical starting screen.
- Screenshots of preview card and trace panel in STATUS.

## 8. Collaboration and Git

Branch `manuel-claude/web`; merge windows G4 (admin) and G5 (rest).

## 9. Completion report

SHA; scenario; timings; accessibility notes; known gaps.

## 10. Blocked-work behaviour

Voice admin not ready: buttons are the primary path (fallback in the demo script). Upload endpoint late: hide the upload entry rather than showing a broken control.
