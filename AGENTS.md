# Projektregeln

Gilt für alle Coding-Agenten in diesem Repo. Inhalte stehen in den primären Dateien. Diese Datei verweist nur auf sie.

## Primäre Dateien

| Thema | Datei |
|---|---|
| Feste Entscheidungen, Reihenfolge, Zeitplan, Abgabe, offene Fragen | `PLAN.md` |
| Stack, Repo-Struktur, Deployment, Datenbank, Routenmodell, Agent Harness, Voice | `docs/architecture.md` |
| Tool-Namen, API, Ereignisse, Ergebnisformate | `docs/contracts.md` |
| Ansichten, AR, Add-ons, Demo | `docs/product.md` |
| ElevenLabs-Dashboard und Gesprächsregeln | `docs/elevenlabs-agent-config.md` |
| Datenformat, Routenmodell der Jury, Antwortformat | `README.md` und `CHANGELOG.md` (Kit von Synera) |

`docs/sources/` enthält Belege, keine Pläne. `docs/archive/` gilt nicht mehr.

## Regeln

- Die festen Entscheidungen in `PLAN.md` §0 ändert nur das Team gemeinsam. Wenn eine davon im Weg steht, frage nach.
- Eine Information steht an genau einer Stelle. Ändere die primäre Datei und verlinke sie, statt Inhalte zu kopieren.
- Ändert sich eine Schnittstelle, ändere zuerst `docs/contracts.md` und sage es allen, die sie nutzen.
- Stack: Node 22+, pnpm, Vitest, strict TypeScript. Python nur in `benchmark/` und im späteren `localizer`.
- `benchmark/score.py` und `data/` nie ändern.
- Keine Daten aus `questions*.jsonl` in die Datenbank, in Prompts oder in Tool-Ergebnisse. Sie sind nur Testdaten.
- Die Datenbankdatei wird erzeugt und nicht committed. Keys nie im Repo, nie im Browser.
- Routen müssen die Warm-up-Antworten in train und dev auf den Zentimeter treffen. Führe die Tests vor jedem Commit aus.
- Für `web/mobile/` gilt zusätzlich `web/mobile/AGENTS.md`.
