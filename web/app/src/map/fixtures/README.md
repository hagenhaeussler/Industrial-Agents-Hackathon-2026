# Three-floor renderer fixture

`campus-three-floor.json` is a compact JSON copy of `data/dev/proc-campus-dev-013/building.json` (actual kit building Laborgebäude037). It contains the unmodified building geometry and assets; no questions or gold labels were used. Tests import this local copy so the isolated Docker frontend build does not require the full server dataset. It is not imported by application code.

Original file SHA-256: `30724e55428ed2610310f69422b2b940457db03d32d0d71af260b532306bcead`.
