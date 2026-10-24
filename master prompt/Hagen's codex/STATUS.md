# STATUS: Hagen's codex (Core & Spatial Intelligence Lead)
Last update: 2026-10-24T21:33+02:00 · Branch: `hagen/core` · HEAD: this checkpoint · Last sync: `d46775f` + platform `53eb592`

Single writer: Hagen's codex.

## Current task
H01 core port; H02 route reconstruction and H03 edit/validator work progressing in separate owned modules.

## Delivered (newest first)
- Building/load_building, canonical content hash, isolated materialisations, repaired polygon warnings, profile validation, shared CoreError/EditError, exact-first numeric-safe resolver.
- Consumed Manuel's published M01 branch/dependencies; no edits to platform-owned files.

## Interfaces exposed / changed
- `from core.building import Building, load_building, content_hash`
- `from core.resolve import resolve`
- `from core.errors import CoreError, EditError`; `core.profiles.current_profile()`

## Evidence
- `.venv/bin/python -m pytest -q tests/core/test_building.py tests/core/test_resolve.py`: 3 passed.
- Kit oracle running; full spatial evaluations next. No paid model calls.

## Blockers and resource requests
- Railway plugin create-project returned: trial expired; human asked to activate plan/provide active workspace. No project or deployment created. Requested test project name: `talk-to-your-building-hagen-test`.
- H6 venue sketch/dimensions not received. A real venue building will not be invented; factory fallback remains available.

## Change requests
- CR-H-1 (C1 §5): physical polyline length cannot equal graph edge rounded to 0.001 m within 1e-6. Preserve raw geometry length separately; validate against raw kit space walks within 1e-6 and rounded graph costs within 0.001. Core owner will document additive geometry metadata and tolerance before H02 handoff.

## Next handoff
- Lenard: core imports ready; `solve` and real fixtures follow.
- Manuel's codex: minimal edits + route/tour/validator API follow. Test Railway deployment will use a separate project once billing access allows it.
- Manuel's Claude: real snapshot/tour/tool fixtures follow; preserve provisional/real geometry status.
