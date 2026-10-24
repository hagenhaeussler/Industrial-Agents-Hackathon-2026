# Munich Urban Colab — photo-informed schematic demo

`building.json` is a canonical kit-format venue **demonstration model**, derived
from the seven supplied photographs and explicitly illustrative additions. It
loads through `core.building.load_building`, validates through
`core.validate.validate_building`, and routes through the existing core. The kit
under `data/` is unchanged.

## What the model represents

| Floor | Basis | Included features |
|---|---|---|
| Ground / 0 | Synthetic | Reception/coworking, demo entrance, service core and office wing. The source legend mentions reception on the ground floor; no ground-floor plan was supplied. |
| 1 | Synthetic, requested for the demo | Office/meeting/kitchen layout, lift and stairs. |
| 2 | Synthetic, requested for the demo | Office/meeting/kitchen layout, lift and stairs. |
| 3 | Photo-derived categories and adjacency; inferred geometry | Five meeting rooms, kitchen, WC/service core, lift, central stair flights, open offices, five-office side wing, Think Tank pods and an indicative terrace. |
| 4 | Photo-derived categories and adjacency; inferred geometry | Four meeting rooms, activity room/library, kitchen, WC/service core, lift, stair flights, office wing, open offices, Think Tank pods and side terraces. |

The photos are partial, perspective-distorted, and posted in different viewing
orientations. The model is an orthogonal schematic of the central area and an
office wing; it is **not a calibrated whole-building trace**. Joining the partial
views and aligning the floors involves inference. No metric scale or measured
reference was supplied. The schematic central area is 56 × 28 m, with an office
wing extending to 36 m in Y; floor elevations are spaced by an assumed 4 m and
clear floor heights are assumed 3.5 m. Door widths are illustrative too.

All `synthetic` flags are `true`, including photo-informed rooms, because their
numeric geometry is generated rather than surveyed. The sidecar carries the
more useful distinction: **observed category**, **inferred geometry**, and
**wholly synthetic floor or furniture**. German `source_label` values preserve
legible plan text; English names and generated room refs support the app. Those
refs are not actual venue signage.

The photographed two central stair-flight shapes are modeled as separate demo
stair stops, plus an office-wing stair; exact vertical correspondence is not
established by the photos. All four modeled connectors (one lift, three stairs)
span floors 0–4 for the demo. Actual lift availability, stair continuity, door
clearance and accessibility have not been surveyed. A small extra stair symbol
on floor 4 is represented locally without inventing another vertical link.

This is not an evacuation plan or verified real-world navigation. Distances are
distances in this schematic model. Follow the venue's own signs and instructions
for actual movement.

## Files and provenance

- `building.json`: five floors and their routable geometry, openings, connectors
  and illustrative assets.
- `equipment.csv`: the same asset inventory flattened into the kit format.
- `metadata.json`: floor, room, door, connector, dimension and asset provenance;
  SHA-256 hashes and original photo filenames; illustrative animation and route
  fixtures.
- `sources/`: all seven source JPEGs, copied **byte-for-byte** with readable names;
  no pixels or embedded metadata were edited. Hashes bind each copy to its source.
- `generate.py`: deterministic generator. No inference service or paid API calls.

Furniture is illustrative: tables, chairs, desks, sofas, refrigerator, coffee
machines, presentation displays and carts were not inventoried from the plans.
Think Tank pod categories are visible, while their precise positions and sizes
remain estimated. Source photos retain their original authorship; no claim is
made that the plan artwork has a newly assigned open license.

```sh
# Rebuild from checked-in photographs; no user-specific absolute path required.
python demo/colab/generate.py

# Optional alternate directory containing the seven original WhatsApp names.
python demo/colab/generate.py --photos /path/to/Fluchtplaene

python -m pytest -q tests/core/test_colab_building.py
```

## Integration contract

Building ID: `munich-urban-colab-demo`. Floor IDs:
`munich-urban-colab-demo-F0` through `munich-urban-colab-demo-F4`.
The initial displayed floor is 3 (`metadata.default_floor_level`). Coordinates
are local metres, X to the right and Y upward; the model is not georeferenced.

`metadata.floor_provenance[floor_id].basis` is `photo-derived` or `synthetic`.
Every room has a matching `space_provenance` entry. Absolute dimensions stay
`estimated_not_measured` even on photo-derived floors.

`metadata.movable_assets` supplies asset IDs, start/end coordinates, room/floor
IDs and duration. These are visual furniture rearrangements, not claimed live
sensor tracking. Each endpoint and connecting line lies in the same modeled
room. The three examples move a floor-4 coffee machine and kitchen table, and a
floor-3 mobile display. `metadata.walk_path` is a hand-placed, checked floor-4
kitchen-to-stairs sequence. It stays on one floor and crosses actual modeled
openings; it does not fake vertical travel. Optional cellular/network status
belongs in the application's session UX, not in invented building geometry.

`metadata.demo_routes` provides real core requests for coffee on floor 3 → coffee
on floor 4: a step-free lift route and a stair route with the lift closed. Closing
the only modeled lift also makes the same step-free request unreachable. These
are model properties, not statements about the real venue's accessibility.

## Validation

The dedicated tests check core validation, source hashes, deterministic
regeneration, CSV parity, non-overlapping room interiors, animation containment,
actual opening crossings, real cross-floor routes, absence of fallback drawing,
and correct unreachable behavior for a closed lift with step-free constraints.
They do not certify the photos' metric accuracy, actual evacuation behavior,
or correspondence of every inferred door and connector to the real building.
