# Locora building database

Status: schema, validated import and full read-back are implemented in `building_db/`.
Agent read tools and write operations are not implemented yet.

## Purpose and source

SQLite stores the building data. `building.json` is the only import source. Every row keeps its source ID,
units, coordinates and references, so a stored building reads back unchanged.

Only building data is imported. Question files, expected answers, generator inputs and submissions never enter
the database. The importer accepts only files named `building.json`. The agent must not reach evaluation data
through any tool.

## Layout

The schema is in [building_db/schema.sql](../building_db/schema.sql). All tables are `STRICT`.

| Table | Content |
|---|---|
| `buildings` | Building metadata, content hash, source path and calculation version |
| `floors` | Level, name, elevation and height. Levels are unique per building. |
| `spaces` | Type, room type, name, ref, polygon as JSON and the stored `area_m2` |
| `openings` | Kind, both sides, position, width and step-free flag |
| `vertical_connectors` | Stairs and lifts |
| `connector_stops` | One row per floor a stair or lift serves, in source order |
| `assets` | Equipment with space, position and footprint |

Entity IDs are unique per building, so primary keys pair them with `building_id`. Foreign keys enforce floor and
space references. An entrance's outer side is the literal `"outside"`, so the importer checks opening sides
instead of a foreign key. Fields the agent will filter on are columns. Polygons stay JSON because they are
always read whole.

## Derived facts

`spaces.area_m2` is a `STORED` generated column: `polygon_area(polygon)`. `polygon_area` uses Shapely (GEOS)
on the full polygon, so irregular rooms get their exact area. `building_db.store.connect` registers the function
as deterministic.

Why `STORED` and not `VIRTUAL`: both recompute automatically when a polygon changes. `STORED` computes once
per write, `VIRTUAL` on every read. In a test, ten area sums over 20,000 rooms took 0.004 s with `STORED` and
1.07 s with `VIRTUAL`. A `STORED` value can also be read by any SQLite client. A `VIRTUAL` read fails without
the registered function.

Consequences of this choice:

- Generated columns see only their own row. Totals across rooms, such as all offices on a floor, are queries.
  A sum of space areas and the area of their geometric union are different operations.
- If `polygon_area` changes, bump `CALCULATION_VERSION` in `building_db/store.py` and rewrite the stored values.
- SQLite cannot add a `STORED` column with `ALTER TABLE`. A new derived column needs a table rebuild migration.

Request-dependent results stay out of the database. Route constraints, closures, target choices and what-if
changes belong to tool requests. A later cache of graphs or geometry needs a key that includes the building
content hash and the calculation version.

## Import

```bash
uv run python -m building_db import buildings.sqlite3 data/dev/osm-way22744230/building.json
```

The command creates the database file if it is missing and prints one status line per file. It exits with 1
if any file failed or conflicted. Pass several `building.json` paths to import several buildings, for example
`data/*/*/building.json`.

| Status | Meaning |
|---|---|
| `imported` | Validated and stored in one transaction |
| `unchanged` | A building with this ID and the same content is already stored |
| `conflict` | A building with this ID but different content is stored. Nothing is overwritten. |
| `failed` | The file was rejected. The message lists every problem found. Nothing is stored. |

Validation rejects unknown fields, wrong types, non-finite numbers, duplicate IDs or floor levels, broken
references, a space reference on the wrong floor, entrances without exactly one `"outside"` side, and invalid
polygons. There is no automatic polygon repair. All 280 kit buildings pass.

Content identity is a SHA-256 hash of the JSON content, independent of whitespace and key order. Replacing a
stored building with changed content is not implemented. Until then, delete the database file and import again.

The home page also accepts a `building.json` upload. It sends the file to `POST /api/buildings/import`
as `application/json`, with a 20 MiB limit. The endpoint uses the same validator and importer as the command
line. It returns 201 for a new building, 200 for identical stored content, 409 for changed content with an
existing ID, 413 for an oversized body, 415 for a non-JSON request, 422 for invalid building data, and 503
when storage is unavailable. It never overwrites an existing building or creates a missing database.
The identity check and insert run in one write transaction, including simultaneous uploads.

Uploads must have at least one floor and one space. Validation also rejects duplicate JSON keys, building
IDs that cannot be used in page URLs, repeated connector floors, and non-finite polygon areas. A UTF-8
byte order mark is accepted. Temporary upload files are removed after import. The database keeps the
content hash and all validated building data; the temporary source path is not a retained file.

## Read access

`building_db.store.load_building(connection, building_id)` returns the stored building as a validated
`BuildingDocument` in the source format. Each list is ordered by entity ID. Agent tools will build on this and on
targeted queries. `building_db.store.connect_readonly` opens an existing file read-only and never creates
or migrates it. Building and route requests use it. Agent access is read-only. The upload route uses a separate
write connection through `connect_existing`. Later write operations must
use the same validation and must not expose raw SQL to the agent.

## Verification

`tests/test_building_db.py` checks:

- A dev building reads back equal to its source.
- Stored areas match the dev answers for `largest_room` and `floor_area_total`. The answers serve only as an
  independent check.
- The area follows a polygon change and is readable without the registered function.
- Re-import of unchanged content is safe and changed content is not overwritten.
- Invalid buildings are rejected with reasons and leave no rows.

A one-off check imported all 280 kit buildings in 1.5 s into a 38 MB database. All 277 area answers in train and
dev matched the stored areas within 0.005 m².

## References

- [SQLite generated columns](https://www.sqlite.org/gencol.html): stored and virtual behavior, expression limits.
- [SQLite deterministic functions](https://www.sqlite.org/deterministic.html): rules for application functions.
- [Shapely](https://github.com/shapely/shapely): planar geometry through GEOS.
