# Review: PLAN.md gegen die zwei User Experiences

**Stand:** Sa 24.10.2026, 18:50. **Eingearbeitet:** Teamgespräch von ca. 18:30 (Prioritäten und User Journey, Abschnitt 1) und Lenards Änderung an `PLAN.md` in `ef84a9d` (Abschnitt 14).
**Geprüft:** Team-Repo bis `ef84a9d` (inkl. `PLAN.md`, `codex reviewed plan suggestions .md`, `open questions for judge .md`, `2026-10-24-fragen-an-juroren.md`, Route-Spec, Lead-Q&A, Brainstorming-Transkript, Challenge-PDF, Kit-README, Daten, `docs/question-overview/`).
**Maßstab:** Der Plan ist die Grundlage für das gesamte Agentic Engineering. Agenten bauen, was dort steht, und nichts, was dort fehlt.

> **Verhältnis zu PLAN.md:** Dieses Review ist der finale Stand. Wo `PLAN.md` widerspricht – auch in der Fassung `ef84a9d` –, gelten dieses Review und [`docs/elevenlabs-agent-config.md`](docs/elevenlabs-agent-config.md). Alles andere aus `PLAN.md` gilt weiter.

**Zielbild (Vorgabe des Teams):**
- **UX A – Laptop/Browser:** Gebäude ansehen, Teile finden, Touren planen; Gebäude anlegen und ändern. Alles auch per Voice-Agent.
- **UX B – Smartphone:** Mit dem Handy durch Fabrik oder Gebäude laufen, live den Weg sehen (auch über die Kamera) und dabei mit dem Voice-Agent sprechen.

---

## 0. Urteil

Der fachliche Kern ist gut und bleibt: deterministischer Python-Core, derselbe Core für App und Benchmark, Client-Tools mit Backend-Brücke, Vorschau → Bestätigung → Undo, Benchmark ohne Voice und Cloud.

**Aber `PLAN.md` bildet die zwei User Experiences nur zur Hälfte ab:**

| | Zielbild | Was PLAN.md sagt | Folge |
|---|---|---|---|
| **UX B** | Handy mit Live-Weg, Kamera, Voice | Fassung 16:38: Kamera und AR „bewusst nicht im Wochenend-Stack“. Fassung `ef84a9d`: „Keine Mobile-App, kein QR-Code, keine Kamera, kein AR“ | Ohne dieses Review baut kein Agent die Handy-Navigation |
| **UX A** | Gebäude aus Floorplans anlegen | Fassung 16:38: Kür, als Erstes gestrichen. Fassung `ef84a9d`: „Einen Bildimport gibt es nicht“ | Laptop-UX schrumpft auf Ansehen und Sperren |

Die Abschnitte 1, 4, 5 und 7 schließen diese Lücken.

---

## 1. Teamgespräch (ca. 18:30): Reihenfolge und User Journey

Quelle ist ein automatisches Transkript. Das Team traut ihm selbst nicht ganz, deshalb stehen hier nur die klar erkennbaren Aussagen. Unklare Zahlen („50 %“, „26“ und „34 Tools“) sind bewusst nicht übernommen.

### 1.1 Reihenfolge

- **Kritischer Pfad ist die Submission:** die Antworten auf die Benchmark-Fragen. Sie tragen den Großteil der 55 Funktionspunkte.
- **Abgestimmte Reihenfolge:** 1. Datenbank/Core → 2. Agent, der die Submission erzeugt → 3. Voice-Agent → 4. UI/UX, dabei Handy vor Admin-Desktop.
- **Gleichzeitig gilt:** Der Benchmark allein gewinnt nichts. Interaktion (25), Kreativität (10) und Demo (10) entscheiden über das Finale.
- **Einigung:** Die Reihenfolge ist die **Priorität bei Konflikten**, gearbeitet wird **parallel**. Zwei Personen bleiben dauerhaft auf Core und Benchmark.
- **Tools sind die größte Lücke.** Der Starter hat sechs Tools (`building_overview`, `search_building`, `find_route`, `set_closed`, `add_door`, `show_route`) und schafft laut Kit-README unter 5 % auf dem Benchmark. Die Fragen-Taxonomie in [`docs/question-overview/`](docs/question-overview/README.md) schlägt 15 Tool-Verträge (T01–T15) für alle 15 Fragearten vor. Das ist der Tool-Backlog für den Core.

### 1.2 User Journey

Persona: Eine Person ist **neu im Gebäude** – oder das **Gebäude ist neu**.

1. **Desktop am Arbeitsplatz:** 3D-Ansicht der Fabrik, daneben die Teileliste. Ein Teil anklicken → sein Ort wird gezeigt. Teile bewegen sich live, weil jemand sie wegträgt oder ein Gabelstapler fährt.
2. **Mehrere Teile holen** (Kommissionierung, z. B. fünf Teile): auswählen → das System berechnet die **beste Reihenfolge** und die Route.
3. **QR-Code auf dem Bildschirm** → mit dem Handy scannen → die Tour ist auf dem Handy.
4. **Mit dem Handy laufen:** Teil 1, Teil 2, Teil 3 …
5. **Der Lift fällt aus** → die App bekommt es mit → neue Route, z. B. über die Mitteltreppe → Teil gefunden.
6. **Pitch-Rahmen:** Neues Gebäude gebaut → Floorplan hochladen → das Gebäude steht in Minuten, die Teile sind eingetragen.

### 1.3 Was die Journey für die Planung bedeutet

| Journey-Schritt | Umsetzung | Aufwand |
|---|---|---|
| Teileliste, Teil anklicken, Ort sehen | `find` und Liste aus dem Core; Hervorhebung auf der Karte | gering, gehört zur Basis |
| 3D-Ansicht am Desktop | **Wieder im Scope** (war gestrichen): Etagen aus den Polygonen extrudiert und gestapelt (react-three-fiber), Route als Linie. Erst nach der 2D-Karte; 2D bleibt der Fallback. `../repo/core/export3d.py` dient als Referenz | 2–3 h |
| Teile bewegen sich | Simulierte `move_asset`-Events über denselben Weg wie Admin-Änderungen. Das ist Belebung der Demo, **nicht** die Level-5-Erweiterung (die bleibt die Kamera) | ca. 1 h |
| Mehrere Teile, beste Reihenfolge | **Neues Core-Tool `plan_tour`:** bis 7 Ziele alle Reihenfolgen durchrechnen, darüber Nearest Neighbor + 2-opt. Ergebnis sind Teilstrecken mit Polylinien. Der Kit-Fragetyp `tour` (feste Reihenfolge) prüft die Teilstrecken | 2 h |
| QR auf dem Bildschirm → Handy | Der QR enthält eine URL `https://<app>/go/<tour_id>`. Die normale Kamera-App des Handys öffnet damit die Web-App mit geladener Tour, ein Scanner in der App ist dafür nicht nötig | ca. 1 h |
| Lift fällt aus → neue Route | Live-Reroute aus Abschnitt 7, ausgeweitet auf die Tour: restliche Stopps neu ordnen und neu routen, mit Ansage. Ausgelöst in der Demo vom Admin am Laptop oder über einen Simulations-Button | ca. 1 h |
| Floorplan hochladen | Import B2 (Abschnitt 4), mit Timebox | siehe dort |

**Zwei Arten von QR-Codes, nicht verwechseln:**
- **Übergabe-QR** auf dem Bildschirm: `…/go/<tour_id>`, bringt die Tour aufs Handy.
- **Positions-QR** an Türen und Eingängen: `…/m/<marker_id>`, sagt der App, wo man steht und wohin man blickt (Abschnitt 4).

Beide sind URLs. So öffnet schon die normale Kamera-App die Web-App an der richtigen Stelle. Der Scanner in der App wird nur für weitere Scans unterwegs gebraucht.

**„Desktop“ ist nicht gleich „Admin“.** Die Desktop-Ansicht der Journey (Teile finden, Tour planen, QR) gehört zur Navigation und hat Vorrang. Das Admin-Bearbeiten (Import, Maßstab, Türen) hat laut Teamgespräch die niedrigste Priorität. Für die Journey reicht vom Admin zunächst „Lift sperren“ und „Undo“.

---

## 2. Teamentscheidungen und verbleibende Widersprüche

| # | Thema | PLAN.md | Andere Quelle | **Gilt jetzt** |
|---|---|---|---|---|
| 1 | **Hosting** | 16:38 und `ef84a9d`: Cloudflare | Codex-Review: Railway | **Railway**, ein Service (Abschnitt 3) |
| 2 | **Sprache im Core** | `ef84a9d`: nur TypeScript | Review 2, Codex: Python-Core | **Python für Core, Server und Benchmark; TypeScript im Frontend** (Begründung in Abschnitt 14) |
| 3 | **Reihenfolge** | – | Teamgespräch | **Core/Datenbank → Agent/Submission → Voice → UI/UX**, parallel bearbeitet (Abschnitt 1.1) |
| 4 | **Testgeräte** | „Handy-Layout“ bzw. gestrichen | – | **Android und iPhone sind im Team vorhanden.** Beide werden unterstützt (Abschnitt 5) |
| 5 | **LLM im ElevenLabs-Agent** | eingebautes `claude-sonnet-5-5` | Dashboard-Standard bisher Qwen3.5-397B | **Das bessere nach Messung.** Start mit Claude Sonnet 5.5, A/B-Test entscheidet (Abschnitt 6) |
| 6 | **Voice-Auth** | „signierte URL“ (auch in `ef84a9d`) | ElevenLabs-Docs: Signed URL ist für **WebSocket**, für **WebRTC** braucht es einen **Conversation Token** | **WebRTC + Conversation Token**, Endpunkt `/api/voice/token` |
| 7 | **Sprache der Demo** | DE/EN | Agent-Config | **Englisch**, wie in der Agent-Config |
| 8 | **ElevenLabs-Einstellungen** | – | – | **[`docs/elevenlabs-agent-config.md`](docs/elevenlabs-agent-config.md) ist verbindlich** |
| 9 | **Cache-Preis** | Sonnet 5.5 Cache-Read 0,20 USD/MTok | Codex: 0,10 USD | **Plan hat recht.** Aktuell: Sonnet 5.5 2/10, Cache-Read 0,20; Haiku 5.5 0,10/0,50; Opus 5.5 4/20 |
| 10 | **Zeitplan** | feste Uhrzeiten ab 17:15 | – | ersetzt durch Abschnitt 10 |

---

## 3. Architektur auf Railway

Ein Service, ein Prozess, ein Docker-Image. Das ersetzt Worker, Hono, Durable Object, Container-Klasse, R2, D1 und Wrangler aus `PLAN.md`.

```
Laptop (UX A) ─┐                        ┌─ /                    SPA (Vite-Build, TypeScript)
Handy  (UX B) ─┼── HTTPS/WSS ── Railway FastAPI (Python) ─┼─ /api/*               Tools, Tour, Import, Edits, Chat
               │                        ├─ /api/voice/token     ElevenLabs Conversation Token (WebRTC)
               │                        ├─ /ws/buildings/{id}   building_changed an alle Clients
               │                        └─ /health
               └── Audio (WebRTC) ── ElevenLabs Agent ── Client-Tools laufen im Browser → /api/*
Volume /state:   SQLite (Gebäude-DB, Events, Proposals, Marker, Touren) + Uploads (Planbilder)
Image  /app/data: Kit-Gebäude (nur building.json + equipment.csv)
Benchmark: lokal, ohne Railway und ohne ElevenLabs, derselbe core/ und dieselbe Gebäude-DB
```

**Gebäude-DB (Lenards Idee, im Teamgespräch als Startpunkt gesetzt, in Python umgesetzt):**
- Ein Import-Schritt liest `building.json` und schreibt SQLite (Python-Standardbibliothek `sqlite3`): Basistabellen wie im JSON plus **vorberechnete Werte** – Fläche, Schwerpunkt und Ankerpunkt pro Raum (mit shapely, also exakt wie das Referenzmodell), gemeinsame Wandlänge (`space_adjacency`, Regel 0,35 m / 1 m), Raum darüber und darunter (`space_stacking`), Weg zum nächsten Eingang.
- **Ein Schreibweg:** Import und Änderungen laufen durch denselben Code; bei einer Änderung werden nur betroffene Werte neu berechnet.
- Benchmark, Server und Tests nutzen **dieselbe** DB-Schicht. Antworten aus `questions*.jsonl` kommen nie in die DB.
- Routen mit Bedingungen (Türbreite, Sperrung, neue Tür) und Touren rechnen Tools zur Laufzeit.

**Festlegungen:**
- **Dockerfile mehrstufig:** Node baut `web/`, dann `python:3.12-slim` mit `core/`, `server/`, `data/` und dem `dist`. Build-Kontext ist die Repo-Wurzel. `uvicorn server.app:app --host 0.0.0.0 --port $PORT`, **ein** Worker.
- **Routenreihenfolge:** `/api`, `/ws`, `/health` vor dem SPA-Fallback.
- **Gemeinsame Typen:** Die TypeScript-Typen im Frontend werden aus dem OpenAPI-Schema von FastAPI erzeugt.
- **Secrets als Railway-Variablen:** `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID_NAVIGATOR`, `ELEVENLABS_AGENT_ID_ADMIN`. Der Browser sieht nur Agent-IDs und den kurzlebigen Token.
- **Volume:** auf `/state`, nicht über `/app/data`. Initialisierung beim Start, nicht beim Build.
- **Grenzen von Railway (geprüft):** Mit Volume sind **keine Replicas** möglich, und ein **Redeploy hat kurze Downtime**. Folgen: kein Deploy während Aufnahme oder Demo; der Client verbindet den WebSocket automatisch neu und lädt danach den Snapshot. App-Sleeping ausschalten.
- **Zustandsvertrag** (aus Codex §6): unveränderliche Basisdaten plus Event-Log; `proposal_id` mit `expected_version`; `commit` idempotent über `operation_id`; Undo als neues Event; jedes Tool-Ergebnis trägt Gebäudeversion und Request-ID, verspätete Antworten überschreiben keine neueren.
- **Rechenlast:** Geometrie und Routing im Threadpool (synchrone `def`-Endpunkte), damit WebSocket und Voice-Tools nicht blockieren. Kein Vorberechnen aller 280 Gebäude beim Start.
- **Handy-Tests brauchen HTTPS.** Kamera, Mikrofon und WebXR laufen nur im Secure Context. Wege: Railway-URL (eigene Dev-Umgebung), auf Android USB-Debugging mit Port-Forwarding (`localhost` gilt als sicher), auf dem iPhone nur Railway oder ein HTTPS-Tunnel.

---

## 4. UX A – Laptop: ansehen, planen, anlegen

### Desktop-Ansicht (Navigation, hohe Priorität)

Teileliste, Suche, Ort auf der Karte, Tour planen, Übergabe-QR. 2D zuerst, dann 3D (Abschnitt 1.3). Voice über den Navigator-Agent.

### Admin (niedrigste Priorität laut Teamgespräch)

**Warum der Import trotzdem im Plan bleibt:**
- Das Challenge-PDF (S. 3) nennt unter „Does it work“ (55 Punkte) ausdrücklich „correct buildings built from plans“. Wie viel das wiegt und wie es geprüft wird, ist offen (Jurorenfrage 4). „Gibt es nicht“ wäre eine Wette gegen den schriftlichen Text.
- Die Journey endet im Pitch mit „Floorplan hochladen, Gebäude steht“.

**Befunde aus den Daten (geprüft an `proc-factory-dev-003`):**
- Die **PNGs haben keinen Maßstab und keine Achsen**. Raumnummern stehen im Bild, Türen sind kleine Punkte, Eingänge rote Dreiecke. Den Maßstab muss das System **im Gespräch erfragen**. Genau das ist „Build … by conversation“.
- Die **SVGs sind Matplotlib-Exporte**: Räume sind `<path>`-Polygone mit Füllfarbe je Raumtyp, Texte nur als Glyphen. Ein SVG-Import liefert die Polygone fast exakt, ein PNG-Import braucht Vision.
- **Das Kit enthält 280 Paare aus Plan und `building.json`.** Damit lässt sich ein Importer messen: dev-`floor_*_plain.png` rekonstruieren und Raumzahl, Flächen-IoU und Türgraph gegen das echte JSON vergleichen.

| Stufe | Inhalt | Priorität |
|---|---|---|
| **B1** | `building.json` hochladen → Validator → sofort darstellen → alle Tools funktionieren darauf. Gleicher Pfad wie das Sonntagsgebäude | Pflicht (Teil von Core/Benchmark) |
| **B3** | Lokale Änderungen mit Vorschau, Bestätigung, Undo: Sperrung, Tür, Asset verschieben | „Lift sperren“ + Undo sind Pflicht für die Journey; der Rest danach |
| **B4** | **Positions-QR erzeugen:** pro Eingang und wichtiger Tür ein Blatt mit `marker_id`, Etage, Position und Blickrichtung | Pflicht für die Kamera |
| **B2** | Plan-Bild (PNG/JPG, auch Foto eines Fluchtplans) → Claude Vision → Entwurf im Kit-Format → Validator → Overlay-Vorschau → Korrektur per Voice oder Klick → speichern | **Timebox 3 h**, nach dem 00:30-Gate |

**Fallback für B2:** Das Demo-Gebäude für den Kamera-Walk wird **ohnehin früh von Hand** als kleiner JSON-Ausschnitt angelegt (Abschnitt 10). Damit hängt die Kamera-Demo nicht am Import. Scheitert B2, wird im Video nichts als „importiert“ gezeigt, was angelegt wurde.

---

## 5. UX B – Smartphone: Tour, Live-Weg, Kamera, Voice (Android und iPhone)

### Basis (vor der Kamera)

Tour vom Übergabe-QR laden, Turn-by-Turn mit Landmarken, 2D-Karte mit „Du bist hier“, Voice-Navigator, Live-Reroute bei Liftausfall. Das ist die Journey ohne Kamera und läuft auf beiden Geräten.

### Der harte Teil der Kamera ist die Position

Das Kit-README sagt es selbst: „The hard part is knowing where you are (QR codes at doors, WiFi, other tricks)“.

| Ansatz | Position | Aufwand bis Sonntag | Urteil |
|---|---|---|---|
| Gaussian Splat / Feature-Matching / VPS (Brainstorming) | potenziell gut | Tage, plus Scan des Gebäudes | **nicht machbar** |
| WLAN | – | keine Daten; laut Q&A nicht erwartet | **raus** |
| **Positions-QR + Schrittliste + 2D-Karte** | exakt am QR, dazwischen über Schritte | 2–3 h | **Basis auf beiden Geräten** |
| **Android: Positions-QR + WebXR `immersive-ar`** (ARCore-Tracking), Route als 3D-Linie auf dem Boden | gut über einige 10 m, driftet; Neu-Verankerung am nächsten QR | 3–4 h zusätzlich | **Hauptszene im Video, die eine Level-5-Erweiterung** |
| **iPhone: Positions-QR + Kamerabild** mit Pfeil-Overlay, Richtung über Gyroskop | Richtung gut, Position nur über Schritte/QR | 2 h zusätzlich | **iPhone-Modus** |

Geprüfte Fakten: iOS Safari unterstützt **kein** WebXR `immersive-ar`; Android Chrome schon (über ARCore, mit Hit-Test und Anchors). `BarcodeDetector` läuft auf Android Chrome, auf iOS Safari ist er standardmäßig aus → QR-Erkennung in der App mit jsQR oder zxing-wasm.

### Eine Codebasis, zwei Renderer

```
Positions-QR (URL oder Scan in der App) → Position in der Sitzung (API) + sendContextualUpdate an den Agenten
        → Route bzw. Tour vom Core (Polylinie + Manöver)
        ├─ navigator.xr.isSessionSupported('immersive-ar') == true  → AR-Renderer (Android)
        └─ sonst                                                    → Overlay-Renderer (iPhone)
Gemeinsam: Marker-Modell, Koordinatentransformation, Manöverliste, Voice-Navigator, Live-Reroute
```

**Android (AR-Renderer):**
- three.js mit WebXR, Session `immersive-ar`, Features `local` (Pflicht), `hit-test` und `dom-overlay` (optional). Über `dom-overlay` liegen Anweisung und Mikrofon-Button als HTML über der AR-Ansicht.
- **Kamera-Übergabe:** Den QR-Stream (`getUserMedia`) **beenden, bevor** die XR-Session startet. Sonst konkurrieren beide um die Kamera.
- Ausgangslage: Der Nutzer steht am QR und blickt darauf. Der XR-Ursprung entspricht damit Marker-Position und -Blickrichtung. Die Route wird als Linie knapp über dem Boden gezeichnet (Boden per Hit-Test, sonst ca. 1,4 m unter dem Gerät).
- Neu verankern: AR verlassen, nächsten QR scannen, AR neu starten. Raw-Camera-Access innerhalb der XR-Session nicht einplanen.

**iPhone (Overlay-Renderer):**
- `getUserMedia({ video: { facingMode: "environment" } })` als Hintergrundvideo, darüber ein Canvas mit Richtungspfeil zum nächsten Wegpunkt.
- Richtung relativ über `DeviceOrientationEvent` ab dem QR-Anker, **nicht** über `webkitCompassHeading`: Das ist magnetisch und in einer Stahlhalle unbrauchbar.
- Keine Schrittzählung versprechen. Fortschritt über „next“ oder den nächsten QR.
- `DeviceOrientationEvent.requestPermission()` braucht auf iOS eine Nutzergeste.

**Für beide gilt:**
- **Keine Nordrichtung.** `building.json` hat keine Nordausrichtung. Die Blickrichtung kommt vom Positions-QR (an einer Wand mit bekannter Ausrichtung).
- **Eine Koordinatentransformation für alles:** Gebäude hat x rechts, y oben (Meter). WebXR hat x rechts, y oben, −z vorwärts. Gebäude-y wird zu −z, dazu die Drehung aus dem Marker. Eine Funktion, mit Tests.
- **Die Route muss eine echte Polylinie sein.** Das README-Modell (Raumanker → Tür in gerader Linie) schneidet in L-Räumen durch Wände, und `viewer.py` wählt bei mehreren Türen die erste statt der gerouteten (Codex §8). Der Portalgraph aus P4 (Tür zu Tür innerhalb der Räume, 15 cm Wandabstand) löst **beides**: Synera-Routenbewertung und Darstellung.
- **Turn-by-Turn kommt aus dem Core:** Manöver aus der Polylinie (Abbiegewinkel), Landmarken aus nahen Assets („links an der Presse“). Der Agent spricht, er rechnet nicht.
- **Berechtigungen in einer Geste:** Ein Button „Navigation starten“ fragt Kamera, Mikrofon und (iOS) Bewegung ab; auf Android kommt die WebXR-Freigabe dazu. Bei Ablehnung bleibt die 2D-Karte.
- **Kamera und Mikrofon gleichzeitig** ist auf beiden Geräten **ungetestet**. Bekanntes Risiko auf dem iPhone: Bei aktivem Mikrofon kommt die Sprachausgabe leise oder aus dem Hörer. Notlösung für die Aufnahme: Kopfhörer. → Geräte-Gate (Abschnitt 10).
- **QR-Druck:** mindestens 10–15 cm Kantenlänge, damit er aus 1–2 m scannt.

### Abgrenzung

Die Interaktionsbewertung (25 Punkte) ist ein **geskriptetes Gespräch**. Das muss auch ohne Kamera und am Laptop funktionieren. Die Kamera ist ein zusätzlicher Modus, nicht der einzige Eingang.

---

## 6. Voice-LLM: Entscheidung nach Messung

**Verfügbar im ElevenLabs-Agent** (Docs-Stand heute): Anthropic (u. a. Claude Sonnet 5.5, Opus 5.5), Google (Gemini-Flash-Familie, Gemini 4 Argon), OpenAI (GPT-6.x, GPT-5.x), von ElevenLabs gehostet u. a. Qwen3.5-397B-A17B (bisheriger Standard) und GLM 5.2. Dazu „Realtime“-Modelle. Die Docs nennen **keine** Zahlen zur Tool-Call-Zuverlässigkeit; ElevenLabs empfiehlt, mit eigenen Prompts und Tools zu messen.

Alle übrigen Agent-Einstellungen (Stimme Eric, Eleven v4 Turbo, Expressive Mode, Scribe v2 Realtime, `turn_v3`, Englisch) stehen in [`docs/elevenlabs-agent-config.md`](docs/elevenlabs-agent-config.md) und bleiben beim A/B-Test gleich. Getauscht wird nur das LLM.

**Was zählt, in dieser Reihenfolge:** 1. richtiges Tool mit richtigen Parametern, auch bei Ketten; 2. Regeln einhalten (vor einer Änderung auf „yes“ warten, genau eine Rückfrage, nichts erfinden); 3. Zeit bis zum ersten gesprochenen Wort; 4. Englisch sicher, Deutsch als Bonus.

**Start-Modell: Claude Sonnet 5.5, niedriger Reasoning-Aufwand.** Gründe: starkes Tool-Calling und Regelbefolgung, und dieselbe Modellfamilie wie der Textchat im Backend. **Backup-LLM** in ElevenLabs aktiv lassen.

**A/B-Test, max. 30 Minuten, direkt nach dem ersten funktionierenden Voice-Durchstich.** Gleiche Äußerungen gegen Sonnet 5.5, Qwen3.5 und ein Gemini-Flash-Modell:

| # | Äußerung | erwartet |
|---|---|---|
| 1 | „Where is the 3D printer?“ | `find`, Ort nennen und zeigen |
| 2 | „I need these five parts: …“ | `plan_tour`, Reihenfolge nennen |
| 3 | „Take me there without stairs.“ | `route` mit `step_free`, Start aus der Sitzung |
| 4 | „Go to the press.“ (drei Pressen vorhanden) | genau eine Rückfrage |
| 5 | „Next.“ | `next_step` |
| 6 | „Where is the coffee machine?“ (gibt es nicht) | sagt, dass es keine gibt, erfindet nichts |
| 7 | Unterbrechung mitten in einer Ansage | hört auf, reagiert auf das Neue |
| 8 | Admin: „Close the east lift.“ | `propose_edit`, Vorschau, wartet |
| 9 | „Yes.“ | `commit_edit` genau einmal |
| 10 | Route ohne Lösung (oben, ohne Treppe, Lift gesperrt) | sagt klar: keine Route |

**Entscheidungsregel:** Sonnet 5.5 bleibt, außer ein anderes Modell löst mehr Fälle richtig oder ist bei gleicher Trefferzahl spürbar schneller (Richtwert: mehr als 0,5 s früher am ersten Wort). Der Navigator darf auf das schnellere Modell wechseln, wenn nur dort Latenz das Problem ist.

**Kosten:** Das Agent-LLM wird über **ElevenLabs-Credits** abgerechnet (Anbieterpreis ohne Aufschlag, bei manchen Claude- und Gemini-Modellen Vertex-Preis +10 %), nicht über das Anthropic-Guthaben.

---

## 7. Gemeinsame Architektur für beide UX

- **Zwei ElevenLabs-Agents**, Details in [`docs/elevenlabs-agent-config.md`](docs/elevenlabs-agent-config.md):
  - **Navigator** (Desktop-Ansicht und Handy): `find`, `plan_tour`, `route`, `next_step`
  - **Admin** (Laptop): `set_scale`, `propose_edit`, `commit_edit`, `undo`, `what_if`, `generate_markers`
  - QR-Scan und Plan-Upload laufen über die Oberfläche. Das Ergebnis geht per `sendContextualUpdate` an den Agenten.
- **Kontext aus der Sitzung, nicht aus dem Gespräch:** Gebäude, Position (QR), Etage, aktive Tour und Profil („wheelchair“) liegen im Session-State und werden serverseitig zu Constraints.
- **Live-Kopplung:** Der Admin sperrt am Laptop den Lift → WebSocket-Event → das Handy berechnet die aktive Tour neu und sagt es an.
- **Datenmodell-Ergänzung als eigene Schicht** (nicht im Kit-Format): `markers[]` mit `id`, `floor_id`, `position`, `facing_deg`, optional `opening_id`; `tours[]` mit Stopps und Fortschritt; für importierte Gebäude `source_image` und `scale_m_per_px`. Das Basis-`building.json` bleibt im Kit-Format.
- **Route-Ergebnis des Core:** `space_path` (für die Bewertung), Portal-IDs, Polylinie je Etage, Manöverliste, Kostenmodell, Gebäudeversion, Request-ID. Eine Tour ist eine Liste solcher Teilstrecken.
- **Benchmark-Agent:** Tool Runner des Anthropic SDK mit den Core-Tools (Tool-Backlog aus Abschnitt 1.1). Die Antwort gibt der Agent über ein typisiertes Tool `submit_answer` ab; den `Answer:`-Text erzeugt der Code, nicht das LLM. Kosten pro Frage messen, bevor große Läufe starten. Achtung: Sonnet 5.5 und Opus 5.5 lehnen erzwungenes `tool_choice` ab, deshalb `strict: true` und Prompt statt Zwang.

---

## 8. Scope und Priorität

Die Reihenfolge folgt dem Teamgespräch. Gearbeitet wird parallel; bei Konflikten gewinnt der höhere Rang.

| Rang | Inhalt | Status |
|---|---|---|
| 1 | **Core und Gebäude-DB** (Python), Tool-Backlog, Portalgraph (P4) | Pflicht, zwei Personen dauerhaft |
| 2 | **Agent und Submission:** M1 (145 Zeilen, dev-Score pro Typ), Sonntagsadapter | Pflicht, wird nie gefährdet |
| 3 | **Voice-Agent** (Navigator), dann A/B-Test | Pflicht |
| 4 | **Journey-Basis:** Desktop 2D (Teileliste, `find`, `plan_tour`, Übergabe-QR), Handy (Tour, Turn-by-Turn, Live-Reroute), „Lift sperren“ + Undo | Pflicht |
| 5 | **Kamera:** AR-Renderer (Android), Overlay-Renderer (iPhone) | **die eine Level-5-Erweiterung** |
| 6 | **3D-Desktop-Ansicht** und simulierte Teilebewegung | Soll |
| 7 | **Admin voll:** Voice-Admin, B4 komplett, weitere Änderungen | Soll |
| 8 | **Import B2** mit 3-h-Timebox | Kann, wegen Rubrik ausdrücklich versuchen |
| – | Gabelstapler-**Demo**, Custom-LLM-Endpoint, gebäudeübergreifendes Routing | **gestrichen** |

**Vorsicht beim Streichen:** Die Gabelstapler-*Demo* kann weg, die Gabelstapler-*Constraints* im Core nicht. Die Route-Spec listet sie als Regel für manche bewertete Routenfragen. Solange Jurorenfrage 6 offen ist, bleibt der Constraint im Core.

**Streichreihenfolge, falls es eng wird:** B2 → 3D und Teilebewegung → iPhone-Overlay (iPhone bekommt 2D + Voice) → Android-AR (zurück auf QR + 2D + Voice). Ränge 1–4 bleiben.

---

## 9. Demo-Story (60 s) entlang der Journey

1. **0–10 s:** „Neu im Gebäude, fünf Teile holen.“
2. **10–25 s, Desktop:** „I need these five parts.“ 3D-Ansicht zeigt die Orte, der Agent nennt die beste Reihenfolge. Übergabe-QR erscheint.
3. **25–45 s, Android-Handy:** QR scannen, Tour startet. Kamerabild mit Linie am Boden, Stimme: „After the column, turn right.“
4. **45–55 s:** Der Lift fällt aus (Admin am Laptop: „Close the east lift.“ – „Yes.“). Das Handy sagt an: „The lift is out of service, I'll take you via the middle stairs.“
5. **55–60 s:** Pitch: „New building? Upload the floor plan.“ Dazu der dev-Score.

Das technische Video zeigt Railway-Architektur, Gebäude-DB, Benchmark-Lauf, Import-Messung (falls B2 steht) und kurz den iPhone-Modus.

---

## 10. Gates ab jetzt (Code Freeze So 13:00)

| Wann | Gate | Bei Fehlschlag |
|---|---|---|
| **≈19:30** | **Railway-Durchstich:** öffentliche URL liefert SPA, `/health`, `/api/voice/token` und einen echten Tool-Aufruf | lokal weiterarbeiten, Deploy-Fehler isolieren; kein Hosting-Wechsel |
| **≈19:45** | **Geräte-Gate auf beiden Handys:** Kamerabild + ElevenLabs-Mikrofon gleichzeitig, Lautstärke, QR-Scan; auf Android Start einer `immersive-ar`-Session | Android-AR scheitert → beide im Overlay-Modus; Audio-Konflikt → Kopfhörer |
| ≈20:00 | Integrationsgate (Voice → Tool → Karte), dann A/B-Test Voice-LLM | Textchat als Fallback |
| **≈20:30** | **Gebäude-DB grün:** Warm-up-Routen auf dev 369/369 aus der DB, drei einfache Geometrie-Fragetypen ≈ 100 % | alle Kür pausieren, Core hat Vorrang |
| ≈22:30 | **M1:** erster vollständiger Lauf mit 145 Zeilen und dev-Score pro Typ | Lücken offen ausweisen, keine Platzhalter |
| ≈23:00 | **Demo-Gebäude** (Ausschnitt des Arbeitsorts) von Hand angelegt, Positions-QR gedruckt und aufgehängt | Ausschnitt verkleinern |
| 00:30 | **Journey-Test:** Desktop → Tour → Übergabe-QR → Handy → Liftausfall → Reroute, auf beiden Handys | danach keine neue Infrastruktur |
| 00:30–03:00 | **B2-Import-Spike** (eine Person, 3-h-Timebox): drei dev-PNGs rekonstruiert und gemessen | B2 entfällt |
| So 07:00–09:00 | Walk bei Tageslicht aufnehmen (Android-AR als Hauptszene), Frischklon-Probe, finale Test-CSV | – |

---

## 11. Kleinere Fehler und Risiken im Plan

- **`PLAN.md` §1 Punkt 4** („Event-Log-Änderungen sind Pflicht, PNG-Import ist Kür“, in `ef84a9d` „Einen Bildimport gibt es nicht“) ist eine Interpretation des Lead-Gesprächs, keine Regel. Die Rubrik sagt etwas anderes (Abschnitt 4).
- **`PLAN.md` §7** verweist für Export, `node_path` und Doku auf `../repo`, und `ef84a9d` auf „Lenards UI-Prototyp“. Beides ist nicht im Team-Repo. Erst übernehmen, dann darauf bauen (Codex §3).
- **API-Fallen für alle Agenten:** Sonnet 5.5 und Opus 5.5 lehnen erzwungenes `tool_choice` (`any`/`tool`) und `thinking: disabled` mit 400 ab. Seit 21.10.2026 liefern `temperature`, `top_p`, `top_k` auf allen Modellen 400. Der Starter-Agent setzt keins davon, neuer Code darf es auch nicht.
- **Scorer-Falle:** Nach `Answer:` genau eine Zahl. Selbst „m²“ dahinter macht die Antwort falsch, weil die „2“ als zweite Zahl zählt (siehe `docs/question-overview/README.md`).
- **Credits:** Plan rechnet mit 600 USD, im Kickoff klang es nach 150 USD pro Person bzw. pro Team. Einmal in der Console nachsehen.

---

## 12. Ergänzung zu den Jurorenfragen

Zu **Frage 4 (Build)** ergänzen: „Wird für den Check ‚correct buildings built from plans‘ ein Planbild ohne JSON geliefert? Welches Format, mit oder ohne Maßstab?“

Zu **Frage 10 (Interaktion)** ergänzen: „Zählt eine AR-Navigation mit QR-Verankerung, die wir im eigenen Gebäude im Video zeigen, als Level-5-Erweiterung, auch wenn ihr sie nicht live auf euren Geräten testet?“

---

## 13. Noch offen

1. **Rollen:** Wer sind die zwei Personen auf Core und Benchmark, wer macht Journey-UI, wer Voice, wer Kamera?
2. **Demo-Gebäude:** Welcher Ausschnitt des Arbeitsorts wird von Hand angelegt (Eingang bis zum Ziel, mit Treppe oder Lift)?

---

## 14. Einordnung von `PLAN.md` in der Fassung `ef84a9d` (Lenard, 18:23)

Die Änderung baut auf dem Plan von 16:38 auf, nicht auf diesem Review (im Kopf steht weiter „Stand 17:00“, die Voice-Anmeldung weiter über eine signierte URL). Einordnung Punkt für Punkt:

| Änderung in `ef84a9d` | Einordnung |
|---|---|
| Cloudflare Worker, Durable Object, D1 | **Verworfen:** Railway (Abschnitt 3) |
| Nur JSON, kein Bildimport | **Verworfen:** B2 bleibt mit Timebox, weil die Rubrik ihn nennt (Abschnitt 4) |
| Keine Mobile-Ansicht, kein QR, keine Kamera, kein AR | **Verworfen:** Handy und QR sind Teil der Journey aus dem Teamgespräch; die Kamera ist die Level-5-Erweiterung |
| Vorberechnete Gebäude-DB als Startpunkt | **Übernommen**, in Python (Abschnitt 3). Im Teamgespräch als erster Schritt gesetzt |
| Tool Runner des Anthropic SDK statt Agent SDK | **Übernommen**, in Python |
| Kosten pro Frage messen, bevor große Läufe starten | **Übernommen** |
| Benchmark als frei laufender Agent | **Mit Auflage übernommen:** Antwort über `submit_answer`, `Answer:`-Text aus dem Code (Abschnitt 7) |
| „Keine Gebäudedaten im Prompt“ | **Übernommen** |
| Alles in TypeScript, Python nur als Referenz | **Verworfen**, Begründung unten |

**Warum Python im Core bleibt:** Der Hauptgrund für TypeScript war, auf Cloudflare keinen Python-Container zu brauchen. Mit Railway fällt er weg. Übrig bliebe das Risiko einer Neuschreibung genau dort, wo die 55 Punkte liegen: Das README-Routenmodell hängt an shapelys `representative_point` (intern ein GEOS-Algorithmus), dazu kommen 0,35-m-Wandtoleranz, Schnittflächen und 0,15-m-Inset. Der Python-Starter trifft die Warm-up-Routen 369/369, und der Codex-Check bestätigt drei Geometrie-Fragetypen mit shapely (64/64 dev, 243/243 train). Bei `errand` zählt 1 %, bei `what_if_door` entscheidet die Grenze „mehr als 1 m kürzer“. Ein Nachbau in TypeScript müsste diese Genauigkeit erst wieder erreichen. Gemeinsame Typen mit dem Frontend entstehen aus dem OpenAPI-Schema. Falls schon TypeScript-Code für Core oder DB existiert: vor dem Verwerfen ansehen, was sich ins Frontend übernehmen lässt.
