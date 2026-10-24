# Plan – Talk to Your Building (Track 01)

**Stand:** Sa 24.10.2026, 17:00 · **Code Freeze:** So 25.10., 13:00 → **ca. 21 reale Stunden.** In der Nacht endet die Sommerzeit (3:00 → 2:00), das bringt eine Stunde extra.
**Stack:** React-Web-App auf **Cloudflare** (Worker + Durable Object), **alles in TypeScript** · vorberechnete SQLite-Datenbank aus `building.json` · Agent Harness mit dem Tool Runner des Anthropic SDK · ElevenLabs Agent mit Eleven v4 Turbo · Claude (600 USD Anthropic-Credits)
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
| 4 | **Build heißt vor allem lokale Änderungen und What-if.** Eine Web-App reicht. Post-Training ist unerwünscht. Die Jury testet mit eigenen Keys (OpenAI oder Anthropic). Im Video zählt die Interaktion am meisten. | Q&A mit dem Lead | Event-Log-Änderungen sind Pflicht. Einen Bildimport gibt es nicht: Wir arbeiten nur mit JSON. Die Jury hat keinen bestätigten ElevenLabs-Zugang. Deshalb wird die Agent-Konfiguration exportiert, und der Benchmark läuft **lokal und ohne ElevenLabs und Cloudflare**. |

## 2. Gesamter Tech-Stack

**Grundsätze (Stand Sa abends):**
- **Nur TypeScript.** Kein Python im Laufzeitcode. Das Python-Kit (`starter_agent/`, `benchmark/`) bleibt unverändert im Repo und dient nur als Referenz.
- **Nur JSON.** Jedes Gebäude kommt als `building.json`. Es gibt keinen Bildimport (kein PNG, kein SVG, kein Foto). 2D- und 3D-Ansicht entstehen direkt aus den Daten.
- **Vorberechnete Datenbank.** Ein Import-Skript liest `building.json` und schreibt SQLite. Dabei berechnet es alle Werte, die der Agent sonst selbst rechnen müsste. Import und Änderungen nutzen denselben Schreibweg.
- **Agent Harness statt einzelner LLM-Aufrufe.** Das Modell führt eine Agent-Schleife aus und entscheidet selbst, welche Tools es wie oft aufruft. Gebäudedaten kommen nie in den Prompt, nur über Tools.
- **Web-App im Browser.** Keine Mobile-App, kein QR-Code, keine Kamera, kein AR.

| Schicht | Technik | Aufgabe |
|---|---|---|
| **Frontend** | React 19 + Vite + TypeScript, Tailwind CSS, Zustand (State). Die UI aus Lenards Prototyp übernehmen wir, wenn sie passt | Navigation und Verwaltung in einer Web-App |
| 2D-Plan | Eigenes SVG aus den Polygonen (lokale Meter, keine Kartenprojektion) | Etagen, Räume, Türen, Assets, Route, Highlights, Vorschau von Änderungen |
| 3D-Ansicht | react-three-fiber + drei, Etagen direkt aus den Polygonen extrudiert | Gestapelte Etagen, animierte Route |
| Voice | `@elevenlabs/react` (`useConversation`), Client-Tools | Mikrofon, Barge-in, Tool-Aufrufe aus dem Agenten |
| **Datenbank** | SQLite (`node:sqlite` lokal; in der Cloud SQLite im Durable Object oder D1, offen) | Basisdaten plus vorberechnete Werte, siehe Abschnitt 5 |
| **Core** | TypeScript-Bibliothek `core/`: Geometrie, Graph, Routing, What-if, Änderungen | Deterministisch. Läuft lokal, im Benchmark und in der Cloud mit demselben Code |
| **Agent** | Tool Runner aus `@anthropic-ai/sdk` (`betaZodTool` + `client.beta.messages.toolRunner`) mit unseren Tools. Sonnet 5.5, Prompt-Caching | Textchat, Benchmark und optional Custom-LLM für ElevenLabs. Läuft im Worker oder in einem eigenen Agent-Worker |
| Agent (Voice) | ElevenLabs Agent: `eleven_v4_turbo` + eingebautes `claude-sonnet-5-5` | Gespräch, Rückfragen, Tool-Auswahl |
| **Benchmark** | TypeScript-CLI, ein Befehl, nutzt denselben Agenten und dieselbe DB | Läuft lokal, schreibt CSV + `answers.json` |
| Tooling | pnpm, Vitest (Tests gegen train/dev), wrangler | |

**Repo-Struktur:**

```
core/        TypeScript: Schema, Import, Geometrie, Graph, Routing, Änderungen
agent/       TypeScript: Agent Harness, Tool-Definitionen, Prompt
bench/       TypeScript: Benchmark-CLI, Parser/Serializer CSV + JSON
web/         React-App
worker/      wrangler.jsonc, Worker (Hono), Durable Object BuildingRoom
data/        Kit-Daten (unverändert)
```

Tests liegen neben dem Code (`*.test.ts`) und laufen gegen die Antworten in train und dev. Die Antworten aus `questions*.jsonl` kommen nie in die Datenbank.

## 3. Deployment auf Cloudflare

```
Browser ──HTTPS/WSS──► Worker  (app.<domain> oder *.workers.dev)
                        ├─ /            Static Assets (Vite-Build von web/)
                        ├─ /api/eleven/token   ELEVENLABS_API_KEY → signierte Conversation-URL
                        ├─ /api/ws/:building   → Durable Object BuildingRoom (WebSocket, Event-Log)
                        └─ /api/tools/*        → BuildingRoom → core/ auf der Gebäude-DB
```

- **Kein Container.** Der Core ist TypeScript und läuft direkt im Worker. Docker, Kaltstart des Containers, Secrets über `envVars` und die Tunnel-Notlösung fallen weg.
- **Durable Object `BuildingRoom`, eins pro Gebäude:** Es hält die Gebäude-DB, das Event-Log (Version, Undo) und verteilt `building_changed` an alle Clients. `commit_edit` nur mit `proposal_id`, idempotent. WebSocket-Hibernation ist eigener Code: `ctx.acceptWebSocket`, passende Handler, Zustand nach dem Aufwachen aus dem Storage.
- **Konfiguration (`worker/wrangler.jsonc`):** `assets` zeigt auf `web/dist`, SPA-Fallback und `run_worker_first: ["/api/*"]`.
- **Secrets:** `wrangler secret put`. Keys stehen nie im Repo und nie im Browser.
- **Agent Harness im Worker** oder in einem eigenen Agent-Worker. Wir nutzen den Tool Runner des Anthropic SDK, nicht das Claude Agent SDK: Das Agent SDK braucht eine Prozessumgebung und bringt Datei- und Shell-Tools mit, die wir nicht brauchen. Ob der Tool Runner im Worker läuft, prüfen wir beim ersten Deploy.
- **Für die Jury:** Die öffentliche URL plus `README` mit lokalem Start (`pnpm i`, `.env.example`). Der Benchmark läuft ohne Cloudflare, mit einem einzigen Befehl.
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
  │      └─ fetch /api/tools/<name> → Worker → BuildingRoom (core/ + DB) → Ergebnis an den Agenten + sofort auf die Karte
  └─ WSS /api/ws/:building ⇄ Durable Object  (building_changed an alle Clients)
```

**Warum Client-Tools, die ans Backend weiterleiten:** ElevenLabs ruft das Tool im Browser auf. Der Browser fragt unser Backend, zeigt das Ergebnis **sofort** auf der Karte und gibt dem Agenten ein kompaktes JSON zurück (`expects_response`). Ein zweiter LLM-Aufruf zum Zeichnen ist nicht nötig, und das gleiche Setup funktioniert lokal wie in der Cloud.

Da die App jetzt eine öffentliche Cloudflare-URL hat, wären auch Server-Tools (Webhooks) ohne Tunnel möglich. Wir bleiben trotzdem bei Client-Tools, weil sie die Karte direkt aktualisieren.

Die Zustandshoheit liegt beim Durable Object: Gebäudeversion pro Gebäude, `commit_edit` nur mit `proposal_id` und idempotent. Wird die Sprache unterbrochen, darf kein Commit doppelt passieren.

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

Der Puffer im Benchmark ist für den Fall gedacht, dass wir auf Sonnet wechseln müssen. Zusätzliche Kosten außerhalb der 600 USD: ElevenLabs-Credits (Agent-Minuten und eingebautes LLM) und der Cloudflare Workers-Paid-Plan.

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
| Lenards UI-Prototyp | Oberfläche | Übernehmen wir, wenn er passt |
| `../repo/ARCHITECTURE.md`, `VIDEO_TAKEAWAYS.md`, `SYNERA.md`, `RESEARCH*.md` | Tool-Schnitt, Prompt-Regeln, ElevenLabs-Wege, Synera-Pitch-Sprache | Referenz. Server-Struktur und Voice-Weg „A“ sind durch Abschnitt 2–4 ersetzt |
| Dieses Repo | Notizen, PDFs, Skizze, dieser Plan | `.env` wird nicht mehr verfolgt, `.gitignore` ist gefüllt (Commit `62074c2`). `agent.py` ist leer |

Testset (145 Fragen): floor_area_total 33 · shared_walls 26 · largest_room 21 · errand 20 · wide_delivery 18 · straight_line_3d 15 · room_stacked 9 · what_if_door 3.

## 8. Arbeitspakete

| Paket | Inhalt | Fertig, wenn |
|---|---|---|
| **P0 Setup** | Repo-Struktur aus Abschnitt 2 anlegen (pnpm, TypeScript, Vitest), `AGENTS.md`, `.env.example` mit `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID`. Ausgabenlimits setzen. ElevenLabs-Agent anlegen. Cloudflare: `wrangler login` | Kein Key im Repo, Agent-ID vorhanden, `wrangler whoami` funktioniert |
| **P1 DB + Geometrie** | Schema, Import, Ankerpunkt, area, centroid, shared_walls, stacked, distance_3d. Tests gegen die Warm-up-Routen und die dev-`inputs` | Warm-up-Routen auf den Zentimeter, 5 Arten ≈ 100 % auf dev und train |
| **P2 Core-Graph** | Constraints, reachable, errand, wide_delivery, step_free_count, what_if_door (Tür in der Wandmitte) | 4 Arten ≈ 100 % auf dev |
| **P3 Bench + erste Abgabe** | TypeScript-CLI mit dem Agent Harness: CSV + answers.json, Checkpointing, Kosten-Log. `BENCHMARK.md`. Getestet wird **end to end auf den dev-Fragetexten**, nicht nur der Core mit vorgegebenen `inputs`. | **M1:** vollständige Test-CSV mit 145 Zeilen und offizieller dev-Score pro Fragetyp, committed |
| **P4 Geodäsie + Fahrzeuge** | Portalgraph, Gabelstapler, kein Transit durch Produktion, unerreichbare Ziele melden | Tests aus Abschnitt 5 sind grün |
| **P5 Voice-Durchstich (lokal)** | Tool-Endpunkt `/tools/route`, Vite-Proxy, minimale 2D-Karte, `useConversation` mit einem Client-Tool `route` | **18:30 Integrationsgate:** Gesprochene Frage zeigt eine Route |
| **P6 Cloudflare-Deploy** | Worker (Hono) mit Assets, Token-Endpunkt, `BuildingRoom`-DO mit Gebäude-DB und WebSocket. Agent Harness im Worker | **20:00 Abnahme:** Die öffentliche URL zeigt dieselbe Route wie lokal |
| **P7 App** | Alle Client-Tools, Vorschau, Bestätigung und Undo über das DO, Broadcast an alle Clients, Textchat als Fallback | **M2:** drei Demo-Abläufe live auf der öffentlichen URL |
| **P8 Showcase** | 3D aus den Polygonen extrudiert, animierte Route. Level 5 Logistik: Gabelstapler, Gang gesperrt, Docks | **M3:** demo-fertig |

## 9. Zeitplan

| Zeit | A: Core/Bench | B: Frontend + Cloudflare | C: Voice/Agent/Demo |
|---|---|---|---|
| **Sa 17:15–17:45** | P0 Core-Teil, Tool-Vertrag einfrieren (Namen, Parameter, Ergebnisformat), Referenzgebäude und erwartete Route für das Gate festlegen | P0 Cloudflare-Teil, Vite/React-Gerüst | Abrechnung klären (ElevenLabs-Credits?), Agent anlegen, Discord-Fragen stellen |
| **17:45–18:30** | P1 | Worker-Gerüst öffentlich, Secret-Test. Dann minimale 2D-Karte | P5: `/tools/route`, `useConversation`. C hält den Vertrag für Tools und Voice, B die Infrastruktur |
| **18:30** | **Integrationsgate (alle):** Voice → Tool → Karte, lokal, auf dem Referenzgebäude | | |
| **18:30–21:00** | P2 → P3 → **M1** (145 Zeilen + dev-Score pro Typ) | P6 Deploy, **20:00 Abnahme** | Alle Client-Tools, Voice-Prompt-Regeln, Textchat |
| **21:00–00:30** | P4 Portalgraph + Constraints | DO-Event-Log: Vorschau, Bestätigung, Undo, Broadcast | Drei Demo-Abläufe, Rückfrage-Logik → **M2** |
| **00:30 Gate** | Bestätigte Änderung, zweites Gerät, Undo, Reconnect, Wiederherstellung nach Neustart des Durable Object. **Danach keine neue Infrastruktur** | | |
| **00:30–03:00** | Regression auf dev, Checkpointing | Test auf der öffentlichen URL mit zwei Browsern, Unterbrechungen | Rohschnitt fürs Video |
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
- Codex schlägt Server-Tools (Webhooks) vor. Wir nehmen **Client-Tools, die ans Backend weiterleiten**, weil die Karte sich so ohne Umweg aktualisiert. Die Zustandshoheit liegt trotzdem auf dem Server (Durable Object).
- Codex gibt für das Lesen aus dem Cache 0,05× an. Laut Anthropic-Preisliste liegt Sonnet 5.5 bei 0,20 USD pro MTok, also 0,1×.

**Zweites Review (Cloudflare, Stack, Repos)** mit dem Urteil „technisch stimmig, für drei Personen aber zu breit“. Übernommen:
- Assets-Routing mit `run_worker_first`
- Hibernation als eigener Code
- Härtere Kriterien für M1 und das 00:30-Gate
- Ausnahme vom Feature Freeze für den Sonntagsadapter
- Keine pauschale Verbindung zerfallener Polygone
- Lizenzen präzisiert, dazu eine Herkunftsliste (Abschnitt 13)

3D und Custom-LLM-Endpoint bleiben verbindlich Kür. Container, Python-Core, Bildimport, QR-Code und Mobile-App sind gestrichen (Abschnitt 2).

## 12. Demo-Story (Video, 25 Interaktionspunkte)

Fabrikhalle, drei Nutzer auf zwei Geräten, eine Karte, alles per Stimme:
1. **Techniker** im Browser: „Welche Presse ist Linie 4, wie komme ich hin?“ Der Agent antwortet mit Landmarken, die Route ist animiert, die nächsten Schritte kommen auf „weiter“.
2. **Facility Manager** am Laptop: „Der Ostlift ist in Wartung.“ Der Agent zeigt eine Vorschau mit den betroffenen Routen und wartet auf ein „Ja“. Danach aktualisiert sich die Karte **sofort auch im Browser des Technikers**.
3. **Gabelstaplerfahrer:** „Gang 4 ist blockiert, schnellster Weg zu Dock B?“ Die Route nutzt nur Öffnungen ab 3 m und fährt nicht durch die Produktion.
4. Aufklappbare Ansicht „So habe ich das berechnet“ mit dem Tool-Trace. Das ist Syneras Linie: *„Das LLM interpretiert, die Regeln entscheiden.“*
5. Am Ende kurz der Benchmark-Score und die Kosten pro Frage als Beleg für Effizienz.

## 13. Wiederverwendung aus unserer Recherche

Quelle: `../repo/RESEARCH.md`, `RESEARCH_FOUNDATION.md`, `VIDEO_TAKEAWAYS.md`. Die Grundregel: Wir übernehmen **Code nur bei MIT- oder Apache-Lizenz**. Aus GPL-Projekten übernehmen wir nur Ideen. Keines der Projekte ersetzt unseren Core, denn die Distanzen müssen exakt Syneras Modellen folgen.

| Wo im Stack | Projekt | Was wir übernehmen | Paket |
|---|---|---|---|
| Suche (`core/model.py`) | [NavigaTUM](https://github.com/TUM-Dev/NavigaTUM) (GPL-3.0, nur Ideen) | Raumnummern normalisieren (führende Nullen), Lexer-Trick `MW1801` → „mw 1801 mw1801“, Synonymliste DE/EN (Hörsaal/HS, WC/Toilette), Such-Regressionstests als YAML | P1/P7 |
| Routing (`core/graph.py`) | [c3nav](https://github.com/c3nav/c3nav) (Apache-2.0) | Kartendaten und abgeleiteter Router getrennt, Einschränkungen als Daten. Das ist das Muster für unsere `Constraints` | P2/P4 |
| Wegbeschreibung | Papers [Grid2Guide](https://arxiv.org/abs/2508.08100), [Floorplan2Guide](https://arxiv.org/abs/2512.12177), [LLM-Guided Indoor Nav](https://arxiv.org/abs/2503.11702v4) | Graph rechnet, LLM formuliert. Anweisungen mit Landmarken statt Raumnummern | P7 |
| 2D-Plan (`web/`) | [KnotzerIO/indoor-wayfinder](https://github.com/KnotzerIO/indoor-wayfinder) (React + SVG, MIT laut Codex) | Vorlage für SVG-Karte und Zoom. Wichtig: eine gemeinsame Koordinatentransformation mit umgedrehter Y-Achse, und den Routenpfad liefert das Backend als Geometrie | P5 |
| 2D-Etagen-UX | NavigaTUM `IndoorMap.vue`, `FloorControl.ts` (nur Ideen) | Route pro Etage schneiden, aktive Etage solid, andere als „Geister“, Etagenwahl mit `level-changed`-Event | P7 |
| Änderungen (Vorschau, Undo) | [indoorMaps](https://github.com/hadencain/indoorMaps) (Lizenz unklar, nur UX) | Vorschau einer neuen Tür, Undo/Redo, Route zum nächsten Ausgang | P7 |
| 3D (`web/`) | [react-three-fiber](https://github.com/pmndrs/react-three-fiber) + drei (MIT); UX von [xeokit-bim-viewer](https://github.com/xeokit/xeokit-bim-viewer) (**AGPL-3.0, nur UX-Ideen**) und Mappedin Stacked Maps | Etagen aus den Polygonen extrudiert. Auseinandergezogene Etagen, nicht aktive Etagen halbtransparent | P8 |
| Voice-UI | [ElevenLabs UI](https://github.com/elevenlabs/ui) (MIT; Orb, Conversation Bar) | Fertige React-Komponenten statt eigener Voice-UI, aber nur, wenn sie im Vite-Gerüst schnell laufen | P5/P7 |
| Logistik (Level 5) | [Open-RMF](https://github.com/open-rmf/rmf_traffic) (Apache-2.0, nur Konzept) | Wegenetz, Fahrzeugprofil und Belegung getrennt. Für den Pitch als nächster Schritt | P8 |
| JSON-Validator | [Open-Location-Stack/floorplan-editor](https://github.com/Open-Location-Stack/floorplan-editor) (IMDF-Validator) | Idee für unseren Validator: gültige Polygone, Türen auf gemeinsamen Wänden, alles erreichbar | P1 |

**Reihenfolge beim Wiederverwenden:** zuerst der eigene funktionierende Kit-Code, dann offizielle SDK-Beispiele, dann kleine UI-Komponenten. Andere Indoor-Systeme dienen heute nur als Referenz, denn ihre Datenmodelle zu integrieren kostet mehr Zeit, als es bringt. Weitere Recherche ist nicht nötig.

**Herkunftsliste `THIRD_PARTY.md`:** Für jede Übernahme notieren wir Projekt, Commit, übernommene Dateien, Lizenz und nötige Hinweise. Aus GPL-Projekten werden keine Synonymlisten oder Test-Fixtures mitkopiert. Unabhängig davon gelten die **Datenlizenzen** aus `ATTRIBUTION.md`: ODbL für OSM, CC BY 4.0 für Swiss Dwellings und ResPlan, CC0 für die prozeduralen Gebäude.

**Bewusst nicht im Wochenend-Stack**, aber als Ausblick für den Pitch geeignet:
- Planerkennung mit ML: [CubiCasa5k](https://github.com/CubiCasa/CubiCasa5k), DeepFloorplan
- BIM-Import mit [IfcOpenShell](https://github.com/IfcOpenShell/IfcOpenShell)
- Kamera-Lokalisierung im Grundriss: [F3Loc](https://github.com/felix-ch/f3loc), PALMS
- VPS mit [hloc](https://github.com/cvg/Hierarchical-Localization), SLAM
- WebXR-AR-Pfeile
