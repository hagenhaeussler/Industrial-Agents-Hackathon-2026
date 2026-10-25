# Building database

Status: requirements and design options. No database schema or importer is implemented yet.

## Purpose and source

Use SQLite to store and query building data. `building.json` is the import source for geometry and equipment.
Preserve source IDs, units, coordinates, floor relationships, openings, vertical connectors, assets and attribution.
Derived facts must be reproducible from that source.

Import only building data. Do not load question files, expected answers, generator inputs or submissions into
the runtime database. The agent must not be able to obtain these through any tool.

The exact table layout and access library are open. Decide which entities need indexed queries before choosing
between relational fields and JSON storage. Do not add an object-relational mapper solely for future flexibility.

## Derived facts

Room area comes from the room polygon. Width times length is only correct for a rectangle. Use the same
validated geometry and repair policy as the building calculations. Never silently replace a failed calculation
with a rectangle estimate or zero.

Shapely uses GEOS for these operations. Area is measured in square metres because the source coordinates
are in metres. Validate coordinates and polygon validity during import. Reject invalid geometry with an
actionable report unless an explicit repair policy has been agreed.

SQLite generated columns are an option for row-local facts:

- `STORED` values are calculated when the row is written and stored in the database.
- `VIRTUAL` values are calculated when read.
- A generated expression can use deterministic scalar functions and fields from the same row.
- It cannot use aggregate functions or subqueries to read other rooms.

A deterministic Python polygon-area function can therefore support a generated room-area column. Register
the function through every application connection that needs it. Its behavior must be stable for the database's
calculation version. Stored values need an explicit recomputation plan if the geometry algorithm changes.

A small isolated SQLite/Shapely check confirmed that a stored generated area handles an L-shaped polygon
and updates when its polygon changes. This proves the mechanism, not a production schema or migration policy.

Recommendation: prototype a stored generated room-area column during the first database step. Compare it
with an ordinary derived column maintained by the import/write transaction. Choose after checking connection
setup, migrations and future updates. Neither option is implemented or final yet.

## Aggregates and caches

Compute area totals across rooms through a query or view over room areas. Define the filter explicitly:
for example, offices on one floor. A sum of selected space areas and the area of their geometric union are
different operations. Do not expose an ambiguous `floor_area` field without its meaning.

Keep reusable facts separate from request-dependent calculations. Route constraints, closures, target choices
and what-if changes belong to tool requests. A cached graph or geometry must use a key that includes the
building content or revision and the calculation version. A later edit must invalidate affected derived data.

## Import workflow

The first importer must support both the existing dataset and later buildings in the same format:

1. Accept an explicit input path and select only `building.json` files. Never bulk-ingest neighboring files.
2. Validate structure, numeric values, references, IDs, units and geometry before making the building available.
3. Insert a building and its dependent records atomically. A failed building import leaves no partial building.
4. Record source provenance, content identity and calculation version with the import result.
5. Return a report of imported, unchanged, conflicting and failed buildings with useful errors.

Repeated import of unchanged content should be safe. A source ID with changed content needs an explicit
replacement policy. Do not silently overwrite it. Dataset-wide all-or-nothing behavior versus per-building
transactions remains an implementation decision.

Agent access starts read-only. Import is a separate operator action. Later write operations must use the same
validation and derived-data rules; future write access does not require exposing arbitrary SQL to the agent.

## Verification and documentation

Test source-to-storage fidelity, references, idempotent imports, conflicts and failure rollback. Cover irregular
polygons and derived-area updates. Check that agent reads cannot reach evaluation data. Use meaningful
interface-level checks rather than tests that repeat SQL statements or geometry formulas.

When implemented, document prerequisites, database location, schema setup, migrations, import, verification
and recovery in [README.md](../README.md). Keep detailed storage behavior here. Do not document invented
commands as usable features.

## Evidence and references

The limited review of `origin/main` at `dc289ba` found SQLite tables for building metadata, application state
and derived caches in `server/state.py`. `core/building.py` loads Shapely polygons in Python. The inspected
schema does not define generated room-area columns. The rewrite is a new design, not a copy of that schema.

- [SQLite generated columns](https://www.sqlite.org/gencol.html): stored/virtual behavior and expression limits.
- [SQLite deterministic functions](https://www.sqlite.org/deterministic.html): rules for application functions.
- [Shapely](https://github.com/shapely/shapely): planar geometry through GEOS.
