# Finaler Plan – Talk to Your Building (Track 01)

**Stand:** Sa 24.10.2026, 20:05 · **Code Freeze:** So 25.10., 13:00 (durch die Zeitumstellung eine Stunde mehr).
**Herkunft:** Review 1 (Codex, `03b4e91`) → Review 2 (dieses Dokument) mit ElevenLabs-Config → Teamgespräch ca. 18:30 → Hagens UX-Erklärung (`07a46bd`), `AGENT_BUILD_SPEC.md` (`c0f2171`), `PLAN.md` `2ab5974`, Lenards Prototyp `web/mobile` (`b411e05`), **Kit 1.1.0** (`4756739`, `a5656fe`) und **`HagenFinalPrompt.md`** (`c2822f9`). Einordnung der Abweichungen in Anhang B.
**Zweck:** Grundlage für das gesamte Agentic Engineering. Agenten bauen, was hier steht, und nichts, was hier fehlt.

> **Rolle dieses Dokuments:** `HagenFinalPrompt.md` gibt einem Master-Agenten die technische Entscheidungshoheit und lässt ihn das Ausführungspaket `master prompt/` für vier Builder schreiben. Dieses Dokument ist **unser konsolidierter Vorschlag dafür**: Es enthält die Teamentscheidungen (Abschnitt 2), Hagens Journey, die Aha-Momente, Verträge und Pakete bereits in der Struktur, die der Master-Agent braucht (Zuordnung in Abschnitt 10). Bis `master prompt/` existiert, gilt dieses Dokument zusammen mit [`docs/elevenlabs-agent-config.md`](docs/elevenlabs-agent-config.md); wo `PLAN.md` widerspricht, gilt dieses Dokument. Fachliche Details aus `PLAN.md`, die hier nicht berührt werden (z. B. Prompt-Regeln, Budget-Limits, Lizenzregeln §13), gelten weiter.

---

## 0. Auf einen Blick

- **Produkt:** Eine Web-App, mit der man mit dem Gebäude spricht – am Desktop Teile finden und Touren planen, am Handy hinlaufen, auf Android mit Live-Kamera.
- **Journey:** Teile am Desktop auswählen → beste Reihenfolge → QR aufs Handy → loslaufen → Lift fällt aus → App routet um (Abschnitt 1).
- **Drei Aha-Momente tragen Demo und Pitch:** „Say what you need“, „From screen to hand“, „The building reacts“ (Abschnitt 1.2).
- **Fokusregel:** Jede Arbeit dient entweder den Benchmark-Punkten oder einem der drei Aha-Momente. Alles andere wartet bis nach dem Journey-Gate (01:00).
- **Stack:** Railway, ein Service. Python (FastAPI, shapely, networkx, SQLite) für Core, Server und Benchmark. React + TypeScript (Bun) im Frontend; die Handy-App baut auf Lenards Prototyp `web/mobile` auf. ElevenLabs für Voice, Claude für Text und Benchmark.
- **Routenmodell:** Seit Kit 1.1.0 gibt es **ein** Modell für alle Antworten, auch die verdeckten Testantworten: Tür zu Tür, 15 cm Wandabstand, kein Weg außen herum. Der Kit-Starter (Python) setzt es exakt um; geprüft: Warm-up-Oracle auf dev **369/369** (Abschnitt 5.4).
- **Kritischer Pfad:** Core + Gebäude-DB → Benchmark-Agent → Submission (M1). Zwei Builder dauerhaft (Hagen's codex, Lenard's codex).
- **Vier Builder** laut `HagenFinalPrompt.md`: Hagen's codex (Core), Lenard's codex (Agent und Evaluation), Manuel's codex (Plattform und Live-Integration), Manuel's Claude (Experience und Frontend).
- **Reihenfolge bei Konflikten:** Core/DB → Agent/Submission → Voice → Journey-UI → Kamera → 3D → Admin → Bildimport.
- **Level-5-Erweiterung:** Kamera-Navigation (Android: WebXR-AR, iPhone: Kamera-Overlay), verankert über QR-Codes an Türen.
- **Gestrichen:** Gabelstapler-Demo, Custom-LLM-Endpoint, gebäudeübergreifendes Routing, Cloudflare.

---

## 1. Ziel und User Journey

### 1.1 Journey

**Persona:** Eine Person ist neu im Gebäude – oder das Gebäude ist neu.

1. **Desktop am Arbeitsplatz:** Ansicht des Gebäudes (2D, später 3D), daneben die Teileliste. Ein Teil anklicken → sein Ort wird gezeigt. Teile bewegen sich live (simuliert, nur wenn Zeit bleibt).
2. **Mehrere Teile holen** (Kommissionierung, z. B. fünf): auswählen oder sagen → **beste Reihenfolge** und Route.
3. **Übergabe-QR auf dem Bildschirm** → mit dem Handy scannen → die Tour ist auf dem Handy.
4. **Mit dem Handy laufen:** Turn-by-Turn mit Landmarken und Stimme; auf Android als Linie im Kamerabild.
5. **Der Lift fällt aus** (Admin sperrt ihn) → das Handy bekommt es live mit → neue Route, Ansage → Teil gefunden.
6. **Pitch-Rahmen:** Neues Gebäude → Floorplan hochladen → das Gebäude steht in Minuten.

**Zwei User Experiences:**
- **UX A – Laptop:** Desktop-Ansicht (Navigation, hohe Priorität) und Admin (Bearbeiten und Import, niedrigste Priorität). „Desktop“ ist nicht gleich „Admin“.
- **UX B – Handy:** Tour, Turn-by-Turn, Live-Reroute, Kamera. Android und iPhone sind im Team vorhanden, beide werden unterstützt.

**Abgrenzung:** Die Interaktionsbewertung (25 Punkte) ist ein geskriptetes Gespräch. Es muss ohne Kamera und am Laptop funktionieren. Die Kamera ist ein zusätzlicher Modus, nicht der einzige Eingang.

### 1.2 Aha-Momente

Ein Aha-Moment ist eine Stelle, an der das Publikum in einer Sekunde versteht, warum das besser ist als ein PDF-Plan. Alle drei entstehen aus Funktionen, die ohnehin im Plan sind. Sie spielen im **selben Hero-Gebäude** hintereinander (Abschnitt 13).

| # | Moment | Was man tut | Was sichtbar passiert | Ziel | Fallback |
|---|---|---|---|---|---|
| **1** | **„Say what you need, not where it is“** | Am Desktop: „I need the filament, the torque wrench and the steel drum.“ | Die Teile leuchten auf, der Agent nennt die beste Reihenfolge, die Route zeichnet sich animiert. Bei Mehrdeutigkeit genau eine Rückfrage („Which press: line 4 or line 7?“) | Route sichtbar < 3 s | Teile in der Liste anklicken, Textchat |
| **2** | **„From screen to hand“** | Übergabe-QR mit dem Handy scannen | Das Handy öffnet genau diese Tour, die Stimme führt („After the column, turn right“). Auf Android liegt die Linie im Kamerabild auf dem echten Boden. Bei Ankunft freut sich der Avatar | Tour auf dem Handy < 2 s nach dem Scan | 2D-Karte + Stimme; iPhone-Overlay |
| **3** | **„The building reacts“** | Am Laptop: „Close the east lift.“ → Vorschau → „Yes.“ | Auf dem Handy, mitten auf dem Weg: Hinweis, Ansage, neue Linie | < 2 s nach „Yes“ | Button „Close lift“ |
| Bonus | **„It understands space“** (Pitch, technisches Video) | „Water is dripping from the ceiling in office 0.29. What's above it?“ | Der Raum darüber leuchtet auf (3D, sonst Etagenwechsel); Panel „How I calculated this“ zeigt die Tool-Aufrufe | – | 2D mit Etagenwechsel |

Der Bonus nutzt `room_stacked` aus dem Benchmark-Core. Er zeigt Syneras Linie „das LLM interpretiert, die Regeln entscheiden“ und verbindet die 55 Benchmark-Punkte sichtbar mit dem Produkt. Er braucht keine neue Funktion.

**Was jeden Moment trägt:** kurze Latenz, eine klare sichtbare Reaktion, eine gesprochene Bestätigung. Ein Moment, der im Test länger als sein Ziel braucht, wird vor neuen Features repariert.

---

## 2. Entscheidungen

| # | Thema | Entscheidung | Grund / Quelle |
|---|---|---|---|
| 1 | Hosting | **Railway**, ein Service, ein Prozess | Teamentscheidung; weniger Teile als Worker + DO + Container + R2 |
| 2 | Sprache | **Python** für Core, Server, Benchmark; **TypeScript** nur im Frontend | **Teamentscheidung (24.10., ca. 20:00).** Der Kit-Starter rechnet das bewertete Routenmodell exakt in Python mit shapely (Anhang A.3); ebenso `AGENT_BUILD_SPEC.md`. `PLAN.md` (TypeScript-Core) ist damit überholt; Lenard informieren |
| 2a | Routenmodell | **Kit 1.1.0**, ein Modell für alle Fragen; Routing-Code aus `starter_agent/building_map.py` wiederverwenden, nicht neu schreiben | `CHANGELOG.md`, README §3; Jurorenfrage 1 damit beantwortet |
| 3 | Datenhaltung | **Gebäude-DB in SQLite**, vorberechnet beim Import (Lenards Idee) | Teamgespräch: „Datenbank zuerst“ |
| 4 | Reihenfolge | Core/DB → Agent/Submission → Voice → UI/UX; parallel bearbeitet | Teamgespräch |
| 5 | Geräte | Android und iPhone | im Team vorhanden |
| 6 | Voice-LLM | Start **Claude Sonnet 5.5**, A/B-Test entscheidet | Abschnitt 9 |
| 7 | Voice-Auth | **WebRTC + Conversation Token** | ElevenLabs-Docs; Signed URL gehört zu WebSocket |
| 8 | Demo-Sprache | **Englisch** | Agent-Config |
| 9 | Benchmark-Modell | **Haiku 5.5** zuerst, Sonnet 5.5 nur bei messbar schlechteren Ergebnissen | PLAN.md, `ef84a9d` |
| 10 | Level 5 | **Kamera-Navigation** mit QR-Verankerung | eine Erweiterung, gut gemacht |
| 11 | Bildimport | **Bleibt, mit Timebox** nach dem Journey-Gate (01:00–03:00) | Rubrik nennt „correct buildings built from plans“ (Anhang A.1) |
| 12 | Handy-UI | **Lenards Prototyp `web/mobile`** (React, Vite, Bun, Blobatar-Avatar, `DESIGN.md`) ist die Basis; seine Demo-Daten werden durch die echte API ersetzt | existiert schon und ist stark präsentierbar |
| 13 | Ortung | **Positions-QR an Türen** als Basis; visuelle Ortung (hloc/MegaLoc, Lenards Test) nur als Upgrade nach Gate | QR ist in Stunden robust; bei hloc fehlt noch die Zuordnung der Referenzbilder zum Grundriss |

---

## 3. Architektur

```
Laptop (UX A) ─┐                        ┌─ /, /desk, /admin, /go/{tour}, /m/{marker}   SPA (Vite, TypeScript)
Handy  (UX B) ─┼── HTTPS/WSS ── Railway FastAPI (Python) ─┼─ /api/*               Tools, Touren, Sessions, Edits, Import, Chat
               │                        ├─ /api/voice/token     ElevenLabs Conversation Token (WebRTC)
               │                        ├─ /ws/buildings/{id}   building_changed an alle Clients
               │                        └─ /health
               └── Audio (WebRTC) ── ElevenLabs Agents ── Client-Tools laufen im Browser → /api/tools/*
Volume /state:    SQLite (Gebäude-DB, Events, Proposals, Sessions, Touren, Marker) + Uploads
Image  /app/data: Kit-Gebäude (nur building.json + equipment.csv)
Benchmark:        lokal, ohne Railway und ohne ElevenLabs, derselbe core/ und dieselbe Gebäude-DB
```

**Betrieb auf Railway:**
- **Dockerfile im Repo-Root, mehrstufig:** Bun baut `web/mobile` und `web/desk`, dann `python:3.12-slim` mit `core/`, `server/`, `data/` und dem `dist`. `uvicorn server.app:app --host 0.0.0.0 --port $PORT`, **ein** Worker.
- Routenreihenfolge: `/api`, `/ws`, `/health` vor dem SPA-Fallback.
- Volume auf `/state`, nicht über `/app/data`. Initialisierung beim Start, nicht beim Build.
- Secrets als Railway-Variablen: `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID_NAVIGATOR`, `ELEVENLABS_AGENT_ID_ADMIN`.
- **Grenzen (geprüft):** Mit Volume **keine Replicas**, und ein **Redeploy hat kurze Downtime**. Kein Deploy während Aufnahme oder Demo. Der Client verbindet den WebSocket automatisch neu und lädt den Snapshot. App-Sleeping aus.
- Geometrie und Routing im Threadpool (synchrone `def`-Endpunkte), damit WebSocket und Voice nicht blockieren. Gebäude-DBs werden bei Bedarf erzeugt, nicht alle 280 beim Start.
- **Handy-Tests brauchen HTTPS** (Kamera, Mikrofon, WebXR). Wege: eigene Railway-Dev-Umgebung; Android per USB-Port-Forwarding auf `localhost`; iPhone nur über Railway oder HTTPS-Tunnel.

**Zustandsvertrag** (aus Review 1, §6):
- Basisdaten unveränderlich, identifiziert durch Gebäude-ID + Inhalts-Hash. Änderungen sind Events mit fortlaufender Gebäudeversion.
- `propose_edit` und `what_if` schreiben nichts dauerhaft. `commit_edit` braucht `proposal_id` + `expected_version`, ist idempotent über `operation_id`. Veralteter Vorschlag → Konflikt + neue Vorschau.
- Undo ist ein neues Event, das eine bestimmte eigene Änderung zurücknimmt.
- Jedes Tool-Ergebnis trägt Gebäudeversion und Request-ID; verspätete Antworten überschreiben keine neueren.
- Sitzung (Position, aktive Tour, Profil wie „wheelchair“) ist getrennt vom Gebäudezustand.
- **Benchmark:** Jede Frage startet vom ursprünglichen Gebäude. Kein Demo-Zustand fließt hinein.

---

## 4. Repo-Struktur und Arbeitsregeln

```
core/        Python: model (laden, validieren), db (Schema, Import, Vorberechnung), geometry,
             graph (Routenmodell Kit 1.1.0, aus dem Starter übernommen), queries (eine Funktion je Frageart), resolve,
             tour, edits (Events), markers
server/      Python: FastAPI-App, Routen, Sessions, WebSocket, Voice-Token, Textchat
bench/       Python: CLI, Benchmark-Agent (Tool Runner), Serializer (CSV + answers.json), Checkpoints
web/mobile/  TypeScript: Handy-App, Lenards Prototyp (Bun; eigene AGENTS.md und DESIGN.md)
web/desk/    TypeScript: Desktop-Ansicht und Admin
web/shared/  TypeScript: generierte API-Typen, Koordinatentransformation, Voice-Anbindung
tests/       pytest: Core gegen train/dev, Bench end to end auf einer dev-Stichprobe
data/        Kit-Daten, unverändert
Dockerfile, pyproject.toml (uv), Bun-Workspace in web/, AGENTS.md
```

**Besitz von Verträgen** (nur der Besitzer ändert sie, alle anderen bauen dagegen):

| Vertrag | Datei | Besitzer |
|---|---|---|
| DB-Schema und Vorberechnung | `core/db/` | Hagen's codex |
| Abfragefunktionen je Frageart | `core/queries/` | Hagen's codex |
| Benchmark-Agent, Serializer, Antwortformate | `bench/` | Lenard's codex |
| Tool- und API-Vertrag (Namen, Parameter, Ergebnis) | `server/api.py`, `docs/elevenlabs-agent-config.md` | Manuel's codex |
| Routen-Ergebnis (Polylinie, Manöver) | `core/graph/` | Hagen's codex |
| Koordinatentransformation Gebäude ↔ Bildschirm ↔ WebXR | `web/shared/geo/transform.ts` | Manuel's codex |
| Design und Manifeste der Web-Apps (`package.json`, `bun.lock`) | `web/` | Manuel's Claude |
| Python-Abhängigkeiten (`pyproject.toml`, `uv.lock`) | Repo-Root | Hagen's codex |

**Gemeinsame Typen:** `openapi-typescript` erzeugt die TypeScript-Typen aus `/openapi.json` von FastAPI. Keine handgeschriebenen Doppel-Typen.

**Git (nach `HagenFinalPrompt.md` §10):** Jeder Builder arbeitet in einem eigenen Branch und Worktree auf Basis des aktuellen Integrationsstands. Kleine Commits an echten Meilensteinen, Branch pushen, SHA und berührte Verträge im eigenen `STATUS.md` melden. **Manuel's codex** ist Integrationsverantwortlicher und führt fertige Stände in Abhängigkeitsreihenfolge per Fast-Forward nach `main`; nie Force-Push auf `main`. Verträge ändern nur ihre Besitzer, nach Absprache mit den Nutzern des Vertrags.

### Inhalt für `AGENTS.md` (in W0 anlegen)

1. Quellenrang: `master prompt/` (sobald vorhanden) → dieses Dokument → `docs/elevenlabs-agent-config.md` → Kit-README und `CHANGELOG.md` → `PLAN.md`.
2. Antworten und `inputs` aus `questions*.jsonl` sind **nur** für Tests. Nie im Produktionspfad, nie in der Gebäude-DB, nie im Prompt.
3. `data/` nicht verändern. Nichts auf die Testgebäude zuschneiden.
4. Vor jedem Commit `uv run pytest` (und `bun run build` in der berührten Web-App). In `web/mobile` gelten zusätzlich dessen `AGENTS.md` und `DESIGN.md`.
5. Claude-API: kein erzwungenes `tool_choice` (`any`/`tool`) bei Sonnet 5.5 und Opus 5.5, kein `thinking: disabled`, keine `temperature`/`top_p`/`top_k` (seit 21.10.2026 überall 400). Stattdessen `strict: true` und Prompt.
6. Nach `Answer:` steht genau eine Zahl bzw. der Raum. Kein „m²“ hinter Zahlen, außer bei `largest_room`.
7. Keine Secrets im Repo, im Browser nur Agent-IDs und kurzlebige Tokens.
8. Nutzertexte auf Englisch.

---

## 5. Core-Verträge

**Ausführlicher Tool-Katalog:** [`AGENT_BUILD_SPEC.md`](AGENT_BUILD_SPEC.md) §3. Davon gelten 3.1–3.4 und 3.7. 3.5 (Build from plans) ist X5 mit Timebox, 3.6 (mehrere Gebäude) ist gestrichen, aus 3.8 ist die Kamera gewählt. Die folgenden Abschnitte legen die Verträge fest, die dort offen sind.

### 5.1 Gebäude-DB

- **Basistabellen** wie im JSON: `buildings`, `floors`, `spaces`, `openings`, `connectors`, `connector_stops`, `assets`.
- **Vorberechnet beim Import** (mit shapely, also exakt wie das Referenzmodell): Fläche, Schwerpunkt, Mittelpunkt für Routen (`representative_point`) pro Raum; **Gehwege innerhalb jedes Raums** (Mittelpunkt ↔ Türen, Tür ↔ Tür, wie `space_walks` im Starter) **mit Länge und Wegpunkten**; `space_adjacency` (gemeinsame Wandlänge, Regel 0,35 m / 1 m, plus Mitte der gemeinsamen Wand für `what_if_door`); `space_stacking` (größte Überdeckung oben/unten); Weg zum nächsten Eingang je Raum.
- Die Gehwege sind die teuerste Rechnung (Sichtbarkeitsgraph auf dem geschrumpften Polygon). Der Starter cacht sie schon pro Raum (`load_cached`); die DB macht diesen Cache dauerhaft. Nach einer Tür-Änderung werden nur die Gehwege der beiden betroffenen Räume neu gerechnet.
- **Ein Schreibweg:** Import und Änderungen laufen durch denselben Code; bei einer Änderung nur betroffene Werte neu.
- Graph und Routen mit Bedingungen werden zur Laufzeit gerechnet und pro Gebäudeversion gecacht.

### 5.2 Abfragefunktionen je Frageart

Parameter genau wie die `inputs` der Kit-Fragen (in train und dev geprüft). Jede Funktion liefert ein typisiertes Ergebnis; den Antworttext erzeugt der Serializer.

| Frageart | Funktion | Parameter | Ergebnis | Bewertung |
|---|---|---|---|---|
| `largest_room` | `largest_room` | `floor_id`, `room_type` | Raum + Fläche | Raum vor Zweitplatz, Fläche ±5 % |
| `floor_area_total` | `floor_area_total` | `floor_id`, `room_type` | m² | ±5 % |
| `errand` | `errand` | `start`, `asset_type`, `floor_id`, `room_type` | m, `via`, `target` | ±1 %, mind. ±1 m |
| `wide_delivery_count` | `wide_delivery_count` | `start`, `floor_id`, `min_width` | Anzahl | exakt |
| `step_free_reachable_count` | `step_free_reachable_count` | `start`, `closed`, `floor_id` | Anzahl | exakt |
| `room_stacked` | `room_stacked` | `start`, `direction` (`above`/`below`) | Raum | Raum vor Zweitplatz |
| `shared_walls_count` | `shared_walls_count` | `start` | Anzahl | exakt |
| `straight_line_3d` | `straight_line_3d` | `first`, `second` | m | ±2 % |
| `what_if_door` | `what_if_door` | `first`, `second`, `door_floor_id`, `floor_id` | Anzahl | exakt |
| Warm-up `locate`, `count` | `locate`, `count` | Name/Typ, Etage | Ort bzw. Anzahl | – |
| Warm-up `route*`, `tour` | `route`, `tour` | Start, Ziel(e), `step_free`, `closed` | Route(n) | Länge auf den Zentimeter |

**Semantik, die oft falsch gemacht wird:**
- `errand`: Treppen sind immer erlaubt. Erst den vom Start aus **nächsten** Raum mit passendem Asset finden, dann zum **größten** Raum vom `room_type` auf `floor_id`. Routenmodell Kit 1.1.0.
- `wide_delivery_count`: immer stufenlos, Lifte erlaubt, jede durchquerte Tür ≥ `min_width` (in den Daten 1,0 oder 1,1 m).
- `shared_walls_count`: mind. 1 m Umriss innerhalb 0,35 m; Korridore, Treppenhäuser und Lifte zählen nicht; nur dieselbe Etage.
- `room_stacked`: Raum auf der nächsten Etage mit der größten Überdeckung, nicht der nächste Schwerpunkt.
- `straight_line_3d`: Polygon-**Schwerpunkt** und `elevation_m` der Etage, nicht der Routen-Mittelpunkt (`representative_point`).
- `what_if_door`: Tür in der **Mitte der gemeinsamen Wand**, auf einer isolierten Kopie. Der Starter setzt ohne `position` an die Stelle größter Nähe (`nearest_points`); seit Kit 1.1.0 nimmt `add_door` eine `position`, also die Wandmitte ausdrücklich übergeben. Zählen, wie viele Räume auf `floor_id` einen um **mehr als 1 m** kürzeren Weg zum nächsten Eingang haben (Routenmodell Kit 1.1.0, kein Weg außen herum).
- Welche Space-Typen bei den Zählfragen als „Raum“ gelten, aus den dev-Antworten ableiten und als Test festhalten.

### 5.3 Entitäten auflösen

`resolve(text, kind)` → Kandidaten mit IDs. Reihenfolge: exakte Raumnummer/ID → exakter Name → normalisiert (Groß/Klein, führende Nullen, DE/EN-Synonyme) → unscharf (RapidFuzz). **Zahlen müssen exakt passen** („Press 4“ ist nicht „Press 14“). Mehrere gleich gute Treffer → Liste zurück, der Agent fragt einmal nach.

### 5.4 Routen

- **Ein Routenmodell (Kit 1.1.0, README §3)** für Benchmark, App und Kamera: Knoten am `representative_point` jedes Raums und an jeder Öffnung; Gehwege innerhalb eines Raums auf `buffer(-0.15)` über einen Sichtbarkeitsgraphen; eine Tür „landet“ 30 cm im Raum; Treppe 2 m pro Höhenmeter, nur zwischen aufeinanderfolgenden Halten; Lift 15 m einmal pro Fahrt plus 1 m pro Höhenmeter, jedes Haltepaar direkt verbunden; Kantenlängen auf 3 Nachkommastellen; parallele Verbindungen behalten; **kein Weg außen herum**.
- **Wiederverwenden statt neu schreiben:** `walking_lengths`, `door_landing`, `space_walks`, `graph`, `route` und die Konstanten aus `starter_agent/building_map.py`. **Geprüft am 24.10. um 20:00:** `uv run python -m starter_agent.evaluate data/dev --oracle` ergibt **369/369** (count 40, locate 100, route 120, route_step_free 40, route_with_closure 29, tour 40), Laufzeit ca. 13 s.
- **Was der Starter nicht liefert:** die Wegpunkte der Gehwege (er speichert nur Längen) und Manöver mit Landmarken. Beides ergänzt K1, denn Karte und Kamera brauchen die echte Linie.
- Bewertungsprofil versioniert (`kit_1_1_0`, später `sunday_vN`, falls Synera etwas ändert); Profil, Daten-Hash und Commit stehen im Laufbericht. Wahl im Code, nie durch das LLM.
- **Constraints:** `step_free`, `min_door_width`, `closed`, `allow_stairs`, `allow_lifts`, Gabelstapler (Öffnungen ab 3 m), kein Transit durch Produktionsbereiche. **Unerreichbar ist ein gültiges Ergebnis** (`reachable: false`); in Kit 1.1.0 sind 112 Warm-up-Routen und Touren genau so beantwortet.
- **Ergebnis:** `space_path` (jeder durchquerte Raum, wie in den Kit-Antworten), `element_path` (jede Öffnung, Treppe, Lift einmal), **Polylinie je Etage** (Karte und Kamera), Manöverliste mit Landmarken, Länge, Profil, Gebäudeversion, Request-ID. Die Oberfläche wählt nie selbst Türen.
- **Touren (`plan_tour`):** bis 7 Ziele alle Reihenfolgen, darüber Nearest Neighbor + 2-opt; `keep_order` für feste Reihenfolge (Kit-Typ `tour`). Ergebnis: Liste von Teilstrecken.

---

## 6. Agents, Tools und API

### 6.1 Benchmark-Agent (Submission)

- Einstieg für den offiziellen Evaluator: `answer(building_directory, question_text) -> str`, nutzbar mit `uv run python -m benchmark.evaluate data/dev --agent bench.agent:answer`.
- Ablauf (entspricht dem „hybrid fast path“ aus `AGENT_BUILD_SPEC.md` §4): Tool Runner des Anthropic SDK (Python) mit `resolve` und den Abfragefunktionen aus 5.2. Der Agent gibt das Ergebnis über ein **typisiertes Tool `submit_answer`** ab (`kind` + Werte). Den Antworttext mit `Answer:`-Zeile erzeugt der **Serializer** im Code.
- Eigener Runner `uv run python -m bench …` für Parallelität, Timeout, Backoff, Checkpoint pro Frage (mit Frage-/Daten-Hash, Modell, Prompt-Version, Profil) und Kostenlog. Keine Batch-API im Sonntagspfad.
- **Sonntagsadapter:** `run_benchmark <building_dir> <questions.json> <answers.json>` laut PDF, zusätzlich CSV laut README. Schema vorläufig, bis Synera es bestätigt.

### 6.2 Textchat

`/api/chat` mit Sonnet 5.5 (effort `low`), denselben Tools wie die Voice-Agents. Fallback ohne Mikrofon.

### 6.3 Voice-Agents

Zwei ElevenLabs-Agents, Einstellungen, Tools und Prompt-Regeln in [`docs/elevenlabs-agent-config.md`](docs/elevenlabs-agent-config.md):
- **Navigator** (Desktop und Handy): `find`, `plan_tour`, `route`, `next_step`
- **Admin** (Laptop): `set_scale`, `propose_edit`, `commit_edit`, `undo`, `what_if`, `generate_markers`
- QR-Scans und Plan-Upload laufen über die Oberfläche; die App meldet das Ergebnis per `sendContextualUpdate`.

### 6.4 HTTP-API (Vertrag, Besitzer C)

| Methode und Pfad | Zweck |
|---|---|
| `GET /api/buildings`, `GET /api/buildings/{id}` | Katalog; Snapshot mit Geometrie und Version |
| `POST /api/buildings` | `building.json` hochladen (B1) |
| `POST /api/buildings/{id}/plan-image` | Planbild für den Import (B2) |
| `POST /api/tools/{name}` | alle Agent-Tools aus 6.3, gleiche Namen und Parameter |
| `POST /api/sessions`, `PATCH /api/sessions/{id}` | Sitzung; Position aus Marker, Profil |
| `GET /api/tours/{id}` | Tour für den Übergabe-QR |
| `GET /api/markers/{id}` | Marker (Position, Etage, Blickrichtung) |
| `GET /api/voice/token?agent=navigator\|admin` | Conversation Token |
| `POST /api/chat` | Textchat |
| `WS /ws/buildings/{id}` | `building_changed` mit Version und Event-ID |
| `GET /health` | Bereitschaft ohne LLM-Aufruf |

**Front-Routen:** `/desk` (Desktop-Ansicht), `/admin`, `/go/{tour_id}` (Übergabe-QR), `/m/{marker_id}` (Positions-QR). Beide QR-Arten sind URLs, damit schon die normale Kamera-App die Web-App öffnet.

---

## 7. UX A – Laptop

### Desktop-Ansicht (Rang 4)

- 2D-Karte als SVG aus den Polygonen; Zoom und Pan mit `react-zoom-pan-pinch`; Etagenwahl; aktive Etage voll, andere als Schatten.
- Teileliste mit Suche, Klick → Hervorhebung; Mehrfachauswahl → `plan_tour` → Reihenfolge, Route, **Übergabe-QR**.
- Voice über den Navigator; Textchat als Alternative.
- **Feinschliff, der auf der Bühne zählt:** Route zeichnet sich animiert; große, lesbare Hervorhebung; Voice-Status sichtbar (ElevenLabs UI, Orb oder Leiste); Panel „How I calculated this“ mit den Tool-Aufrufen; Hinweis „Building updated: east lift closed“ auf allen Geräten.
- **Später (Rang 6):** 3D-Ansicht (react-three-fiber, Etagen aus Polygonen extrudiert und gestapelt, Route als Linie; `../repo/core/export3d.py` als Referenz).
- **Erst nach dem Journey-Gate:** simulierte Teilebewegung über `move_asset`-Events; Präsenz anderer Nutzer als Mock (Lenards Idee). Beides im Pitch nicht als echte Funktion darstellen.

### Admin (B3a Rang 4, Rest Rang 7–8)

| Stufe | Inhalt | Priorität |
|---|---|---|
| **B1** | `building.json` hochladen → Validator → darstellen → alle Tools funktionieren. Gleicher Pfad wie das Sonntagsgebäude | Pflicht (Teil von Core) |
| **B3a** | „Lift sperren“ und „Undo“ mit Vorschau und Bestätigung | Pflicht für die Journey |
| **B4** | Positions-QR erzeugen: Blatt mit `marker_id`, Etage, Position, Blickrichtung | Pflicht für die Kamera |
| **B3b** | Weitere Änderungen (Tür, Asset verschieben, Raumtyp), Voice-Admin | Soll |
| **B2** | Planbild (PNG/JPG, auch Foto eines Fluchtplans) → Claude Vision → Entwurf im Kit-Format → Validator → Overlay-Vorschau → Korrektur per Voice oder Klick („the hall is 40 m wide“) → speichern | Timebox 01:00–03:00 nach dem Journey-Gate |

**B2 messbar machen:** Das Kit hat zu jedem Plan das echte `building.json`. Drei dev-`floor_*_plain.png` rekonstruieren und Raumzahl, Flächen-IoU und Türgraph vergleichen. Die PNGs haben keinen Maßstab, also fragt der Agent ihn ab. SVGs sind Matplotlib-Exporte mit Raum-Polygonen als `<path>` und lassen sich fast exakt einlesen.

---

## 8. UX B – Handy

### Basis (Rang 4, beide Geräte)

**Auf Basis von `web/mobile`:** Route-Banner, Minimap, Kamera-Steuerung und Agent-Dock mit Blobatar bleiben, ebenso die Regeln aus `DESIGN.md`. Die Demo-Daten des Prototyps werden durch Tour, Manöver und Position aus der API ersetzt; der lokal geskriptete Chat durch den Voice-Navigator. Führungsart wählbar: **Karte**, **Wegbeschreibung**, **Kamera**.

`/go/{tour_id}` lädt die Tour. Turn-by-Turn mit Landmarken („after the press, turn left“), 2D-Karte mit Position, Fortschritt über „next“ (Stimme oder Button) oder den nächsten Positions-QR. Bei `building_changed` wird die aktive Tour neu berechnet, Ansage per `sendContextualUpdate` an den Agenten.

### Kamera (Rang 5, die Level-5-Erweiterung)

```
Positions-QR (URL oder Scan in der App) → Position in der Sitzung + sendContextualUpdate
        → Route/Tour vom Core (Polylinie + Manöver)
        ├─ navigator.xr.isSessionSupported('immersive-ar') → AR-Renderer (Android)
        └─ sonst                                          → Overlay-Renderer (iPhone)
```

**Android (AR):** three.js + WebXR `immersive-ar`, Features `local` (Pflicht), `hit-test` und `dom-overlay` (optional, für Anweisung und Mikrofon-Button). QR-Kamera (`getUserMedia`) **beenden, bevor** die XR-Session startet. Am QR stehend und auf ihn blickend entspricht der XR-Ursprung Marker-Position und -Richtung. Route als Linie knapp über dem Boden. Neu verankern: AR verlassen, nächsten QR scannen, AR neu starten.

**iPhone (Overlay):** Hintergrundvideo (`facingMode: "environment"`), darüber Pfeil zum nächsten Wegpunkt. Richtung relativ über `DeviceOrientationEvent` ab dem QR, **nicht** über den Kompass (in Stahlhallen unbrauchbar). `DeviceOrientationEvent.requestPermission()` braucht eine Nutzergeste. Keine Schrittzählung versprechen.

**Für beide:**
- QR in der App mit jsQR oder zxing-wasm (iOS Safari hat `BarcodeDetector` standardmäßig aus).
- `building.json` hat keine Nordrichtung; die Blickrichtung kommt vom Marker (an einer Wand mit bekannter Ausrichtung).
- **Eine** Transformationsfunktion: Gebäude (x rechts, y oben, Meter) → WebXR (x rechts, y oben, −z vorwärts): Gebäude-y wird −z, dazu die Drehung aus dem Marker. Mit Tests.
- Ein Button „Start navigation“ fragt Kamera, Mikrofon, Bewegung (iOS) und WebXR (Android) in einer Geste ab. Bei Ablehnung bleibt die 2D-Karte.
- Positions-QR mindestens 10–15 cm groß.
- Die Linie kommt aus den **Wegpunkten der Gehwege** (K1), also 15 cm von der Wand und um Ecken herum. Bis K1 sie liefert, zeigt die Kamera nur Räume ohne Ecken; eine gerade Linie von Tür zu Tür würde in L-Räumen durch Wände gehen.

**Upgrade (Kann, X6):** visuelle Ortung ohne QR mit hloc und MegaLoc als eigener Python-Dienst, nach Lenards Offline-Test (ein Foto fand das passende Videobild, 1,2 s auf der CPU). Es fehlt die Zuordnung der Referenzbilder zu Grundriss-Koordinaten. Nur wenn das bis zum Journey-Gate (01:00) im Hero-Gebäude funktioniert; sonst bleibt der QR-Anker. Zwischen zwei Ortungen braucht es weiter WebXR für die Bewegung.

---

## 9. Voice-LLM: Entscheidung nach Messung

Verfügbar im ElevenLabs-Agent u. a. Claude Sonnet 5.5 und Opus 5.5, Gemini-Flash-Familie, GPT-6.x, von ElevenLabs gehostet Qwen3.5-397B-A17B (bisheriger Standard) und GLM 5.2. Die Docs nennen keine Zahlen zur Tool-Call-Zuverlässigkeit und empfehlen, selbst zu messen. Alle anderen Agent-Einstellungen bleiben beim Test gleich.

**Start: Claude Sonnet 5.5, niedriger Reasoning-Aufwand, Backup-LLM aktiv.** **A/B-Test** (max. 30 min, direkt nach dem ersten Voice-Durchstich) gegen Qwen3.5 und ein Gemini-Flash-Modell:

| # | Äußerung | erwartet |
|---|---|---|
| 1 | „Where is the 3D printer?“ | `find`, Ort nennen und zeigen |
| 2 | „I need these five parts: …“ | `plan_tour`, Reihenfolge nennen |
| 3 | „Take me there without stairs.“ | `route` mit `step_free`, Start aus der Sitzung |
| 4 | „Go to the press.“ (drei Pressen) | genau eine Rückfrage |
| 5 | „Next.“ | `next_step` |
| 6 | „Where is the coffee machine?“ (gibt es nicht) | sagt, dass es keine gibt |
| 7 | Unterbrechung mitten in einer Ansage | hört auf, reagiert auf das Neue |
| 8 | Admin: „Close the east lift.“ | `propose_edit`, Vorschau, wartet |
| 9 | „Yes.“ | `commit_edit` genau einmal |
| 10 | Route ohne Lösung | sagt klar: keine Route |

**Regel:** Sonnet 5.5 bleibt, außer ein anderes Modell löst mehr Fälle oder ist bei gleicher Trefferzahl mehr als 0,5 s früher am ersten Wort. Der Navigator darf allein wechseln, wenn nur dort Latenz das Problem ist. Ergebnis in die Agent-Config eintragen. Abrechnung über ElevenLabs-Credits, nicht über das Anthropic-Guthaben.

---

## 10. Rollen und Arbeitspakete

**Builder** laut `HagenFinalPrompt.md` §7. Integrationsverantwortlicher: **Manuel's codex**, Vertretung: **Lenard's codex**.

| Builder | Titel | Pakete |
|---|---|---|
| Hagen's codex | Core & Spatial Intelligence Lead | K1, K2, X2 (Daten), X5 |
| Lenard's codex | Agent & Evaluation Lead | K3, Auflösung (`resolve`), Textchat-Agent, Voice-Prompts und A/B-Test |
| Manuel's codex | Platform & Live Integration Lead | W0, S1, V1 (Brücke), X0, X1, X3 (Backend), Integration, R1 |
| Manuel's Claude | Experience & Frontend Lead | W1, W2 (inkl. Kamera-Oberfläche), X3 (Oberfläche), X4, D1 |

| Paket | Builder | Inhalt | Abhängig von | Fertig, wenn |
|---|---|---|---|---|
| **W0 Setup** | Manuel's codex | Struktur aus Abschnitt 4, uv, Bun-Workspace, Dockerfile, Railway-Service + Volume + Variablen, `AGENTS.md`, `.env.example`, Branch-/Worktree-Schema | – | Railway-URL liefert `/health`; frischer Klon: `uv run pytest` läuft |
| **K1 Gebäude-DB + Routing** | Hagen's codex | Laden, Validieren, SQLite-Import, Vorberechnung (5.1) mit dem Routing-Code des Starters; **Wegpunkte der Gehwege**, Manöver mit Landmarken; Constraints inkl. Gabelstapler und kein Transit durch Produktion | W0 | **Warm-up-Oracle dev 369/369 aus der DB** (heute 369/369 mit dem Starter, das darf nicht sinken); `largest_room`, `floor_area_total`, `straight_line_3d`, `shared_walls_count`, `room_stacked` ≈ 100 % auf dev und train mit Gold-`inputs`; jede Polylinie liegt im Raum |
| **K2 Abfragen** | Hagen's codex | `errand`, `wide_delivery_count`, `step_free_reachable_count`, `what_if_door` (Wandmitte), `locate`, `count`, `route`, `tour`, `plan_tour` | K1 | 4 Graph-Arten ≈ 100 % auf dev mit Gold-`inputs` |
| **K3 Benchmark-Agent** | Lenard's codex | `resolve`, `bench.agent:answer`, `submit_answer`, Serializer, Runner, Checkpoints, Kostenlog, `BENCHMARK.md`, Sonntagsadapter | K1, K2 (gegen Fixtures schon vorher) | **M1:** 145 Zeilen, Format automatisch geprüft, offizieller dev-Score pro Typ end to end aus Fragetexten, committed |
| **S1 Server** | Manuel's codex | API aus 6.4, Sessions, Event-Log, Proposal/Commit/Undo, WebSocket, Voice-Token, Textchat-Endpunkt | W0, K1 | API-Tests; zwei Browser synchron; Neustart ohne Zustandsverlust |
| **V1 Voice** | Manuel's codex (Prompts: Lenard's codex) | Zwei Agents laut Config, Client-Tools im Web, A/B-Test | S1 | 10 Äußerungen aus Abschnitt 9 bestehen mit dem gewählten Modell |
| **W1 Desktop** | Manuel's Claude | 2D-Karte, Teileliste, `find`, `plan_tour`, Übergabe-QR, animierte Route, Panel „How I calculated this“ | S1 (vorher gegen Fixtures) | Aha 1 auf der Railway-URL unter 3 s |
| **W2 Handy** | Manuel's Claude | Auf Basis von `web/mobile`: `/go/{tour}`, Route-Banner mit echten Manövern, Minimap mit echter Etage, Live-Reroute mit Hinweis, Voice statt Demo-Chat, Führungsart Karte/Wegbeschreibung/Kamera | W1, S1 | Aha 2 (ohne Kamera) und Aha 3 auf Android und iPhone |
| **X0 Geräte-Gate** | Manuel's codex | Kamera + Mikrofon gleichzeitig, QR-Scan, `immersive-ar` auf Android | W0 | Ergebnis im `STATUS.md`, AR-Pfad entschieden |
| **X1 Kamera** | Manuel's codex | Marker-Modell, Transformation, AR-Renderer, Overlay-Renderer; Kamera-Lebenszyklus (`useCamera`) aus dem Prototyp wiederverwenden | X0, S1 (Marker), K1 (Wegpunkte) | Aha 2 mit Kamera im Hero-Gebäude auf beiden Handys |
| **X2 Hero-Gebäude** | Hagen's codex + Menschen vor Ort | Ausschnitt des Arbeitsorts von Hand als `building.json`. **Echte Objekte vor Ort als Assets** (z. B. Drucker, Werkzeugschrank). **Mindestens zwei Wege zum Ziel**, damit eine Sperrung sichtbar umleitet; ideal Lift und Treppe. Marker drucken und aufhängen | W0 | Gebäude lädt, QR hängen, alle drei Aha-Momente sind darin spielbar |
| **X3 Admin** | Manuel's codex + Manuel's Claude | B3a mit Voice (`propose_edit` „close“, `commit_edit`, `undo`) sofort; danach B4, B3b | S1 | Aha 3: Sperren am Laptop wirkt live auf dem Handy |
| **X4 3D** | Manuel's Claude | 3D-Desktop; simulierte `move_asset`-Events erst nach dem Journey-Gate | W1 | Aha 1 und Bonus in 3D stabil |
| **D1 Demo-Härtung** | Manuel's Claude + Manuel's codex | Demo-Modus (`/desk?demo=hero`: Hero-Gebäude, feste Startposition, vorbereitete Teileliste), Button „Reset demo“ (alle Events zurück), Handy-Spiegelung auf den Laptop, Hotspot als Netz-Reserve, Backup-Video, Sprechtext | X2, W1, W2 | alle drei Aha-Momente zweimal hintereinander ohne Eingriff, mit Stoppuhr innerhalb der Ziele |
| **X5 Bildimport** | Hagen's codex, nach dem Journey-Gate | B2 mit Messung | B1 | Messung von drei dev-PNGs liegt vor, sonst gestrichen |
| **X6 Visuelle Ortung** | offen (Lenard hat den Test gebaut) | hloc/MegaLoc-Dienst in Python, Referenzbilder des Hero-Gebäudes, Zuordnung zu Grundriss-Koordinaten | X2, X1 | bis zum Journey-Gate eine Position im Hero-Gebäude, die auf der Karte sichtbar stimmt; sonst gestrichen |
| **R1 Abgabe** | Manuel's codex + alle (Benchmark-Teil: Lenard's codex) | zwei 1-Minuten-Videos, technische Erklärung, README mit lokalem Start, `BENCHMARK.md`, Antworten, Agent-Config-Export ohne Secrets, öffentliche URL, Frischklon-Probe | alles | Abgabe-Checkliste (Abschnitt 13) erfüllt |

**Parallel ab Start:** W0, K1, K3 (gegen Fixtures), W1/W2 (gegen Fixtures aus 6.4), X0, X2. Fixtures sind als solche markiert und werden ersetzt, sobald S1 und K2 liefern.

---

## 11. Gates und Zeitplan

| Wann | Gate | Bei Fehlschlag |
|---|---|---|
Stand 20:05: Noch kein Produktcode im Repo außer Kit und `web/mobile`. Die Zeiten gelten ab dem Start der Builder (Ziel ≈20:30). Verschiebt sich der Start, rutschen alle Gates bis zum Journey-Gate mit; die Zeiten ab Sonntag 07:00 bleiben fest.

| Wann | Gate | Bei Fehlschlag |
|---|---|---|
| **≈21:15** | W0: Railway-URL mit `/health` und einem echten Tool-Aufruf | lokal weiterarbeiten; kein Hosting-Wechsel |
| **≈21:30** | X0: Geräte-Gate auf beiden Handys | Android-AR scheitert → beide im Overlay-Modus; Audio-Konflikt → Kopfhörer |
| **≈21:45** | K1 grün: Warm-up-Oracle 369/369 aus der DB (Routing-Code des Starters übernommen) | alle Kür pausieren, Core hat Vorrang |
| ≈22:00 | Integration: Voice → Tool → Karte; danach A/B-Test | Textchat als Fallback |
| ≈23:00 | **Aha-3-Probe lokal:** Laptop sperrt per Stimme, Handy routet in < 2 s um | Reroute-Pfad vor allem anderen reparieren |
| ≈23:30 | **M1** (K3) | Lücken offen ausweisen, keine Platzhalter |
| ≈23:30 | X2: Hero-Gebäude angelegt, QR hängen | Ausschnitt verkleinern |
| **01:00** | **Journey-Gate: erster Durchlauf aller drei Aha-Momente** im Hero-Gebäude auf der Railway-URL, beide Handys, mit Stoppuhr | danach keine neue Infrastruktur; was das Ziel verfehlt, wird zuerst repariert |
| 01:00–03:00 | X5 Import-Spike (Hagen's codex), Regression auf dev, Rohschnitt | X5 entfällt |
| 03:00–07:00 | Schlafen | – |
| So 07:00–09:00 | Frischklon-Probe, ein dev-Gebäude wie ein unbekanntes durchlaufen lassen, finale Test-CSV. **08:00 Generalprobe:** Pitch mit Timer und Handy-Spiegelung (D1); danach Demo-Video bei Tageslicht aufnehmen (Android-AR) | Backup-Video statt Live-Demo |
| ab 09:00 | Eine Person in Bereitschaft für das Sonntagsgebäude; Lauf sofort nach Veröffentlichung | – |
| **10:00** | Feature Freeze. Ausnahme: Sonntagsformat und Datenadapter | – |
| 12:00–13:00 | Nur Abschlusslauf, Upload, Abgabe prüfen | – |

---

## 12. Scope

Jede Zeile dient den Benchmark-Punkten oder einem Aha-Moment. Was keinem dient, steht nicht im Plan.

| Rang | Inhalt | Status | dient |
|---|---|---|---|
| 1 | K1, K2: Core, Gebäude-DB, Routing | Pflicht | 55 Punkte; die Wegpunkte aus K1 auch Aha 2 (Linie bleibt im Raum) |
| 2 | K3: M1 und Sonntagsadapter | Pflicht, wird nie gefährdet | 55 Punkte |
| 3 | V1: Voice-Navigator | Pflicht | Aha 1–3, Interaktion |
| 4 | W1, W2, X2, X3 (B3a mit Voice), D1 | Pflicht | Aha 1–3 |
| 5 | X0, X1: Kamera | Level-5-Erweiterung | Aha 2 |
| 6 | X4: 3D | Soll | Aha 1 und Bonus als Bild |
| 7 | X6 visuelle Ortung (Gate 01:00); nach 01:00: simulierte Bewegung, Mock-Präsenz, X3 Rest | Kann | Aha 2 ohne QR; Lebendigkeit; Admin |
| 8 | X5: Bildimport | Kann, ausdrücklich versuchen | Rubrik, Pitch-Satz „upload the floor plan“ |
| – | Gabelstapler-**Demo**, Custom-LLM-Endpoint, gebäudeübergreifend, What-if-Heatmap, weitere Personas | gestrichen | – |

Die Gabelstapler-**Constraints** bleiben im Core (K1): Die Route-Spec nennt sie als Regel für bewertete Routenfragen; in Kit 1.1.0 kommen sie in den Fragen nicht vor, für Sonntag sind sie nicht ausgeschlossen.

**Streichreihenfolge:** X5 → Rang 7 → X4 → iPhone-Overlay → Android-AR. Ränge 1–4 bleiben; ohne Kamera tragen Aha 1 und 3 die Demo allein.

---

## 13. Demo, Pitch und Abgabe

Laut Kickoff-Folie 32: ein 1-Minuten-Demo-Video, ein 1-Minuten-Technikvideo; im Finale 3 Minuten Pitch plus 1 Minute Q&A. Alle Szenen spielen im **Hero-Gebäude** (X2).

### Demo-Video (60 s)

| Zeit | Szene | Aha |
|---|---|---|
| 0–8 s | Person in einer fremden Halle: „New here. I need five parts.“ | Problem |
| 8–25 s | Desktop: „I need the filament, the torque wrench and the steel drum.“ Teile leuchten auf, Reihenfolge, animierte Route, Übergabe-QR | 1 |
| 25–42 s | Android: QR scannen, Tour startet, Linie im Kamerabild auf dem Boden: „After the column, turn right.“ | 2 |
| 42–55 s | Laptop: „Close the east lift.“ – „Yes.“ Handy mitten auf dem Weg: „The east lift is closed. I'll take you via the stairs.“ Neue Linie | 3 |
| 55–60 s | Abschlusssatz und Produktname | – |

### Technikvideo (60 s)

Architektur in einem Bild (Railway, Gebäude-DB, Core, zwei Agents). Bonus „It understands space“ mit dem Panel „How I calculated this“. Benchmark: dev-Score pro Frageart und Kosten pro Frage, gemessen. Kurz der iPhone-Modus. Import-Messung, falls X5 steht.

### Finale (3 min + 1 min Q&A)

| Zeit | Inhalt |
|---|---|
| 0:00–0:20 | Problem in einem Satz, aus Sicht der Persona |
| 0:20–1:50 | **Live:** Aha 1 → Aha 2 (Übergabe, 2D) → Aha 3. Kamera-AR als kurzer Videoclip, nicht live auf der Bühne |
| 1:50–2:30 | Wie es funktioniert: „The LLM interprets, the rules decide.“ Ein Architekturbild, dev-Score, Kosten pro Frage |
| 2:30–3:00 | Warum es zählt: neues Gebäude aus dem Floorplan in Minuten (wenn X5 steht), nächste Schritte |

**Q&A vorbereiten:** Woher weiß die App, wo ich bin (QR-Anker, AR-Tracking, kein WLAN nötig)? Wie genau sind die Routen (Referenzmodell exakt, 369/369, dev-Score)? Was passiert mit einem neuen Gebäude? Was kostet eine Frage, wie schnell ist die Antwort (gemessene Zahlen)?

### Live-Setup und Absicherung (D1)

- **Beide Bildschirme sichtbar:** Laptop am Beamer; daneben das gespiegelte Handy (Android über `scrcpy` per USB, iPhone über QuickTime-Filmaufnahme per Kabel). Ton der Handy-Stimme vorher am Beamer testen.
- **Demo-Modus:** `/desk?demo=hero` lädt Hero-Gebäude, Startposition und Teileliste. Vor jedem Durchlauf „Reset demo“.
- **Netz:** WLAN vor Ort, Handy-Hotspot als Reserve. Railway vorher aufgewärmt; nach der Generalprobe kein Deploy mehr.
- **Rückfallstufen:** Voice fällt aus → dieselben Sätze in den Textchat tippen. Handy fällt aus → `/go/{tour}` im Laptop-Browser zeigen. Alles fällt aus → Backup-Video.

**Abgabe-Checkliste:**
- Test-CSV: genau die 145 IDs, nur `question_id,answer`, UTF-8, ≤ 5 MB, keine leeren Antworten, automatisch geprüft
- Sonntagsantworten im bestätigten Format
- `BENCHMARK.md` mit genau dem getesteten Befehl, Keys, Versionen, Grenzen
- README mit lokalem Start (`uv sync`, `bun install` in `web/`, `.env.example`), öffentliche URL
- Agent-Konfiguration exportiert, ohne Secrets
- Beide Videos, Architektur-Erklärung; altes Architekturbild als „initialer Entwurf“ markiert
- Frischklon-Probe mit Datum

---

## 14. Risiken

| Risiko | Wirkung | Gegenmaßnahme |
|---|---|---|
| Sonntagsformat unklar (PDF: `answers.json`, README: CSV) | ungültige Abgabe | Adapter austauschbar, beide Formate; Jurorenfrage 2 |
| Sonntag weicht doch vom Kit-1.1.0-Modell ab | falsche Längen | Profil versioniert (`kit_1_1_0`), Wahl im Code; Kit sagt: auch die verdeckten Antworten nutzen 1.1.0 |
| Kamera + Mikrofon auf dem iPhone | leise oder falsche Tonausgabe | Geräte-Gate (X0); Kopfhörer |
| WebXR auf dem Android-Gerät nicht verfügbar | keine AR-Szene | Overlay-Modus auf beiden |
| Railway-Redeploy mit Downtime | Abbruch in der Demo | kein Deploy während Aufnahme; Auto-Reconnect |
| Zählsemantik „Raum“ unklar | Zählfragen falsch | aus dev ableiten, Tests |
| Gabelstapler-Felder fehlen in den Daten | ungültige Fahrzeugrouten | Jurorenfrage 6; Demo gestrichen |
| Credits (600 vs. 150 USD), Rate Limits | Läufe brechen ab | Console prüfen; Checkpoints; Kosten pro Frage messen |
| Live-Demo scheitert (Netz, Mikrofon, Licht) | Aha-Moment verpufft auf der Bühne | Demo-Modus mit Reset, Hotspot, Textchat-Rückfall, Backup-Video; AR nur als Clip |
| Publikum sieht das Handy nicht | Aha 2 und 3 unsichtbar | Handy-Spiegelung (D1), in der Generalprobe getestet |
| Aha-Moment zu langsam | Wirkung weg | Ziel-Latenzen aus 1.2 bei jedem Gate stoppen; Reparatur vor neuen Features |
| `PLAN.md` nennt noch TypeScript-Core und Cloudflare-Reste | Agenten folgen der falschen Quelle | Aufteilung entschieden: Python hinten, TypeScript vorne (Abschnitt 2); Lenard informieren; Quellenrang in `AGENTS.md`; Master-Agent übernimmt die Entscheidung in `master prompt/` |
| Master-Agent aus `HagenFinalPrompt.md` entscheidet anders als dieses Dokument | Planwechsel mitten in der Nacht | dieses Dokument als Eingabe übergeben; Teamentscheidungen aus Abschnitt 2 dort als menschliche Vorgaben nennen |
| Entscheidungen aus Transkripten | Missverständnisse | Plan nach dem Hochladen gemeinsam lesen |

---

## 15. Offen

1. **Lenard informieren:** Backend und Core in Python, Frontend in TypeScript; der TypeScript-Core aus `PLAN.md` entfällt. `PLAN.md` angleichen oder als überholt markieren.
2. **Master-Agent starten** mit `HagenFinalPrompt.md` und diesem Dokument als Eingabe. Die Teamentscheidungen aus Abschnitt 2 dort als feste menschliche Vorgaben nennen, damit sie nicht neu verhandelt werden.
3. **Hero-Gebäude:** Welcher Ausschnitt des Arbeitsorts? Er braucht zwei Wege zum Ziel, ideal Lift und Treppe, und echte Objekte als Teile.
4. **Produktname** und ein Abschlusssatz für Video und Pitch.
5. **Jurorenfragen** 2–6 aus `open questions for judge .md` (Frage 1 ist durch Kit 1.1.0 beantwortet), dazu:
   - zu Frage 4: „Wird für ‚correct buildings built from plans‘ ein Planbild ohne JSON geliefert? Welches Format, mit oder ohne Maßstab?“
   - zu Frage 10: „Zählt eine AR-Navigation mit QR-Verankerung, die wir im eigenen Gebäude im Video zeigen, als Level-5-Erweiterung, auch wenn ihr sie nicht live testet?“

---

## Anhang A: Befunde und Begründungen

**A.1 Warum der Bildimport bleibt.** Das Challenge-PDF (S. 3) nennt unter „Does it work“ (55 Punkte) ausdrücklich „correct buildings built from plans“. Der Lead hat lokale Änderungen betont und gesagt, ein kompletter Neuaufbau sei nicht unbedingt nötig. Wie viel der Import wiegt, ist offen (Jurorenfrage 4). Ganz zu streichen wäre eine Wette gegen den schriftlichen Text; deshalb ein begrenzter, messbarer Versuch.

**A.2 Befunde aus den Daten** (an `proc-factory-dev-003` und den Fragedateien geprüft):
- PNGs ohne Maßstab und Achsen; Raumnummern im Bild, Türen als Punkte, Eingänge als rote Dreiecke.
- SVGs sind Matplotlib-Exporte: Räume als `<path>`-Polygone, Füllfarbe je Raumtyp, Text nur als Glyphen.
- Kit-Gebäude sind nicht begehbar; der Arbeitsort ist nicht im Datensatz. Darum das handgebaute Hero-Gebäude.
- Eingabefelder je Frageart sind in train und dev einheitlich (Tabelle 5.2). `errand` erlaubt immer Treppen, `wide_delivery_count` ist immer stufenlos mit 1,0 oder 1,1 m.
- Seit Kit 1.1.0 gibt es keinen Weg außen herum mehr; 112 Warm-up-Routen und Touren sind `reachable: false`. `space_path` listet jeden durchquerten Raum, `element_path` jede Öffnung, Treppe und jeden Lift einmal.

**A.3 Warum Python im Core (entschieden).** Der Grund für „nur TypeScript“ war, auf Cloudflare keinen Python-Container zu brauchen. Mit Railway entfällt er. Seit Kit 1.1.0 ist das bewertete Routenmodell ein Sichtbarkeitsgraph auf `buffer(-0.15)` mit 30-cm-Türlandung, Abdeckungsprüfung über `buffer(0.02)` und `representative_point` als Raummittelpunkt – alles shapely. Der Kit-Starter setzt genau das in Python um; am 24.10. um 20:00 lokal geprüft: Warm-up-Oracle dev **369/369** in ca. 13 s. Dazu kommen 0,35-m-Wandtoleranz und Schnittflächen für die Geometrie-Fragen (der Codex-Check bestätigte drei Geometrie-Fragetypen mit 64/64 dev und 243/243 train; diese Antworten hat Kit 1.1.0 nicht verändert). Bei `errand` zählt 1 %, bei `what_if_door` die Grenze „mehr als 1 m“. Ein TypeScript-Nachbau müsste diese Geometrie erst wieder exakt erreichen.

**A.4 Geprüfte Plattformfakten.** iOS Safari: kein WebXR `immersive-ar`, `BarcodeDetector` standardmäßig aus. Android Chrome: `immersive-ar` über ARCore mit Hit-Test und Anchors. ElevenLabs: Conversation Token für WebRTC (`/v1/convai/conversation/token`), Signed URL für WebSocket; Hooks im `ConversationProvider`; Client-Tools brauchen „Wait for response“; `sendContextualUpdate` löst keine Antwort aus. Railway: keine Replicas mit Volume, kurze Downtime beim Redeploy. Anthropic-Preise: Sonnet 5.5 2/10 USD pro MTok, Cache-Read 0,20; Haiku 5.5 0,10/0,50; Opus 5.5 4/20.

---

## Anhang B: Einordnung der `PLAN.md`-Fassungen

**Fassung 16:38 (Cloudflare mit Python-Container):** Kamera und AR „bewusst nicht im Stack“, Bildimport als Kür zuerst gestrichen, Voice über signierte URL. Durch Railway und dieses Dokument ersetzt; fachliche Teile (Prompt-Regeln, Budget, Lizenzen) gelten weiter.

**Fassung `ef84a9d` (Lenard, 18:23):** baut auf der Fassung 16:38 auf, nicht auf Review 1 oder 2.

| Änderung | Einordnung |
|---|---|
| Cloudflare Worker, Durable Object, D1 | verworfen: Railway |
| Nur JSON, kein Bildimport | verworfen: X5 mit Timebox (A.1) |
| Keine Mobile-Ansicht, kein QR, keine Kamera, kein AR | verworfen: Teil der Journey und Level-5-Erweiterung |
| Alles in TypeScript | verworfen für Core, Server, Benchmark (A.3); TypeScript im Frontend |
| Vorberechnete Gebäude-DB als Startpunkt | **übernommen**, in Python (5.1) |
| Tool Runner des Anthropic SDK statt Agent SDK | **übernommen**, in Python |
| Kosten pro Frage messen, Haiku zuerst | **übernommen** |
| Benchmark als Agent mit Tools | **übernommen mit Auflage:** `submit_answer` + Serializer (6.1) |
| Keine Gebäudedaten im Prompt | **übernommen** |
| `AGENTS.md` in P0 | **übernommen** (Abschnitt 4) |

Falls schon TypeScript-Code für Core oder DB existiert: vor dem Verwerfen ansehen, was sich ins Frontend übernehmen lässt.

**Fassung `2ab5974` (Lenard, 19:13):** Das Team läuft zusammen.

| Änderung | Einordnung |
|---|---|
| Railway, ein Service, SQLite auf dem Volume `/state`, Railway-Grenzen | **übereinstimmend** |
| Reihenfolge Datenbank → Agent → Voice und UI parallel | **übereinstimmend** (Abschnitt 12) |
| Zwei Web-Apps, Handy und Desktop, keine nativen Apps | **übereinstimmend** (`web/mobile`, `web/desk`) |
| QR-Code vom Desktop zum Handy | **übereinstimmend** (Übergabe-QR) |
| QR „nicht zur Ortung“ | **abweichend:** Positions-QR bleibt die robuste Basis; visuelle Ortung ist X6 |
| AR über hloc/MegaLoc als eigener Python-Dienst | **übernommen als X6**, mit Journey-Gate |
| Führungsart wählbar: Karte, Wegbeschreibung, AR | **übernommen** (Abschnitt 8) |
| Desktop mit Mock-Präsenz anderer Nutzer | **übernommen als Kann** (Rang 7), im Pitch nicht als echt darstellen |
| Core in TypeScript auf Node | **verworfen:** Core, Server und Benchmark in Python, TypeScript im Frontend (Abschnitt 2) |
| Kein Bildimport | **abweichend:** X5 mit Timebox (A.1) |
| Signierte URL, eine Agent-ID | **abweichend:** Conversation Token, zwei Agents (Agent-Config) |

**`AGENT_BUILD_SPEC.md` (magicj75):** Python, das Kit erweitern, deterministische Tools, Benchmark-Einstieg `answer(...)`, Selbstprüfung vor der Antwort. **Übereinstimmend** mit diesem Dokument und dient als Tool-Katalog (Abschnitt 5). Abweichungen: mehrere Gebäude (3.6) gestrichen; Build from plans (3.5) nur als X5.

**Nicht mehr nötig, nur zur Nachvollziehbarkeit – Kompromiss für einen TypeScript-Server:** Python macht Import und Vorberechnung in die SQLite-DB (Ankerpunkte, Flächen, Schwerpunkte, Nachbarschaft, Überdeckung, Wandmitten für neue Türen, Wege innerhalb der Räume) – exakt mit shapely. TypeScript liest die DB zur Laufzeit und rechnet nur noch Graphen (Dijkstra, Touren) auf vorberechneten Koordinaten; das ist in jeder Sprache exakt. Der Sonntagslauf ist dann `uv run …import` gefolgt vom Benchmark. Nachteil: zwei Laufzeiten im Image und ein Python-Schritt bei jedem neuen Gebäude.

**Fassung `a5656fe` (Lenard, 19:52) und Kit 1.1.0 (`4756739`):** ein Routenmodell für alle Antworten, neue train/dev-Antworten, Jurorenfrage 1 beantwortet, `docs/question-overview/` gelöscht (die Tool-Liste darin war auf das alte Modell bezogen). **Übereinstimmend** übernommen (Abschnitte 2 und 5.4). `PLAN.md` hält weiter am TypeScript-Core fest; das ist durch die Teamentscheidung für Python überholt.

**`HagenFinalPrompt.md` (`c2822f9`):** Auftrag an einen Master-Agenten, aus allen Quellen das Ausführungspaket `master prompt/` für vier Builder zu schreiben, mit eigener technischer Entscheidungshoheit. Dieses Dokument ist dafür vorbereitet: Hagens Journey (Abschnitt 1), Entscheidungen (2), Verträge (5, 6), Zuordnung zu den vier Buildern (4, 10), Gates (11), Abnahme (10, 13). **Wichtig für den Start:** Die Teamentscheidungen aus Abschnitt 2 – vor allem Railway und Python – sind menschliche Vorgaben und sollten dem Master-Agenten auch so übergeben werden.
