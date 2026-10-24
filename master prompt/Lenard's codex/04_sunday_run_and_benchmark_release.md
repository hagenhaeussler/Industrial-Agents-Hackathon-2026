# L04: Sunday rehearsal, release benchmark and the unseen building (Sunday 07:00–12:30 CET)

## 1. Outcome and user value

The submitted answers are reproducible from the release commit by one documented command, and the unseen building is answered within minutes of its release.

## 2. Starting state

L01–L03 merged; release candidate on `main` (captain tags it). The organizers may have answered Q-1/Q-2 overnight; read Discord via your human first thing.

## 3. Scope and ownership

`submissions/`, `BENCHMARK.md`, `bench/run_benchmark.py` (the only code allowed to change after the 10:00 CET feature freeze, together with data adapters).

## 4. Implementation obligations

1. **07:00 G6 benchmark part:** in the captain's fresh-clone container run `uv sync`, `uv run pytest -q`, kit oracle, `core.evaluate --check text`, the Sunday adapter on one converted dev building. Record times.
2. If the organizers published a schema: adapt `bench/run_benchmark.py`, update CONTRACTS §12 + changelog, rerun the rehearsal, push, ask the captain to merge immediately.
3. **Release run (after the 10:00 CET freeze, on the tagged release SHA):** regenerate `submissions/test_answers.csv` with the official evaluator, validate, and confirm it is byte-identical to the committed one (or commit the new one with the reason). Run dev official once more; update `BENCHMARK.md` tables with SHA and date.
4. **Unseen building (when released, standby from 09:00 CET with the H10 human):** place it under `data/sunday/<building_id>/` (or wherever the organizers specify), run the documented command, validate output, commit `submissions/sunday_answers.json` (+ CSV), push, ask the captain to merge; tell Manuel's Claude so the building can be loaded into the app via JSON upload for the demo if useful. If some questions are unanswered, look at the wording: improving templates or the fallback prompt is allowed (it is generalisation, not hand-labelling); editing answers by hand is not.
5. **`BENCHMARK.md` final:** exact commands that were run, environment (`uv` version, Python), keys required, profile, models, results per kind (dev official, train template, paraphrase LLM path), Sunday run summary, limits.

## 5. Interfaces

`bench.run_benchmark` command line is the documented interface for judges' reruns.

## 6. Execution order

G6 checks (07:00) → schema adaptation if any (07:30) → help the captain with release merges as backup (09:00–10:00) → release run (10:00–10:30) → standby and Sunday run → final `BENCHMARK.md` (by 12:00) → confirm files on `main` (12:30).

## 7. Acceptance

Validator ok on both submissions; `BENCHMARK.md` commands reproduce the files on a fresh clone (captain's rehearsal); final SHAs in STATUS.

## 8. Collaboration and Git

After 10:00 CET only adapter/data commits; each one goes through the captain immediately. If the captain is unavailable for 30 minutes you take over merges (announce it in both STATUS files).

## 9. Completion report

Release SHA, files, validator output, Sunday summary (answered/unanswered/errors), time from release to submission.

## 10. Blocked-work behaviour

Sunday building released late or not at all: document the ready command and the rehearsal; submit the test CSV and the reproducible command. Format unclear at 12:15 CET: submit both `answers.json` (provisional schema) and CSV and say so in the submission notes.
