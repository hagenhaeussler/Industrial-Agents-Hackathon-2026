# Venue building: measurement handoff pending

No measured venue sketch or coordinates have been supplied to Hagen's builder.
There is intentionally no invented `building.json` here. A real venue model needs
the floor outline, room and doorway positions, widths, lift/stair stop positions,
floor elevations, actual part locations, and a documented origin in metres.
Marker positions also need a floor standing point and heading facing the code.

The validated fallback is the supplied procedural building
`data/dev/proc-factory-dev-003`. Its snapshot and three-stop route are published
in `fixtures/`. This represents an on-screen factory demo, not a measured model
of the hackathon venue. Manuel's Claude owns `demo/scenario.json` and should use
these facts to create the scenario rather than claiming a physical venue walk.

Use the building's `Office lift` (connector ending `-V02`) for a closure. Normal
walking can use the stairs; a step-free route across floors becomes unavailable
when no alternative lift path exists. Both behaviors are covered by core tests.

When measurements arrive, construct the kit-format building and equipment CSV,
record who measured it and expected accuracy, run `core.validate` and route
checks, then provide actual marker coordinates to Manuel's codex. Do not reuse
procedural coordinates under a real venue name.
