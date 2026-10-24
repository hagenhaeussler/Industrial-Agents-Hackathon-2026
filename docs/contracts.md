# Schnittstellen

Primäre Datei für **Schnittstellen zwischen den Teilen**: Tool-Namen, API-Endpunkte, Ereignisse, Routenergebnis, Änderungsablauf, Sitzung, QR-Links und Benchmark. Wer hier etwas ändert, sagt es allen, die die Schnittstelle nutzen. Architektur: [`architecture.md`](architecture.md).

**Stand:** Entwurf. Die Tool-Namen der Voice-Agents sind der Vorschlag aus der ElevenLabs-Konfiguration. Die Tools des Agent Harness legen wir in Phase 2 fest und tragen sie hier ein. Ab dem Einfrieren ändern wir Namen nur noch gemeinsam.

## 1. Allgemeine Regeln

- Einheiten in Metern, Koordinaten im lokalen Rahmen des Gebäudes (x rechts, y oben), wie in `building.json` (README Abschnitt 3).
- IDs sind die IDs aus `building.json` (`space_id`, `opening_id`, `connector_id`, `asset_id`).
- Jedes Tool-Ergebnis enthält `building_version` und `request_id`. Eine verspätete Antwort überschreibt keine neuere.
- Ein Fehler kommt als Fehler zurück (`{ "error": { "code", "message", "candidates"? } }`), nie als Erfolg. Bei mehreren Treffern kommen die Kandidaten für eine Rückfrage zurück.
- Tool-Ergebnisse sind kompakt, weil jedes Token Geld und Zeit kostet.

## 2. HTTP und WebSocket

| Endpunkt | Zweck |
|---|---|
| `GET /api/voice/token?agent=navigator\|admin` | Der Server holt mit `ELEVENLABS_API_KEY` einen Conversation Token (WebRTC) für den gewählten Agenten und gibt nur den Token weiter. Rate-Limit |
| `POST /api/tools/<name>` | Führt ein Tool auf der Gebäude-DB aus. Dieselben Tools wie im Agent Harness |
| `POST /api/chat` | Textchat über den Agent Harness, mit denselben Tools. Fallback ohne Mikrofon |
| `POST /api/llm/v1/chat/completions` | Nur bei Option 2 (ein Gehirn): Custom LLM für ElevenLabs, OpenAI-kompatibel, SSE |
| `WSS /ws/:building` | Ereignisse an alle Clients: `building_changed { building_id, version, event }`. Nach einem Reconnect lädt der Client den aktuellen Stand |

## 3. Client-Tools der Voice-Agents

Alle Tools sind vom Typ **Client** mit „Wait for response“. Namen und Parameter müssen exakt (auch Groß- und Kleinschreibung) mit `clientTools` im Code übereinstimmen. Jedes Client-Tool ruft `POST /api/tools/<name>` auf und zeigt das Ergebnis sofort auf der Karte.

**Navigator**

| Tool | Parameter | Wirkung |
|---|---|---|
| `find` | `query` (String, Pflicht): Name, Typ oder Raumnummer, wie gesagt, z. B. „3D printer“, „room 0.21“ | Treffer mit Ort; bei mehreren Treffern die Kandidaten für eine Rückfrage |
| `route` | `destination` (String, Pflicht); `step_free` (Boolean); `min_door_width_m` (Number) | Route ab der aktuellen Position aus der Sitzung, die Karte zeigt sie sofort |
| `next_step` | – | nächste Anweisung mit Landmarke; in einer Tour auch der nächste Stopp |
| `plan_tour` (Add-on) | `items` (String, Pflicht): Teile oder Orte, durch Komma getrennt; `keep_order` (Boolean, Standard false); `step_free` (Boolean) | gute Reihenfolge und Route über alle Stopps ab der aktuellen Position; liefert `tour_id` für den QR-Code |

**Admin**

| Tool | Parameter | Wirkung |
|---|---|---|
| `propose_edit` | `action` (String, Pflicht): `close`, `open`, `add_door`, `move_asset`, `set_room_type`; `target` (String, Pflicht); `second_target` (String); `value` (String) | Vorschau mit betroffenen Routen, liefert `proposal_id`, ändert nichts |
| `commit_edit` | `proposal_id` (String, Pflicht) | übernimmt die Änderung genau einmal (idempotent) |
| `undo` | – | macht die letzte eigene Änderung rückgängig |
| `what_if` | wie `propose_edit` | Was-wäre-wenn ohne Vorschlag zum Speichern |

**Was kein Tool ist:** QR-Scan und der Import einer `building.json` laufen über die Oberfläche. Die App teilt dem Agenten solche Ereignisse per `sendContextualUpdate` mit, z. B. „Destination from QR code: CNC mill 0.21“ oder „Lift V02 closed“. Das löst keine Antwort aus.

## 4. Änderungen: Vorschau, Bestätigung, Undo

1. `propose_edit` legt einen Vorschlag mit `proposal_id` und `expected_version` an und zeigt die betroffenen Routen. Die DB ändert sich nicht.
2. `commit_edit` übernimmt den Vorschlag genau einmal über den einen Schreibweg. Passt `expected_version` nicht mehr, kommt ein Fehler.
3. Der Schreibweg rechnet nur die betroffenen abgeleiteten Werte neu, erhöht `version` und sendet `building_changed`.
4. `undo` ist ein neues Ereignis im Event-Log, kein Löschen.
5. `what_if` rechnet auf einer Kopie und speichert nichts.

## 5. Routenergebnis

```jsonc
{
  "reachable": true,                 // false mit "reason", wenn es keine Route gibt
  "length_m": 37.75,
  "space_path": ["…-S021", "…-S030", "…-S019"],   // jeder durchquerte Raum, für die Bewertung
  "element_path": ["…-O0035", "…-V02"],          // jede Tür, Treppe und jeder Lift, je einmal
  "polyline": { "<floor_id>": [[x, y], …] },      // für Karte und AR
  "steps": [ { "text": "…", "landmark": "…" } ],  // Wegbeschreibung aus dem Core
  "constraints": { "step_free": false },
  "building_version": 12,
  "request_id": "…"
}
```

Eine Tour ist eine Liste solcher Teilstrecken plus `tour_id` und Fortschritt.

## 6. Sitzung und QR-Links

- **Sitzung** (Server): Gebäude, Ziel oder Tour, Position falls bekannt, Profil (zum Beispiel `wheelchair` → immer stufenlos). Der Agent nimmt diese Werte aus der Sitzung, nicht aus dem Gesprächsverlauf.
- **QR-Link** vom Desktop zum Handy (Vorschlag): `https://<app>/nav/asset/<asset_id>` für ein Objekt, `https://<app>/nav/tour/<tour_id>` für eine Tour. Die normale Kamera-App des Handys öffnet damit die Mobile-Ansicht. Der Link ortet niemanden.

## 7. Benchmark

- **Offizieller Evaluator:** `uv run --env-file .env python -m benchmark.evaluate data/dev --agent bench.answer:answer`. `bench/answer.py` implementiert `answer(building_directory: Path, question_text: str) -> str` und ruft unsere TypeScript-CLI auf. In Phase 2 wird unser Agent der Standard, wenn `--agent` fehlt.
- **Antwortformat:** Die letzte Zeile, die mit `Answer:` beginnt, zählt. Regeln und Toleranzen pro Fragetyp: README Abschnitt 6. Vorschlag: Der Agent gibt die Antwort über ein typisiertes Tool ab, und der Code schreibt die `Answer:`-Zeile. Bei Fragetypen mit genau einer Zahl steht in der Zeile keine zweite Zahl, auch kein „m²“, weil die „2“ als Zahl zählt.
- **Abgabe:** eine CSV `question_id,answer` mit allen 145 Testfragen (README Abschnitt 6). `answers.json` nur, falls Synera es für das Sonntagsgebäude verlangt ([`PLAN.md`](../PLAN.md) §6).
