# Plan import spike: measured vector drafts

Recommendation: **mention only**. The importer accurately recovers room outlines
and explicit opening markers from the kit's Matplotlib SVG exports after a known
distance calibration. It produces a preview draft requiring human corrections.
The three tested floors support this narrow claim; they do not establish reliable
import of arbitrary architect drawings, PDFs, scans, or photographs.

```python
from core.plan_import import import_plan

result = import_plan(
    file_bytes, "svg", floor_level=0,
    scale={"p1": [100, 200], "p2": [300, 200], "length_m": 10},
)
# result: {draft, validation, needs, ready_to_commit, source_frame, diagnostics}
```

Scale points use SVG viewBox/user coordinates. The browser must convert clicked
screen pixels into this frame. Their distance gives metres per SVG unit; `p1`
becomes the local origin and SVG y is flipped to building y-up. This supplies
neither a geographic heading nor alignment between independent floor drawings.
Without scale, `building.units` is `svg_user_units`, validation reports invalid
units, and `needs` includes `scale`. Raw SVG dimensions are never called metres.

The implementation receives only plan bytes, format, floor level and user scale.
It never looks up a filename, building directory, labels or gold building JSON.
SVG paths with the kit's room-outline style yield polygons. Brown/grey point
marks yield candidate openings; red points yield candidate entrances. Marks are
associated only when exactly two room boundaries (one for entrances) meet them.
Shared walls alone never create doors. Compound or curved room paths and other
rendering conventions need manual correction or a future importer.

Room fill colours are retained as hints. The importer uses `generic_room` because
the files do not establish a complete unambiguous semantic colour legend. Glyph
labels are not decoded. Door width 0.9 m, inaccessible/unknown `step_free: false`,
height 3 m and local floor elevation 0 are explicitly provisional defaults;
`import_requires_confirmation` and `needs` identify them. They are not recovered
facts and must be confirmed or corrected before saving. Every result has
`ready_to_commit: false`; schema validation passing alone never authorizes commit.

Measured locally on 24 October 2026 with:

```sh
.venv/bin/python -m core.plan_import.measure --output core/plan_import/measurement.json
.venv/bin/pytest -q tests/core/test_plan_import.py
```

| Dev source, floor 0 | Rooms matched / true | Room recall | Mean matched IoU | Door adjacencies recovered / true | Door graph recall / precision | Draft validates |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| `proc-factory-dev-003` | 47 / 47 | 100% | 1.000000 | 50 / 50 | 100% / 100% | yes |
| `proc-campus-dev-000` | 28 / 28 | 100% | 1.000000 | 27 / 27 | 100% / 100% | yes |
| `osm-way27326387` | 21 / 21 | 100% | 1.000000 | 25 / 25 | 100% / 100% | yes |

These are rounded metrics for three selected floors, with an **evaluation-only
oracle calibration** derived from reference bounds. Only `measure.py` reads gold
JSON. It compares imported polygons with translated reference polygons using
greedy one-to-one matches at IoU ≥ 0.5; door graph recall and precision count
distinct internal room pairs, excluding entrances. Calibration anisotropy error
is under 2×10⁻⁹. No unmatched room or unresolved marker occurred on these floors.
Widths, accessibility, labels, room semantic types, multi-floor registration and
arbitrary file formats are unmeasured. Full results are in `measurement.json`.

Eleven focused tests pass, including actual user calibration, absent scale,
invalid scale, wall contact without a door mark, malformed entity input and all
three measured floors. Zero vision/API calls were made; vision cost is zero.
PNG extraction returns an explicit unavailable draft and correction needs.

For a product UI, the remaining work is: a viewBox-aware two-point calibration,
polygon/door overlay, room label/type editor, widths and accessibility review,
floor-height confirmation, revalidation and explicit preview/save confirmation.
The complete correction step has not been built or tested, so the stronger
“show: a new usable building from any floor plan” gate is not passed. Keep JSON
upload and the validated factory fallback as the dependable demo paths; a real
venue building still requires the human measurements in `demo/hero/README.md`.
