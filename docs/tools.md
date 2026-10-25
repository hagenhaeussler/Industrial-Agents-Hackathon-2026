# Locora building tools

Status: nine tools are implemented in `building_tools/` with tests. `building_tools/server.py` publishes them as
an MCP server for one building. Together they cover all nine benchmark kinds.

## Rules for every tool

- The tool calculates every number and count. The model never calculates.
- Tools take entity IDs. `find_spaces` turns names from a question into IDs.
- Results are typed Pydantic models with IDs, names and units. Floats are rounded to centimetres or finer.
- A request the building cannot answer raises `ToolInputError` with a message for the agent, for example
  an unknown ID, an unknown floor or a missing floor above. The message names the valid choices when useful.
- Ambiguity stays visible. `find_spaces` returns every match, so duplicate room names are not resolved by
  chance.
- Tools are generic. Their parameters describe building facts, not question wording. The README definitions
  are their defaults.
- Tools read the database through `building_tools.building.load`. Room areas come from the stored `area_m2`
  column. Overlaps and shared walls are calculated per request, so they stay correct after an edit.

## Tool list

Kinds and test counts come from `data/test/*/questions.jsonl` (145 questions).

| Tool | Input | Output | Kinds (test questions) | State |
|---|---|---|---|---|
| `building_overview` | building | Floors from lowest to highest with level, name and elevation. Stairs and lifts with IDs and names. Space, room and asset types with counts. | All, to map "floor 2", "Lift 1" or "generic room" to data | Done |
| `find_spaces` | name or ref, floor, space type, room type, limit (all optional) | Matches, largest first, with ID, name, ref, floor and area. Count and total area of all matches. | `largest_room` (21), `floor_area_total` (33), room lookup everywhere | Done |
| `find_assets` | asset type, name text, space, floor, limit | Assets with type, position and their space | `errand` (20), warm-up locate and count | Done |
| `stacked_spaces` | space, direction, number of floors | Overlapping spaces on the target floor, largest overlap first, with m² and shares | `room_stacked` (9) | Done |
| `shared_walls` | space, counted space types, minimum length, maximum gap | Counted and not counted neighbours with shared wall length, and the count | `shared_walls_count` (26) | Done |
| `distance_3d` | two spaces | Both centres as x, y, z and the distance | `straight_line_3d` (15) | Done |
| `route` | two or more stops, route conditions, optional conditions per leg | Total length; per leg the length, spaces passed and openings, stairs and lifts used, or the conditions that block it | `errand` (20), warm-up routes and tours | Done |
| `reachable_spaces` | start, route conditions, floor, space type, room type and asset type filters | Reachable spaces nearest first with walking distance, and the count | `wide_delivery_count` (18), `step_free_reachable_count` (0), nearest item for `errand` | Done |
| `exit_distance_change` | floor, the change (added doors, closures), minimum change | Spaces whose walk to the nearest entrance got shorter or longer, before and after, and both counts | `what_if_door` (3) | Done |

## Route model

`walks.py` computes walks inside one space. `network.py` builds the walking network for one set of
`RouteConditions` and `routes.py` holds the three route tools. The rules follow README section 3 and the organizer
rules in [challenge.md](challenge.md):

- Nodes are space centres (`representative_point`) and openings. Walks inside a space join its centre and its
  openings on `buffer(-0.15)` through a visibility graph; openings land at `buffer(-0.30)`. Edges are rounded to
  millimetres.
- Stairs cost 2 m per metre climbed, one edge per flight. A lift costs 15 m once per ride plus 1 m per metre.
- An entrance belongs to one space, so no route goes round the outside.
- `RouteConditions` holds every rule: `step_free`, `min_door_width_m`, `closed` element IDs, `added_doors` and
  `no_pass_through_room_types`. A space that may not be passed through can still be entered as a destination
  and left as a start; this applies to walks, stairs and lifts.
- Room types compare in plain words, so "production zone" matches `production_zone`. An unknown room type is an
  error that lists the known types, in route conditions and in every room type filter. A typo must not turn
  into a count of 0 or a route through a space it was meant to avoid.
- The graph is directed only for that rule. All other edges go both ways. Parallel edges are kept.
- Walks inside each space are cached on the loaded building. A space with an added door is computed fresh.

Checked against the dev warm-up answers: all 161 routes match length, space sequence and element sequence. All
route and tour lengths in train and dev match to the centimetre. The source order of openings is not kept in the
database, so in a tie between equal-length routes another sequence could be chosen. Such a sequence scores the
same.

## Definitions checked against the answers

The README definitions were checked against every train and dev answer of each kind. Answers and `inputs`
serve only as test data.

| Kind | Definition used | Result |
|---|---|---|
| `largest_room` | Largest stored area among spaces of the room type on the floor | 96 of 96 |
| `floor_area_total` | Sum of stored areas of the room type on the floor | 181 of 181, within 0.01 m² |
| `room_stacked` | Largest polygon overlap on the next floor up or down | 26 of 26 |
| `shared_walls_count` | At least 1 m of one outline within 0.35 m of the other. Count spaces of type `room` and `hall` only. | 143 of 143 |
| `straight_line_3d` | Distance between polygon centroids at the floors' `elevation_m` | 30 of 30, within 0.01 m |
| `errand` | Nearest space holding the asset by walking distance, then a route through it to the largest space of the room type | 93 of 93 |
| `wide_delivery_count`, `step_free_reachable_count` | Step-free, width or closure conditions; count reachable spaces of type `room` on the floor | 82 of 82 |
| `what_if_door` | New 0.9 m step-free door in the middle of the shared wall; count rooms whose walk to the nearest entrance gets more than 1 m shorter | 4 of 4 |

"Rooms" in `shared_walls_count` means types `room` and `hall`. Balconies have type `outdoor` and do not count.
Counting all types except corridors, stairs and lifts gave only 90 of 143. Counting only type `room` gave 124.
Reachability counts use the other meaning: only type `room`. Counting halls too gave 61 of 80. The instructions
tell the agent: "rooms" are type `room`, unless the question lists what does not count; then rooms and halls.

The door position matters. The middle of the shared wall gives 4 of 4 `what_if_door` answers. The midpoint of the
two nearest points of both outlines, which the kit's starter agent used, gives 3 of 4.

## Stacking

`stacked_spaces` takes the number of floors as a parameter. Do not chain two one-floor calls. The space two
floors up with the largest overlap differs from "the space above the space above" for 317 of 3,581 rooms (9%),
because the space in between can be larger or offset.

The result lists every overlap with its share of the start space. In all 26 train and dev questions, the
answer covers 65% to 100% of the start space and the runner-up at most 19%. A long list of small overlaps
therefore does not hide the answer.

Swiss buildings do not share one XY frame between floors. The README limits stacking questions to procedural
and OSM buildings. The tool does not detect misaligned floors.

## Story details in questions

Questions wrap the task in a story, such as a leaking washing machine or water dripping from a ceiling. The
story does not match the building data:

- In 0 of 14 "leaking" questions does the start room hold a washing machine.
- In 0 of 12 "dripping" questions does the answer room hold a water asset (sink, toilet, shower, bathtub,
  washing machine or dishwasher).

The benchmark agent must therefore apply the geometric definition and treat story details as context only.
The agent could combine `stacked_spaces` and `find_assets` to reason about likely water sources, but that would
give wrong benchmark answers. Such hints can suit the free ElevenLabs conversation, which gets its own prompt.

## Verification

```bash
uv run python -m unittest discover -s tests
```

`tests/test_building_tools.py` checks the lookup rules and errors on a small fixture building, the definitions
above against all train and dev answers, and that every labelled space is found by its question label
`"<name> (<floor name>)"`.

## References

- [README section 4](../README.md#4-questions): question kinds and the spatial definitions.
- [Shapely](https://github.com/shapely/shapely): polygon area, intersection, buffer and centroid.
