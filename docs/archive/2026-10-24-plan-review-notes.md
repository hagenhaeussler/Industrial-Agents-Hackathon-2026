# Review-Notizen aus PLAN.md (Stand 24.10.2026)

Aus `PLAN.md` §11 ins Archiv verschoben. Nur Geschichte.

## Codex-Review: übernommen und abweichend

Übernommen:
- Abrechnung als Entscheidungspunkt am Anfang
- Randfälle beim Verkleinern der Polygone (jetzt im Routenmodell der Jury geregelt)
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

3D bleibt Kür. Ob wir den Custom-LLM-Endpoint bauen, ist offen (Abschnitt 4). Container, Python-Core, Bildimport und native Apps sind gestrichen (Abschnitt 2).
