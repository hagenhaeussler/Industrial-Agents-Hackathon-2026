# Plan – Talk to Your Building (Track 01)

**Stand:** Sa 24.10.2026, 16:45 · **Code Freeze:** So 25.10., 13:00 → **ca. 21 reale Stunden.** In der Nacht endet die Sommerzeit (3:00 → 2:00), das bringt eine Stunde extra.
**Stack:** ElevenLabs Agent mit Eleven v4 Turbo · Claude (600 USD Anthropic-Credits) · Python-Core · React-Web-App
**Grundlage:**
- dieses Team-Repo: Meeting-Notizen, Q&A mit dem Challenge-Lead, Route-Scoring-Spec, Challenge-PDF
- das offizielle Synera-Kit (`../repo/`, Commit `cb51a6f`, aktuell) mit unserer lokalen Vorarbeit
- ein Review durch Codex (gpt-6.1-sol, medium), siehe Abschnitt 9

---

## 1. Was neu ist und den Plan ändert

| # | Fund | Quelle | Folge |
|---|---|---|---|
| 1 | **Für Routen gibt es ein zweites Distanzmodell.** Gemessen wird Tür zu Tür *innerhalb* der Räume, 15 cm Abstand zur Wand, um Ecken herum. Treppe = 2 m pro Höhenmeter, Lift = 15 m + 1 m pro Höhenmeter. Bewertet wird die **Raumfolge**. Score = beste Länge ÷ unsere Länge, innerhalb 1 % gibt volle Punkte, eine ungültige Route gibt 0. | `2026-10-24-route-scoring-specifications.md` | Für Routenfragen brauchen wir ein **geodätisches Modell** (Abschnitt 4). Das README-Modell bleibt für `errand` und `what_if_door` im Testset, weil die dev-Antworten damit übereinstimmen. |
| 2 | **Neue Routing-Regeln:** Ein Gabelstapler fährt nur durch Gänge und Öffnungen ab 3 m. Produktionsbereiche sind nur Ziel, kein Transit. Eine Route zu einem Gerät endet im Raum, der es enthält. Wenn es keine Route gibt, sagen wir das. | dieselbe Datei | Das kommt als Constraints in den Graphen. In den Fabrikdaten gibt es Hallen-Öffnungen mit 4–20 m. |
| 3 | **Das Sonntagsformat ist widersprüchlich.** Das PDF verlangt `answers.json` mit Route als Knotenliste und Länge. Die README verlangt CSV mit einer `Answer:`-Zeile. | PDF vs. README | Parser und Serializer müssen austauschbar sein. Wir schreiben beide Formate und decken alle 15 Fragearten ab, auch die Warm-up-Arten. |
| 4 | **Build heißt vor allem lokale Änderungen und What-if.** Eine Web-App reicht. Post-Training ist unerwünscht. Die Jury testet mit eigenen Keys (OpenAI oder Anthropic). Im Video zählt die Interaktion am meisten. | Q&A mit dem Lead | Event-Log-Änderungen sind Pflicht, PNG-Import ist Kür. Die Jury hat keinen bestätigten ElevenLabs-Zugang. Deshalb wird die Agent-Konfiguration exportiert, und der Benchmark läuft **ohne ElevenLabs**. |

## 2. Voice-Architektur (Entscheidung)

```
Browser (React)
  ├─ @elevenlabs/react  useConversation  ── Audio ⇄ ──  ElevenLabs Agent
  │                                                     · STT, Turn-Taking, Barge-in
  │                                                     · LLM: Claude Sonnet 5.5
  │                                                     · TTS: eleven_v4_turbo (~100 ms), DE/EN
  │      clientTools: find, route, what_if, propose_edit, commit_edit, show
  │        └─ fetch → FastAPI /tools/<name>  → Ergebnis an den Agenten + sofort auf die Karte
  └─ WebSocket ⇄ FastAPI  (building_changed an alle Clients, Textchat)
FastAPI ── core/ (deterministisch)          bench/ ── Claude direkt über die Anthropic-API (Haiku 5.5)
```

**Warum Client-Tools, die an unser Backend weiterleiten:** ElevenLabs ruft das Tool im Browser auf. Der Browser fragt FastAPI, zeigt das Ergebnis **sofort** auf der Karte und gibt dem Agenten ein kompaktes JSON zurück (`expects_response`). Ein zweiter LLM-Aufruf zum Zeichnen ist nicht nötig. Wir brauchen **keinen öffentlichen HTTPS-Tunnel** für Webhooks, und es läuft lokal genauso wie bei der Jury.

Die Zustandshoheit bleibt beim Backend: Gebäudeversion pro Session, `commit_edit` nur mit `proposal_id` und idempotent. Wird die Sprache unterbrochen, darf kein Commit doppelt passieren.

**Welches LLM im Agenten?** Darüber entscheiden wir **um 17:00**, abhängig davon, wie die Kosten abgerechnet werden:
- **Phase 1 (heute, schnell):** das in ElevenLabs eingebaute `claude-sonnet-5-5`, mit niedrigem Reasoning-Aufwand. Das wird über **ElevenLabs-Credits** abgerechnet, nicht über unsere Anthropic-Credits.
- **Phase 2 (nur bei Bedarf):** ein **Custom-LLM-Endpoint**, also ein OpenAI-kompatibles `/v1/chat/completions` mit SSE in FastAPI, das Claude über unsere 600 USD aufruft. Dafür brauchen wir einen Tunnel (cloudflared), weil ElevenLabs unseren Server aus dem Netz erreichen muss. Das lohnt sich nur, wenn die ElevenLabs-Credits knapp werden oder wir Caching und Tool-Runner selbst steuern wollen. Pro Turn darf nur **eine** Seite Tools ausführen.

**Prompt-Regeln für Voice:**
- Sofort eine kurze Bestätigung sprechen, etwa „Okay, ich suche den Weg zur Presse …“.
- Höchstens drei Schritte auf einmal, dann „sag *weiter*“.
- Landmarken statt Raumnummern.
- Genau eine Rückfrage, wenn ein Pflichtparameter fehlt (Start, Breite, Etage).
- Vor jeder Änderung eine Vorschau zeigen und auf ein „Ja“ warten.
- Persona merken: Wer „Rollstuhl“ sagt, bekommt ab dann immer stufenlose Routen.

**Latenzziel (messen, nicht versprechen):** erste hörbare Reaktion unter 1 s, einfache Route auf der Karte unter 3 s. Dafür Geometrie pro Gebäude vorberechnen, möglichst nur einen fachlichen Tool-Aufruf pro Frage, kurze Tool-Ergebnisse.

**Fallback ohne Mikrofon oder Credits:** Textchat im selben UI, direkt gegen Claude mit denselben Tools.

## 3. Modelle und Budget (600 USD Anthropic)

| Einsatz | Modell | Preis pro MTok (in/out) | Grobe Rechnung |
|---|---|---|---|
| Benchmark (dev, test, Sonntag) | **Haiku 5.5** als Parameter-Extraktor mit aufgabenförmigen Tools. Sonnet 5.5 nur für nachgewiesene Problemfälle | 0,10 / 0,50 | etwa 10k in + 1k out pro Frage ≈ **0,0015 USD**. 1.000 Fragen kosten ≈ 1,50 USD |
| Chat und Voice (falls Custom LLM) | **Sonnet 5.5**, effort `low` | 2 / 10, Cache-Lesen 0,20 | ≈ 0,03–0,05 USD pro Turn. 1.000 Turns ≈ 40 USD |
| Entwicklung und Experimente | Sonnet 5.5, gezielt Opus 5.5 (4 / 20) | | |

**Ausgabenlimits** (im Console-Workspace als Limit setzen):

| Posten | Limit | Aufteilung |
|---|---|---|
| Benchmark | 200 USD | dev 60, Test 40, Sonntag 100 |
| Chat und Voice | 100 USD | |
| Entwicklung | 220 USD | |
| Reserve | 80 USD | wird nicht angetastet |

Mit Haiku bleibt der Benchmark weit unter dem Limit, der Puffer ist für den Fall gedacht, dass wir auf Sonnet wechseln müssen.

**Caching:**
- Tool-Schemas und Systemregeln stehen eingefroren am Anfang, die Frage kommt zuletzt.
- Gebäudedaten nur über Tools abfragen, **nie das ganze JSON** in den Prompt.
- `cache_control` setzen und `cache_read_input_tokens` loggen.
- Batch-API (−50 %) für große dev-Läufe, wenn die Latenz egal ist.
- Für jede Frage Kosten, Tool-Aufrufe und Latenz loggen. Ergebnisse checkpointen, bei Wiederholung nur die fehlerhaften Fragen neu laufen lassen.

## 4. Core: zwei Kostenmodelle

- **`readme`:** exakt wie `building_map.py` (Ankerpunkt, 12 m pro Etage, 15 + 6 m). Gilt für errand, what_if und die Warm-up-Routen. Wird gegen die dev-Antworten geprüft.
- **`geodesic`:** nach der Spec von Synera. Das Modell wird **im Code nach Fragetyp gewählt**, nicht vom LLM, und im Ergebnis protokolliert.
  - **Portalgraph statt Raumknoten:** Knoten sind die Türen, Kanten sind Wege innerhalb eines Raums von Tür zu Tür. Die Kosten für das Durchqueren eines Raums hängen von Eingangs- und Ausgangstür ab. Aus dem Graphen wird am Ende die Raumfolge exportiert.
  - Der Raum wird um 0,15 m nach innen verkleinert, dann wird ein Sichtbarkeitsgraph gebaut. Schmale Bereiche, die dabei zerfallen, Türen außerhalb des verkleinerten Polygons und ungültige Polygone behandeln wir ausdrücklich: Türpunkt auf den Rand projizieren, Komponenten verbinden.
  - Den kostenlosen `outside`-Knoten übernehmen wir nicht ungeprüft. Die Lift-Wartepauschale fällt nur einmal pro Fahrt an.
  - **Tests:** Handprüfbare L- und U-Räume, keine Strecke durch Wände, Konnektivität. Der Vergleich „geodätisch ≥ README“ ist **kein** gültiger Test, weil auch der README-Anker Umwege erzeugt.
- **Constraints:** `step_free, min_door_width, vehicle(forklift), allow_stairs, allow_lifts, closed, extra_doors, no_transit_types`. Produktionsbereiche bleiben als Start und Ziel erreichbar. Eine Öffnung ab 3 m beweist allein noch keinen Gabelstapler-Gang (Frage an Synera). „Gang blockiert“ heißt in der Demo, dass ein **vorhandener** Gang gesperrt wird; Teilsperrungen innerhalb einer Halle bauen wir nicht.

## 5. Was schon da ist

| Wo | Inhalt | Zustand |
|---|---|---|
| `starter_agent/building_map.py` | MultiGraph nach README, Dijkstra, Sperrungen, `add_door` | Warm-up-Oracle 369/369. Das prüft weder die Geodäsie noch die 9 Benchmark-Arten. `../repo` hat zusätzlich das Feld `node_path` |
| `../repo/core/export3d.py`, `viewer3d.html` | GLB/USD-Export, gestapelte Etagen, Route als Röhre | Funktioniert |
| `../repo/ARCHITECTURE.md`, `VIDEO_TAKEAWAYS.md`, `SYNERA.md`, `RESEARCH*.md` | Tool-Schnitt, Prompt-Regeln, ElevenLabs-Wege, Synera-Pitch-Sprache | Referenz. Voice-Weg „A“ (nur STT/TTS) ist durch Abschnitt 2 ersetzt |
| Dieses Repo | Notizen, PDFs, Skizze | `agent.py`, `.env` und `.gitignore` sind leer, `.env` ist **eingecheckt** |

Testset (145 Fragen): floor_area_total 33 · shared_walls 26 · largest_room 21 · errand 20 · wide_delivery 18 · straight_line_3d 15 · room_stacked 9 · what_if_door 3.

## 6. Arbeitspakete

| Paket | Inhalt | Fertig, wenn |
|---|---|---|
| **P0 Setup** | `.env` aus dem Git-Index nehmen, `.gitignore` füllen. Lokale Arbeit aus `../repo` übernehmen. `.env.example` mit `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID`. Ausgabenlimits setzen. ElevenLabs-Agent anlegen | Oracle grün, kein Key im Repo, Agent-ID vorhanden |
| **P1 Core-Geometrie** | area, centroid, shared_walls, stacked, distance_3d. Tests gegen die dev-`inputs` | 5 Arten ≈ 100 % auf dev und train |
| **P2 Core-Graph** | Constraints, reachable, errand, wide_delivery, step_free_count, what_if_door (Tür in der Wandmitte) | 4 Arten ≈ 100 % auf dev |
| **P3 Bench + erste Abgabe** | `python -m bench` mit Haiku: CSV + answers.json, Checkpointing, Kosten-Log. `BENCHMARK.md` | **M1:** dev-Score, Test-CSV committed |
| **P4 Geodäsie + Fahrzeuge** | Portalgraph, Gabelstapler, kein Transit durch Produktion, unerreichbare Ziele melden | Tests aus Abschnitt 4 sind grün |
| **P5 Voice-Durchstich** | Agent mit `eleven_v4_turbo` + Sonnet 5.5. Ein Client-Tool `route` → FastAPI → Route auf einer minimalen 2D-Karte | **18:30 Integrationsgate:** Gesprochene Frage zeigt eine Route |
| **P6 App** | 2D-SVG (Etagen, Polygone, Türen, Assets), alle Client-Tools, Vorschau, Bestätigung und Undo, Broadcast an alle Clients, Textchat als Fallback, Handy-Layout | **M2:** drei Demo-Abläufe live |
| **P7 Showcase** | 3D mit dem GLB-Export, animierte Route. Level 5 Logistik: Gabelstapler, Gang gesperrt, Docks | **M3:** demo-fertig |
| **P8 Kür** | PNG → Claude Vision → Validator → Vorschau | Nur mit Puffer |

## 7. Zeitplan

| Zeit | A: Core/Bench | B: Frontend | C: Voice/Agent/Demo |
|---|---|---|---|
| **Sa 16:45–17:15** | P0, Tool-Vertrag einfrieren (Namen, Parameter, Ergebnisformat) | Vite/React-Gerüst | Abrechnung klären (ElevenLabs-Credits?), Agent anlegen, Discord-Fragen stellen |
| **17:15–18:30** | P1 | Minimale 2D-Karte aus `building.json` | P5: useConversation, Client-Tool `route` → FastAPI |
| **18:30** | **Integrationsgate (alle):** Voice → Tool → Karte | | |
| **18:30–21:00** | P2 → P3 → **M1** (Test-CSV) | Karte vervollständigen, ui_events | Alle Client-Tools, Voice-Prompt-Regeln |
| **21:00–00:30** | P4 Portalgraph + Constraints | Vorschau, Bestätigung, Undo, Broadcast | Drei Demo-Abläufe, Rückfrage-Logik → **M2**. Danach keine neue Infrastruktur |
| **00:30–03:00** | Regression auf dev, Checkpointing | Handy-Test, Unterbrechungen | Rohschnitt fürs Video |
| 03:00–07:00 | **Schlafen** (dank Zeitumstellung eine Stunde mehr) | | |
| **So 07:00–09:00** | Ein dev-Gebäude wie ein unbekanntes durchlaufen lassen, finale Test-CSV, Installationsprobe auf frischem Klon | 3D, falls die Pflichtabläufe grün sind → **M3** | Härtetest mit schwierigen Nutzern |
| **ab 09:00** | **Bereitschaft für das Sonntagsgebäude:** eine Person verarbeitet es, sobald es erscheint | Bugfixes | Video aufnehmen |
| **10:00 Feature Freeze** | BENCHMARK.md, README, exportierte Agent-Konfiguration | Video schneiden | Technische Erklärung (Architektur statt Code) |
| **12:00–13:00** | Nur Abschlusslauf, Upload, Abgabe prüfen | | |

**Streichreihenfolge:** PNG-Import → 3D → zusätzliche Logistikfunktionen. **Voice bleibt Pflicht**, M1 wird nie gefährdet.

## 8. Offene Fragen an Synera (heute per Discord)

1. Gilt für die `errand`-Distanzen im **Testset** noch das README-Modell oder schon das geodätische?
2. Sonntagsformat: **`answers.json` (PDF) oder CSV (README)**? Sind die Knoten-IDs `space_id`s? Wie wird „unerreichbar“ dargestellt? Wann wird veröffentlicht, wie lange haben wir?
3. Woran erkennt man **Gabelstapler-Gänge und Fußwege** in den Daten? Welche Raumtypen sind „Produktionsbereich“?
4. Kommen am Sonntag auch locate-, route- und tour-Fragen?
5. Kann die Jury eine ElevenLabs-Agent-Konfiguration nutzen, oder reicht das Video plus Textchat?

## 9. Codex-Review: übernommen und abweichend

Übernommen:
- Abrechnung als Entscheidungspunkt um 17:00
- Portalgraph statt Raumknoten, mit den Randfällen beim Verkleinern der Polygone
- „geodätisch ≥ README“ ist kein Test
- Modellwahl im Code, nicht im LLM
- Integrationsgate um 18:30
- Haiku für den Benchmark, Sonnet für den Chat
- Budgetaufteilung
- Feature Freeze um 10:00, Zeitumstellung, „Voice bleibt Pflicht“

Abweichend:
- Codex schlägt Server-Tools (Webhooks) vor. Wir nehmen **Client-Tools, die an FastAPI weiterleiten**: kein öffentlicher Tunnel nötig, die Karte aktualisiert sich ohne Umweg, die Zustandshoheit bleibt trotzdem beim Backend.
- Codex gibt für das Lesen aus dem Cache 0,05× an. Laut Anthropic-Preisliste liegt Sonnet 5.5 bei 0,20 USD pro MTok, also 0,1×.

## 10. Demo-Story (Video, 25 Interaktionspunkte)

Fabrikhalle, drei Nutzer, eine Karte, alles per Stimme:
1. **Techniker:** „Welche Presse ist Linie 4, wie komme ich hin?“ Der Agent antwortet mit Landmarken, die Route ist animiert, die nächsten Schritte kommen auf „weiter“.
2. **Facility Manager:** „Der Ostlift ist in Wartung.“ Der Agent zeigt eine Vorschau mit den betroffenen Routen und wartet auf ein „Ja“. Danach aktualisiert sich die Karte auf allen Geräten.
3. **Gabelstaplerfahrer:** „Gang 4 ist blockiert, schnellster Weg zu Dock B?“ Die Route nutzt nur Öffnungen ab 3 m und fährt nicht durch die Produktion.
4. Aufklappbare Ansicht „So habe ich das berechnet“ mit dem Tool-Trace. Das ist Syneras Linie: *„Das LLM interpretiert, die Regeln entscheiden.“*
5. Am Ende kurz der Benchmark-Score und die Kosten pro Frage als Beleg für Effizienz.
