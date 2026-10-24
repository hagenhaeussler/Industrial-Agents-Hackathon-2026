# Plan – Talk to Your Building (Track 01)

**Stand:** Sa 24.10.2026, 17:00 · **Code Freeze:** So 25.10., 13:00 → **ca. 21 reale Stunden.** In der Nacht endet die Sommerzeit (3:00 → 2:00), das bringt eine Stunde extra.
**Stack:** React-Web-App auf **Cloudflare** (Worker + Durable Object + Container mit Python-Core) · ElevenLabs Agent mit Eleven v4 Turbo · Claude (600 USD Anthropic-Credits)
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
| 4 | **Build heißt vor allem lokale Änderungen und What-if.** Eine Web-App reicht. Post-Training ist unerwünscht. Die Jury testet mit eigenen Keys (OpenAI oder Anthropic). Im Video zählt die Interaktion am meisten. | Q&A mit dem Lead | Event-Log-Änderungen sind Pflicht, PNG-Import ist Kür. Die Jury hat keinen bestätigten ElevenLabs-Zugang. Deshalb wird die Agent-Konfiguration exportiert, und der Benchmark läuft **lokal und ohne ElevenLabs und Cloudflare**. |

## 2. Gesamter Tech-Stack

| Schicht | Technik | Aufgabe |
|---|---|---|
| **Frontend** | React 19 + Vite + TypeScript, Tailwind CSS, Zustand (State) | Eine responsive App mit zwei Ansichten: Navigation (Handy) und Verwaltung (Desktop) |
| 2D-Plan | Eigenes SVG, direkt aus den Polygonen in `building.json` (lokale Meter, keine Kartenprojektion) | Etagen, Räume, Türen, Assets, Route, Highlights, Vorschau von Änderungen |
| 3D-Ansicht | react-three-fiber + drei; GLB aus `core/export3d.py` | Gestapelte Etagen, animierte Route |
| Voice | `@elevenlabs/react` (`useConversation`), Client-Tools | Mikrofon, Barge-in, Tool-Aufrufe aus dem Agenten |
| **Edge** | Cloudflare Worker (TypeScript, Hono) + Static Assets | Liefert die App aus, `/api/*`-Routing, Token für ElevenLabs, Secrets |
| Echtzeit | Durable Object `BuildingRoom`, eins pro Gebäude, mit WebSocket-Hibernation und SQLite-Storage | Event-Log der Änderungen (Version, Undo), Broadcast `building_changed` an alle Clients |
| **Compute** | Cloudflare Container mit **Python 3.12, FastAPI, uvicorn, pydantic, shapely, networkx** | Der deterministische `core/`: Suche, Routing (README und geodätisch), Geometrie, What-if. Zustandslos: bekommt `building_id` + Events, Ergebnis wird pro Version gecacht |
| Gebäudedaten | Kit-Gebäude im Container-Image, **nur `building.json` und `equipment.csv`** (keine PNG/SVG, keine Antworten); neue Gebäude in **R2** | Basis für alle Berechnungen; das Sonntagsgebäude kann ohne neues Image hochgeladen werden |
| **Agent (Voice)** | ElevenLabs Agent: `eleven_v4_turbo` + eingebautes `claude-sonnet-5-5` | Gespräch, Rückfragen, Tool-Auswahl |
| Agent (Text) | Anthropic Python SDK im Container, Sonnet 5.5, Tool-Runner, Prompt-Caching | Textchat als Fallback; später optional Custom-LLM-Endpoint für ElevenLabs |
| **Benchmark** | Python-CLI `python -m bench`, Anthropic SDK mit Haiku 5.5 | Läuft lokal, schreibt CSV + `answers.json`, nutzt denselben `core/` |
| Tooling | uv, pytest (Core-Tests gegen dev), ruff; pnpm, wrangler; Docker für das Image | |
| Observability | Workers Logs; Logging von Kosten, Tool-Aufrufen und Latenz pro Anfrage | Zahlen für Demo und Pitch |

**Repo-Struktur:**

```
core/        Python: model, geometry, graph, geodesic, routing, edits, export3d
server/      Python: FastAPI-App (Tool-Endpunkte, Textchat-Agent), Dockerfile
bench/       Python: Benchmark-CLI, Parser/Serializer CSV + JSON
web/         React-App
worker/      wrangler.jsonc, Worker (Hono), Durable Object BuildingRoom, Container-Klasse
data/        Kit-Daten (unverändert)
tests/       pytest gegen dev-inputs
```

## 3. Deployment auf Cloudflare

```
Browser ──HTTPS/WSS──► Worker  (app.<domain> oder *.workers.dev)
                        ├─ /            Static Assets (Vite-Build von web/)
                        ├─ /api/eleven/token   ELEVENLABS_API_KEY → signierte Conversation-URL
                        ├─ /api/ws/:building   → Durable Object BuildingRoom (WebSocket, Event-Log)
                        └─ /api/tools/*, /api/chat
                               → BuildingRoom hängt die Events an → Container "core" (FastAPI :8000)
                                                                    └─ R2 (neue Gebäude)
```

- **Warum ein Container und kein Python Worker:** shapely ist eine native Bibliothek, und ob sie in Python Workers (Pyodide) läuft, steht nicht in den Cloudflare-Docs. Im Container läuft derselbe Code wie lokal und im Benchmark, ohne zweite Laufzeitumgebung.
- **Voraussetzung: Workers-Paid-Plan.** Laut Docs gibt es Containers nur dort. Wir prüfen um 17:15, ob der Cloudflare-Account ihn hat; sonst buchen wir ihn (5 USD pro Monat).
- **Konfiguration (`worker/wrangler.jsonc`):**
  - `assets` zeigt auf `web/dist`, der Pfad ist relativ zur Wrangler-Datei. Dazu SPA-Fallback und `run_worker_first: ["/api/*"]`, damit die API nicht als statische Datei behandelt wird. Vite baut vor jedem Deploy.
  - `[[containers]]` mit dem Dockerfile aus `server/`.
  - Durable-Object-Bindings für `BuildingRoom` und die Container-Klasse, dazu ein R2-Bucket `buildings`.
- **Docker:** Der Build-Kontext ist die Repo-Wurzel, damit das Dockerfile `core/` und `data/` kopieren kann. Zielarchitektur `linux/amd64`, FastAPI hört auf `0.0.0.0:8000`.
- **Eine feste Container-Instanz `"core"`.** `max_instances` allein verteilt keine Last und routet nichts. Der Cache-Schlüssel im Container ist Gebäude-ID + Version der Basisdaten + Event-Version.
- **Secrets:** `wrangler secret put` macht die Keys nur im Worker verfügbar. `ANTHROPIC_API_KEY` reichen wir **ausdrücklich** über `envVars` der Container-Klasse weiter. `ELEVENLABS_API_KEY` bleibt nur im Worker. Keys stehen nie im Repo und nie im Browser; der Browser bekommt nur die signierte Conversation-URL.
- **Durable Object `BuildingRoom`:** Es führt nur das Event-Log, prüft die Version, macht den Commit idempotent und verteilt die Änderungen. Geometrie rechnet es nicht. WebSocket-Hibernation ist eigener Code und kein Schalter: `ctx.acceptWebSocket` statt `ws.accept()`, die passenden Handler, und nach dem Aufwachen den Zustand aus dem Storage wiederherstellen. Nach einem Reconnect lädt der Client den aktuellen Stand neu.
- **Kaltstart:** `sleepAfter` setzen wir bewusst. `/health` meldet erst dann „bereit“, wenn die Anwendung wirklich bereit ist. Wir messen die Dauer eines Neustarts samt Geometrieaufbau und wärmen den Container **unmittelbar** vor Aufnahme und Demo vor.
- **Neue Gebäude aus R2:** Der Container hat kein R2-Binding. Der Worker führt deshalb einen Gebäudekatalog und liefert die Basisdaten über einen internen Endpunkt an den Container. Nach einem Upload wird der Cache für dieses Gebäude ungültig.
- **Lokale Entwicklung:** `uvicorn server.app:app` + `pnpm dev` (Vite-Proxy auf `/api`) + `wrangler dev` für Worker und DO. Der Core wird nicht für jede Änderung neu in den Container gebaut.
- **Notlösung, falls der Container hakt:** Cloudflare Tunnel in dieser Richtung: Worker → öffentliche Tunnel-Adresse → FastAPI auf dem Laptop. Frontend, DO, URL und Backend-Vertrag bleiben gleich. Laptop, Netzwerk und Prozess müssen dann während der ganzen Vorführung laufen. Die Entscheidung fällt **um 19:00**; um 20:00 wird abgenommen.
- **Für die Jury:** Die öffentliche URL plus `README` mit lokalem Start (`uv sync`, `pnpm i`, `.env.example`). Der Benchmark läuft ohne Cloudflare, mit einem einzigen Befehl.
- **Sonntagsgebäude:** `bench` läuft lokal auf dem Ordner. Für die Demo laden wir es zusätzlich nach R2 hoch und tragen es in den Katalog ein.

## 4. Voice-Architektur

```
Browser (React)
  ├─ GET /api/eleven/token → signierte URL
  ├─ useConversation ── Audio ⇄ ── ElevenLabs Agent
  │                                · STT, Turn-Taking, Barge-in
  │                                · LLM: Claude Sonnet 5.5
  │                                · TTS: eleven_v4_turbo (~100 ms), DE/EN
  │    clientTools: find, route, what_if, propose_edit, commit_edit, show
  │      └─ fetch /api/tools/<name> → Worker → Container → Ergebnis an den Agenten + sofort auf die Karte
  └─ WSS /api/ws/:building ⇄ Durable Object  (building_changed an alle Clients)
```

**Warum Client-Tools, die ans Backend weiterleiten:** ElevenLabs ruft das Tool im Browser auf. Der Browser fragt unser Backend, zeigt das Ergebnis **sofort** auf der Karte und gibt dem Agenten ein kompaktes JSON zurück (`expects_response`). Ein zweiter LLM-Aufruf zum Zeichnen ist nicht nötig, und das gleiche Setup funktioniert lokal wie in der Cloud.

Da die App jetzt eine öffentliche Cloudflare-URL hat, wären auch Server-Tools (Webhooks) ohne Tunnel möglich. Wir bleiben trotzdem bei Client-Tools, weil sie die Karte direkt aktualisieren.

Die Zustandshoheit liegt beim Durable Object: Gebäudeversion pro Gebäude, `commit_edit` nur mit `proposal_id` und idempotent. Wird die Sprache unterbrochen, darf kein Commit doppelt passieren.

**Welches LLM im Agenten?** Darüber entscheiden wir **um 17:15**, abhängig davon, wie die Kosten abgerechnet werden:
- **Phase 1 (heute, schnell):** das in ElevenLabs eingebaute `claude-sonnet-5-5`, mit niedrigem Reasoning-Aufwand. Das wird über **ElevenLabs-Credits** abgerechnet, nicht über unsere Anthropic-Credits.
- **Phase 2 (nur bei Bedarf):** ein **Custom-LLM-Endpoint** `/api/llm/v1/chat/completions` (OpenAI-kompatibel, SSE) im Container, der Claude über unsere 600 USD aufruft. Durch Cloudflare ist er öffentlich erreichbar, ein Tunnel ist nicht nötig. Pro Turn darf nur **eine** Seite Tools ausführen.

**Prompt-Regeln für Voice:**
- Sofort eine kurze Bestätigung sprechen, etwa „Okay, ich suche den Weg zur Presse …“.
- Höchstens drei Schritte auf einmal, dann „sag *weiter*“.
- Landmarken statt Raumnummern.
- Genau eine Rückfrage, wenn ein Pflichtparameter fehlt (Start, Breite, Etage).
- Vor jeder Änderung eine Vorschau zeigen und auf ein „Ja“ warten.
- Persona merken: Wer „Rollstuhl“ sagt, bekommt ab dann immer stufenlose Routen.

**Latenzziel (messen, nicht versprechen):** erste hörbare Reaktion unter 1 s, einfache Route auf der Karte unter 3 s. Dafür Geometrie und Graph pro Gebäudeversion im Container vorberechnen und cachen, möglichst nur einen fachlichen Tool-Aufruf pro Frage, kurze Tool-Ergebnisse.

**Fallback ohne Mikrofon oder Credits:** Textchat im selben UI über `/api/chat`, mit denselben Tools.

## 5. Core: zwei Kostenmodelle

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
| Benchmark (dev, test, Sonntag) | **Haiku 5.5** als Parameter-Extraktor mit aufgabenförmigen Tools. Sonnet 5.5 nur für nachgewiesene Problemfälle | 0,10 / 0,50 | etwa 10k in + 1k out pro Frage ≈ **0,0015 USD**. 1.000 Fragen kosten ≈ 1,50 USD |
| Textchat und Custom LLM (falls genutzt) | **Sonnet 5.5**, effort `low` | 2 / 10, Cache-Lesen 0,20 | ≈ 0,03–0,05 USD pro Turn. 1.000 Turns ≈ 40 USD |
| Entwicklung und Experimente | Sonnet 5.5, gezielt Opus 5.5 (4 / 20) | | |

**Ausgabenlimits** (im Console-Workspace als Limit setzen):

| Posten | Limit | Aufteilung |
|---|---|---|
| Benchmark | 200 USD | dev 60, Test 40, Sonntag 100 |
| Chat und Voice | 100 USD | |
| Entwicklung | 220 USD | |
| Reserve | 80 USD | wird nicht angetastet |

Mit Haiku bleibt der Benchmark weit unter dem Limit; der Puffer ist für den Fall gedacht, dass wir auf Sonnet wechseln müssen. Zusätzliche Kosten außerhalb der 600 USD: ElevenLabs-Credits (Agent-Minuten und eingebautes LLM) und der Cloudflare Workers-Paid-Plan.

**Caching:**
- Tool-Schemas und Systemregeln stehen eingefroren am Anfang, die Frage kommt zuletzt.
- Gebäudedaten nur über Tools abfragen, **nie das ganze JSON** in den Prompt.
- `cache_control` setzen und `cache_read_input_tokens` loggen.
- Batch-API (−50 %) für große dev-Läufe, wenn die Latenz egal ist.
- Für jede Frage Kosten, Tool-Aufrufe und Latenz loggen. Ergebnisse checkpointen, bei Wiederholung nur die fehlerhaften Fragen neu laufen lassen.

## 7. Was schon da ist

| Wo | Inhalt | Zustand |
|---|---|---|
| `starter_agent/building_map.py` | MultiGraph nach README, Dijkstra, Sperrungen, `add_door` | Warm-up-Oracle 369/369. Das prüft weder die Geodäsie noch die 9 Benchmark-Arten. `../repo` hat zusätzlich das Feld `node_path` |
| `../repo/core/export3d.py`, `viewer3d.html` | GLB/USD-Export, gestapelte Etagen, Route als Röhre | Funktioniert, wird für die 3D-Ansicht genutzt |
| `../repo/ARCHITECTURE.md`, `VIDEO_TAKEAWAYS.md`, `SYNERA.md`, `RESEARCH*.md` | Tool-Schnitt, Prompt-Regeln, ElevenLabs-Wege, Synera-Pitch-Sprache | Referenz. Server-Struktur und Voice-Weg „A“ sind durch Abschnitt 2–4 ersetzt |
| Dieses Repo | Notizen, PDFs, Skizze, dieser Plan | `.env` wird nicht mehr verfolgt, `.gitignore` ist gefüllt (Commit `62074c2`). `agent.py` ist leer |

Testset (145 Fragen): floor_area_total 33 · shared_walls 26 · largest_room 21 · errand 20 · wide_delivery 18 · straight_line_3d 15 · room_stacked 9 · what_if_door 3.

## 8. Arbeitspakete

| Paket | Inhalt | Fertig, wenn |
|---|---|---|
| **P0 Setup** | Repo-Struktur aus Abschnitt 2 anlegen, lokale Arbeit aus `../repo` übernehmen, `.env.example` mit `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID`. Ausgabenlimits setzen. ElevenLabs-Agent anlegen. Cloudflare: Paid-Plan prüfen, `wrangler login`, R2-Bucket anlegen | Oracle grün, kein Key im Repo, Agent-ID vorhanden, `wrangler whoami` funktioniert |
| **P1 Core-Geometrie** | area, centroid, shared_walls, stacked, distance_3d. Tests gegen die dev-`inputs` | 5 Arten ≈ 100 % auf dev und train |
| **P2 Core-Graph** | Constraints, reachable, errand, wide_delivery, step_free_count, what_if_door (Tür in der Wandmitte) | 4 Arten ≈ 100 % auf dev |
| **P3 Bench + erste Abgabe** | `python -m bench` mit Haiku: CSV + answers.json, Checkpointing, Kosten-Log. `BENCHMARK.md`. Getestet wird **end to end auf den dev-Fragetexten**, nicht nur der Core mit vorgegebenen `inputs`. Sonnet springt nur bei messbaren Extraktionsfehlern ein | **M1:** vollständige Test-CSV mit 145 Zeilen und offizieller dev-Score pro Fragetyp, committed |
| **P4 Geodäsie + Fahrzeuge** | Portalgraph, Gabelstapler, kein Transit durch Produktion, unerreichbare Ziele melden | Tests aus Abschnitt 5 sind grün |
| **P5 Voice-Durchstich (lokal)** | FastAPI `/tools/route`, Vite-Proxy, minimale 2D-Karte, `useConversation` mit einem Client-Tool `route` | **18:30 Integrationsgate:** Gesprochene Frage zeigt eine Route |
| **P6 Cloudflare-Deploy** | **18:00:** minimaler Container öffentlich deployt, Secret-Test. Danach Worker (Hono) mit Assets, Token-Endpunkt, `BuildingRoom`-DO mit WebSocket | **19:00 Entscheidung:** Scheitert ein echter Tool-Aufruf über die öffentliche URL, schalten wir den Tunnel ein. **20:00 Abnahme:** Die öffentliche URL zeigt dieselbe Route wie lokal |
| **P7 App** | Alle Client-Tools, Vorschau, Bestätigung und Undo über das DO, Broadcast an alle Clients, Textchat als Fallback, Handy-Layout | **M2:** drei Demo-Abläufe live auf der öffentlichen URL |
| **P8 Showcase** | 3D mit dem GLB-Export, animierte Route. Level 5 Logistik: Gabelstapler, Gang gesperrt, Docks | **M3:** demo-fertig |
| **P9 Kür** | PNG → Claude Vision → Validator → Vorschau → R2 | Nur mit Puffer |

## 9. Zeitplan

| Zeit | A: Core/Bench | B: Frontend + Cloudflare | C: Voice/Agent/Demo |
|---|---|---|---|
| **Sa 17:15–17:45** | P0 Core-Teil, Tool-Vertrag einfrieren (Namen, Parameter, Ergebnisformat), Referenzgebäude und erwartete Route für das Gate festlegen | P0 Cloudflare-Teil, Vite/React-Gerüst | Abrechnung klären (ElevenLabs-Credits?), Agent anlegen, Discord-Fragen stellen |
| **17:45–18:30** | P1 | **Bis 18:00:** minimaler Container öffentlich, Secret-Test. Dann minimale 2D-Karte | P5: FastAPI `/tools/route`, `useConversation`. C hält den Vertrag für FastAPI und Voice, B die Infrastruktur |
| **18:30** | **Integrationsgate (alle):** Voice → Tool → Karte, lokal, auf dem Referenzgebäude | | |
| **18:30–21:00** | P2 → P3 → **M1** (145 Zeilen + dev-Score pro Typ) | P6 Deploy, **19:00 Entscheidung Container oder Tunnel, 20:00 Abnahme** | Alle Client-Tools, Voice-Prompt-Regeln, Textchat |
| **21:00–00:30** | P4 Portalgraph + Constraints | DO-Event-Log: Vorschau, Bestätigung, Undo, Broadcast | Drei Demo-Abläufe, Rückfrage-Logik → **M2** |
| **00:30 Gate** | Bestätigte Änderung, zweites Gerät, Undo, Reconnect, Wiederherstellung nach Container-Neustart. **Danach keine neue Infrastruktur** | | |
| **00:30–03:00** | Regression auf dev, Checkpointing | Handy-Test auf der öffentlichen URL, Unterbrechungen | Rohschnitt fürs Video |
| 03:00–07:00 | **Schlafen** (dank Zeitumstellung eine Stunde mehr) | | |
| **So 07:00–09:00** | Ein dev-Gebäude wie ein unbekanntes durchlaufen lassen, finale Test-CSV, Installationsprobe auf frischem Klon | 3D **erst nach** bestandenem Frischklon- und Benchmark-Lauf → **M3** | Härtetest mit schwierigen Nutzern |
| **ab 09:00 bis zur Abgabe** | **Bereitschaft für das Sonntagsgebäude:** eine Person lässt `bench` laufen, sobald es erscheint, und lädt es nach R2 | Bugfixes, Container vor der Aufnahme vorwärmen | Video aufnehmen |
| **10:00 Feature Freeze** | BENCHMARK.md, README, exportierte Agent-Konfiguration. **Ausnahme:** Anpassungen an Sonntagsformat und Datenadapter bleiben erlaubt | Letztes Deploy, URL in die Abgabe | Video schneiden, technische Erklärung (Architektur statt Code) |
| **12:00–13:00** | Nur Abschlusslauf, Upload, Abgabe prüfen | | |

**Streichreihenfolge:** PNG-Import → 3D → zusätzliche Logistikfunktionen → Cloudflare-Container (dann Tunnel). **Voice bleibt Pflicht**, M1 wird nie gefährdet.

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
- Haiku für den Benchmark, Sonnet für den Chat
- Budgetaufteilung
- Feature Freeze um 10:00, Zeitumstellung, „Voice bleibt Pflicht“

Abweichend:
- Codex schlägt Server-Tools (Webhooks) vor. Wir nehmen **Client-Tools, die ans Backend weiterleiten**, weil die Karte sich so ohne Umweg aktualisiert. Die Zustandshoheit liegt trotzdem auf dem Server (Durable Object).
- Codex gibt für das Lesen aus dem Cache 0,05× an. Laut Anthropic-Preisliste liegt Sonnet 5.5 bei 0,20 USD pro MTok, also 0,1×.

**Zweites Review (Cloudflare, Stack, Repos)** mit dem Urteil „technisch stimmig, für drei Personen aber zu breit“. Übernommen:
- Container-Details: Build-Kontext, amd64, eine feste Instanz, Secrets über `envVars`, `sleepAfter`, echtes `/health`
- Assets-Routing mit `run_worker_first`
- Hibernation als eigener Code
- Weg von R2 über den Worker zum Container, nur JSON im Image
- Container-Durchstich bis 18:00, Entscheidung um 19:00
- Härtere Kriterien für M1 und das 00:30-Gate
- Ausnahme vom Feature Freeze für den Sonntagsadapter
- Keine pauschale Verbindung zerfallener Polygone
- Lizenzen präzisiert, dazu eine Herkunftsliste (Abschnitt 13)

3D, Custom-LLM-Endpoint und PNG-Import bleiben verbindlich Kür.

## 12. Demo-Story (Video, 25 Interaktionspunkte)

Fabrikhalle, drei Nutzer auf zwei Geräten, eine Karte, alles per Stimme:
1. **Techniker** am Handy: „Welche Presse ist Linie 4, wie komme ich hin?“ Der Agent antwortet mit Landmarken, die Route ist animiert, die nächsten Schritte kommen auf „weiter“.
2. **Facility Manager** am Laptop: „Der Ostlift ist in Wartung.“ Der Agent zeigt eine Vorschau mit den betroffenen Routen und wartet auf ein „Ja“. Danach aktualisiert sich die Karte **sofort auch auf dem Handy**.
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
| 3D (`web/`) | [react-three-fiber](https://github.com/pmndrs/react-three-fiber) + drei (MIT); UX von [xeokit-bim-viewer](https://github.com/xeokit/xeokit-bim-viewer) (**AGPL-3.0, nur UX-Ideen**) und Mappedin Stacked Maps | Unser vorhandener GLB-Export, keine zweite Extrusionspipeline. Auseinandergezogene Etagen, nicht aktive Etagen halbtransparent | P8 |
| Voice-UI | [ElevenLabs UI](https://github.com/elevenlabs/ui) (MIT; Orb, Conversation Bar) | Fertige React-Komponenten statt eigener Voice-UI, aber nur, wenn sie im Vite-Gerüst schnell laufen | P5/P7 |
| Logistik (Level 5) | [Open-RMF](https://github.com/open-rmf/rmf_traffic) (Apache-2.0, nur Konzept) | Wegenetz, Fahrzeugprofil und Belegung getrennt. Für den Pitch als nächster Schritt | P8 |
| Kür Build | [Open-Location-Stack/floorplan-editor](https://github.com/Open-Location-Stack/floorplan-editor) (IMDF-Validator) | Idee für unseren Validator: gültige Polygone, Türen auf gemeinsamen Wänden, alles erreichbar | P9 |
| Startpunkt | Brainstorming + [WebXR-Videos](https://www.youtube.com/watch?v=riiJdNq2LWI) | **QR-Code am Eingang/an Türen** kodiert `opening_id` → Startpunkt in der App. Ohne AR, in einer Stunde machbar | P8 |

**Reihenfolge beim Wiederverwenden:** zuerst der eigene funktionierende Kit-Code, dann offizielle SDK-Beispiele, dann kleine UI-Komponenten. Andere Indoor-Systeme dienen heute nur als Referenz, denn ihre Datenmodelle zu integrieren kostet mehr Zeit, als es bringt. Weitere Recherche ist nicht nötig.

**Herkunftsliste `THIRD_PARTY.md`:** Für jede Übernahme notieren wir Projekt, Commit, übernommene Dateien, Lizenz und nötige Hinweise. Aus GPL-Projekten werden keine Synonymlisten oder Test-Fixtures mitkopiert. Unabhängig davon gelten die **Datenlizenzen** aus `ATTRIBUTION.md`: ODbL für OSM, CC BY 4.0 für Swiss Dwellings und ResPlan, CC0 für die prozeduralen Gebäude.

**Bewusst nicht im Wochenend-Stack**, aber als Ausblick für den Pitch geeignet:
- Planerkennung mit ML: [CubiCasa5k](https://github.com/CubiCasa/CubiCasa5k), DeepFloorplan
- BIM-Import mit [IfcOpenShell](https://github.com/IfcOpenShell/IfcOpenShell)
- Kamera-Lokalisierung im Grundriss: [F3Loc](https://github.com/felix-ch/f3loc), PALMS
- VPS mit [hloc](https://github.com/cvg/Hierarchical-Localization), SLAM
- WebXR-AR-Pfeile
