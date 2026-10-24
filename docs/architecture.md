# Architektur

Primäre Datei für das **Wie**: Stack, Repo-Struktur, Deployment, Datenbank, Routenmodell, Agent Harness und Voice-Architektur. Feste Entscheidungen stehen in [`PLAN.md`](../PLAN.md) §0, Schnittstellen in [`contracts.md`](contracts.md).

## 1. Stack

| Schicht | Technik | Aufgabe |
|---|---|---|
| **Frontend** | React 19 + Vite + TypeScript, CSS mit Design-Tokens wie im Prototyp, Zustand (State). Die UI aus Lenards Prototyp (`web/mobile/`) übernehmen wir | Eine Web-App, zwei Ansichten: Verwaltung (Desktop) und Navigation (Handy), siehe [`product.md`](product.md) |
| 2D-Plan | Eigenes SVG aus den Polygonen (lokale Meter, keine Kartenprojektion) | Etagen, Räume, Türen, Assets, Route, Highlights, Vorschau von Änderungen |
| 3D-Ansicht | react-three-fiber + drei, Etagen direkt aus den Polygonen extrudiert | Gestapelte Etagen, animierte Route |
| Voice | `@elevenlabs/react` (`useConversation`), Client-Tools | Mikrofon, Barge-in, Tool-Aufrufe aus dem Agenten |
| **Datenbank** | SQLite über `node:sqlite`, lokal und auf dem Railway-Volume | Basisdaten plus vorberechnete Werte (Abschnitt 5) |
| **Core** | TypeScript-Bibliothek `core/`: Geometrie, Graph, Routing, What-if, Änderungen | Deterministisch. Läuft lokal, im Benchmark und in der Cloud mit demselben Code |
| **Agent** | Claude Agent SDK (`@anthropic-ai/claude-agent-sdk`). Unsere DB-Tools hängen als MCP-Server im selben Prozess am Agenten. Eingebaute Datei-, Shell- und Web-Tools sind aus. Sonnet 5.5, Prompt-Caching | Textchat, Benchmark und optional Custom-LLM für ElevenLabs. Läuft im Node-Service auf Railway |
| Agent (Voice) | Zwei ElevenLabs-Agents (Navigation, Verwaltung): `eleven_v4_turbo` + eingebautes `claude-sonnet-5-5`. Einstellungen in [`elevenlabs-agent-config.md`](elevenlabs-agent-config.md) | Gespräch, Rückfragen, Tool-Auswahl |
| **Benchmark** | TypeScript-CLI, ein Befehl, nutzt denselben Agenten und dieselbe DB. Ein kleiner Python-Adapter `bench/answer.py` ruft die CLI auf, damit der offizielle Evaluator läuft | Läuft lokal, schreibt die Abgabe-CSV (und `answers.json`, falls gefordert) |
| Tooling | pnpm, Vitest (Tests gegen train/dev), Railway CLI. Python-Tools (`uv`) nur für `benchmark/` | |

## 2. Repo-Struktur

```
AGENTS.md    Regeln für Coding-Agenten
PLAN.md      Entscheidungen, Reihenfolge, Zeitplan, Abgabe, offene Fragen
core/        TypeScript: Schema, Import, Geometrie, Graph, Routing, Änderungen
agent/       TypeScript: Agent Harness, Tool-Definitionen, Prompts
bench/       TypeScript: Benchmark-CLI, Parser/Serializer CSV + JSON; answer.py als Adapter
web/         React-App mit zwei Ansichten (Mobile-Prototyp in web/mobile/)
server/      Node-Server (Hono): API, WebSocket, Static Assets, Event-Log
data/        Kit-Daten (Kit 1.1.0, unverändert)
benchmark/   offizieller Evaluator und Scorer von Synera (Python)
docs/        primäre Dateien, sources/ (Belege), archive/ (gilt nicht mehr)
```

Tests liegen neben dem Code (`*.test.ts`) und laufen gegen die Antworten in train und dev.

## 3. Deployment auf Railway

```
Browser ──HTTPS/WSS──► Railway-Service "app" (Node, TypeScript)
                        ├─ /            Static Assets (Vite-Build von web/)
                        ├─ /api/voice/token   ELEVENLABS_API_KEY → Conversation Token (WebRTC)
                        ├─ /api/tools/*, /api/chat   → Agent Harness + core/ auf der Gebäude-DB
                        └─ /ws/:building       WebSocket: Ereignisse an alle Clients
                               └─ Volume /state: SQLite (Gebäude-DB + Event-Log)

Später, nur für AR:  Railway-Service "localizer" (Python, hloc) ← Kamerabilder vom Handy
```

- **Ein Node-Service** liefert App, API und WebSocket aus. Server-Framework: Hono auf Node. Core, Agent Harness und DB laufen im selben Prozess.
- **Datenbank:** SQLite über `node:sqlite` auf einem Railway-Volume unter `/state`, nicht unter `/app/data`. Basisdaten plus Event-Log (Version, Undo). Die Kit-Gebäude importieren wir beim Start, nicht beim Build. Die DB-Datei wird erzeugt und nicht committed.
- **Grenzen von Railway:** Mit Volume sind keine Replicas möglich, und ein Redeploy hat kurze Downtime. Deshalb kein Deploy während Aufnahme oder Demo. Der Client verbindet den WebSocket automatisch neu und lädt danach den aktuellen Stand. App-Sleeping ausschalten.
- **Secrets als Railway-Variablen:** `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID_NAVIGATOR`, `ELEVENLABS_AGENT_ID_ADMIN`. Keys stehen nie im Repo und nie im Browser. Der Browser bekommt nur den kurzlebigen Conversation Token.
- **Offene Demo, nicht öffentlich gelistet:** Die App braucht kein Login, damit Jury und Live-Demo ohne Hürde laufen. Die URL steht nur in der Abgabe und im Team, nicht in öffentlichen Links. Die Seite setzt `noindex`. Ausgabenlimits bei Anthropic und ElevenLabs und ein einfaches Rate-Limit am Token-Endpunkt begrenzen den Schaden, falls die URL bekannt wird.
- **Python** läuft nur im offiziellen Evaluator (lokal, nicht auf Railway) und im späteren Service `localizer` für hloc und MegaLoc.
- **Handy-Tests brauchen HTTPS**, weil Kamera und Mikrofon nur im Secure Context laufen. Die Railway-URL erfüllt das.
- **Für die Jury:** die öffentliche URL plus `README` mit lokalem Start (`pnpm i`, `.env.example`). Der Benchmark läuft ohne Railway, mit einem einzigen Befehl.
- **Sonntagsgebäude:** `bench` importiert den Ordner in die DB und beantwortet die Fragen. Für die Demo laden wir dasselbe JSON in die App.

## 4. Agent Harness

- **Claude Agent SDK im Node-Service.** Es bringt Agent-Schleife, Kontextverwaltung, Hooks und Sessions mit. Seine eingebauten Datei-, Shell- und Web-Tools schalten wir aus, damit der Agent nur unsere Tools nutzt. Die genauen Optionsnamen nehmen wir bei der Umsetzung aus der Doku (code.claude.com/docs/en/agent-sdk).
- Das Modell entscheidet selbst, welche Tools es wie oft aufruft. Gebäudedaten kommen nur über Tools.
- Der Agent liest die DB. Schreiben geht nur über den einen Schreibweg mit Vorschau und Bestätigung ([`contracts.md`](contracts.md) §4).
- Skills und Prompts pro Fragetyp liegen in `agent/`.

**Caching:**
- Tool-Schemas und Systemregeln stehen eingefroren am Anfang, die Frage kommt zuletzt.
- Gebäudedaten nur über Tools abfragen, **nie das ganze JSON** in den Prompt.
- `cache_control` setzen und `cache_read_input_tokens` loggen.
- Batch-API (−50 %) für große dev-Läufe, wenn die Latenz egal ist.
- Für jede Frage Kosten, Tool-Aufrufe und Latenz loggen. Ergebnisse checkpointen, bei Wiederholung nur die fehlerhaften Fragen neu laufen lassen.

## 5. Voice-Architektur

```
Browser (React)
  ├─ GET /api/voice/token?agent=navigator|admin → Conversation Token (WebRTC)
  ├─ useConversation ── Audio ⇄ ── ElevenLabs Agent
  │                                · STT, Turn-Taking, Barge-in
  │                                · LLM: Claude Sonnet 5.5
  │                                · TTS: eleven_v4_turbo (~100 ms)
  │    clientTools (siehe contracts.md §3)
  │      └─ fetch /api/tools/<name> → Node-Service (core/ + DB) → Ergebnis an den Agenten + sofort auf die Karte
  └─ WSS /ws/:building ⇄ Node-Service  (Ereignisse an alle Clients)
```

**Warum Client-Tools, die ans Backend weiterleiten:** ElevenLabs ruft das Tool im Browser auf. Der Browser fragt unser Backend, zeigt das Ergebnis **sofort** auf der Karte und gibt dem Agenten ein kompaktes JSON zurück. Ein zweiter LLM-Aufruf zum Zeichnen ist nicht nötig, und das gleiche Setup funktioniert lokal wie in der Cloud. Server-Tools (Webhooks) wären auch möglich, aktualisieren die Karte aber nicht direkt.

**Zustandshoheit beim Server:** Gebäudeversion pro Gebäude, `commit_edit` nur mit `proposal_id` und idempotent. Wird die Sprache unterbrochen, darf kein Commit doppelt passieren.

**Ein oder zwei „Gehirne“** (offen, siehe [`PLAN.md`](../PLAN.md) §6):
- **Option 1, ElevenLabs-LLM wählt die Tools:** das eingebaute `claude-sonnet-5-5` mit niedrigem Reasoning-Aufwand ruft die Client-Tools direkt auf. Schnell und einfach. Nachteil: ein zweiter Prompt und eine zweite Tool-Auswahl neben Textchat und Benchmark. Abgerechnet über ElevenLabs-Credits.
- **Option 2, ein Gehirn:** ElevenLabs nutzt einen **Custom-LLM-Endpoint** `/api/llm/v1/chat/completions` (OpenAI-kompatibel, SSE) auf unserem Harness. Voice, Textchat und Benchmark nutzen dann denselben Agenten und dieselben Tools. Nachteil: mehr Latenz und mehr Bauaufwand. Abgerechnet über unsere Anthropic-Credits. Pro Turn darf nur **eine** Seite Tools ausführen.

**Latenzziel (messen, nicht versprechen):** erste hörbare Reaktion unter 1 s, einfache Route auf der Karte unter 3 s. Dafür liegen Geometrie und Graphdaten vorberechnet in der Gebäude-DB, möglichst nur ein fachlicher Tool-Aufruf pro Frage, kurze Tool-Ergebnisse.

**Fallback ohne Mikrofon oder Credits:** Textchat im selben UI über `/api/chat`, mit denselben Tools.

## 6. Core: Datenbank und Routenmodell

**Vorberechnete Datenbank (SQLite):**
- **Basistabellen** wie in `building.json`: `buildings`, `floors`, `spaces`, `openings`, `connectors`, `connector_stops`, `assets`.
- **Vorberechnet** beim Import: Fläche, Mittelpunkt und Ankerpunkt pro Raum; Ankunftspunkt jeder Tür im Raum; Gehwege innerhalb jedes Raums (Ankerpunkt zu Tür, Tür zu Tür); gemeinsame Wandlänge zwischen Räumen (`space_adjacency`, Regel 0,35 m / 1 m); Raum darüber und darunter (`space_stacking`); Weg zum nächsten Eingang. Kürzeste Wege zwischen allen Räumen (normal und stufenlos) nur, wenn die Tabelle klein genug bleibt.
- **Ein Schreibweg:** Import und Änderungen (Tür, Sperrung, Raum, Objekt verschieben) laufen durch denselben Code. Bei einer Änderung rechnet er nur die betroffenen Werte neu. Eine neue Tür ändert nur die Gehwege der zwei Räume, die sie verbindet.
- Routen mit Bedingungen (Türbreite, Sperrung, neue Tür) berechnen Tools zur Laufzeit.
- **Geometrie ohne shapely:** Ankerpunkt (`representative_point`), Verkleinern und Vergrößern von Polygonen (`buffer`), nächster Punkt und „Segment liegt im Polygon“ in TypeScript. Flächen und Mittelpunkte mit Standardformeln. Das Verkleinern muss die runden Ecken wie shapely erzeugen, sonst stimmen die Längen nicht auf den Zentimeter.

**Routenmodell** (README Abschnitt 3, gilt für alle Routenfragen, Warm-up und Benchmark):
- **Knoten:** ein Ankerpunkt pro Raum (`representative_point`) und ein Knoten pro Tür.
- **Gehen im Raum:** Jede Tür landet 30 cm im Raum (nächster Punkt von `buffer(-0.30)`, bei schmalen Räumen `buffer(-0.05)`). Der Schritt von der Tür zur Landung zählt mit. Zwischen Ankerpunkt und Türen eines Raums gilt der kürzeste Weg auf `buffer(-0.15)`: Sichtbarkeitsgraph aus den Punkten und den Ecken der verkleinerten Fläche. Ein Segment ist frei, wenn `buffer(0.02)` der verkleinerten Fläche es abdeckt. Gibt es keinen freien Weg, zählt die Luftlinie × 1,5. Kantenlängen auf 3 Nachkommastellen gerundet.
- **Ein Flur, durch den man nur geht,** wird von Tür zu Tür gemessen, nicht über seinen Ankerpunkt. Start und Ziel sind die Ankerpunkte der Räume.
- **Treppe:** 2 m pro Höhenmeter, nur zwischen benachbarten Halten. **Lift:** 15 m einmal pro Fahrt + 1 m pro Höhenmeter, eine Kante zwischen jedem Paar von Halten. Höhe = Differenz der `elevation_m`.
- **Kein Weg außen herum:** Eingänge verbinden nichts miteinander. Sind zwei Teile nur außen verbunden, ist die Antwort `reachable: false`.
- **Parallele Verbindungen** bleiben erhalten (Treppe und Lift, zwei Türen zwischen denselben Räumen). `space_path` listet jeden durchquerten Raum.
- **Tests:** Warm-up-Routen in train und dev auf den Zentimeter, dazu handprüfbare L- und U-Räume ohne Strecke durch Wände.

**Constraints:** `step_free, min_door_width, vehicle(forklift), allow_stairs, allow_lifts, closed, extra_doors, no_transit_types`.
- Ein Gabelstapler fährt nur durch Gänge und Öffnungen ab 3 m. Eine Öffnung ab 3 m beweist allein noch keinen Gabelstapler-Gang (Frage an Synera).
- Produktionsbereiche sind nur Ziel, kein Transit. Sie bleiben als Start und Ziel erreichbar.
- Eine Route zu einem Gerät endet im Raum, der es enthält.
- „Gang blockiert“ heißt in der Demo, dass ein **vorhandener** Gang gesperrt wird. Teilsperrungen innerhalb einer Halle bauen wir nicht.

## 7. Wiederverwendung und Lizenzen

Wir übernehmen **Code nur bei MIT- oder Apache-Lizenz**. Aus GPL-Projekten übernehmen wir nur Ideen. Keines der Projekte ersetzt unseren Core, denn die Distanzen müssen exakt dem Routenmodell folgen. Reihenfolge: zuerst offizielle SDK-Beispiele, dann kleine UI-Komponenten.

| Wo im Stack | Projekt | Was wir übernehmen | Phase |
|---|---|---|---|
| Suche (`core/`) | [NavigaTUM](https://github.com/TUM-Dev/NavigaTUM) (GPL-3.0, nur Ideen) | Raumnummern normalisieren (führende Nullen), Lexer-Trick `MW1801` → „mw 1801 mw1801“, Synonymliste DE/EN (Hörsaal/HS, WC/Toilette), Such-Regressionstests als YAML | 1, B.2 |
| Routing (`core/`) | [c3nav](https://github.com/c3nav/c3nav) (Apache-2.0) | Kartendaten und abgeleiteter Router getrennt, Einschränkungen als Daten. Das ist das Muster für unsere Constraints | 1 |
| Wegbeschreibung | Papers [Grid2Guide](https://arxiv.org/abs/2508.08100), [Floorplan2Guide](https://arxiv.org/abs/2512.12177), [LLM-Guided Indoor Nav](https://arxiv.org/abs/2503.11702v4) | Graph rechnet, LLM formuliert. Anweisungen mit Landmarken statt Raumnummern | B.2 |
| 2D-Plan (`web/`) | [KnotzerIO/indoor-wayfinder](https://github.com/KnotzerIO/indoor-wayfinder) (React + SVG, MIT) | Vorlage für SVG-Karte und Zoom. Eine gemeinsame Koordinatentransformation mit umgedrehter Y-Achse; den Routenpfad liefert das Backend als Geometrie | B.1 |
| 2D-Etagen-UX | NavigaTUM `IndoorMap.vue`, `FloorControl.ts` (nur Ideen) | Route pro Etage schneiden, aktive Etage solid, andere als „Geister“ | B.2 |
| Änderungen (Vorschau, Undo) | [indoorMaps](https://github.com/hadencain/indoorMaps) (Lizenz unklar, nur UX) | Vorschau einer neuen Tür, Undo/Redo | B.2 |
| 3D (`web/`) | [react-three-fiber](https://github.com/pmndrs/react-three-fiber) + drei (MIT); UX von [xeokit-bim-viewer](https://github.com/xeokit/xeokit-bim-viewer) (AGPL-3.0, nur Ideen) | Etagen aus den Polygonen extrudiert, auseinandergezogen, nicht aktive Etagen halbtransparent | B.1 |
| Voice-UI | [ElevenLabs UI](https://github.com/elevenlabs/ui) (MIT; Orb, Conversation Bar) | Fertige React-Komponenten, wenn sie im Vite-Gerüst schnell laufen | A, B.2 |
| Logistik | [Open-RMF](https://github.com/open-rmf/rmf_traffic) (Apache-2.0, nur Konzept) | Wegenetz, Fahrzeugprofil und Belegung getrennt | Danach |
| JSON-Validator | [Open-Location-Stack/floorplan-editor](https://github.com/Open-Location-Stack/floorplan-editor) | Idee: gültige Polygone, Türen auf gemeinsamen Wänden, alles erreichbar | 1 |

**Herkunftsliste `THIRD_PARTY.md`:** Für jede Übernahme notieren wir Projekt, Commit, übernommene Dateien, Lizenz und nötige Hinweise. Unabhängig davon gelten die **Datenlizenzen** aus `ATTRIBUTION.md`: ODbL für OSM, CC BY 4.0 für Swiss Dwellings und ResPlan, CC0 für die prozeduralen Gebäude.

**Nicht geplant**, nur als Ausblick für den Pitch: Planerkennung mit ML (CubiCasa5k, DeepFloorplan), BIM-Import (IfcOpenShell), Kamera-Lokalisierung ohne Referenzbilder (F3Loc, PALMS), WebXR-AR-Pfeile und SLAM. AR per Kamera mit hloc und MegaLoc ist dagegen als späteres Add-on geplant ([`product.md`](product.md) §3).
