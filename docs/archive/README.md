# Archive

These documents are older plans, reviews, research and image prompts. They are kept as history only.

`PLAN.md` is the current plan. Where a document here differs from `PLAN.md`, `PLAN.md` wins. In particular, these points in the archive are no longer valid:

- Python core, FastAPI, shapely or NetworkX. We use TypeScript. Python is only used by the official evaluator (`benchmark/`) and the later localization service.
- Image, PDF or SVG floor plan import. Buildings come only as `building.json`.
- QR codes for position. A QR code only opens the mobile view from the desktop view.
- Two route models, the room-anchor graph, 12 m per floor and the free `outside` node. Kit 1.1.0 has one route model (README section 3).
- Cloudflare. We host on Railway.
- Links to `docs/question-overview/`. That folder was deleted because it copied the old answers.
