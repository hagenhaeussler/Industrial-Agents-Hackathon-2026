# Workspace equipment selection

Base and pull request target: `t3/rewrite-synera-project-baseline`.

## Delivered behavior

- Equipment types expand into selectable items. Every type and item remains available.
- Search matches equipment names, IDs, types, room names, room refs and floor names.
- Items show their ID and location to distinguish repeated names.
- Selection uses the workspace's existing details, floor focus, highlight, route and move actions.
- Choosing an item through the browser or top search returns to the select tool and shows equipment.

## Checks run

- `pnpm --dir web check`: passed.
- `pnpm --dir web test`: 22 tests passed, including 10 equipment browser tests.
- `pnpm --dir web build`: passed. Vite reports bundles larger than 500 kB.
- `pnpm --dir packages/building-view test`: 22 tests passed.
- `pnpm --dir packages/building-view check`: passed.
- `git diff --check`: passed.
- `scripts/check.sh`: unavailable on the rewrite branch. The checks above are the commands from this branch's web documentation.

The first equipment test run failed in two search cases. The fixture's equipment name contained the same number as the floor query. The test now uses a distinct floor name to check location filtering without ambiguous matches. The final run passes.

## Browser evidence

Used the real local building API with imported dev building documents. No paid provider calls were made.

Verified at 1440 x 900 and 1280 x 800:

- Select items on the ground floor and floor 2. The details, selected row and floor agree.
- Set the start from equipment and route to equipment on another floor. The API returned a 39 m route with eight steps.
- Select an item with Tab and Enter.
- Search with no matches, clear search, expand the 192-chair type and select its last item.
- Scroll the long equipment list while the sidebar footer stays visible.
- Switch to floor plans while preserving the selected item and floor.

Screenshots: `equipment-selection-desktop.png` and `equipment-selection-plan-1280.png`, uploaded on the separate `assets/workspace-equipment-selection` branch and embedded in the pull request.

The T3 preview snapshot timed out twice. Browser checks used the Playwright CLI skill with the installed Chromium test browser.

## Existing limitation

At a 390 px viewport, the desktop workspace's fixed side columns leave the map at 0 px width and produce horizontal overflow. This layout predates the equipment change. A separate responsive workspace layout is needed.
