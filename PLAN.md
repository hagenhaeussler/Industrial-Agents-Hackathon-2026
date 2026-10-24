# Plan – Talk to Your Building (Track 01)

**Code Freeze:** So 25.10.2026, 13:00. In der Nacht endet die Sommerzeit (3:00 → 2:00), das bringt eine Stunde extra.

Primäre Datei für das **Was und Wann**: feste Entscheidungen, Fakten der Organisatoren, Reihenfolge, Zeitplan, Abgabe, Budget und offene Fragen.

## Wo steht was

Jede Information steht an genau einer Stelle. Andere Dateien verlinken sie.

| Thema | Primäre Datei |
|---|---|
| Entscheidungen, Reihenfolge, Zeitplan, Abgabe, Budget, offene Fragen | `PLAN.md` (diese Datei) |
| Stack, Repo-Struktur, Railway, Datenbank, Routenmodell, Agent Harness, Voice-Architektur, Lizenzen | [`docs/architecture.md`](docs/architecture.md) |
| Tool-Namen, API, Ereignisse, Routenergebnis, Änderungsablauf, QR-Links, Benchmark-Schnittstelle | [`docs/contracts.md`](docs/contracts.md) |
| Zwei Ansichten, AR, Add-ons, Demo-Story | [`docs/product.md`](docs/product.md) |
| ElevenLabs-Dashboard und Gesprächsregeln | [`docs/elevenlabs-agent-config.md`](docs/elevenlabs-agent-config.md) |
| Regeln für Coding-Agenten | [`AGENTS.md`](AGENTS.md), für den Prototyp [`web/mobile/AGENTS.md`](web/mobile/AGENTS.md) |
| Datenformat, Routenmodell der Jury, Antwortformat | [`README.md`](README.md) (Kit 1.1.0 von Synera), [`CHANGELOG.md`](CHANGELOG.md) |
| Belege: Lead-Q&A, Transkripte, Route-Spec, PDFs | [`docs/sources/`](docs/sources/) |
| Ältere Pläne, Reviews, Recherchen (gelten nicht mehr) | [`docs/archive/`](docs/archive/) |

## 0. Feste Entscheidungen

Diese Punkte gelten für alle Menschen und Agenten im Team. Andere Dokumente, auch `HagenFinalPrompt.md`, überschreiben sie nicht. Ändern kann sie nur das Team gemeinsam.

- **TypeScript für alles.** Python nur an zwei Stellen: im offiziellen Evaluator von Synera (`benchmark/`) und im späteren Ortungsdienst für AR. Der Scorer `benchmark/score.py` bleibt unverändert. In `benchmark/evaluate.py` ersetzen wir später nur den Standard-Agenten durch unseren eigenen.
- **Nur JSON.** Jedes Gebäude kommt als `building.json`. Kein Import von Bildern, PDFs oder SVGs. 2D und 3D entstehen aus den Daten.
- **Railway**, ein Node-Service, SQLite auf einem Volume. Kein Cloudflare.
- **Vorberechnete Datenbank.** Der Import berechnet alles, was der Agent sonst selbst rechnen müsste. Import und Änderungen nutzen denselben Schreibweg.
- **Agent Harness mit dem Claude Agent SDK** (`@anthropic-ai/claude-agent-sdk`, TypeScript), keine einzelnen LLM-Aufrufe. Gebäudedaten kommen nur über Tools, nie in einen Prompt.
- **ElevenLabs** für Voice, mit zwei Voice-Agents: Navigation und Verwaltung.
- **Eine Web-App mit zwei Ansichten**, keine native App: Verwaltung am Desktop und Navigation am Handy. QR-Codes sind nur ein Link vom Desktop zum Handy, keine Ortung.
- **Kein Starter Agent.** Wir schreiben den Agenten neu. Ground Truth sind die erwarteten Antworten in train und dev.
- **Keine Antworten aus `questions*.jsonl`** in der Datenbank, in Prompts oder in Tool-Ergebnissen. Sie dienen nur als Testdaten.

## 1. Fakten der Organisatoren, die den Plan prägen

| # | Fakt | Quelle | Folge |
|---|---|---|---|
| 1 | **Ein Routenmodell (Kit 1.1.0):** Tür zu Tür innerhalb der Räume, 15 cm Abstand zur Wand, Treppe 2 m pro Höhenmeter, Lift 15 m einmal pro Fahrt + 1 m pro Höhenmeter, kein Weg außen herum. Bewertet wird die Raumfolge. Score = beste Länge ÷ unsere Länge, innerhalb 1 % volle Punkte, eine ungültige Route gibt 0. | README Abschnitt 3, `CHANGELOG.md`, `docs/sources/2026-10-24-route-scoring-specifications.md` | Alle Routenfragen nutzen dieses Modell. Details: [`docs/architecture.md`](docs/architecture.md) §6 |
| 2 | **Routing-Regeln:** Gabelstapler nur durch Gänge und Öffnungen ab 3 m, Produktionsbereiche nur als Ziel, Route zu einem Gerät endet in seinem Raum, „keine Route“ sagen, wenn es keine gibt. | Route-Spec | Constraints im Core ([`docs/architecture.md`](docs/architecture.md) §6) |
| 3 | **Das Sonntagsformat ist widersprüchlich.** Das PDF verlangt `answers.json` mit Route als Knotenliste und Länge. Die README verlangt CSV mit einer `Answer:`-Zeile. | PDF vs. README | Parser und Serializer austauschbar. Wir schreiben beide Formate und decken alle 15 Fragearten ab |
| 4 | **Build heißt vor allem lokale Änderungen und What-if.** Eine Web-App reicht. Post-Training ist unerwünscht. Die Jury prüft das ganze System mit eigenen Keys. Die Organisatoren haben Zugang zu OpenAI, Anthropic und ElevenLabs. | Lead-Q&A | Änderungen über das Event-Log sind Pflicht. ElevenLabs-Konfiguration ohne Secrets exportieren. Der Benchmark läuft lokal ohne ElevenLabs und Railway |
| 5 | **Abgabe und Bewertung** ändern sich zwischen PDF und README 1.1.0. | README 1.1.0, Challenge-PDF S. 3 | Siehe §4 |

## 2. Implementierungsreihenfolge

**Reihenfolge:** 1 Datenbank → 2 Agent → danach parallel **A** Voice und **B** Oberfläche (B.1 Visualisierung, B.2 UI/UX) → Add-ons.

| Phase | Inhalt | Fertig, wenn |
|---|---|---|
| **1 Datenbank** | Setup: pnpm, TypeScript, Vitest, `.env.example`. **Import-Feature:** `building.json` → Validator → DB, derselbe Weg für Kit-Gebäude, Sonntagsgebäude und Import in der App. Vorberechnete Werte und Routenmodell ([`docs/architecture.md`](docs/architecture.md) §6). Ein Schreibweg für Änderungen. Constraints, Erreichbarkeit, Routen, What-if | Warm-up-Routen auf den Zentimeter, Geometrie-Arten ≈ 100 % auf dev und train, alle 280 Gebäude importierbar |
| **2 Agent** | Harness mit dem Claude Agent SDK, eingebaute Tools aus. **DB-Tools zum Lesen und Schreiben**, Schreiben nur über den Schreibweg mit Vorschau und Bestätigung. Tool-Namen in [`docs/contracts.md`](docs/contracts.md) eintragen. Skills und Prompts pro Fragetyp. Benchmark-CLI, `bench/answer.py`, `BENCHMARK.md`. `benchmark/evaluate.py` startet ohne `--agent` unseren Agenten. API im Node-Service | **M1:** vollständige Test-CSV mit 145 Zeilen und dev-Score pro Fragetyp, end to end auf den dev-Fragetexten |
| **A Voice** | Zwei ElevenLabs-Agents für Mobile und Desktop. Token-Endpunkt, Client-Tools auf dieselbe Tool-API wie der Agent | Eine gesprochene Frage zeigt eine Route, auf Mobile und Desktop |
| **B.1 Visualisierung** | 2D (SVG) und 3D (extrudiert), **deterministisch aus der DB**: Etagen, Räume, Türen, Assets, Route, Highlights, Vorschau von Änderungen | Gleiche Daten ergeben immer dasselbe Bild. Alle Etagen eines dev-Gebäudes korrekt |
| **B.2 UI/UX** | Eine Web-App mit zwei Ansichten ([`docs/product.md`](docs/product.md) §1) | **M2:** Die Demo-Story ([`docs/product.md`](docs/product.md) §5) läuft auf der öffentlichen URL |
| **Add-ons** | Gabelstapler-Constraints; Hagens Journey (Tour, Störung, bewegte Teile); später AR mit hloc und MegaLoc ([`docs/product.md`](docs/product.md) §3–§4) | Jedes Add-on hat einen eigenen Test |

## 3. Zeitplan

Stand Sa 17:00, nur als grober Rahmen.

| Zeit | A: Core/Bench | B: Frontend + Railway | C: Voice/Agent/Demo |
|---|---|---|---|
| **Sa 17:15–17:45** | Phase 1 Setup, Tool-Vertrag einfrieren (Namen, Parameter, Ergebnisformat), Referenzgebäude und erwartete Route für das Gate festlegen | Railway-Setup, Vite/React-Gerüst | Abrechnung klären (ElevenLabs-Credits?), Agent anlegen, Discord-Fragen stellen |
| **17:45–18:30** | Phase 1 Datenbank | Node-Service öffentlich auf Railway, Secret-Test. Dann B.1 minimale 2D-Karte | `/api/tools/route`, `useConversation` |
| **18:30** | **Integrationsgate (alle):** Voice → Tool → Karte, lokal, auf dem Referenzgebäude | | |
| **18:30–21:00** | Phase 2 Agent → **M1** | Deploy, **20:00 Abnahme**, dann B.1 Visualisierung | Alle Client-Tools, Gesprächsregeln, Textchat |
| **21:00–00:30** | Constraints (Gabelstapler, Produktion) | B.2 Mobile und Desktop, Änderungen mit Vorschau, Bestätigung und Undo | Voice auf Mobile und Desktop, Rückfrage-Logik → **M2** |
| **00:30 Gate** | Bestätigte Änderung, QR-Code vom Desktop öffnet die Mobile-Ansicht, Undo, Wiederherstellung nach Neustart des Service (Volume). **Danach keine neue Infrastruktur** | | |
| **00:30–03:00** | Regression auf dev, Checkpointing | Handy-Test auf der öffentlichen URL (HTTPS) | Rohschnitt fürs Video |
| 03:00–07:00 | **Schlafen** | | |
| **So 07:00–09:00** | Ein dev-Gebäude wie ein unbekanntes durchlaufen lassen, finale Test-CSV, Installationsprobe auf frischem Klon | 3D **erst nach** bestandenem Frischklon- und Benchmark-Lauf → **M3** | Härtetest mit schwierigen Nutzern |
| **ab 09:00** | **Bereitschaft für das Sonntagsgebäude:** eine Person lässt `bench` laufen, sobald es erscheint, und lädt es in die App | Bugfixes | Video aufnehmen |
| **10:00 Feature Freeze** | `BENCHMARK.md`, README, exportierte Agent-Konfiguration. **Ausnahme:** Anpassungen an Sonntagsformat und Datenadapter | Letztes Deploy, URL in die Abgabe | Video schneiden, technische Erklärung |
| **12:00–13:00** | Nur Abschlusslauf, Upload, Abgabe prüfen | | |

**Streichreihenfolge:** 3D → zusätzliche Logistikfunktionen. **Voice bleibt Pflicht**, M1 wird nie gefährdet.

## 4. Abgabe und Bewertung

- **README 1.1.0 (neuer):** „Pitch and demo“ (10 Punkte) ist „a 3–5 minute live demo that works without a restart“. Der Text zu vier Finalisten (3 min Pitch + 1 min Q&A), zu `BENCHMARK.md` und zur Liste der Abgaben ist entfernt. Abgabe für den Benchmark: eine CSV mit den 145 Testantworten (README Abschnitt 6).
- **Challenge-PDF (älter):** Demo-Video, kurze technische Erklärung, Repo mit `BENCHMARK.md` und `answers.json`, vier Finalisten mit 3 + 1 Minuten.
- **Wir liefern:** die CSV, eine geprobte **Live-Demo von 3–5 Minuten ohne Neustart** ([`docs/product.md`](docs/product.md) §5), dazu Video, technische Erklärung und `BENCHMARK.md`, weil sie wenig kosten. Was genau gilt, fragen wir Synera (§6).
- **Bewertung:** Does it work 55, Interaction 25, Creativity 10, Pitch and demo 10 (README Abschnitt 1).
- **Sonntagsgebäude:** kommt kurz vor Code Freeze im gleichen Format. `bench` importiert es und beantwortet die Fragen mit einem Befehl.

## 5. Modelle und Budget (600 USD Anthropic)

| Einsatz | Modell | Preis pro MTok (in/out) | Grobe Rechnung |
|---|---|---|---|
| Benchmark (dev, test, Sonntag) | **Agent Harness** mit unseren Tools. Zuerst Haiku 5.5 testen, Sonnet 5.5 bei messbar schlechteren Ergebnissen | Haiku 0,10 / 0,50 | Mehrere Tool-Runden pro Frage. Kosten pro Frage messen, bevor wir große Läufe starten |
| Textchat und Custom LLM (falls genutzt) | **Sonnet 5.5**, effort `low` | 2 / 10, Cache-Lesen 0,20 | ≈ 0,03–0,05 USD pro Turn. 1.000 Turns ≈ 40 USD |
| Entwicklung und Experimente | Sonnet 5.5, gezielt Opus 5.5 (4 / 20) | | |

**Ausgabenlimits** (im Console-Workspace als Limit setzen):

| Posten | Limit | Aufteilung |
|---|---|---|
| Benchmark | 200 USD | dev 60, Test 40, Sonntag 100 |
| Chat und Voice | 100 USD | |
| Entwicklung | 220 USD | |
| Reserve | 80 USD | wird nicht angetastet |

Zusätzliche Kosten außerhalb der 600 USD: ElevenLabs-Credits (Agent-Minuten und eingebautes LLM) und Railway. Caching-Regeln: [`docs/architecture.md`](docs/architecture.md) §4.

## 6. Offene Fragen

**An Synera (per Discord):**
1. Sonntagsformat: **`answers.json` (PDF) oder CSV (README)**? Sind die Knoten-IDs `space_id`s? Wie wird „unerreichbar“ dargestellt? Wann wird veröffentlicht, wie lange haben wir?
2. Woran erkennt man **Gabelstapler-Gänge und Fußwege** in den Daten? Welche Raumtypen sind „Produktionsbereich“?
3. Kommen am Sonntag auch locate-, route- und tour-Fragen?
4. Abgabe: Gilt die README 1.1.0 (CSV und 3–5 Minuten Live-Demo ohne Neustart) oder noch das PDF (Demo-Video, technische Erklärung, `BENCHMARK.md`, `answers.json`, vier Finalisten mit 3 + 1 Minuten)? Gibt es noch eine Finalrunde?

Beantwortet durch Kit 1.1.0: welches Routenmodell gilt (nur noch eines) und wo Start und Ziel liegen (Ankerpunkt des Raums).

**Im Team, vor Phase A:**
- **Ein oder zwei „Gehirne“:** Wählt das LLM in ElevenLabs die Tools, oder nutzt ElevenLabs unseren Agent Harness als Custom LLM? Optionen: [`docs/architecture.md`](docs/architecture.md) §5.

## 7. Was schon da ist

| Wo | Inhalt | Zustand |
|---|---|---|
| `benchmark/` | Offizieller Evaluator (`evaluate.py`) und Scorer (`score.py`) von Synera, Python | `score.py` bleibt unverändert. `evaluate.py` lädt ohne `--agent` noch den entfernten Starter Agent; Phase 2 ändert den Standard |
| `web/mobile/` | Lenards Prototyp „Building Guide“: Vollbildkamera, Route, Minimap, Chat, Blobatar. React 19, Vite, pnpm, Vitest | Vorlage für die Mobile-Ansicht. Route, Position und Chat sind Demo-Daten |
| `data/` | Kit 1.1.0: 280 Gebäude, Fragen mit Antworten in train und dev, 145 Testfragen | Testset: floor_area_total 33 · shared_walls 26 · largest_room 21 · errand 20 · wide_delivery 18 · straight_line_3d 15 · room_stacked 9 · what_if_door 3 |
