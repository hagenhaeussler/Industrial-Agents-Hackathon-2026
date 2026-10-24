# M04: Integration captain duties, release and submission (continuous; Sunday 07:00–12:45 CET)

## 1. Outcome and user value

`main` is always a working product with a known good tag, the public URL runs the release commit, the fresh-clone instructions work, and the submission is complete and verifiable before 13:00 CET.

## 2. Starting state

All builders push to their branches; you merge (OWNERSHIP §5). Backup: Lenard's codex.

## 3. Scope and ownership

`main` merges, gate tags, Railway deploys, `scripts/check.sh`, README "Run it locally", ElevenLabs config export (with H4), `ATTRIBUTION.md` compliance notes, submission checklist (INTEGRATION §4), honest release report.

## 4. Obligations

1. **Merge windows** (G1 23:00, G2 23:30, G3 00:30, G4 01:15, G5 02:15 CEST; Sunday 07:30, 09:30, 10:00, 11:00 CET): read STATUS files; merge in dependency order (core → server → bench/agent → web); run `scripts/check.sh` and the gate checklist; push; tag; deploy to Railway; record SHAs. A red check means the branch waits; tell its owner precisely what failed.
2. **Conflict handling:** resolve only mechanical conflicts yourself; behavioural conflicts go back to the owners with the failing case. Never take "ours/theirs" wholesale.
3. **Overnight (03:00–07:00 CET):** no merges, no deploys.
4. **G6 fresh-clone rehearsal (07:00 CET):** in a Linux container (`docker run --rm -it python:3.12-slim bash`, install `git`, `curl`, `uv` per the README), clone the repo, follow README "Run it locally" literally, run `scripts/check.sh` (without Bun: web build via Docker), build the Docker image, run it with an empty volume, load the hero building, run the Sunday adapter rehearsal with Lenard. Fix the instructions, not the container.
5. **Demo safety:** demo mode `/desk?demo=hero` and `POST /api/demo/reset` tested twice in a row before G7; Railway warmed (one request per demo building) before recordings and before the final.
6. **Release (10:00 → 11:00 CET):** after feature freeze only Sunday adapter/data fixes and demo-critical bugs. Tag `release-1`, deploy at 11:00 CET, verify `/health` shows the release SHA; no deploy afterwards except to roll back to a previous tag.
7. **ElevenLabs export:** with the H4 human, export both agent configurations without secrets (dashboard export or `GET /v1/convai/agents/{agent_id}` with the key, then remove secrets) into `docs/elevenlabs-agents/navigator.json` and `admin.json`.
8. **Submission (12:15–12:45 CET):** checklist in INTEGRATION §4; give the humans the URL, repository link, videos, architecture notes and answer files; record `git ls-remote origin main` in STATUS; write the honest release report (INTEGRATION §6).

## 5. Interfaces

Gate tags; Railway URL; release SHA.

## 6. Execution order

Continuous during the night; Sunday sequence: 07:00 G6 → 07:30 merge → 08:00 G7 support (mirroring: `scrcpy`, QuickTime) → 09:30 merge → 10:00 freeze → 11:00 release deploy → 12:15 submission.

## 7. Acceptance

All INTEGRATION §3–§4 checklists ticked with evidence; final remote SHA equals the deployed `/health` commit.

## 8. Collaboration and Git

You alone push `main`. If you are unavailable for 30 minutes, Lenard's codex takes over (announced in both STATUS files).

## 9. Completion report

Per window: merged SHAs, checks, tag, deploy. Final: release SHA, URL, submission items, release report.

## 10. Blocked-work behaviour

Railway outage during the final: local server + hotspot (MASTER_PLAN §6). A red `main` at 11:00 CET: deploy the last green tag, not the red head.
