# Review: PLAN.md gegen die zwei User Experiences

**Stand:** Sa 24.10.2026, 17:30. **Geprüft:** Team-Repo `bfbfb22` (inkl. `PLAN.md`, `codex reviewed plan suggestions .md`, `open questions for judge .md`, `2026-10-24-fragen-an-juroren.md`, Route-Spec, Lead-Q&A, Brainstorming-Transkript, Challenge-PDF, Kit-README, Daten), dazu die lokale, nicht committete `docs/elevenlabs-agent-config.md`.
**Maßstab:** Der Plan ist die Grundlage für das gesamte Agentic Engineering. Agenten bauen, was dort steht, und nichts, was dort fehlt.

> **Verhältnis zu PLAN.md:** `PLAN.md` wird bewusst nicht umgeschrieben. Dieses Review ergänzt es. **Wo sich beide widersprechen, gelten die Teamentscheidungen in Abschnitt 1** (Hosting, Geräte, Voice-LLM) und die Architektur in Abschnitt 2. Alles andere aus `PLAN.md` gilt weiter.

**Zielbild (Vorgabe des Teams):**
- **UX A – Laptop/Browser:** Gebäude anlegen und konfigurieren, Floorplans, Änderungen, alles auch per Voice-Agent.
- **UX B – Smartphone:** Mit dem Handy durch Fabrik oder Gebäude laufen, in der Web-App live über die Kamera den Weg sehen und dabei mit dem Voice-Agent sprechen.

---

## 0. Urteil

Der fachliche Kern ist gut und bleibt: deterministischer Python-Core, derselbe Core für App und Benchmark, Client-Tools mit Backend-Brücke, Vorschau → Bestätigung → Undo, Benchmark ohne Voice und Cloud.

**Aber der Plan bildet die zwei User Experiences nur zur Hälfte ab:**

| | Zielbild | Was PLAN.md heute sagt | Folge |
|---|---|---|---|
| **UX B** | Live-Kamera mit Weg, Voice | §13: „Kamera-Lokalisierung … WebXR-AR-Pfeile“ stehen unter **„Bewusst nicht im Wochenend-Stack“**. Codex-Review: „keine Kameraortung im Pflichtpfad“. QR-Startpunkt nur als P8-Showcase | Ohne dieses Review baut kein Agent die Kamera-Navigation |
| **UX A** | Gebäude aus Floorplans anlegen | P9 „Kür, nur mit Puffer“, und **als Erstes gestrichen** (§9 Streichreihenfolge) | Laptop-UX schrumpft auf „Lift sperren, Tür hinzufügen“ |

Abschnitte 3 und 4 schließen diese Lücken.

---

## 1. Teamentscheidungen (24.10., 17:30) und verbleibende Widersprüche

| # | Thema | PLAN.md | Andere Quelle | **Gilt jetzt** |
|---|---|---|---|---|
| 1 | **Hosting** | Cloudflare: Worker + Durable Object + Container + R2 | Codex-Review: Railway | **Railway**, ein Service. Architektur in Abschnitt 2. Alles Cloudflare-Spezifische in `PLAN.md` §2–3, P0, P6 und im Zeitplan entfällt |
| 2 | **Testgeräte** | „Handy-Layout“ | Brainstorming: „Jury hat keine iPhones“ (unbestätigt) | **Android und iPhone sind im Team vorhanden.** Beide Plattformen werden unterstützt (Abschnitt 4) |
| 3 | **LLM im ElevenLabs-Agent** | eingebautes `claude-sonnet-5-5` | `docs/elevenlabs-agent-config.md`: Standard Qwen3.5-397B | **Das bessere nach Messung.** Start mit Claude Sonnet 5.5, kurzer A/B-Test entscheidet (Abschnitt 5) |
| 4 | **Voice-Auth** | „Token-Endpunkt“ liefert „signierte URL“ | ElevenLabs-Docs: Signed URL ist für **WebSocket**, für **WebRTC** braucht es einen **Conversation Token**; Voice nutzt standardmäßig WebRTC | **WebRTC + Conversation Token**, Endpunkt `/api/voice/token` (Abschnitt 2). Die Agent-Config-Datei entsprechend korrigieren |
| 5 | **Sprache** | DE/EN | Agent-Config: Englisch | offen – Demo-Sprache festlegen (Jury ist international, Video vermutlich Englisch) |
| 6 | **Cache-Preis** | Sonnet 5.5 Cache-Read 0,20 USD/MTok | Codex: 0,10 USD | **Plan hat recht.** Aktuelle Preisliste: Sonnet 5.5 2/10, Cache-Read 0,20; Haiku 5.5 0,10/0,50; Opus 5.5 4/20 |
| 7 | **Zeitplan** | feste Gates 17:15, 18:00, 19:00 | – | ersetzt durch die Gates in Abschnitt 8 |

---

## 2. Architektur auf Railway

Ein Service, ein Prozess, ein Docker-Image. Das ersetzt Worker, Hono, Durable Object, Container-Klasse, R2 und Wrangler aus `PLAN.md` §2–3.

```
Laptop (UX A) ─┐                       ┌─ /                SPA (Vite-Build)
Handy  (UX B) ─┼── HTTPS/WSS ── Railway FastAPI ─┼─ /api/*           Tools, Import, Edits, Chat
               │                       ├─ /api/voice/token ElevenLabs Conversation Token (WebRTC)
               │                       ├─ /ws/buildings/{id}  building_changed an alle Clients
               │                       └─ /health
               └── Audio (WebRTC) ── ElevenLabs Agent ── Client-Tools laufen im Browser → /api/*
Volume /state:  SQLite (Events, Proposals, Marker, Gebäudekatalog) + Uploads (Planbilder)
Image  /app/data: Kit-Gebäude (nur building.json + equipment.csv)
Benchmark: lokal, ohne Railway und ohne ElevenLabs, derselbe core/
```

**Festlegungen:**
- **Dockerfile mehrstufig:** Node baut `web/`, dann `python:3.12-slim` mit `core/`, `server/`, `data/` und dem `dist`. Build-Kontext ist die Repo-Wurzel. `uvicorn server.app:app --host 0.0.0.0 --port $PORT`, **ein** Worker.
- **Routenreihenfolge:** `/api`, `/ws`, `/health` vor dem SPA-Fallback.
- **Secrets als Railway-Variablen:** `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID_NAVIGATOR`, `ELEVENLABS_AGENT_ID_ADMIN`. Der Browser sieht nur Agent-IDs und den kurzlebigen Token.
- **Volume:** auf `/state`, nicht über `/app/data`. Initialisierung beim Start, nicht beim Build.
- **Grenzen von Railway (geprüft):** Mit Volume sind **keine Replicas** möglich, und ein **Redeploy hat kurze Downtime**. Folgen: kein Deploy während Aufnahme oder Demo; der Client verbindet den WebSocket automatisch neu und lädt danach den Snapshot. App-Sleeping ausschalten.
- **Zustandsvertrag** (statt Durable Object, übernommen aus Codex §6): unveränderliche Basisdaten plus Event-Log in SQLite; `proposal_id` mit `expected_version`; `commit` idempotent über `operation_id`; Undo als neues Event; jedes Tool-Ergebnis trägt Gebäudeversion und Request-ID, verspätete Antworten überschreiben keine neueren.
- **Rechenlast:** Geometrie und Routing laufen im Threadpool (synchrone `def`-Endpunkte), damit WebSocket und Voice-Tools nicht blockieren. Geometrie-Cache pro Gebäude und Version, kein Vorberechnen aller 280 Gebäude beim Start.
- **Handy-Tests brauchen HTTPS.** Kamera, Mikrofon und WebXR laufen nur im Secure Context. Eine LAN-IP über `http://` reicht nicht. Wege: Railway-URL (eigene Dev-Umgebung), auf Android USB-Debugging mit Port-Forwarding (`localhost` gilt als sicher), auf dem iPhone nur Railway oder ein HTTPS-Tunnel.

---

## 3. UX A – Laptop: Gebäude anlegen und konfigurieren

### Was fehlt und warum es zählt

- **Die Rubrik zählt es zu den 55 Funktionspunkten.** Challenge-PDF S. 3: „automatic checks … covering levels 1 to 4: … **correct buildings built from plans**“. Der Lead hat lokale Änderungen betont, die schriftliche Rubrik aber nicht aufgehoben (Jurorenfrage 4 ist offen). Den Import als erstes Streichopfer zu führen, passt nicht zu dieser Rubrik.
- **UX B braucht UX A.** Die Kit-Gebäude kann man nicht begehen. Im Manifest gibt es Münchner OSM-Gebäude (TUM-Bauten, Terminal 2, Pasing Arcaden), aber nicht den Arbeitsort. Für einen echten Kamera-Walk muss das Demo-Gebäude **über UX A** angelegt werden.

### Befunde aus den Daten (geprüft an `proc-factory-dev-003`)

- Die **PNGs haben keinen Maßstab und keine Achsen**. Raumnummern stehen im Bild, Türen sind kleine Punkte, Eingänge rote Dreiecke. Den Maßstab muss das System **im Gespräch erfragen** („Wie breit ist die Halle?“). Genau das ist „Build … by conversation“.
- Die **SVGs sind Matplotlib-Exporte**: Räume sind `<path>`-Polygone mit Füllfarbe je Raumtyp, Texte nur als Glyphen. Ein SVG-Import liefert die Polygone fast exakt (bis auf Maßstab und Y-Achse), ein PNG-Import braucht Vision.
- **Das Kit enthält 280 Paare aus Plan und `building.json`.** Damit lässt sich ein Importer messen: dev-`floor_*_plain.png` rekonstruieren und Raumzahl, Flächen-IoU und Türgraph gegen das echte JSON vergleichen. Das ergibt eine Zahl für Video und Pitch.

### Build in vier Stufen

| Stufe | Inhalt | Priorität |
|---|---|---|
| **B1** | `building.json` hochladen → Validator (IDs, Referenzen, gültige Polygone, Türen auf gemeinsamen Wänden) → sofort darstellen → alle Tools funktionieren darauf. Gleicher Pfad wie das Sonntagsgebäude | Pflicht |
| **B2** | Plan-Bild (PNG/JPG, auch **Foto eines Flucht- und Rettungsplans**) → Claude Vision → Entwurf im Kit-Format → Validator → Overlay-Vorschau über dem Bild → Korrektur per Voice oder Klick („0.21 ist ein Labor“, „hier fehlt eine Tür“, „die Halle ist 40 m breit“) → bestätigen → speichern | Pflicht mit Timebox 3 h, Fallback siehe unten |
| **B3** | Lokale Änderungen mit Vorschau, Bestätigung, Undo (schon im Plan): Tür, Sperrung, Asset verschieben („das steht jetzt hier“) | Pflicht |
| **B4** | **QR-Marker erzeugen:** pro Eingang und wichtiger Tür ein druckbares Blatt mit `marker_id`, Etage, Position und **Blickrichtung**. Das ist die Brücke zu UX B | Pflicht für UX B |

**Fallback für B2:** Scheitert der Import an der Timebox, wird das Demo-Gebäude als kleiner Ausschnitt des Arbeitsorts von Hand angelegt (Editor oder JSON). Das ist kein Testdatum und damit zulässig, muss im Video aber als „angelegt“ und nicht als „importiert“ gezeigt werden.

**Voice am Laptop:** Agent-Modus „Admin“ (Abschnitt 6). Bearbeiten ist serverseitig an eine Admin-Sitzung gebunden; ein vom LLM gelieferter Parameter ist keine Berechtigung.

---

## 4. UX B – Smartphone: Kamera, Live-Weg, Voice (Android und iPhone)

### Der harte Teil ist die Position, nicht die Darstellung

Das Kit-README sagt es selbst: „The hard part is knowing where you are (QR codes at doors, WiFi, other tricks)“.

| Ansatz | Position | Aufwand bis Sonntag | Urteil |
|---|---|---|---|
| Gaussian Splat / Feature-Matching / VPS (Brainstorming) | potenziell gut | Tage, plus Scan des Gebäudes | **nicht machbar** |
| WLAN | – | keine Daten; laut Q&A nicht erwartet | **raus** |
| **QR an Türen + Schrittliste + 2D-Karte** | exakt am QR, dazwischen über Schritte | 2–3 h | **Basis auf beiden Geräten** |
| **Android: QR-Anker + WebXR `immersive-ar`** (ARCore-Tracking), Route als 3D-Linie auf dem Boden | gut über einige 10 m, driftet; Neu-Verankerung am nächsten QR | 3–4 h zusätzlich | **Hauptdemo im Video** |
| **iPhone: QR-Anker + Kamerabild** mit Pfeil-Overlay, Richtung über Gyroskop | Richtung gut, Position nur über Schritte/QR | 2 h zusätzlich | **iPhone-Modus** |

Geprüfte Fakten: iOS Safari unterstützt **kein** WebXR `immersive-ar`; Android Chrome schon (über ARCore, mit Hit-Test und Anchors). `BarcodeDetector` läuft auf Android Chrome, auf iOS Safari ist er standardmäßig aus → QR-Erkennung in JS (jsQR oder zxing-wasm) für beide.

### Eine Codebasis, zwei Renderer

```
QR-Scan (getUserMedia + jsQR) → set_position(marker) → Route vom Core (Polylinie + Manöver)
        │
        ├─ navigator.xr.isSessionSupported('immersive-ar') == true  → AR-Renderer (Android)
        └─ sonst                                                    → Overlay-Renderer (iPhone)
Gemeinsam: Marker-Modell, Koordinatentransformation, Manöverliste, Voice-Navigator, Live-Reroute
```

**Android (AR-Renderer):**
- three.js mit WebXR, Session `immersive-ar`, Features `local` (Pflicht), `hit-test` und `dom-overlay` (optional). Über `dom-overlay` liegen Anweisungstext und Mikrofon-Button als HTML über der AR-Ansicht.
- **Kamera-Übergabe:** Den QR-Stream (`getUserMedia`) **beenden, bevor** die XR-Session startet. Sonst konkurrieren beide um die Kamera.
- Ausgangslage: Der Nutzer steht am QR und blickt darauf. Der XR-Ursprung entspricht damit Marker-Position und -Blickrichtung. Die Route wird als Linie knapp über dem Boden gezeichnet (Boden per Hit-Test, sonst ca. 1,4 m unter dem Gerät).
- Neu verankern: AR verlassen, nächsten QR scannen, AR neu starten. Raw-Camera-Access innerhalb der XR-Session nicht einplanen.

**iPhone (Overlay-Renderer):**
- `getUserMedia({ video: { facingMode: "environment" } })` als Hintergrundvideo, darüber ein Canvas mit Richtungspfeil zum nächsten Wegpunkt.
- Richtung relativ über `DeviceOrientationEvent` ab dem QR-Anker, **nicht** über `webkitCompassHeading`: Das ist magnetisch und in einer Stahlhalle unbrauchbar.
- Keine Schrittzählung versprechen. Fortschritt über „weiter“ oder den nächsten QR. Angezeigt wird die Distanz bis zur nächsten Abbiegung laut Route.
- `DeviceOrientationEvent.requestPermission()` braucht auf iOS eine Nutzergeste.

**Für beide gilt:**
- **Keine Nordrichtung.** `building.json` hat keine Nordausrichtung. Die Blickrichtung kommt **vom QR-Marker** (an einer Wand mit bekannter Ausrichtung angebracht).
- **Eine Koordinatentransformation für alles:** Gebäude hat x rechts, y oben (Meter). WebXR hat x rechts, y oben, −z vorwärts. Gebäude-y wird zu −z, dazu die Drehung aus dem Marker. Dieselbe Y-Falle wie im SVG. Eine Funktion, mit Tests.
- **Die Route muss eine echte Polylinie sein.** Das README-Modell (Raumanker → Tür in gerader Linie) schneidet in L-Räumen durch Wände, und `viewer.py` wählt bei mehreren Türen die erste statt der gerouteten (Codex §8). In der Kamera sieht man das sofort. Der Portalgraph aus P4 (Tür zu Tür innerhalb der Räume, 15 cm Wandabstand) löst **beides**: Synera-Routenbewertung und Kamera-Darstellung. P4 wird damit wichtiger, nicht optional.
- **Turn-by-Turn kommt aus dem Core:** Manöver aus der Polylinie (Abbiegewinkel), Landmarken aus nahen Assets („links an der Presse“). Der Agent spricht und beantwortet Rückfragen, er rechnet nicht.
- **Berechtigungen in einer Geste:** Ein Button „Navigation starten“ fragt Kamera, Mikrofon und (iOS) Bewegung ab; auf Android kommt die WebXR-Freigabe dazu. Ablehnungen sauber behandeln, dann bleibt die 2D-Karte.
- **Kamera und Mikrofon gleichzeitig** (ElevenLabs über WebRTC plus Kamera bzw. XR-Session) ist auf beiden Geräten **ungetestet**. Bekanntes Risiko auf dem iPhone: Bei aktivem Mikrofon kommt die Sprachausgabe leise oder aus dem Hörer statt aus dem Lautsprecher. Notlösung für die Aufnahme: Kopfhörer. → **Erstes Gate** (Abschnitt 8).
- **QR-Druck:** mindestens 10–15 cm Kantenlänge, damit er aus 1–2 m scannt.

### Abgrenzung

Die Interaktionsbewertung (25 Punkte) ist ein **geskriptetes Gespräch**. Das muss auch ohne Kamera und am Laptop funktionieren. Die Kamera ist ein zusätzlicher Modus von UX B, nicht der einzige Eingang.

---

## 5. Voice-LLM: Entscheidung nach Messung

**Verfügbar im ElevenLabs-Agent** (Docs-Stand heute): Anthropic (u. a. Claude Sonnet 5.5, Opus 5.5), Google (Gemini-Flash-Familie, Gemini 4 Argon), OpenAI (GPT-6.x, GPT-5.x), von ElevenLabs gehostet u. a. Qwen3.5-397B-A17B (aktueller Standard in unserer Config) und GLM 5.2. Dazu „Realtime“-Modelle für niedrige Latenz. Die Docs nennen **keine** Zahlen zur Tool-Call-Zuverlässigkeit; ElevenLabs empfiehlt ausdrücklich, mit eigenen Prompts und Tools zu messen.

**Was für uns zählt, in dieser Reihenfolge:**
1. Richtiges Tool mit richtigen Parametern, auch bei Ketten (`find` → `route`)
2. Regeln einhalten: vor einer Änderung auf „Ja“ warten, genau eine Rückfrage, nichts erfinden
3. Zeit bis zum ersten gesprochenen Wort
4. Deutsch und Englisch

**Start-Modell: Claude Sonnet 5.5, niedriger Reasoning-Aufwand.** Gründe: starkes Tool-Calling und Regelbefolgung, und dieselbe Modellfamilie wie der Textchat im Backend. Damit gelten ein Tool-Vertrag und ein Prompt-Stil für Voice und Text. **Backup-LLM** in ElevenLabs aktiv lassen (nicht „Disabled“), mit einem schnellen Flash-Modell als Ausweichpfad.

**A/B-Test, max. 30 Minuten, direkt nach dem ersten funktionierenden Voice-Durchstich.** Gleiche zehn Äußerungen gegen Sonnet 5.5, Qwen3.5 (aktueller Standard) und ein Gemini-Flash-Modell:

| # | Äußerung | erwartet |
|---|---|---|
| 1 | „Wo ist der 3D-Drucker?“ | `find`, Ort nennen und zeigen |
| 2 | „Bring mich hin, ohne Treppen.“ | `route` mit `step_free`, Startpunkt aus der Sitzung |
| 3 | „Zur Presse.“ (drei Pressen vorhanden) | genau eine Rückfrage |
| 4 | „Weiter.“ | `next_step` |
| 5 | „Wo ist der Kaffeeautomat?“ (gibt es nicht) | sagt, dass es keinen gibt, erfindet nichts |
| 6 | Unterbrechung mitten in einer Ansage | hört auf, reagiert auf das Neue |
| 7 | Admin: „Sperr den Ostlift.“ | `propose_edit`, Vorschau, wartet |
| 8 | „Ja.“ | `commit_edit` genau einmal |
| 9 | „Mach das rückgängig.“ | `undo` |
| 10 | Route ohne Lösung (oben, ohne Treppe, Lift gesperrt) | sagt klar: keine Route |

**Entscheidungsregel:** Sonnet 5.5 bleibt, außer ein anderes Modell löst mehr Fälle richtig oder ist bei gleicher Trefferzahl spürbar schneller (Richtwert: mehr als 0,5 s früher am ersten Wort). Der Navigator darf auf das schnellere Modell wechseln, wenn nur dort Latenz das Problem ist. Der Admin-Agent bleibt dann trotzdem beim treffsichersten Modell.

**Kosten:** Das Agent-LLM wird über **ElevenLabs-Credits** abgerechnet (Anbieterpreis ohne Aufschlag, bei manchen Claude- und Gemini-Modellen Vertex-Preis +10 %), nicht über das Anthropic-Guthaben.

---

## 6. Gemeinsame Architektur für beide UX

- **Zwei ElevenLabs-Agents** mit getrennten Prompts:
  - **Navigator** (Handy): `find`, `route`, `next_step`, `set_position`, `report_issue`
  - **Admin** (Laptop): `import_plan`, `set_scale`, `propose_edit`, `commit_edit`, `undo`, `what_if`, `generate_markers`
- **Kontext aus der Sitzung, nicht aus dem Gespräch:** Gebäude, Position (QR), Etage und Profil („Rollstuhl“) liegen im Session-State und werden serverseitig zu Constraints.
- **Live-Kopplung:** Der Admin sperrt am Laptop eine Tür → WebSocket-Event → das Handy berechnet die aktive Route neu und sagt es an. Das ist die Multiuser-Funktion aus dem Plan, jetzt mit konkretem Nutzen.
- **Datenmodell-Ergänzung als eigene Schicht** (nicht im Kit-Format): `markers[]` mit `id`, `floor_id`, `position`, `facing_deg`, optional `opening_id`; für importierte Gebäude `source_image` und `scale_m_per_px`. Das Basis-`building.json` bleibt im Kit-Format, damit Benchmark und Sonntagslauf unberührt sind.
- **Route-Ergebnis des Core:** `space_path` (für die Bewertung), Portal-IDs, Polylinie je Etage (Karte und Kamera), Manöverliste (Ansagen), Kostenmodell, Gebäudeversion, Request-ID.

---

## 7. Scope neu ordnen

Der Plan war laut zweitem Review schon „für drei Personen zu breit“. Kamera-Navigation und Import kommen nur hinein, wenn anderes herausgeht.

| Rang | Inhalt | Status |
|---|---|---|
| 1 | **M1 Benchmark** (145 Zeilen, dev-Score pro Typ) und Sonntagsadapter | unverändert, wird nie gefährdet |
| 2 | Core inkl. Portalgraph (P4) – dient Bewertung **und** Kamera | Pflicht |
| 3 | **UX A Basis:** B1, B3, Voice-Admin, Vorschau/Undo | Pflicht |
| 4 | **UX B Basis:** Handy-Layout, QR-Start, 2D-Karte, Turn-by-Turn, Voice-Navigator, Live-Reroute | Pflicht |
| 5 | **UX B Kamera:** AR-Renderer (Android), Overlay-Renderer (iPhone) | **die eine Level-5-Erweiterung** |
| 6 | **UX A Import (B2)** mit Timebox und Fallback | Pflicht mit Timebox |
| – | Gabelstapler-**Demo**, 3D-Viewer (r3f), Custom-LLM-Endpoint, gebäudeübergreifendes Routing | **gestrichen** |

**Vorsicht beim Streichen:** Die Gabelstapler-*Demo* kann weg, die Gabelstapler-*Constraints* im Core nicht. Die Route-Spec listet sie als Regel für manche bewertete Routenfragen. Solange Jurorenfrage 6 offen ist, bleibt der Constraint im Core (P4).

**Streichreihenfolge, falls es eng wird:** 3D → iPhone-Overlay (nur Android-AR zeigen, iPhone bekommt 2D + Voice) → Android-AR (zurück auf QR + 2D + Voice) → B2-Import (Fallback-Gebäude). Benchmark und beide UX-Basen bleiben.

---

## 8. Gates ab jetzt (Code Freeze So 13:00)

| Wann | Gate | Bei Fehlschlag |
|---|---|---|
| **≈18:30** | **Railway-Durchstich:** öffentliche URL liefert SPA, `/health`, `/api/voice/token` und einen echten Tool-Aufruf | lokal weiterarbeiten, Deploy-Fehler isolieren; kein Hosting-Wechsel |
| **≈18:45** | **Geräte-Gate auf beiden Handys** über die Railway-URL: Kamerabild + ElevenLabs-Mikrofon gleichzeitig, Lautstärke der Sprachausgabe, QR-Scan mit jsQR; auf Android Start einer `immersive-ar`-Session | Android-AR scheitert → beide Geräte im Overlay-Modus; Audio-Konflikt → Kopfhörer für die Aufnahme |
| ≈19:00 | Integrationsgate (Voice → Tool → Karte), dann A/B-Test Voice-LLM (Abschnitt 5) | Textchat als Fallback |
| **≈20:30** | **Import-Spike:** drei dev-PNGs rekonstruiert, Abweichung gegen `building.json` gemessen | Fallback-Gebäude anlegen, B2 pausieren |
| ≈21:30 | **Demo-Gebäude** existiert, QR-Marker gedruckt und aufgehängt | Ausschnitt verkleinern |
| 00:30 | **Walk-Test vor Ort mit beiden Handys:** QR → Route → AR-Linie bzw. Overlay → „weiter“ → Live-Reroute nach Admin-Sperrung | danach keine neue Infrastruktur |
| So 07:00–09:00 | Mobile-Walk bei Tageslicht aufnehmen (Android-AR als Hauptszene) | – |

---

## 9. Demo-Story (60 s), die beide UX verbindet

1. **0–15 s, Laptop:** Facility Manager fotografiert den Fluchtplan und lädt ihn hoch. Agent: „Wie breit ist die Halle?“ – Gebäude steht, QR-Blatt wird gedruckt. *(Level 4, „minutes, not days“)*
2. **15–40 s, Android-Handy:** Techniker scannt den QR am Eingang: „Wo ist der 3D-Drucker?“ Kamerabild mit Linie am Boden, Stimme: „Nach der Säule rechts.“ *(Level 2/5, Voice)*
3. **40–55 s, Laptop → Handy:** „Die Tür zu Flur B ist gesperrt.“ Vorschau, „Ja“ – das Handy routet live um und sagt es an. *(React, Multiuser)*
4. **55–60 s:** „Das LLM interpretiert, die Regeln entscheiden“ plus dev-Score.

Das technische Video zeigt Railway-Architektur, Benchmark-Lauf, Import-Messung und kurz den iPhone-Modus.

---

## 10. Kleinere Fehler und Risiken im Plan

- **§1 Punkt 4** („Event-Log-Änderungen sind Pflicht, PNG-Import ist Kür“) ist eine Interpretation des Lead-Gesprächs, keine Regel. Die Rubrik sagt etwas anderes (Abschnitt 3).
- **§7** verweist für Export, `node_path` und Doku auf `../repo`. Dieser Ordner ist nicht im Team-Repo; dort liegen u. a. `core/export3d.py`, GLB-Dateien und ungestagte Änderungen an `building_map.py`. Erst übernehmen, dann darauf bauen (Codex §3).
- **API-Fallen für alle Agenten:** Sonnet 5.5 und Opus 5.5 lehnen erzwungenes `tool_choice` (`any`/`tool`) und `thinking: disabled` mit 400 ab. Seit 21.10.2026 liefern `temperature`, `top_p`, `top_k` auf allen Modellen 400. Der Starter-Agent setzt keins davon, neuer Code darf es auch nicht.
- **Credits:** Plan rechnet mit 600 USD, im Kickoff klang es nach 150 USD pro Person bzw. pro Team. Einmal in der Console nachsehen.
- **`docs/elevenlabs-agent-config.md`** ist nicht committet und widerspricht dem Plan (Qwen statt Claude, „OpenAI und Gemini im Backend“, Signed URL). Nach dem A/B-Test aktualisieren und committen.

---

## 11. Ergänzung zu den Jurorenfragen

Zu **Frage 4 (Build)** ergänzen: „Wird für den Check ‚correct buildings built from plans‘ ein Planbild ohne JSON geliefert? Welches Format, mit oder ohne Maßstab?“

Zu **Frage 10 (Interaktion)** ergänzen: „Zählt eine AR-Navigation mit QR-Verankerung, die wir im eigenen Gebäude im Video zeigen, als Level-5-Erweiterung, auch wenn ihr sie nicht live auf euren Geräten testet?“

---

## 12. Noch offene Entscheidungen

1. **Demo-Gebäude:** der echte Arbeitsort (Empfehlung; braucht Import oder Fallback-Gebäude) oder ein Kit-Gebäude mit simuliertem Rundgang?
2. **Demo-Sprache:** Deutsch oder Englisch?
3. **Rollen:** Wer verantwortet UX A, UX B (Kamera), Core/Benchmark, Integration?
