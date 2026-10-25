# Fragen an Juroren und Organisatoren

**Ziel:** Die Annahmen aus dem Brainstorming vom 24. Oktober 2026 so weit klären, dass Umfang, Bewertung und technische Umsetzung zusammenpassen. Alle Antworten unten sind noch offen; dieses Dokument protokolliert keine bereits erfolgte Zusage.

Grundlage: [Meeting-Zusammenfassung](2026-10-24-brainstorming-zusammenfassung.md) und Repo-Snapshot cb51a6f. Bei „Build“ und Sonntags-Input sollten die Track-Verantwortlichen antworten, beim gemeinsamen Finale möglichst die Organisatoren.

## Einstieg für das Gespräch

> Unser Plan ist eine mobile Web-App, in der man mit dem Gebäude spricht. Ein gemeinsamer Gebäudekern berechnet Wege und räumliche Antworten; denselben Kern nutzen wir für die automatisierte Abgabe. Dazu wollen wir Gebäude aus Plänen übernehmen und per Gespräch ändern. Bevor wir zu viel in Visualisierung oder kamerabasierte Navigation investieren, möchten wir euren erwarteten Umfang und die Prüfbedingungen bestätigen.

## Zuerst klären — die acht wichtigsten Fragen

### 1. Was muss Level 4 „Build“ konkret leisten?

**Frage:** „Welche konkrete Aufgabe gebt ihr uns bei Build: ein komplett neues Gebäude aus einem Plan anlegen, ein vorhandenes verändern oder beides? Welches kleinste End-to-End-Beispiel würde diesen Teil überzeugend erfüllen?“

**Nachhaken:** Welche Planformate, Maßstabsangaben, Etagen und enthaltenen Objekte sind zu erwarten? Dürfen wir im Dialog Rückfragen stellen oder die erkannten Räume und Türen bestätigen lassen? Wie bewertet ihr Geometrie, Verbindungen und Vollständigkeit?

**Warum zuerst:** Updates sind wesentlich kleiner als vollständiger Planimport. Die README nennt beides, legt aber keinen genauen Prüfvertrag fest. Bezug: 09:15–12:08.

**Antwort / bestätigte Mindestleistung:** …

### 2. Wie hängen Testset, Sonntagsgebäude und Build-Prüfung zusammen?

**Frage:** „Wir lesen die README so: 145 Antworten auf das vorhandene Testset plus ein automatisierter Lauf auf einem neuen Gebäude. Ist das korrekt? Wird beim Sonntagslauf fertiges building.json geliefert, oder gehört Planerkennung aus PNG/PDF dort dazu beziehungsweise wird sie separat geprüft?“

**Nachhaken:** Wann erscheint das Paket, wie ist es aufgebaut, wann ist Code Freeze, und welche Ausgabedateien gehören jeweils in die Abgabe?

**Warum:** Die README sagt grundsätzlich dasselbe Gebäudeformat zu, kündigt die genaue Auslieferung aber erst zur Veröffentlichung an. Ein JSON-Ladepfad und Bildimport müssen getrennt geplant werden. Bezug: 03:31–08:10; 22:21–24:08.

**Antwort / Format / Termine:** …

### 3. Was genau steckt in den 55 Funktionspunkten?

**Frage:** „Wie verteilt ihr diese Punkte auf das veröffentlichte Testset, den Sonntags-Benchmark, Routing und Gebäudeerstellung? Gibt es Mindestanforderungen oder Ausschlusskriterien für die Finalauswahl?“

**Nachhaken:** Zählen alle Fragen gleich? Wie wirken sich ein sehr gutes Benchmark-Ergebnis und ein noch begrenzter Planimport aufeinander aus?

**Warum:** Die vier Hauptgewichte sind bekannt; die interne Gewichtung bestimmt die sinnvolle Zeitverteilung. Bezug: 00:23–01:57; 07:29–08:10.

**Antwort / Prioritäten:** …

### 4. Bleibt der Fragen- und Gebäudevertrag stabil?

**Frage:** „Können wir für die unbekannten Inputs von den dokumentierten neun Benchmark-Arten und dem vorhandenen Gebäudeschema ausgehen? Oder kommen zusätzliche Aufgabentypen, Eigenschaften oder andere Gebäudeklassen dazu?“

**Nachhaken:** Welche Abweichungen sollen wir robust behandeln: neue Raum-/Asset-Typen, viele Etagen, Untergeschosse, mehrere Gebäude oder ungewöhnliche Verbindungen?

**Warum:** Die Lösung soll generalisieren. Wir wollen generische Operationen bauen und wissen, welche Schnittstellen verbindlich sind. Bezug: 03:18–03:30; 07:42–08:03.

**Antwort / verbindliche Grenzen:** …

### 5. Wie führt ihr unseren Benchmarklauf aus?

**Frage:** „Welche Laufzeitumgebung, Internetverbindung und API-Zugänge stehen bei einem möglichen Re-Run zur Verfügung? Gibt es Zeit-, Kosten- oder Aufruflimits pro Frage und pro Gebäude?“

**Nachhaken:** Dürfen Daten vorberechnet werden? Gibt es einen Build-/Import-Zeitraum vor den Fragen? Wie sollen Schlüssel und Startkommando übergeben werden?

**Warum:** Ein Headless-Lauf mit externem LLM muss reproduzierbar funktionieren. Die im Gespräch vermuteten zehn Minuten Importzeit sind keine bestätigte Grenze. Bezug: 11:31–12:08; 24:52–26:40.

**Antwort / Limits / Umgebung:** …

### 6. Wie testet ihr die Interaktion praktisch?

**Frage:** „Wie läuft das geskriptete Nutzer-Gespräch ab: live in unserer App oder anhand einer Aufnahme? Auf welchen Geräten, Browsern und in welcher Sprache testet ihr? Welche Rolle spielen Rückfragen, Sprachlatenz und sichtbare Bestätigung vor einer Änderung?“

**Nachhaken:** Darf die Startposition durch Raumwahl, QR-Code oder Nachfrage bestimmt werden, oder erwartet ihr automatische Lokalisierung? Reicht eine responsive Web-App?

**Warum:** Voice zählt bereits laut README; ungeklärt sind Testablauf und Geräte. Die Behauptung über fehlende iPhones in der Jury ist bisher nicht bestätigt. Bezug: 02:01–03:08; 20:33–21:26; 29:34–30:38.

**Antwort / Geräte / Sprache / Startposition:** …

### 7. Welche Regeln gelten im gemeinsamen Finale?

**Frage:** „Bleiben die technischen Ergebnisse aus der Track-Auswahl im Finale relevant, oder gibt es dort ein separates Bewertungsverfahren? Nach welchen Kriterien wird entschieden, und wer bewertet?“

**Nachhaken:** Bestätigt ihr drei Minuten Pitch plus eine Minute Q&A? Live-Demo oder Video? Bewertet ihr den belegten Funktionsumfang erneut?

**Warum:** Die Annahme, im Finale zählten praktisch nur Demo und Kreativität, ist für unsere Strategie entscheidend und bislang nicht belastbar bestätigt. Bezug: 00:23–01:57.

**Antwort / Finalkriterien / Format:** …

### 8. Welche Grenzen gelten für die eingereichten Videos und die Erklärung?

**Frage:** „Welche genaue Länge und welches Format erwartet ihr für Produktdemo und technische Erklärung? Sind das zwei getrennte Artefakte? Was soll jeweils unbedingt gezeigt werden?“

**Nachhaken:** Möchtet ihr reale UI-Abläufe, neuen Planimport, Live-Sprache, Architektur oder Code sehen? Wie kennzeichnen wir vorbereitete Szenen gegenüber live berechneten Ergebnissen?

**Warum:** Im Gespräch wurden zwei Minuten und getrennte Technical-/Functionality-Teile vermutet. Die geprüfte README legt diese Längen nicht fest. Bezug: 33:15–34:12.

**Antwort / Länge / Pflichtinhalte:** …

## Wenn noch Zeit ist — vier gezielte Folgefragen

9. **Datenvertrag bestätigen:** „Für Gebäude mit fertigem JSON möchten wir unsere Ansicht daraus erzeugen. Gibt es eine Bewertung, die ausdrücklich die mitgelieferten PNGs/SVGs oder zusätzliche Bildinformationen braucht? Welche Quelle gilt bei widersprüchlichen Daten?“ Bezug: 12:33–15:12; 21:28–24:08.

10. **Änderungen präzisieren:** „Welche Änderungen wollt ihr tatsächlich sehen — Türen ergänzen, Räume ändern, Assets verschieben, Lift sperren? Müssen Änderungen dauerhaft gespeichert und für andere Nutzer sofort sichtbar sein?“ Der Starter hat bereits add_door und set_closed; Mehrnutzerbetrieb wird als optionale Erweiterung genannt. Bezug: 10:02–11:30; 44:36–45:23.

11. **Erweiterung gegenprüfen:** „Wir erwägen kamerabasierte Positionierung/AR. Ist euch für die zehn Kreativitätspunkte der zusätzliche Nutzen für reale Nutzer wichtiger als die technische Neuheit? Würde für euch eine robuste Navigation mit manueller oder QR-basierter Startposition plus einem klaren Industrie-Feature stärker wirken?“ Das ist eine Priorisierungsfrage, keine Bitte um eine Erfolgsgarantie. Bezug: 29:20–33:13.

12. **Technologiefreiheit:** „Ist der bereitgestellte Claude-/ElevenLabs-Stack optional, oder gibt es dazu konkrete Vorgaben? Dürfen wir vorhandene Open-Source-Komponenten nutzen, wenn Herkunft und Eigenleistung sauber dokumentiert sind?“ Die README beschreibt einen Claude-Starter, aus dem Gespräch folgt keine bestätigte Sponsorpflicht. Bezug: 18:28–19:40; 34:31–38:30; 42:16–43:12.

## Bereits aus dem Repo geklärt

Diese Grundlagen müssen wir nicht erneut als offene Fragen behandeln:

- Es gibt 200 Train-, 40 Dev- und 40 Testgebäude; nur Train und Dev enthalten Antworten. Die vorhandenen Testfragen sind bekannt und müssen automatisch beantwortet werden.
- Das eigentliche Benchmarkset hat neun dokumentierte Arten. Die Warm-up-Fragen sind ein anderer Satz und belegen keine gute Benchmark-Leistung.
- Ein eigenes ML-Modell zu trainieren ist keine erklärte Voraussetzung. Generische Tools und ein fertiges LLM entsprechen dem bereitgestellten Ansatz.
- Der Starter leitet den Graph bereits aus dem Gebäudemodell ab. Nachbarschaft allein ist keine begehbare Verbindung; Öffnungen und vertikale Verbinder bestimmen die Route.
- Die Track-Gewichte sind 55/25/10/10. AR, Multiuser und Asset-Tracking sind optionale Erweiterungen. Voice trägt zur Interaktion bei.
- BENCHMARK.md soll einen automatisierten Ein-Kommando-Lauf dokumentieren. Die CSV hat question_id und answer; der vorhandene Scorer wertet die letzte Answer:-Zeile aus.

Belege und unveränderliche Repo-Links stehen im Abschnitt „Quellen zum Repo-Abgleich“ der Zusammenfassung.

## Danach intern entscheiden

Die Jury klärt den Erwartungsrahmen. Diese Architekturentscheidungen bleiben bei uns:

- Ein gemeinsamer Rechenkern für Voice-App und Batch-Evaluation; die exakten API- und Datenmodelle dazu festlegen.
- Dateiablage oder Datenbank, konkrete Frameworks, Toolzuschnitt und Modellwahl anhand Aufwand und Dev-Ergebnissen bestimmen.
- Speech früh in einem kleinen Durchlauf testen oder später vollständig integrieren; einen konkreten Integrationszeitpunkt vereinbaren.
- Eine Erweiterung auswählen und für kamerabasierte Positionierung ein Zeitlimit sowie eine einfachere Ersatzlösung definieren.
- Zuständigkeiten, gemeinsamen Plan, Branch-/Commit-Ablauf und Demo-Verantwortung festlegen.

## Antworten festhalten

Für wichtige Aussagen jeweils **Antwort, Name/Rolle der Auskunftsperson, Uhrzeit und daraus folgende Entscheidung** ergänzen. Unterschiedliche Aussagen sichtbar lassen und durch die Track-Verantwortlichen klären. Nach dem Gespräch vor allem die Antworten zu Build, Sonntags-Input und Bewertungsgewicht in den gemeinsamen Plan übernehmen.
