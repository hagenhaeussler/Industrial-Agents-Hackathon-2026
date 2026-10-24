# ElevenLabs-Agents – Konfiguration

Primäre Datei für **die Einstellungen im ElevenLabs-Dashboard und das Gesprächsverhalten**. Wer die Agents nachbauen will, etwa die Jury, kann diese Werte übernehmen. Die Client-Tools und der Token-Endpunkt stehen in [`contracts.md`](contracts.md) §2 und §3, die Voice-Architektur in [`architecture.md`](architecture.md) §5.

## 1. Zwei Agents mit gleicher Basis

| Agent | Gerät | Aufgabe |
|---|---|---|
| **Navigator** | Handy (Navigation) und Desktop | Teile und Räume finden, Weg führen, Schritt für Schritt ansagen. Touren über mehrere Teile als Add-on |
| **Admin** | Desktop (Verwaltung) | Objekte verschieben, Bereiche sperren, Änderungen vorschlagen, bestätigen und rückgängig machen, What-if |

## 2. Basiseinstellungen

| Bereich | Einstellung |
|---|---|
| Stimme | Eric („Smooth, Trustworthy“, männlich, amerikanisch) |
| Sprachmodell (TTS) | Eleven v4 Turbo (`eleven_v4_turbo`) |
| Expressive Mode | an |
| Spracherkennung (ASR) | Scribe v2 Realtime (`scribe_realtime`), Qualität `high` |
| Turn-Taking | Modell `turn_v3`, Turn-Timeout 7 s |
| Sprache | Englisch (über den Prompt) |
| LLM im Agent | **Soll:** Claude Sonnet 5.5, niedriger Reasoning-Aufwand. Offen, ob das LLM in ElevenLabs bleibt oder ElevenLabs unseren Agent Harness als Custom LLM nutzt ([`PLAN.md`](../PLAN.md) §6). **Ist (Dashboard-Standard):** Qwen3.5-397B-A17B |
| Backup-LLM | „Default“ (nicht „Disabled“), damit ein Ausfall des Haupt-LLM das Gespräch nicht beendet |
| Sicherheit | Enable authentication an. Die App holt pro Gespräch einen Conversation Token (WebRTC) vom Server |
| Client-Tools | Typ **Client**, „Wait for response“ an. Nur dann wartet der Agent auf das Ergebnis; sonst nimmt er Erfolg an. Liste in [`contracts.md`](contracts.md) §3 |

## 3. Gesprächsregeln

Gelten für beide Agents und für den Textchat.
- Sofort eine kurze Bestätigung sprechen, dann das Tool aufrufen, etwa „Okay, I'm looking up the way to the press …“.
- Landmarken statt Raumnummern.
- Genau eine Rückfrage, wenn ein Pflichtparameter fehlt (Start, Breite, Etage) oder es mehrere Treffer gibt. Nie still den ähnlichsten Treffer nehmen („Press 4“ ist nicht „Press 14“).
- Nichts erfinden: Gibt es ein Objekt oder eine Route nicht, das klar sagen. „Keine Route“ ist eine gültige Antwort.
- Ein Tool-Fehler wird als Fehler gesagt, nie als „Route angezeigt“.
- Gebäude, Ziel, Position (falls bekannt) und Profil kommen aus der Sitzung, nicht aus dem Gesprächsverlauf. Wer „wheelchair“ sagt, bekommt ab dann immer stufenlose Routen.
- **Keine Gebäudedaten im Prompt.** Alles kommt über Tools.

Nur Navigator: höchstens drei Schritte auf einmal, dann auf „next“ warten. Fällt unterwegs etwas aus (Lift gesperrt), meldet die App das per `sendContextualUpdate`; der Agent sagt die neue Route kurz an.

Nur Admin: vor jeder Änderung `propose_edit`, die Vorschau beschreiben und auf ein klares „yes“ warten. Erst dann `commit_edit`.

## 4. Einbindung in die App

- **Paket:** `@elevenlabs/react` (enthält `@elevenlabs/client`), Version im Lockfile festschreiben. Alle Hooks innerhalb eines `ConversationProvider`.
- **Token:** Der Server ruft `https://api.elevenlabs.io/v1/convai/conversation/token?agent_id=<AGENT_ID>` mit Header `xi-api-key` auf und gibt nur den Token weiter. Der Client startet mit `startSession({ conversationToken })`.
- **Eine signierte URL gehört zur WebSocket-Verbindung** und passt nicht zu diesem Weg. Nur nutzen, wenn ausdrücklich auf `connectionType: "websocket"` umgestellt wird.

## 5. Hinweise

- **Secrets** (Namen in [`architecture.md`](architecture.md) §3) liegen lokal in `.env` und auf Railway in den Service-Variablen, nie in dieser Datei.
- **Kosten:** Das Agent-LLM wird über ElevenLabs-Credits abgerechnet, nicht über das Anthropic-Guthaben.
- **Abgabe:** Beide Agent-Konfigurationen ohne Secrets exportieren und neben diese Datei legen.
