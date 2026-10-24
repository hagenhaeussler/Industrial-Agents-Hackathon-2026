# Plan – Talk to Your Building (Track 01)

**Stand:** Sa 24.10.2026, 17:00 · **Code Freeze:** So 25.10., 13:00 → **ca. 21 reale Stunden.** In der Nacht endet die Sommerzeit (3:00 → 2:00), das bringt eine Stunde extra.
**Stack:** Web-Apps auf **Railway** (ein Node-Service), **alles in TypeScript** · vorberechnete SQLite-Datenbank aus `building.json` · Agent Harness mit dem Tool Runner des Anthropic SDK · ElevenLabs Agent mit Eleven v4 Turbo · Claude (600 USD Anthropic-Credits)
**Grundlage:**
- dieses Team-Repo: Meeting-Notizen, Q&A mit dem Challenge-Lead, Route-Scoring-Spec, Challenge-PDF
- das offizielle Synera-Kit (`../repo/`, Commit `cb51a6f`, aktuell) mit unserer lokalen Vorarbeit
- ein Review durch Codex (gpt-6.1-sol, medium), siehe Abschnitt 10

---

## 1. Was neu ist und den Plan ändert

| # | Fund | Quelle | Folge |
|---|---|---|---|
| 1 | **Für Routen gibt es ein zweites Distanzmodell.** Gemessen wird Tür zu Tür *innerhalb* der Räume, 15 cm Abstand zur Wand, um Ecken herum. Treppe = 2 m pro Höhenmeter, Lift = 15 m + 1 m pro Höhenmeter. Bewertet wird die **Raumfolge**. Score = beste Länge ÷ unsere Länge, innerhalb 1 % gibt volle Punkte, eine ungültige Route gibt 0. | `2026-10-24-route-scoring-specifications.md` | Für Routenfragen brauchen wir ein **geodätisches Modell** (Abschnitt 5). Das README-Modell bleibt für `errand` und `what_if_door` im Testset, weil die dev-Antworten damit übereinstimmen. |
| 2 | **Neue Routing-Regeln:** Ein Gabelstapler fährt nur durch Gänge und Öffnungen ab 3 m. Produktionsbereiche sind nur Ziel, kein Transit. Eine Route zu einem Gerät endet im Raum, der es enthält. Wenn es keine Route gibt, sagen wir das. | dieselbe Datei | Das kommt als Constraints in den Graphen. In den Fabrikdaten gibt es Hallen-Öffnungen mit 4–20 m. |
| 3 | **Das Sonntagsformat ist widersprüchlich.** Das PDF verlangt `answers.json` mit Route als Knotenliste und Länge. Die README verlangt CSV mit einer `Answer:`-Zeile. | PDF vs. README | Parser und Serializer müssen austauschbar sein. Wir schreiben beide Formate und decken alle 15 Fragearten ab, auch die Warm-up-Arten. |
| 4 | **Build heißt vor allem lokale Änderungen und What-if.** Eine Web-App reicht. Post-Training ist unerwünscht. Die Jury testet mit eigenen Keys (OpenAI oder Anthropic). Im Video zählt die Interaktion am meisten. | Q&A mit dem Lead | Event-Log-Änderungen sind Pflicht. Einen Bildimport gibt es nicht: Wir arbeiten nur mit JSON. Die Jury hat keinen bestätigten ElevenLabs-Zugang. Deshalb wird die Agent-Konfiguration exportiert, und der Benchmark läuft **lokal und ohne ElevenLabs und Railway**. |

## 2. Gesamter Tech-Stack

**Grundsätze (Stand Sa abends):**
- **Nur TypeScript.** Kein Python im Laufzeitcode. Einzige Ausnahme ist der spätere Ortungsdienst für AR (Abschnitt 8). Das Python-Kit (`starter_agent/`, `benchmark/`) bleibt unverändert im Repo und dient nur als Referenz.
- **Nur JSON.** Jedes Gebäude kommt als `building.json`. Es gibt keinen Bildimport (kein PNG, kein SVG, kein Foto). 2D- und 3D-Ansicht entstehen direkt aus den Daten.
- **Vorberechnete Datenbank.** Ein Import-Skript liest `building.json` und schreibt SQLite. Dabei berechnet es alle Werte, die der Agent sonst selbst rechnen müsste. Import und Änderungen nutzen denselben Schreibweg.
- **Agent Harness statt einzelner LLM-Aufrufe.** Das Modell führt eine Agent-Schleife aus und entscheidet selbst, welche Tools es wie oft aufruft. Gebäudedaten kommen nie in den Prompt, nur über Tools.
- **Nur Web-Apps, keine nativen Apps:** eine Mobile-Ansicht für unterwegs und eine Desktop-Ansicht für Admins (Abschnitt 8). QR-Codes dienen nur als Link vom Desktop zur Mobile-Ansicht, nicht zur Ortung.

| Schicht | Technik | Aufgabe |
|---|---|---|
| **Frontend** | React 19 + Vite + TypeScript, Tailwind CSS, Zustand (State). Die UI aus Lenards Prototyp übernehmen wir, wenn sie passt | Zwei Web-Apps: Mobile (Navigation) und Desktop (Admin) |
| 2D-Plan | Eigenes SVG aus den Polygonen (lokale Meter, keine Kartenprojektion) | Etagen, Räume, Türen, Assets, Route, Highlights, Vorschau von Änderungen |
| 3D-Ansicht | react-three-fiber + drei, Etagen direkt aus den Polygonen extrudiert | Gestapelte Etagen, animierte Route |
| Voice | `@elevenlabs/react` (`useConversation`), Client-Tools | Mikrofon, Barge-in, Tool-Aufrufe aus dem Agenten |
| **Datenbank** | SQLite über `node:sqlite`, lokal und auf dem Railway-Volume | Basisdaten plus vorberechnete Werte, siehe Abschnitt 5 |
| **Core** | TypeScript-Bibliothek `core/`: Geometrie, Graph, Routing, What-if, Änderungen | Deterministisch. Läuft lokal, im Benchmark und in der Cloud mit demselben Code |
| **Agent** | Tool Runner aus `@anthropic-ai/sdk` (`betaZodTool` + `client.beta.messages.toolRunner`) mit unseren Tools. Sonnet 5.5, Prompt-Caching | Textchat, Benchmark und optional Custom-LLM für ElevenLabs. Läuft im Node-Service auf Railway |
| Agent (Voice) | ElevenLabs Agent: `eleven_v4_turbo` + eingebautes `claude-sonnet-5-5` | Gespräch, Rückfragen, Tool-Auswahl |
| **Benchmark** | TypeScript-CLI, ein Befehl, nutzt denselben Agenten und dieselbe DB | Läuft lokal, schreibt CSV + `answers.json` |
| Tooling | pnpm, Vitest (Tests gegen train/dev), Railway CLI | |

**Repo-Struktur:**

```
core/        TypeScript: Schema, Import, Geometrie, Graph, Routing, Änderungen
agent/       TypeScript: Agent Harness, Tool-Definitionen, Prompt
bench/       TypeScript: Benchmark-CLI, Parser/Serializer CSV + JSON
web/         React-App
server/      Node-Server (Hono): API, WebSocket, Static Assets, Event-Log
data/        Kit-Daten (unverändert)
```

Tests liegen neben dem Code (`*.test.ts`) und laufen gegen die Antworten in train und dev. Die Antworten aus `questions*.jsonl` kommen nie in die Datenbank.

## 3. Deployment auf Railway

```
Browser ──HTTPS/WSS──► Railway-Service "app" (Node, TypeScript)
                        ├─ /            Static Assets (Vite-Build von web/)
                        ├─ /api/eleven/token   ELEVENLABS_API_KEY → signierte Conversation-URL
                        ├─ /api/tools/*, /api/chat   → Agent Harness + core/ auf der Gebäude-DB
                        └─ /ws/:building       WebSocket: building_changed an alle Clients
                               └─ Volume /state: SQLite (Gebäude-DB + Event-Log)

Später, nur für AR:  Railway-Service "localizer" (Python, hloc) ← Kamerabilder vom Handy
```

- **Ein Node-Service** liefert App, API und WebSocket aus. Server-Framework: Hono auf Node. Core, Agent Harness und DB laufen im selben Prozess.
- **Datenbank:** SQLite über `node:sqlite` auf einem Railway-Volume unter `/state`, nicht unter `/app/data`. Basisdaten plus Event-Log (Version, Undo). `commit_edit` nur mit `proposal_id`, idempotent. Die Kit-Gebäude importieren wir beim Start, nicht beim Build.
- **Grenzen von Railway:** Mit Volume sind keine Replicas möglich, und ein Redeploy hat kurze Downtime. Deshalb kein Deploy während Aufnahme oder Demo. Der Client verbindet den WebSocket automatisch neu und lädt danach den aktuellen Stand. App-Sleeping ausschalten.
- **Secrets als Railway-Variablen:** `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID`. Keys stehen nie im Repo und nie im Browser.
- **Agent Harness im Node-Service.** Wir nutzen den Tool Runner des Anthropic SDK, nicht das Claude Agent SDK: Das Agent SDK bringt Datei- und Shell-Tools mit, die wir nicht brauchen.
- **Python nur im eigenen Service `localizer`** für hloc und MegaLoc (Abschnitt 8). Alles andere ist TypeScript.
- **Handy-Tests brauchen HTTPS**, weil Kamera und Mikrofon nur im Secure Context laufen. Die Railway-URL erfüllt das.
- **Für die Jury:** Die öffentliche URL plus `README` mit lokalem Start (`pnpm i`, `.env.example`). Der Benchmark läuft ohne Railway, mit einem einzigen Befehl.
- **Sonntagsgebäude:** `bench` importiert den Ordner in die DB und beantwortet die Fragen. Für die Demo laden wir dasselbe JSON in die App.

## 4. Voice-Architektur

```
Browser (React)
  ├─ GET /api/eleven/token → signierte URL
  ├─ useConversation ── Audio ⇄ ── ElevenLabs Agent
  │                                · STT, Turn-Taking, Barge-in
  │                                · LLM: Claude Sonnet 5.5
  │                                · TTS: eleven_v4_turbo (~100 ms), DE/EN
  │    clientTools: find, route, what_if, propose_edit, commit_edit, show
  │      └─ fetch /api/tools/<name> → Node-Service (core/ + DB) → Ergebnis an den Agenten + sofort auf die Karte
  └─ WSS /ws/:building ⇄ Node-Service  (building_changed an alle Clients)
```

**Warum Client-Tools, die ans Backend weiterleiten:** ElevenLabs ruft das Tool im Browser auf. Der Browser fragt unser Backend, zeigt das Ergebnis **sofort** auf der Karte und gibt dem Agenten ein kompaktes JSON zurück (`expects_response`). Ein zweiter LLM-Aufruf zum Zeichnen ist nicht nötig, und das gleiche Setup funktioniert lokal wie in der Cloud.

Da die App eine öffentliche Railway-URL hat, wären auch Server-Tools (Webhooks) ohne Tunnel möglich. Wir bleiben trotzdem bei Client-Tools, weil sie die Karte direkt aktualisieren.

Die Zustandshoheit liegt beim Server: Gebäudeversion pro Gebäude, `commit_edit` nur mit `proposal_id` und idempotent. Wird die Sprache unterbrochen, darf kein Commit doppelt passieren.

**Welches LLM im Agenten?** Darüber entscheiden wir **um 17:15**, abhängig davon, wie die Kosten abgerechnet werden:
- **Phase 1 (heute, schnell):** das in ElevenLabs eingebaute `claude-sonnet-5-5`, mit niedrigem Reasoning-Aufwand. Das wird über **ElevenLabs-Credits** abgerechnet, nicht über unsere Anthropic-Credits.
- **Phase 2 (nur bei Bedarf):** ein **Custom-LLM-Endpoint** `/api/llm/v1/chat/completions` (OpenAI-kompatibel, SSE) beim Agent Harness, der Claude über unsere 600 USD aufruft. Pro Turn darf nur **eine** Seite Tools ausführen.

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

## 5. Core: Datenbank und zwei Kostenmodelle

**Vorberechnete Datenbank (SQLite):**
- **Basistabellen** wie in `building.json`: `buildings`, `floors`, `spaces`, `openings`, `connectors`, `connector_stops`, `assets`.
- **Vorberechnet** beim Import: Fläche, Mittelpunkt und Ankerpunkt pro Raum; gemeinsame Wandlänge zwischen Räumen (`space_adjacency`, Regel 0,35 m / 1 m); Raum darüber und darunter (`space_stacking`); Weg zum nächsten Eingang. Kürzeste Wege zwischen allen Räumen (normal und stufenlos) nur, wenn die Tabelle klein genug bleibt.
- **Ein Schreibweg:** Import und Änderungen (Tür, Sperrung, Raum) laufen durch denselben Code. Bei einer Änderung rechnet er nur die betroffenen Werte neu.
- Der Agent liest die DB nur. Routen mit Bedingungen (Türbreite, Sperrung, neue Tür) berechnen Tools zur Laufzeit.
- **Geometrie ohne shapely:** Ankerpunkt (`representative_point`) nachgebaut, Flächen und Mittelpunkte mit Standardformeln, Überlappungen mit einem reinen JS-Paket. Geprüft mit Vitest gegen die Routenlängen der Warm-up-Fragen in train und dev.

- **`readme`:** exakt wie `building_map.py` (Ankerpunkt, 12 m pro Etage, 15 + 6 m). Gilt für errand, what_if und die Warm-up-Routen. Wird gegen die dev-Antworten geprüft.
- **`geodesic`:** nach der Spec von Synera. Das Modell wird **im Code nach Fragetyp gewählt**, nicht vom LLM, und im Ergebnis protokolliert.
  - **Portalgraph statt Raumknoten:** Knoten sind die Türen, Kanten sind Wege innerhalb eines Raums von Tür zu Tür. Die Kosten für das Durchqueren eines Raums hängen von Eingangs- und Ausgangstür ab. Aus dem Graphen wird am Ende die Raumfolge exportiert.
  - Der Raum wird um 0,15 m nach innen verkleinert, dann wird ein Sichtbarkeitsgraph gebaut. Schmale Bereiche, die dabei zerfallen, Türen außerhalb des verkleinerten Polygons und ungültige Polygone behandeln wir ausdrücklich: Türpunkt auf den Rand projizieren. Zerfallene Teilflächen verbinden wir **nicht pauschal**, weil das verbotene Abkürzungen erzeugen kann. Erlaubt sind nur geometrisch gültige Übergänge. Wie Start und Ziel in der neuen Distanzregel zählen, ist noch offen (Frage an Synera).
  - Den kostenlosen `outside`-Knoten übernehmen wir nicht ungeprüft. Die Lift-Wartepauschale fällt nur einmal pro Fahrt an.
  - **Tests:** Handprüfbare L- und U-Räume, keine Strecke durch Wände, Konnektivität. Der Vergleich „geodätisch ≥ README“ ist **kein** gültiger Test, weil auch der README-Anker Umwege erzeugt.
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
| `starter_agent/building_map.py` | MultiGraph nach README, Dijkstra, Sperrungen, `add_door` | Python-Referenz für unseren TypeScript-Core. Warm-up-Oracle 369/369 |
| Lenards UI-Prototyp "Building Guide" (`building-guide` im Codex-Workspace) | Mobile-Ansicht mit Vollbildkamera, Route, Minimap, Chat und Blobatar-Avatar. React 19, Vite, Bun | Vorlage für B.2 Mobile. Nutzt Bun statt pnpm |
| `../repo/ARCHITECTURE.md`, `VIDEO_TAKEAWAYS.md`, `SYNERA.md`, `RESEARCH*.md` | Tool-Schnitt, Prompt-Regeln, ElevenLabs-Wege, Synera-Pitch-Sprache | Referenz. Server-Struktur und Voice-Weg „A“ sind durch Abschnitt 2–4 ersetzt |
| Dieses Repo | Notizen, PDFs, Skizze, dieser Plan | `.env` wird nicht mehr verfolgt, `.gitignore` ist gefüllt (Commit `62074c2`). `agent.py` ist leer |

Testset (145 Fragen): floor_area_total 33 · shared_walls 26 · largest_room 21 · errand 20 · wide_delivery 18 · straight_line_3d 15 · room_stacked 9 · what_if_door 3.

## 8. Implementierungsreihenfolge

**Reihenfolge:** 1 Datenbank → 2 Agent → danach parallel **A** Voice und **B** Oberfläche (B.1 Visualisierung, B.2 UI/UX mit Mobile und Desktop).

| Phase | Inhalt | Fertig, wenn |
|---|---|---|
| **1 Datenbank** | Setup: pnpm, TypeScript, Vitest, `AGENTS.md`, `.env.example`. **Vorberechnete Felder** für die Fragen (Abschnitt 5). **Import-Feature:** `building.json` → Validator → DB, derselbe Weg für Kit-Gebäude, Sonntagsgebäude und Upload in der App. Core-Graph: Constraints, Erreichbarkeit, Routen, What-if | Warm-up-Routen auf den Zentimeter, Geometrie-Arten ≈ 100 % auf dev und train, alle 280 Gebäude importierbar |
| **2 Agent** | Harness wählen und aufsetzen (Tool Runner). API zum LLM. **DB-Tools zum Lesen und Schreiben**, Schreiben nur über den einen Schreibweg mit Vorschau und Bestätigung. Skills und Prompts pro Fragetyp. Benchmark-CLI und `BENCHMARK.md`. API im Node-Service | **M1:** vollständige Test-CSV mit 145 Zeilen und dev-Score pro Fragetyp, end to end auf den dev-Fragetexten |
| **A Voice** | Realtime-Voice-Layer mit ElevenLabs für Mobile und Desktop. Token-Endpunkt, Client-Tools auf dieselbe Tool-API wie der Agent | Eine gesprochene Frage zeigt eine Route, auf Mobile und Desktop |
| **B.1 Visualisierung** | 2D (SVG) und 3D (extrudiert), **deterministisch aus der DB**: Etagen, Räume, Türen, Assets, Route, Highlights, Vorschau von Änderungen | Gleiche Daten ergeben immer dasselbe Bild. Alle Etagen eines dev-Gebäudes korrekt |
| **B.2 UI/UX** | Zwei Web-Apps, siehe unten | **M2:** Demo-Abläufe aus Abschnitt 12 laufen auf der öffentlichen URL |
| Danach | Geodäsie und Fahrzeuge (Abschnitt 5): Portalgraph, Gabelstapler, kein Transit durch Produktion | Tests aus Abschnitt 5 sind grün |

### UI/UX: zwei Web-Apps, keine nativen Apps

**Mobile (unterwegs):**
- Ziel: schnell herausfinden, wohin ich gehen muss, und dorthin kommen. Fokus auf dem Voice-Agenten.
- Vor dem Start wähle ich die Art der Führung: **Karte**, **Wegbeschreibung** oder **AR** (Kamerabild mit Weganweisungen).
- Start auch über einen QR-Code aus der Desktop-Ansicht. Der Link öffnet die Mobile-Ansicht mit dem Objekt als Ziel.
- **AR nur per Kamera, als späteres Zusatzfeature** nach den Phasen 1, 2, A und B. Keine Tiefen- oder Abstandssensoren. Ablauf aus Lenards Codex-Test:
  - Einmalig: Video des Gebäudes aufnehmen, Referenzbilder auswählen, pro Bild einen MegaLoc-Suchvektor und SuperPoint-Merkmale speichern.
  - Live: Das Handy schickt 1–2 klare Bilder pro Sekunde an den Server. [hloc](https://github.com/cvg/Hierarchical-Localization) sucht mit MegaLoc die ähnlichsten Referenzbilder, LightGlue gleicht nur diese ab, eine geometrische Prüfung verwirft unsichere Treffer. "Keine sichere Position" ist ein gültiges Ergebnis.
  - Die Position geht direkt an Routenplanung und Anzeige. Der Voice-Agent bekommt Raum- und Etagenwechsel als Kontext-Update. Laut ElevenLabs unterbricht ein solches Update keine laufende Antwort.
  - **Stand:** Offline auf dem Mac getestet. Ein Foto fand das passende Videobild mit 180 geprüften Punkten, 1,2 s Rechenzeit auf der CPU. Es fehlt noch die Zuordnung der Referenzbilder zu Koordinaten im Grundriss.
  - Grenzen: Eine Web-App hat ohne WebXR keine Bewegungsverfolgung zwischen zwei Ortungen. iPhone Safari unterstützt kein WebXR `immersive-ar`.
  - **Eigener Dienst in Python**, getrennt vom TypeScript-Stack, weil hloc ein Python-Projekt ist. Code: `floor-localizer` im Codex-Workspace.

**Desktop (Admin):**
- Elemente und Objekte verschieben, zum Beispiel eine Maschine in einen anderen Raum. Das läuft über den Schreibweg der DB.
- Voice- und Chat-Layer.
- **Multi-User nur als Mock:** Andere Nutzer, Anwesenheit und Aktivitäten sehen echt aus, sind aber nicht implementiert. Die App soll wie ein vollständiges Produkt wirken.
- Klick auf ein Objekt, zum Beispiel eine Maschine, zeigt einen **QR-Code**. Mit dem Handy gescannt, startet er die Mobile-Ansicht mit Navigation zu diesem Objekt.

## 9. Zeitplan

| Zeit | A: Core/Bench | B: Frontend + Railway | C: Voice/Agent/Demo |
|---|---|---|---|
| **Sa 17:15–17:45** | Phase 1 Setup, Tool-Vertrag einfrieren (Namen, Parameter, Ergebnisformat), Referenzgebäude und erwartete Route für das Gate festlegen | Railway-Setup, Vite/React-Gerüst | Abrechnung klären (ElevenLabs-Credits?), Agent anlegen, Discord-Fragen stellen |
| **17:45–18:30** | Phase 1 Datenbank | Node-Service öffentlich auf Railway, Secret-Test. Dann B.1 minimale 2D-Karte | A: `/tools/route`, `useConversation`. C hält den Vertrag für Tools und Voice, B die Infrastruktur |
| **18:30** | **Integrationsgate (alle):** Voice → Tool → Karte, lokal, auf dem Referenzgebäude | | |
| **18:30–21:00** | Phase 2 Agent → **M1** (145 Zeilen + dev-Score pro Typ) | Deploy, **20:00 Abnahme**, dann B.1 Visualisierung | Alle Client-Tools, Voice-Prompt-Regeln, Textchat |
| **21:00–00:30** | Geodäsie + Constraints | B.2 Mobile und Desktop, Änderungen mit Vorschau, Bestätigung und Undo | Voice auf Mobile und Desktop, Rückfrage-Logik → **M2** |
| **00:30 Gate** | Bestätigte Änderung, QR-Code vom Desktop öffnet die Mobile-Ansicht, Undo, Wiederherstellung nach Neustart des Service (Volume). **Danach keine neue Infrastruktur** | | |
| **00:30–03:00** | Regression auf dev, Checkpointing | Handy-Test auf der öffentlichen URL (HTTPS), AR mit Timebox | Rohschnitt fürs Video |
| 03:00–07:00 | **Schlafen** (dank Zeitumstellung eine Stunde mehr) | | |
| **So 07:00–09:00** | Ein dev-Gebäude wie ein unbekanntes durchlaufen lassen, finale Test-CSV, Installationsprobe auf frischem Klon | 3D **erst nach** bestandenem Frischklon- und Benchmark-Lauf → **M3** | Härtetest mit schwierigen Nutzern |
| **ab 09:00 bis zur Abgabe** | **Bereitschaft für das Sonntagsgebäude:** eine Person lässt `bench` laufen, sobald es erscheint, und lädt es in die App | Bugfixes | Video aufnehmen |
| **10:00 Feature Freeze** | BENCHMARK.md, README, exportierte Agent-Konfiguration. **Ausnahme:** Anpassungen an Sonntagsformat und Datenadapter bleiben erlaubt | Letztes Deploy, URL in die Abgabe | Video schneiden, technische Erklärung (Architektur statt Code) |
| **12:00–13:00** | Nur Abschlusslauf, Upload, Abgabe prüfen | | |

**Streichreihenfolge:** 3D → zusätzliche Logistikfunktionen. **Voice bleibt Pflicht**, M1 wird nie gefährdet.

## 10. Offene Fragen an Synera (heute per Discord)

1. Gilt für die `errand`-Distanzen im **Testset** noch das README-Modell oder schon das geodätische?
2. Sonntagsformat: **`answers.json` (PDF) oder CSV (README)**? Sind die Knoten-IDs `space_id`s? Wie wird „unerreichbar“ dargestellt? Wann wird veröffentlicht, wie lange haben wir?
3. Woran erkennt man **Gabelstapler-Gänge und Fußwege** in den Daten? Welche Raumtypen sind „Produktionsbereich“?
4. Kommen am Sonntag auch locate-, route- und tour-Fragen?
5. Kann die Jury eine ElevenLabs-Agent-Konfiguration nutzen, oder reicht die öffentliche URL plus Video und Textchat?
6. Wie zählt das geodätische Modell Start und Ziel: ab dem Raummittelpunkt, ab der ersten Tür oder anders?

## 11. Codex-Review: übernommen und abweichend

Übernommen:
- Abrechnung als Entscheidungspunkt am Anfang
- Portalgraph statt Raumknoten, mit den Randfällen beim Verkleinern der Polygone
- „geodätisch ≥ README“ ist kein Test
- Modellwahl im Code, nicht im LLM
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

3D und Custom-LLM-Endpoint bleiben verbindlich Kür. Container, Python-Core, Bildimport und native Apps sind gestrichen (Abschnitt 2).

## 12. Demo-Story (Video, 25 Interaktionspunkte)

Fabrikhalle, drei Nutzer auf zwei Geräten, eine Karte, alles per Stimme:
1. **Techniker** am Handy (Mobile-Ansicht, gestartet über den QR-Code an der Maschine im Desktop): „Welche Presse ist Linie 4, wie komme ich hin?“ Der Agent antwortet mit Landmarken, die Route ist animiert, die nächsten Schritte kommen auf „weiter“.
2. **Facility Manager** am Laptop: „Der Ostlift ist in Wartung.“ Der Agent zeigt eine Vorschau mit den betroffenen Routen und wartet auf ein „Ja“. Danach aktualisiert sich die Karte **sofort auch auf dem Handy des Technikers**.
3. **Gabelstaplerfahrer:** „Gang 4 ist blockiert, schnellster Weg zu Dock B?“ Die Route nutzt nur Öffnungen ab 3 m und fährt nicht durch die Produktion.
4. Aufklappbare Ansicht „So habe ich das berechnet“ mit dem Tool-Trace. Das ist Syneras Linie: *„Das LLM interpretiert, die Regeln entscheiden.“*
5. Am Ende kurz der Benchmark-Score und die Kosten pro Frage als Beleg für Effizienz.

## 13. Wiederverwendung aus unserer Recherche

Quelle: `../repo/RESEARCH.md`, `RESEARCH_FOUNDATION.md`, `VIDEO_TAKEAWAYS.md`. Die Grundregel: Wir übernehmen **Code nur bei MIT- oder Apache-Lizenz**. Aus GPL-Projekten übernehmen wir nur Ideen. Keines der Projekte ersetzt unseren Core, denn die Distanzen müssen exakt Syneras Modellen folgen.

| Wo im Stack | Projekt | Was wir übernehmen | Phase |
|---|---|---|---|
| Suche (`core/model.py`) | [NavigaTUM](https://github.com/TUM-Dev/NavigaTUM) (GPL-3.0, nur Ideen) | Raumnummern normalisieren (führende Nullen), Lexer-Trick `MW1801` → „mw 1801 mw1801“, Synonymliste DE/EN (Hörsaal/HS, WC/Toilette), Such-Regressionstests als YAML | 1, B.2 |
| Routing (`core/graph.py`) | [c3nav](https://github.com/c3nav/c3nav) (Apache-2.0) | Kartendaten und abgeleiteter Router getrennt, Einschränkungen als Daten. Das ist das Muster für unsere `Constraints` | 1, Geodäsie |
| Wegbeschreibung | Papers [Grid2Guide](https://arxiv.org/abs/2508.08100), [Floorplan2Guide](https://arxiv.org/abs/2512.12177), [LLM-Guided Indoor Nav](https://arxiv.org/abs/2503.11702v4) | Graph rechnet, LLM formuliert. Anweisungen mit Landmarken statt Raumnummern | B.2 |
| 2D-Plan (`web/`) | [KnotzerIO/indoor-wayfinder](https://github.com/KnotzerIO/indoor-wayfinder) (React + SVG, MIT laut Codex) | Vorlage für SVG-Karte und Zoom. Wichtig: eine gemeinsame Koordinatentransformation mit umgedrehter Y-Achse, und den Routenpfad liefert das Backend als Geometrie | B.1 |
| 2D-Etagen-UX | NavigaTUM `IndoorMap.vue`, `FloorControl.ts` (nur Ideen) | Route pro Etage schneiden, aktive Etage solid, andere als „Geister“, Etagenwahl mit `level-changed`-Event | B.2 |
| Änderungen (Vorschau, Undo) | [indoorMaps](https://github.com/hadencain/indoorMaps) (Lizenz unklar, nur UX) | Vorschau einer neuen Tür, Undo/Redo, Route zum nächsten Ausgang | B.2 |
| 3D (`web/`) | [react-three-fiber](https://github.com/pmndrs/react-three-fiber) + drei (MIT); UX von [xeokit-bim-viewer](https://github.com/xeokit/xeokit-bim-viewer) (**AGPL-3.0, nur UX-Ideen**) und Mappedin Stacked Maps | Etagen aus den Polygonen extrudiert. Auseinandergezogene Etagen, nicht aktive Etagen halbtransparent | B.1 |
| Voice-UI | [ElevenLabs UI](https://github.com/elevenlabs/ui) (MIT; Orb, Conversation Bar) | Fertige React-Komponenten statt eigener Voice-UI, aber nur, wenn sie im Vite-Gerüst schnell laufen | A, B.2 |
| Logistik (Level 5) | [Open-RMF](https://github.com/open-rmf/rmf_traffic) (Apache-2.0, nur Konzept) | Wegenetz, Fahrzeugprofil und Belegung getrennt. Für den Pitch als nächster Schritt | Danach |
| JSON-Validator | [Open-Location-Stack/floorplan-editor](https://github.com/Open-Location-Stack/floorplan-editor) (IMDF-Validator) | Idee für unseren Validator: gültige Polygone, Türen auf gemeinsamen Wänden, alles erreichbar | 1 |

**Reihenfolge beim Wiederverwenden:** zuerst der eigene funktionierende Kit-Code, dann offizielle SDK-Beispiele, dann kleine UI-Komponenten. Andere Indoor-Systeme dienen heute nur als Referenz, denn ihre Datenmodelle zu integrieren kostet mehr Zeit, als es bringt. Weitere Recherche ist nicht nötig.

**Herkunftsliste `THIRD_PARTY.md`:** Für jede Übernahme notieren wir Projekt, Commit, übernommene Dateien, Lizenz und nötige Hinweise. Aus GPL-Projekten werden keine Synonymlisten oder Test-Fixtures mitkopiert. Unabhängig davon gelten die **Datenlizenzen** aus `ATTRIBUTION.md`: ODbL für OSM, CC BY 4.0 für Swiss Dwellings und ResPlan, CC0 für die prozeduralen Gebäude.

**Bewusst nicht im Wochenend-Stack**, aber als Ausblick für den Pitch geeignet:
- Planerkennung mit ML: [CubiCasa5k](https://github.com/CubiCasa/CubiCasa5k), DeepFloorplan
- BIM-Import mit [IfcOpenShell](https://github.com/IfcOpenShell/IfcOpenShell)
- Kamera-Lokalisierung im Grundriss: [F3Loc](https://github.com/felix-ch/f3loc), PALMS
- VPS mit [hloc](https://github.com/cvg/Hierarchical-Localization), SLAM
- WebXR-AR-Pfeile
