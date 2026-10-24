# Plan – Talk to Your Building (Track 01)

**Stand:** Sa 24.10.2026, 17:00 · **Code Freeze:** So 25.10., 13:00 → **ca. 21 reale Stunden.** In der Nacht endet die Sommerzeit (3:00 → 2:00), das bringt eine Stunde extra.
**Stack:** eine Web-App mit zwei Ansichten auf **Railway** (ein Node-Service), **alles in TypeScript** · vorberechnete SQLite-Datenbank aus `building.json` · Agent Harness mit dem Claude Agent SDK (TypeScript) · zwei ElevenLabs-Agents mit Eleven v4 Turbo · Claude (600 USD Anthropic-Credits)
**Grundlage:**
- dieses Team-Repo: Meeting-Notizen, Q&A mit dem Challenge-Lead, Route-Scoring-Spec, Challenge-PDF
- das offizielle Synera-Kit, Version 1.1.0 (Branch `patch/fix-answers-ruleset`, Commit `6a2cdec`): neue Antworten nach den Routenregeln der Jury, siehe `CHANGELOG.md`
- ein Review durch Codex (gpt-6.1-sol, medium), siehe Abschnitt 11
- Ältere Pläne, Reviews und Recherchen liegen in `docs/archive/`. Sie gelten nicht mehr, wo sie von diesem Plan abweichen.

## 0. Feste Entscheidungen

Diese Punkte gelten für alle Menschen und Agenten im Team. Andere Dokumente, auch `HagenFinalPrompt.md`, überschreiben sie nicht. Ändern kann sie nur das Team gemeinsam.

- **TypeScript für alles.** Python nur an zwei Stellen: im offiziellen Evaluator von Synera (`benchmark/`) und im späteren Ortungsdienst für AR. Der Scorer `benchmark/score.py` bleibt unverändert. In `benchmark/evaluate.py` ersetzen wir später nur den Standard-Agenten durch unseren eigenen.
- **Nur JSON.** Jedes Gebäude kommt als `building.json`. Kein Import von Bildern, PDFs oder SVGs.
- **Railway**, ein Node-Service, SQLite auf einem Volume. Kein Cloudflare.
- **Agent Harness mit dem Claude Agent SDK** (`@anthropic-ai/claude-agent-sdk`, TypeScript), keine einzelnen LLM-Aufrufe. Gebäudedaten kommen nur über Tools, nie in einen Prompt.
- **ElevenLabs** für Voice, mit zwei Voice-Agents: Navigation und Verwaltung.
- **Eine Web-App mit zwei Ansichten**, keine native App: Verwaltung am Desktop und Navigation am Handy.
- **Kein Starter Agent.** Wir schreiben den Agenten neu. Ground Truth sind die erwarteten Antworten in train und dev.
- **Keine Antworten aus `questions*.jsonl`** in der Datenbank, in Prompts oder in Tool-Ergebnissen. Sie dienen nur als Testdaten.

---

## 1. Was neu ist und den Plan ändert

| # | Fund | Quelle | Folge |
|---|---|---|---|
| 1 | **Es gibt nur noch ein Routenmodell (Kit 1.1.0).** Gemessen wird Tür zu Tür *innerhalb* der Räume, 15 cm Abstand zur Wand, um Ecken herum. Treppe = 2 m pro Höhenmeter, Lift = 15 m einmal pro Fahrt + 1 m pro Höhenmeter. Kein Weg außen herum. Bewertet wird die **Raumfolge**. Score = beste Länge ÷ unsere Länge, innerhalb 1 % gibt volle Punkte, eine ungültige Route gibt 0. | `CHANGELOG.md`, README Abschnitt 3, `2026-10-24-route-scoring-specifications.md` | Alle Routenfragen nutzen dieses Modell. Das alte README-Modell (Ankerpunkt, 12 m pro Etage, 15 + 6 m, `outside`-Knoten) ist ungültig. |
| 2 | **Neue Routing-Regeln:** Ein Gabelstapler fährt nur durch Gänge und Öffnungen ab 3 m. Produktionsbereiche sind nur Ziel, kein Transit. Eine Route zu einem Gerät endet im Raum, der es enthält. Wenn es keine Route gibt, sagen wir das. | dieselbe Datei | Das kommt als Constraints in den Graphen. In den Fabrikdaten gibt es Hallen-Öffnungen mit 4–20 m. |
| 3 | **Das Sonntagsformat ist widersprüchlich.** Das PDF verlangt `answers.json` mit Route als Knotenliste und Länge. Die README verlangt CSV mit einer `Answer:`-Zeile. | PDF vs. README | Parser und Serializer müssen austauschbar sein. Wir schreiben beide Formate und decken alle 15 Fragearten ab, auch die Warm-up-Arten. |
| 4 | **Build heißt vor allem lokale Änderungen und What-if.** Eine Web-App reicht. Post-Training ist unerwünscht. Die Jury prüft das ganze System mit eigenen Keys. Die Organisatoren haben Zugang zu OpenAI, Anthropic und ElevenLabs. Im Video zählt die Interaktion am meisten. | Q&A mit dem Lead | Änderungen über das Event-Log sind Pflicht. Wir arbeiten nur mit JSON. Die ElevenLabs-Agent-Konfiguration exportieren wir ohne Secrets. Der Benchmark läuft **lokal und ohne ElevenLabs und Railway**. |
| 5 | **Abgabe und Bewertung (Kit 1.1.0).** Die README nennt jetzt für „Pitch and demo“ (10 Punkte): „A 3–5 minute live demo that works without a restart“. Der Text zu vier Finalisten mit 3 min Pitch + 1 min Q&A, zu `BENCHMARK.md` und zur Liste der Abgaben ist aus der README entfernt. Abgabe für den Benchmark ist eine CSV mit den 145 Testantworten. Das ältere PDF nennt noch Demo-Video, technische Erklärung, `BENCHMARK.md`, `answers.json` und vier Finalisten. | README 1.1.0 Abschnitte 1 und 6, Challenge-PDF S. 3 | Wir planen eine **Live-Demo von 3–5 Minuten ohne Neustart** und proben sie. Video, technische Erklärung und `BENCHMARK.md` liefern wir trotzdem, weil sie wenig kosten. Was genau gilt, fragen wir Synera (Abschnitt 10). |

## 2. Gesamter Tech-Stack

**Grundsätze (Stand Sa abends):**
- **Nur TypeScript.** Kein Python im Laufzeitcode. Ausnahmen: der offizielle Evaluator `benchmark/` (Python, von Synera; der Scorer bleibt unverändert, damit wir genau wie die Jury bewerten) und der spätere Ortungsdienst für AR (Abschnitt 8). Den Starter Agent haben wir entfernt.
- **Nur JSON.** Jedes Gebäude kommt als `building.json`. Es gibt keinen Bildimport (kein PNG, kein SVG, kein Foto). 2D- und 3D-Ansicht entstehen direkt aus den Daten.
- **Vorberechnete Datenbank.** Ein Import-Skript liest `building.json` und schreibt SQLite. Dabei berechnet es alle Werte, die der Agent sonst selbst rechnen müsste. Import und Änderungen nutzen denselben Schreibweg.
- **Agent Harness statt einzelner LLM-Aufrufe.** Das Modell führt eine Agent-Schleife aus und entscheidet selbst, welche Tools es wie oft aufruft. Gebäudedaten kommen nie in den Prompt, nur über Tools.
- **Eine Web-App mit zwei Ansichten, keine native App:** Verwaltung am Desktop und Navigation am Handy (Abschnitt 8). QR-Codes dienen nur als Link vom Desktop zur Mobile-Ansicht, nicht zur Ortung.

| Schicht | Technik | Aufgabe |
|---|---|---|
| **Frontend** | React 19 + Vite + TypeScript, CSS mit Design-Tokens wie im Prototyp, Zustand (State). Die UI aus Lenards Prototyp (`web/mobile/`) übernehmen wir | Eine Web-App, zwei Ansichten: Verwaltung (Desktop) und Navigation (Handy) |
| 2D-Plan | Eigenes SVG aus den Polygonen (lokale Meter, keine Kartenprojektion) | Etagen, Räume, Türen, Assets, Route, Highlights, Vorschau von Änderungen |
| 3D-Ansicht | react-three-fiber + drei, Etagen direkt aus den Polygonen extrudiert | Gestapelte Etagen, animierte Route |
| Voice | `@elevenlabs/react` (`useConversation`), Client-Tools | Mikrofon, Barge-in, Tool-Aufrufe aus dem Agenten |
| **Datenbank** | SQLite über `node:sqlite`, lokal und auf dem Railway-Volume | Basisdaten plus vorberechnete Werte, siehe Abschnitt 5 |
| **Core** | TypeScript-Bibliothek `core/`: Geometrie, Graph, Routing, What-if, Änderungen | Deterministisch. Läuft lokal, im Benchmark und in der Cloud mit demselben Code |
| **Agent** | Claude Agent SDK (`@anthropic-ai/claude-agent-sdk`). Unsere DB-Tools hängen als MCP-Server im selben Prozess am Agenten. Eingebaute Datei-, Shell- und Web-Tools sind aus. Sonnet 5.5, Prompt-Caching | Textchat, Benchmark und optional Custom-LLM für ElevenLabs. Läuft im Node-Service auf Railway |
| Agent (Voice) | Zwei ElevenLabs-Agents (Navigation, Verwaltung): `eleven_v4_turbo` + eingebautes `claude-sonnet-5-5`. Einstellungen in `docs/elevenlabs-agent-config.md` | Gespräch, Rückfragen, Tool-Auswahl |
| **Benchmark** | TypeScript-CLI, ein Befehl, nutzt denselben Agenten und dieselbe DB. Ein kleiner Python-Adapter `bench/answer.py` ruft die CLI auf, damit der offizielle Evaluator läuft: `python -m benchmark.evaluate data/dev --agent bench.answer:answer` | Läuft lokal, schreibt die Abgabe-CSV (und `answers.json`, falls gefordert) |
| Tooling | pnpm, Vitest (Tests gegen train/dev), Railway CLI. Python-Tools (`uv`) nur für `benchmark/` | Der Prototyp `web/mobile/` ist von Bun auf pnpm und Vitest umgestellt |

**Repo-Struktur:**

```
core/        TypeScript: Schema, Import, Geometrie, Graph, Routing, Änderungen
agent/       TypeScript: Agent Harness, Tool-Definitionen, Prompt
bench/       TypeScript: Benchmark-CLI, Parser/Serializer CSV + JSON
web/         React-App mit zwei Ansichten (Mobile-Prototyp in web/mobile/)
server/      Node-Server (Hono): API, WebSocket, Static Assets, Event-Log
data/        Kit-Daten (Kit 1.1.0, unverändert)
benchmark/   offizieller Evaluator und Scorer von Synera (Python, unverändert)
```

Tests liegen neben dem Code (`*.test.ts`) und laufen gegen die Antworten in train und dev. Die Antworten aus `questions*.jsonl` kommen nie in die Datenbank.

## 3. Deployment auf Railway

```
Browser ──HTTPS/WSS──► Railway-Service "app" (Node, TypeScript)
                        ├─ /            Static Assets (Vite-Build von web/)
                        ├─ /api/voice/token?agent=navigator|admin   ELEVENLABS_API_KEY → Conversation Token (WebRTC)
                        ├─ /api/tools/*, /api/chat   → Agent Harness + core/ auf der Gebäude-DB
                        └─ /ws/:building       WebSocket: building_changed an alle Clients
                               └─ Volume /state: SQLite (Gebäude-DB + Event-Log)

Später, nur für AR:  Railway-Service "localizer" (Python, hloc) ← Kamerabilder vom Handy
```

- **Ein Node-Service** liefert App, API und WebSocket aus. Server-Framework: Hono auf Node. Core, Agent Harness und DB laufen im selben Prozess.
- **Datenbank:** SQLite über `node:sqlite` auf einem Railway-Volume unter `/state`, nicht unter `/app/data`. Basisdaten plus Event-Log (Version, Undo). `commit_edit` nur mit `proposal_id`, idempotent. Die Kit-Gebäude importieren wir beim Start, nicht beim Build.
- **Grenzen von Railway:** Mit Volume sind keine Replicas möglich, und ein Redeploy hat kurze Downtime. Deshalb kein Deploy während Aufnahme oder Demo. Der Client verbindet den WebSocket automatisch neu und lädt danach den aktuellen Stand. App-Sleeping ausschalten.
- **Secrets als Railway-Variablen:** `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID_NAVIGATOR`, `ELEVENLABS_AGENT_ID_ADMIN`. Keys stehen nie im Repo und nie im Browser. Der Browser bekommt nur den kurzlebigen Conversation Token.
- **Offene Demo, nicht öffentlich gelistet:** Die App braucht kein Login, damit Jury und Live-Demo ohne Hürde laufen. Die URL steht nur in der Abgabe und im Team, nicht in öffentlichen Links. Die Seite setzt `noindex`. Ausgabenlimits bei Anthropic und ElevenLabs und ein einfaches Rate-Limit am Token-Endpunkt begrenzen den Schaden, falls die URL bekannt wird.
- **Agent Harness im Node-Service** mit dem Claude Agent SDK. Es bringt Agent-Schleife, Kontextverwaltung, Hooks und Sessions mit. Seine eingebauten Datei-, Shell- und Web-Tools schalten wir aus, damit der Agent nur unsere Tools nutzt. Die genauen Optionsnamen nehmen wir bei der Umsetzung aus der Doku (code.claude.com/docs/en/agent-sdk).
- **Python nur im offiziellen Evaluator** (lokal, nicht auf Railway) **und im eigenen Service `localizer`** für hloc und MegaLoc (Abschnitt 8). Alles andere ist TypeScript.
- **Handy-Tests brauchen HTTPS**, weil Kamera und Mikrofon nur im Secure Context laufen. Die Railway-URL erfüllt das.
- **Für die Jury:** Die öffentliche URL plus `README` mit lokalem Start (`pnpm i`, `.env.example`). Der Benchmark läuft ohne Railway, mit einem einzigen Befehl.
- **Sonntagsgebäude:** `bench` importiert den Ordner in die DB und beantwortet die Fragen. Für die Demo laden wir dasselbe JSON in die App.

## 4. Voice-Architektur

```
Browser (React)
  ├─ GET /api/voice/token?agent=navigator|admin → Conversation Token (WebRTC)
  ├─ useConversation ── Audio ⇄ ── ElevenLabs Agent
  │                                · STT, Turn-Taking, Barge-in
  │                                · LLM: Claude Sonnet 5.5
  │                                · TTS: eleven_v4_turbo (~100 ms), DE/EN
  │    clientTools (Namen in docs/elevenlabs-agent-config.md):
  │      Navigation: find, route, next_step, plan_tour (Add-on)
  │      Verwaltung: propose_edit, commit_edit, undo, what_if
  │      └─ fetch /api/tools/<name> → Node-Service (core/ + DB) → Ergebnis an den Agenten + sofort auf die Karte
  └─ WSS /ws/:building ⇄ Node-Service  (building_changed an alle Clients)
```

**Warum Client-Tools, die ans Backend weiterleiten:** ElevenLabs ruft das Tool im Browser auf. Der Browser fragt unser Backend, zeigt das Ergebnis **sofort** auf der Karte und gibt dem Agenten ein kompaktes JSON zurück (`expects_response`). Ein zweiter LLM-Aufruf zum Zeichnen ist nicht nötig, und das gleiche Setup funktioniert lokal wie in der Cloud.

Da die App eine öffentliche Railway-URL hat, wären auch Server-Tools (Webhooks) ohne Tunnel möglich. Wir bleiben trotzdem bei Client-Tools, weil sie die Karte direkt aktualisieren.

Die Zustandshoheit liegt beim Server: Gebäudeversion pro Gebäude, `commit_edit` nur mit `proposal_id` und idempotent. Wird die Sprache unterbrochen, darf kein Commit doppelt passieren.

**Offen: ein oder zwei „Gehirne“ (vor Phase A gemeinsam entscheiden).** Der Voice-Agent hat ein eigenes LLM in ElevenLabs. Unser Agent Harness hat ein zweites. 
- **Option 1, ElevenLabs-LLM wählt die Tools:** das eingebaute `claude-sonnet-5-5` mit niedrigem Reasoning-Aufwand ruft die Client-Tools direkt auf. Schnell und einfach. Nachteil: ein zweiter Prompt und eine zweite Tool-Auswahl neben Textchat und Benchmark. Abgerechnet über ElevenLabs-Credits.
- **Option 2, ein Gehirn:** ElevenLabs nutzt einen **Custom-LLM-Endpoint** `/api/llm/v1/chat/completions` (OpenAI-kompatibel, SSE) auf unserem Harness. Voice, Textchat und Benchmark nutzen dann denselben Agenten und dieselben Tools. Nachteil: mehr Latenz und mehr Bauaufwand. Abgerechnet über unsere 600 USD. Pro Turn darf nur **eine** Seite Tools ausführen.
- **Harness:** entschieden, Claude Agent SDK (Abschnitt 2). Bei Option 2 läuft auch Voice durch diesen Agenten.

**Prompt-Regeln für Voice:**
- Sofort eine kurze Bestätigung sprechen, etwa „Okay, ich suche den Weg zur Presse …“.
- Höchstens drei Schritte auf einmal, dann „sag *weiter*“.
- Landmarken statt Raumnummern.
- Genau eine Rückfrage, wenn ein Pflichtparameter fehlt (Start, Breite, Etage).
- Vor jeder Änderung eine Vorschau zeigen und auf ein „Ja“ warten.
- Persona merken: Wer „Rollstuhl“ sagt, bekommt ab dann immer stufenlose Routen.
- **Keine Gebäudedaten im Prompt** des Voice-Agenten. Er bekommt alles über Tools.

**Latenzziel (messen, nicht versprechen):** erste hörbare Reaktion unter 1 s, einfache Route auf der Karte unter 3 s. Dafür liegen Geometrie und Graphdaten vorberechnet in der Gebäude-DB, möglichst nur einen fachlichen Tool-Aufruf pro Frage, kurze Tool-Ergebnisse.

**Fallback ohne Mikrofon oder Credits:** Textchat im selben UI über `/api/chat`, mit denselben Tools.

## 5. Core: Datenbank und Routenmodell

**Vorberechnete Datenbank (SQLite):**
- **Basistabellen** wie in `building.json`: `buildings`, `floors`, `spaces`, `openings`, `connectors`, `connector_stops`, `assets`.
- **Vorberechnet** beim Import: Fläche, Mittelpunkt und Ankerpunkt pro Raum; Ankunftspunkt jeder Tür im Raum; Gehwege innerhalb jedes Raums (Ankerpunkt zu Tür, Tür zu Tür); gemeinsame Wandlänge zwischen Räumen (`space_adjacency`, Regel 0,35 m / 1 m); Raum darüber und darunter (`space_stacking`); Weg zum nächsten Eingang. Kürzeste Wege zwischen allen Räumen (normal und stufenlos) nur, wenn die Tabelle klein genug bleibt.
- **Ein Schreibweg:** Import und Änderungen (Tür, Sperrung, Raum) laufen durch denselben Code. Bei einer Änderung rechnet er nur die betroffenen Werte neu. Eine neue Tür ändert nur die Gehwege der zwei Räume, die sie verbindet.
- Der Agent liest die DB nur. Routen mit Bedingungen (Türbreite, Sperrung, neue Tür) berechnen Tools zur Laufzeit.
- **Geometrie ohne shapely:** Ankerpunkt (`representative_point`), Verkleinern und Vergrößern von Polygonen (`buffer`), nächster Punkt und "Segment liegt im Polygon" in TypeScript. Flächen und Mittelpunkte mit Standardformeln. Das Verkleinern muss die runden Ecken wie shapely erzeugen, sonst stimmen die Längen nicht auf den Zentimeter. Wir prüfen mit Vitest gegen die Routenlängen der Warm-up-Fragen in train und dev.

**Routenmodell** (README Abschnitt 3, gilt für alle Routenfragen, Warm-up und Benchmark):
- **Knoten:** ein Ankerpunkt pro Raum (`representative_point`) und ein Knoten pro Tür.
- **Gehen im Raum:** Jede Tür landet 30 cm im Raum (nächster Punkt von `buffer(-0.30)`, bei schmalen Räumen `buffer(-0.05)`). Der Schritt von der Tür zur Landung zählt mit. Zwischen Ankerpunkt und Türen eines Raums gilt der kürzeste Weg auf `buffer(-0.15)`: Sichtbarkeitsgraph aus den Punkten und den Ecken der verkleinerten Fläche. Ein Segment ist frei, wenn `buffer(0.02)` der verkleinerten Fläche es abdeckt. Gibt es keinen freien Weg, zählt die Luftlinie × 1,5. Kantenlängen auf 3 Nachkommastellen gerundet.
- **Ein Flur, durch den man nur geht,** wird von Tür zu Tür gemessen, nicht über seinen Ankerpunkt. Start und Ziel sind die Ankerpunkte der Räume.
- **Treppe:** 2 m pro Höhenmeter, nur zwischen benachbarten Halten. **Lift:** 15 m einmal pro Fahrt + 1 m pro Höhenmeter, eine Kante zwischen jedem Paar von Halten. Höhe = Differenz der `elevation_m`.
- **Kein Weg außen herum:** Eingänge verbinden nichts miteinander. Sind zwei Teile nur außen verbunden, ist die Antwort `reachable: false`.
- **Parallele Verbindungen** bleiben erhalten (Treppe und Lift, zwei Türen zwischen denselben Räumen). `space_path` listet jeden durchquerten Raum.
- **Tests:** Warm-up-Routen in train und dev auf den Zentimeter, dazu handprüfbare L- und U-Räume ohne Strecke durch Wände.
- **Constraints:** `step_free, min_door_width, vehicle(forklift), allow_stairs, allow_lifts, closed, extra_doors, no_transit_types`. Produktionsbereiche bleiben als Start und Ziel erreichbar. Eine Öffnung ab 3 m beweist allein noch keinen Gabelstapler-Gang (Frage an Synera). „Gang blockiert“ heißt in der Demo, dass ein **vorhandener** Gang gesperrt wird; Teilsperrungen innerhalb einer Halle bauen wir nicht.

## 6. Modelle und Budget (600 USD Anthropic)

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

Der Puffer im Benchmark ist für den Fall gedacht, dass wir auf Sonnet wechseln müssen. Zusätzliche Kosten außerhalb der 600 USD: ElevenLabs-Credits (Agent-Minuten und eingebautes LLM) und Railway.

**Caching:**
- Tool-Schemas und Systemregeln stehen eingefroren am Anfang, die Frage kommt zuletzt.
- Gebäudedaten nur über Tools abfragen, **nie das ganze JSON** in den Prompt.
- `cache_control` setzen und `cache_read_input_tokens` loggen.
- Batch-API (−50 %) für große dev-Läufe, wenn die Latenz egal ist.
- Für jede Frage Kosten, Tool-Aufrufe und Latenz loggen. Ergebnisse checkpointen, bei Wiederholung nur die fehlerhaften Fragen neu laufen lassen.

## 7. Was schon da ist

| Wo | Inhalt | Zustand |
|---|---|---|
| `benchmark/` | Offizieller Evaluator (`evaluate.py`) und Scorer (`score.py`) von Synera, Python | `score.py` bleibt unverändert. `evaluate.py` lädt ohne `--agent` noch den entfernten Starter Agent. In Phase 2 stellen wir den Standard auf unseren eigenen Agenten um (über `bench/answer.py`) |
| Lenards UI-Prototyp "Building Guide" (`web/mobile/`) | Mobile-Ansicht mit Vollbildkamera, Route, Minimap, Chat und Blobatar-Avatar. React 19, Vite, pnpm, Vitest | Vorlage für die Mobile-Ansicht. Route, Position und Chat sind noch Demo-Daten |
| Dieses Repo | Notizen, PDFs, Transkripte (Lead-Q&A, Hagens UX-Erklärung, Brainstorming), Route-Spec, dieser Plan | Ältere Pläne und Recherchen in `docs/archive/`. `.env` wird nicht verfolgt |

Testset (145 Fragen): floor_area_total 33 · shared_walls 26 · largest_room 21 · errand 20 · wide_delivery 18 · straight_line_3d 15 · room_stacked 9 · what_if_door 3.

## 8. Implementierungsreihenfolge

**Reihenfolge:** 1 Datenbank → 2 Agent → danach parallel **A** Voice und **B** Oberfläche (B.1 Visualisierung, B.2 UI/UX mit Mobile und Desktop).

| Phase | Inhalt | Fertig, wenn |
|---|---|---|
| **1 Datenbank** | Setup: pnpm, TypeScript, Vitest, `AGENTS.md`, `.env.example`. **Vorberechnete Felder** für die Fragen (Abschnitt 5). **Import-Feature:** `building.json` → Validator → DB, derselbe Weg für Kit-Gebäude, Sonntagsgebäude und Upload in der App. Core-Graph: Constraints, Erreichbarkeit, Routen, What-if | Warm-up-Routen auf den Zentimeter, Geometrie-Arten ≈ 100 % auf dev und train, alle 280 Gebäude importierbar |
| **2 Agent** | Harness mit dem Claude Agent SDK aufsetzen, eingebaute Tools aus. API zum LLM. **DB-Tools zum Lesen und Schreiben**, Schreiben nur über den einen Schreibweg mit Vorschau und Bestätigung. Skills und Prompts pro Fragetyp. Benchmark-CLI und `BENCHMARK.md`. `benchmark/evaluate.py` startet ohne `--agent` unseren eigenen Agenten statt des Starter Agents. API im Node-Service | **M1:** vollständige Test-CSV mit 145 Zeilen und dev-Score pro Fragetyp, end to end auf den dev-Fragetexten |
| **A Voice** | Realtime-Voice-Layer mit ElevenLabs für Mobile und Desktop. Token-Endpunkt, Client-Tools auf dieselbe Tool-API wie der Agent | Eine gesprochene Frage zeigt eine Route, auf Mobile und Desktop |
| **B.1 Visualisierung** | 2D (SVG) und 3D (extrudiert), **deterministisch aus der DB**: Etagen, Räume, Türen, Assets, Route, Highlights, Vorschau von Änderungen | Gleiche Daten ergeben immer dasselbe Bild. Alle Etagen eines dev-Gebäudes korrekt |
| **B.2 UI/UX** | Eine Web-App mit zwei Ansichten, siehe unten | **M2:** Demo-Abläufe aus Abschnitt 12 laufen auf der öffentlichen URL |
| Danach | Fahrzeuge (Abschnitt 5): Gabelstapler, kein Transit durch Produktion | Tests aus Abschnitt 5 sind grün |

### UI/UX: eine Web-App, zwei Ansichten, keine native App

**Mobile (unterwegs):**
- Ziel: schnell herausfinden, wohin ich gehen muss, und dorthin kommen. Fokus auf dem Voice-Agenten.
- Vor dem Start wähle ich die Art der Führung: **Karte**, **Wegbeschreibung** oder **AR** (Kamerabild mit Weganweisungen).
- Start auch über einen QR-Code aus der Desktop-Ansicht. Der Link öffnet die Mobile-Ansicht mit dem Objekt als Ziel, als Add-on auch mit einer ganzen Tour.
- **AR nur per Kamera, als späteres Zusatzfeature** nach den Phasen 1, 2, A und B. Keine Tiefen- oder Abstandssensoren. Ablauf aus Lenards Codex-Test:
  - Einmalig: Video des Gebäudes aufnehmen, Referenzbilder auswählen, pro Bild einen MegaLoc-Suchvektor und SuperPoint-Merkmale speichern.
  - Live: Das Handy schickt 1–2 klare Bilder pro Sekunde an den Server. [hloc](https://github.com/cvg/Hierarchical-Localization) sucht mit MegaLoc die ähnlichsten Referenzbilder, LightGlue gleicht nur diese ab, eine geometrische Prüfung verwirft unsichere Treffer. "Keine sichere Position" ist ein gültiges Ergebnis.
  - Die Position geht direkt an Routenplanung und Anzeige. Der Voice-Agent bekommt Raum- und Etagenwechsel als Kontext-Update. Laut ElevenLabs unterbricht ein solches Update keine laufende Antwort.
  - **Stand:** Offline auf dem Mac getestet. Ein Foto fand das passende Videobild mit 180 geprüften Punkten, 1,2 s Rechenzeit auf der CPU. Es fehlt noch die Zuordnung der Referenzbilder zu Koordinaten im Grundriss.
  - Grenzen: Eine Web-App hat ohne WebXR keine Bewegungsverfolgung zwischen zwei Ortungen. iPhone Safari unterstützt kein WebXR `immersive-ar`.
  - **Eigener Dienst in Python**, getrennt vom TypeScript-Stack, weil hloc ein Python-Projekt ist. Code: `floor-localizer` im Codex-Workspace.
  - **Kamerabilder:** Bis AR kommt, verlassen keine Bilder den Browser (Regel in `web/mobile/AGENTS.md`). Mit AR schickt das Handy Bilder nur im AR-Modus und nur an unseren eigenen Ortungsdienst. Der Dienst speichert sie nicht.

**Desktop (Verwaltung und Planung):**
- Gebäude ansehen, Teile und Räume suchen, ihren Ort auf der Karte zeigen.
- Elemente und Objekte verschieben, zum Beispiel eine Maschine in einen anderen Raum. Das läuft über den Schreibweg der DB.
- Voice- und Chat-Layer.
- **Multi-User nur als Mock:** Andere Nutzer, Anwesenheit und Aktivitäten sehen echt aus, sind aber nicht implementiert. Die App soll wie ein vollständiges Produkt wirken.
- Klick auf ein Objekt, zum Beispiel eine Maschine, zeigt einen **QR-Code**. Mit dem Handy gescannt, startet er die Mobile-Ansicht mit Navigation zu diesem Objekt.

**Add-ons aus Hagens User Journey** (nach den Phasen 1, 2, A und B, Quelle: `Hagen UX explanation transcript.md`):
- **Tour mit mehreren Teilen:** Am Desktop mehrere Teile wählen, das System schlägt eine gute Reihenfolge vor. Der QR-Code bringt die ganze Tour aufs Handy. Bis 7 Stopps rechnen wir alle Reihenfolgen durch, darüber eine Heuristik, die wir als solche benennen.
- **Störung während der Tour:** Ein Lift wird in der Verwaltung gesperrt. Das Handy bekommt das Ereignis über den WebSocket, sagt es an und berechnet die restliche Tour neu. Mit Rollstuhlprofil wird daraus nie still eine Treppenroute. „Keine Route“ ist eine gültige Antwort.
- **Teile bewegen sich:** kleine Animation in der Verwaltungsansicht, keine echte Ortung.

## 9. Zeitplan

| Zeit | A: Core/Bench | B: Frontend + Railway | C: Voice/Agent/Demo |
|---|---|---|---|
| **Sa 17:15–17:45** | Phase 1 Setup, Tool-Vertrag einfrieren (Namen, Parameter, Ergebnisformat), Referenzgebäude und erwartete Route für das Gate festlegen | Railway-Setup, Vite/React-Gerüst | Abrechnung klären (ElevenLabs-Credits?), Agent anlegen, Discord-Fragen stellen |
| **17:45–18:30** | Phase 1 Datenbank | Node-Service öffentlich auf Railway, Secret-Test. Dann B.1 minimale 2D-Karte | A: `/tools/route`, `useConversation`. C hält den Vertrag für Tools und Voice, B die Infrastruktur |
| **18:30** | **Integrationsgate (alle):** Voice → Tool → Karte, lokal, auf dem Referenzgebäude | | |
| **18:30–21:00** | Phase 2 Agent → **M1** (145 Zeilen + dev-Score pro Typ) | Deploy, **20:00 Abnahme**, dann B.1 Visualisierung | Alle Client-Tools, Voice-Prompt-Regeln, Textchat |
| **21:00–00:30** | Constraints (Gabelstapler, Produktion) | B.2 Mobile und Desktop, Änderungen mit Vorschau, Bestätigung und Undo | Voice auf Mobile und Desktop, Rückfrage-Logik → **M2** |
| **00:30 Gate** | Bestätigte Änderung, QR-Code vom Desktop öffnet die Mobile-Ansicht, Undo, Wiederherstellung nach Neustart des Service (Volume). **Danach keine neue Infrastruktur** | | |
| **00:30–03:00** | Regression auf dev, Checkpointing | Handy-Test auf der öffentlichen URL (HTTPS), AR mit Timebox | Rohschnitt fürs Video |
| 03:00–07:00 | **Schlafen** (dank Zeitumstellung eine Stunde mehr) | | |
| **So 07:00–09:00** | Ein dev-Gebäude wie ein unbekanntes durchlaufen lassen, finale Test-CSV, Installationsprobe auf frischem Klon | 3D **erst nach** bestandenem Frischklon- und Benchmark-Lauf → **M3** | Härtetest mit schwierigen Nutzern |
| **ab 09:00 bis zur Abgabe** | **Bereitschaft für das Sonntagsgebäude:** eine Person lässt `bench` laufen, sobald es erscheint, und lädt es in die App | Bugfixes | Video aufnehmen |
| **10:00 Feature Freeze** | BENCHMARK.md, README, exportierte Agent-Konfiguration. **Ausnahme:** Anpassungen an Sonntagsformat und Datenadapter bleiben erlaubt | Letztes Deploy, URL in die Abgabe | Video schneiden, technische Erklärung (Architektur statt Code) |
| **12:00–13:00** | Nur Abschlusslauf, Upload, Abgabe prüfen | | |

**Streichreihenfolge:** 3D → zusätzliche Logistikfunktionen. **Voice bleibt Pflicht**, M1 wird nie gefährdet.

## 10. Offene Fragen an Synera (heute per Discord)

Beantwortet durch Kit 1.1.0: welches Routenmodell für errand und Routen gilt (nur noch eines) und wo Start und Ziel liegen (Ankerpunkt des Raums).

1. Sonntagsformat: **`answers.json` (PDF) oder CSV (README)**? Sind die Knoten-IDs `space_id`s? Wie wird „unerreichbar“ dargestellt? Wann wird veröffentlicht, wie lange haben wir?
2. Woran erkennt man **Gabelstapler-Gänge und Fußwege** in den Daten? Welche Raumtypen sind „Produktionsbereich“?
3. Kommen am Sonntag auch locate-, route- und tour-Fragen?
4. Abgabe: Gilt die README 1.1.0 (CSV und 3–5 Minuten Live-Demo ohne Neustart) oder noch das PDF (Demo-Video, technische Erklärung, `BENCHMARK.md`, `answers.json`, vier Finalisten mit 3 + 1 Minuten)? Gibt es noch eine Finalrunde?

## 11. Codex-Review: übernommen und abweichend

Übernommen:
- Abrechnung als Entscheidungspunkt am Anfang
- Randfälle beim Verkleinern der Polygone (jetzt im Routenmodell der Jury geregelt)
- Integrationsgate um 18:30
- Budgetaufteilung
- Feature Freeze um 10:00, Zeitumstellung, „Voice bleibt Pflicht“

Abweichend:
- Codex schlägt Server-Tools (Webhooks) vor. Wir nehmen **Client-Tools, die ans Backend weiterleiten**, weil die Karte sich so ohne Umweg aktualisiert. Die Zustandshoheit liegt trotzdem auf dem Server.
- Codex gibt für das Lesen aus dem Cache 0,05× an. Laut Anthropic-Preisliste liegt Sonnet 5.5 bei 0,20 USD pro MTok, also 0,1×.

**Zweites Review (Hosting, Stack, Repos)** mit dem Urteil „technisch stimmig, für drei Personen aber zu breit“. Übernommen:
- Härtere Kriterien für M1 und das 00:30-Gate
- Ausnahme vom Feature Freeze für den Sonntagsadapter
- Keine pauschale Verbindung zerfallener Polygone
- Lizenzen präzisiert, dazu eine Herkunftsliste (Abschnitt 13)

3D bleibt Kür. Ob wir den Custom-LLM-Endpoint bauen, ist offen (Abschnitt 4). Container, Python-Core, Bildimport und native Apps sind gestrichen (Abschnitt 2).

## 12. Demo-Story (Live-Demo 3–5 Minuten, 25 Interaktionspunkte)

**Regeln:** Die Demo läuft live und ohne Neustart (README 1.1.0). Kein Deploy vor der Demo, ein vollständiger Probelauf auf der öffentlichen URL, Textchat als Fallback, wenn das Mikrofon versagt. Dieselbe Geschichte nutzen wir für das Video.

Fabrikhalle, drei Nutzer auf zwei Geräten, eine Karte, alles per Stimme:
1. **Techniker** am Handy (Mobile-Ansicht, gestartet über den QR-Code an der Maschine im Desktop): „Welche Presse ist Linie 4, wie komme ich hin?“ Der Agent antwortet mit Landmarken, die Route ist animiert, die nächsten Schritte kommen auf „weiter“.
2. **Facility Manager** am Laptop: „Der Ostlift ist in Wartung.“ Der Agent zeigt eine Vorschau mit den betroffenen Routen und wartet auf ein „Ja“. Danach aktualisiert sich die Karte **sofort auch auf dem Handy des Technikers**.
3. **Gabelstaplerfahrer:** „Gang 4 ist blockiert, schnellster Weg zu Dock B?“ Die Route nutzt nur Öffnungen ab 3 m und fährt nicht durch die Produktion.
4. Aufklappbare Ansicht „So habe ich das berechnet“ mit dem Tool-Trace. Das ist Syneras Linie: *„Das LLM interpretiert, die Regeln entscheiden.“*
5. Am Ende kurz der Benchmark-Score und die Kosten pro Frage als Beleg für Effizienz.

**Erweiterung, wenn die Add-ons stehen:** Manfred ist neu in der Fabrik und muss fünf Teile holen. Er wählt sie am Desktop, scannt den QR-Code und läuft die Tour mit dem Handy. Unterwegs fällt ein Lift aus, und die App führt ihn über die Treppe weiter.

## 13. Wiederverwendung aus unserer Recherche

Quelle: frühere Recherche außerhalb dieses Repos (`../repo/`, nicht verfügbar) und `docs/archive/research/`. Die Grundregel: Wir übernehmen **Code nur bei MIT- oder Apache-Lizenz**. Aus GPL-Projekten übernehmen wir nur Ideen. Keines der Projekte ersetzt unseren Core, denn die Distanzen müssen exakt Syneras Modellen folgen.

| Wo im Stack | Projekt | Was wir übernehmen | Phase |
|---|---|---|---|
| Suche (`core/`) | [NavigaTUM](https://github.com/TUM-Dev/NavigaTUM) (GPL-3.0, nur Ideen) | Raumnummern normalisieren (führende Nullen), Lexer-Trick `MW1801` → „mw 1801 mw1801“, Synonymliste DE/EN (Hörsaal/HS, WC/Toilette), Such-Regressionstests als YAML | 1, B.2 |
| Routing (`core/`) | [c3nav](https://github.com/c3nav/c3nav) (Apache-2.0) | Kartendaten und abgeleiteter Router getrennt, Einschränkungen als Daten. Das ist das Muster für unsere `Constraints` | 1 |
| Wegbeschreibung | Papers [Grid2Guide](https://arxiv.org/abs/2508.08100), [Floorplan2Guide](https://arxiv.org/abs/2512.12177), [LLM-Guided Indoor Nav](https://arxiv.org/abs/2503.11702v4) | Graph rechnet, LLM formuliert. Anweisungen mit Landmarken statt Raumnummern | B.2 |
| 2D-Plan (`web/`) | [KnotzerIO/indoor-wayfinder](https://github.com/KnotzerIO/indoor-wayfinder) (React + SVG, MIT laut Codex) | Vorlage für SVG-Karte und Zoom. Wichtig: eine gemeinsame Koordinatentransformation mit umgedrehter Y-Achse, und den Routenpfad liefert das Backend als Geometrie | B.1 |
| 2D-Etagen-UX | NavigaTUM `IndoorMap.vue`, `FloorControl.ts` (nur Ideen) | Route pro Etage schneiden, aktive Etage solid, andere als „Geister“, Etagenwahl mit `level-changed`-Event | B.2 |
| Änderungen (Vorschau, Undo) | [indoorMaps](https://github.com/hadencain/indoorMaps) (Lizenz unklar, nur UX) | Vorschau einer neuen Tür, Undo/Redo, Route zum nächsten Ausgang | B.2 |
| 3D (`web/`) | [react-three-fiber](https://github.com/pmndrs/react-three-fiber) + drei (MIT); UX von [xeokit-bim-viewer](https://github.com/xeokit/xeokit-bim-viewer) (**AGPL-3.0, nur UX-Ideen**) und Mappedin Stacked Maps | Etagen aus den Polygonen extrudiert. Auseinandergezogene Etagen, nicht aktive Etagen halbtransparent | B.1 |
| Voice-UI | [ElevenLabs UI](https://github.com/elevenlabs/ui) (MIT; Orb, Conversation Bar) | Fertige React-Komponenten statt eigener Voice-UI, aber nur, wenn sie im Vite-Gerüst schnell laufen | A, B.2 |
| Logistik (Level 5) | [Open-RMF](https://github.com/open-rmf/rmf_traffic) (Apache-2.0, nur Konzept) | Wegenetz, Fahrzeugprofil und Belegung getrennt. Für den Pitch als nächster Schritt | Danach |
| JSON-Validator | [Open-Location-Stack/floorplan-editor](https://github.com/Open-Location-Stack/floorplan-editor) (IMDF-Validator) | Idee für unseren Validator: gültige Polygone, Türen auf gemeinsamen Wänden, alles erreichbar | 1 |

**Reihenfolge beim Wiederverwenden:** zuerst offizielle SDK-Beispiele, dann kleine UI-Komponenten. Andere Indoor-Systeme dienen heute nur als Referenz, denn ihre Datenmodelle zu integrieren kostet mehr Zeit, als es bringt. Weitere Recherche ist nicht nötig.

**Herkunftsliste `THIRD_PARTY.md`:** Für jede Übernahme notieren wir Projekt, Commit, übernommene Dateien, Lizenz und nötige Hinweise. Aus GPL-Projekten werden keine Synonymlisten oder Test-Fixtures mitkopiert. Unabhängig davon gelten die **Datenlizenzen** aus `ATTRIBUTION.md`: ODbL für OSM, CC BY 4.0 für Swiss Dwellings und ResPlan, CC0 für die prozeduralen Gebäude.

**Bewusst nicht im Wochenend-Stack**, aber als Ausblick für den Pitch geeignet:
- Planerkennung mit ML: [CubiCasa5k](https://github.com/CubiCasa/CubiCasa5k), DeepFloorplan
- BIM-Import mit [IfcOpenShell](https://github.com/IfcOpenShell/IfcOpenShell)
- Kamera-Lokalisierung im Grundriss: [F3Loc](https://github.com/felix-ch/f3loc), PALMS
- WebXR-AR-Pfeile und SLAM

AR per Kamera mit hloc und MegaLoc ist dagegen als späteres Add-on geplant (Abschnitt 8).
