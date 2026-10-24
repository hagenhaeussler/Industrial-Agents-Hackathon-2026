# ElevenLabs-Agent – Konfiguration

**Stand:** 24.10.2026. Hier steht, wie die Voice-Agents im ElevenLabs-Dashboard eingestellt werden. Wer sie nachbauen will, etwa die Jury, kann diese Werte übernehmen. Architektur und Begründungen: [Finaler Plan](../2026-10-24-plan-review-zwei-ux.md), Abschnitte 3, 6 und 9.

## Zwei Agents mit gleicher Basis

| Agent | Gerät | Aufgabe |
|---|---|---|
| **Navigator** | Desktop-Ansicht und Handy | Teile finden, Touren planen, Weg führen, Schritt für Schritt ansagen |
| **Admin** | Laptop (UX A) | Gebäude anlegen, Maßstab setzen, Änderungen vorschlagen, bestätigen, rückgängig machen |

Beide Agents bekommen dieselben Basiseinstellungen:

| Bereich | Einstellung |
|---|---|
| Stimme | Eric („Smooth, Trustworthy“, männlich, amerikanisch) |
| Sprachmodell (TTS) | Eleven v4 Turbo (`eleven_v4_turbo`) |
| Expressive Mode | an |
| Spracherkennung (ASR) | Scribe v2 Realtime (`scribe_realtime`), Qualität `high` |
| Turn-Taking | Modell `turn_v3`, Turn-Timeout 7 s |
| Sprache | Englisch (über den Prompt) |
| LLM im Agent | **Soll:** Claude Sonnet 5.5, niedriger Reasoning-Aufwand. Endgültig nach dem A/B-Test (Finaler Plan §9); das Ergebnis wird hier eingetragen. **Ist (Dashboard-Standard):** Qwen3.5-397B-A17B |
| Backup-LLM | „Default“ (nicht „Disabled“), damit ein Ausfall des Haupt-LLM das Gespräch nicht beendet |
| Sicherheit | Enable authentication an. Die App holt pro Gespräch einen **Conversation Token (WebRTC)** vom Server |

## Client-Tools

Alle Tools sind vom Typ **Client** und haben **„Wait for response“** an. Nur dann wartet der Agent auf das Ergebnis; sonst nimmt er Erfolg an. Namen und Parameter müssen **exakt** (Groß-/Kleinschreibung) mit `clientTools` im Code übereinstimmen. Die Namen unten sind der Vorschlag für den Tool-Vertrag aus P0; ab dem Einfrieren werden sie nur noch gemeinsam geändert.

**Navigator**

| Tool | Parameter | Wirkung |
|---|---|---|
| `find` | `query` (String, Pflicht): Name, Typ oder Raumnummer, wie gesagt, z. B. „3D printer“, „room 0.21“ | Treffer mit Ort; bei mehreren Treffern die Kandidaten für eine Rückfrage |
| `plan_tour` | `items` (String, Pflicht): Teile oder Orte, durch Komma getrennt; `keep_order` (Boolean, Standard false); `step_free` (Boolean) | beste Reihenfolge und Route über alle Stopps ab der aktuellen Position; liefert `tour_id` für den Übergabe-QR |
| `route` | `destination` (String, Pflicht); `step_free` (Boolean); `min_door_width_m` (Number) | Route ab der aktuellen Position aus der Sitzung, Karte bzw. Kamera zeigt sie sofort |
| `next_step` | – | nächste Anweisung mit Landmarke; in einer Tour auch der nächste Stopp |

**Admin**

| Tool | Parameter | Wirkung |
|---|---|---|
| `set_scale` | `reference` (String, Pflicht): Raum oder Wand; `length_m` (Number, Pflicht) | Maßstab eines hochgeladenen Plans setzen |
| `propose_edit` | `action` (String, Pflicht): `close`, `open`, `add_door`, `move_asset`, `set_room_type`; `target` (String, Pflicht); `second_target` (String); `value` (String) | Vorschau mit betroffenen Routen, liefert `proposal_id`, ändert nichts |
| `commit_edit` | `proposal_id` (String, Pflicht) | übernimmt die Änderung genau einmal (idempotent) |
| `undo` | – | macht die letzte eigene Änderung rückgängig |
| `what_if` | wie `propose_edit` | Was-wäre-wenn ohne Vorschlag zum Speichern |
| `generate_markers` | – | QR-Blatt für Eingänge und wichtige Türen erzeugen |

**Was kein Tool ist:** QR-Scan (Übergabe-QR mit `tour_id`, Positions-QR an Türen) und Plan-Upload laufen über die Oberfläche. Der Browser kann keinen Dateidialog aus einem Tool-Aufruf öffnen. Die App teilt dem Agenten das Ergebnis per `sendContextualUpdate` mit, z. B. „Position: north entrance, ground floor“ oder „Plan uploaded: 14 rooms detected, scale missing“. Das löst keine Antwort aus.

Ein Tool-Fehler wird als Fehler zurückgegeben, nie als „Route angezeigt“.

## Prompt-Regeln

Für beide Agents (aus `PLAN.md` §4):

- Sofort eine kurze Bestätigung sprechen, dann das Tool aufrufen.
- Landmarken statt Raumnummern.
- Genau eine Rückfrage, wenn ein Pflichtparameter fehlt oder es mehrere Treffer gibt. Nie still den ähnlichsten Treffer nehmen („Press 4“ ist nicht „Press 14“).
- Nichts erfinden: Gibt es ein Objekt oder eine Route nicht, das klar sagen.
- Positionen, Gebäude und Profil („wheelchair“) kommen aus der Sitzung, nicht aus dem Gesprächsverlauf.

Nur Navigator: höchstens drei Schritte auf einmal, dann auf „next“ warten. Fällt unterwegs etwas aus (Lift gesperrt), meldet die App das per `sendContextualUpdate`; der Agent sagt die neue Route kurz an.

Nur Admin: vor jeder Änderung `propose_edit`, die Vorschau beschreiben und auf ein klares „yes“ warten. Erst dann `commit_edit`.

## Einbindung in die App

- **Paket:** `@elevenlabs/react` (enthält `@elevenlabs/client`), Version im Lockfile festschreiben. Alle Hooks innerhalb eines `ConversationProvider`.
- **Token:** Der Server (`GET /api/voice/token?agent=navigator|admin`) ruft `https://api.elevenlabs.io/v1/convai/conversation/token?agent_id=<AGENT_ID>` mit Header `xi-api-key` auf und gibt nur den Token weiter. Der Client startet mit `startSession({ conversationToken })`.
- **Eine signierte URL gehört zur WebSocket-Verbindung** und passt nicht zu diesem Weg. Nur nutzen, wenn ausdrücklich auf `connectionType: "websocket"` umgestellt wird.

## Hinweise

- **Secrets:** `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID_NAVIGATOR` und `ELEVENLABS_AGENT_ID_ADMIN` liegen lokal in `.env` und auf Railway in den Service-Variablen, nie in dieser Datei. Der Key bleibt auf dem Server; der Browser sieht nur den kurzlebigen Token.
- **Kosten:** Das Agent-LLM wird über ElevenLabs-Credits abgerechnet, nicht über das Anthropic-Guthaben.
- **Abgabe:** Beide Agent-Konfigurationen ohne Secrets exportieren und neben diese Datei legen.

## Live preview update — 2026-10-25

The Navigator preview now allows **10 calls/day, 180 seconds/call, one concurrent call**, as approved by Hagen. Admin limits remain unchanged. This ongoing preview allowance is separate from the team's $5 paid testing budget. Authenticated tokens and the no-audio-recording privacy settings remain enabled.

The app uses a real two-way ElevenLabs WebRTC conversation with transcripts, a small audio-responsive orb, mute/End/Retry and safe connection errors. Typed messages while connected call `sendUserMessage`, keeping the current voice conversation; disconnected text chat uses the existing backend.

`desk-ui-tools.json` describes two additional **browser-only planning desk actions** (`update_selection`, `focus_floor`). They validate current building asset/floor IDs before modifying selection or floor focus. They do not add endpoints to the canonical eleven server tools. Current desk context supplies selected parts, floors, position and mobility, with session bearers and admin codes excluded. The Navigator must not invoke these two tools on phone/admin surfaces.
