# Hackathon-Brainstorming — Zusammenfassung und Arbeitsstand

**Stand:** 24. Oktober 2026. Grundlage ist das ca. 50-minütige Fireflies-Meeting „Oct 24, 02:08 PM“. Gesprächsaussagen sind unten vom nachträglichen Repo-Abgleich und von Empfehlungen getrennt.

**Dateien:** [Bereinigtes Transkript](2026-10-24-brainstorming-transkript.md) · [Fragen für Juroren und Organisatoren](../archive/2026-10-24-fragen-an-juroren.md) · [Fireflies-Quelle](https://app.fireflies.ai/view/01M5PX0WV7MKXJ3VN6CXRAQH74).

Fireflies liefert keine verifizierten Sprechernamen und meldet teilweise fehlende Felder. Deshalb werden hier keine Aufgaben oder Zusagen einzelnen Personen zugeschrieben. Die Zeitmarken beziehen sich auf die Aufzeichnung.

## 1. Die Richtung des Gesprächs

Ihr wollt ein Gebäude über natürliche Sprache zugänglich machen: Dinge finden, Wege berechnen, Einschränkungen berücksichtigen und Änderungen am Gebäude erfassen. Dafür sollen zwei Wege denselben Gebäudekern verwenden: die sichtbare, möglichst sprachbasierte App und ein automatisierter Lauf auf den Bewertungsfragen. Diese Trennung wurde früh erkannt (02:01–03:30).

Die stärkste gemeinsame Richtung ist eine mobile Web-App für die Navigation und eine größere Verwaltungsansicht zum Anlegen oder Bearbeiten von Gebäuden. Ein QR-Code am Eingang könnte den Einstieg in die Website ermöglichen. Eine eigene native App wurde erwogen; nach der Diskussion wirkte eine Website ausreichend, beschlossen wurde das nicht abschließend (19:45–21:26).

## 2. Architektur, die ihr diskutiert habt

**Nutzer → Sprachschicht → LLM-Agent → Werkzeuge und Gebäudedaten → Darstellung und gesprochene Antwort.**

- **Gebäudedaten:** JSON als veränderbares Arbeitsformat; eine Datenbank als mögliche gemeinsame Ablage. Eine konkrete Datenbank oder ihr tatsächlicher Bedarf wurde nicht festgelegt (16:03–16:34; 21:28–22:17).
- **Agent:** Ein LLM liest Daten, stößt Änderungen an und ruft Rechenwerkzeuge auf. Claude ist ein naheliegender Kandidat; zeitweise wurden auch andere Modellfamilien und eigenes Training diskutiert. Die genannten Modellversionen sind im Transkript teilweise unklar (18:28–19:40; 24:52–26:40; 42:16–43:12).
- **Sprache:** ElevenLabs als Sprachschicht beziehungsweise Agent-Plattform. Noch offen war, ob dessen eingebundenes LLM genügt oder ein eigener Agent dahintersteht. Die genaue Version ist im Transkript nicht zuverlässig erkennbar (25:36–26:12; 49:41–50:02).
- **Berechnung:** Separate Tools für Flächen, Entfernungen und ähnliche Fragen. Die Diskussion schwankte zwischen wenigen generischen Read-/Write-/Calculate-Tools und spezifischen Funktionen beziehungsweise Skills (28:29–29:10; 48:15–48:54).
- **Darstellung:** Gebäudeansicht aus den strukturierten Daten, möglichst mit sichtbarer Route. Eine isometrische oder dreidimensionale Ansicht wurde gewünscht; eine funktionsfähige Kameralösung war als Erweiterung gedacht (02:17–03:08; 27:24–28:25).

**Noch kein endgültiger Stack:** Frontend-Framework, API-Schnittstelle, Datenbankprodukt, Modellrouting und die genaue Trennung zwischen ElevenLabs und eigener Agent-Logik wurden im Gespräch nicht beschlossen.

## 3. Produkt und mögliche Differenzierung

Zwei Nutzergruppen kristallisierten sich heraus: Eine verwaltende Person lädt Pläne hoch und ändert das Gebäude; eine Person vor Ort sucht Dinge und lässt sich navigieren (20:33–21:26; 34:01–34:12).

Die umfangreichste Zusatzidee war kamerabasierte Positionierung: Das Gebäude einmal aufnehmen beziehungsweise rekonstruieren, anschließend die Kameraansicht eines Nutzers damit abgleichen und die Route darüberlegen. Gaussian Splatting, Feature-Matching, eine Minimap und ein Avatar wurden genannt. Das sind Ideen, keine nachgewiesene Lösung. Ein konkretes Verfahren und dessen Genauigkeit wurden nicht validiert (29:20–33:13; 45:42–46:24).

Weitere Themen waren bewegliche Assets, mehrere Nutzer und plattformübergreifende Nutzung. Es wurde keine einzelne Erweiterung verbindlich gewählt. Die Aussage, die Jury habe keine iPhones, stammt aus dem Gespräch und ist nicht unabhängig bestätigt (17:36–17:48; 29:34–30:38).

## 4. Strategie und Zusammenarbeit

Im Gespräch gab es die Annahme, zunächst die Track-Jury mit Funktionalität überzeugen zu müssen und im Finale stärker auf Demo und Kreativität zu setzen. Eine Person berichtete dazu ein Gespräch mit einem Organisator. Die genaue Finalbewertung wurde nicht belegt; insbesondere ist „der Code ist im Finale egal“ eine Gesprächsinterpretation, keine gesicherte Regel (00:23–01:57).

Ihr wollt vorhandene Projekte recherchieren und geeignete Komponenten nutzen, statt alle Features neu zu bauen. Navigatum und Architektur-/Rekonstruktionsprojekte wurden angesprochen; eine endgültige Auswahl gab es nicht. Gemeinsames Sammeln der Links, ein abgestimmter Plan und nachvollziehbare Commits waren wichtige Themen (34:31–41:49).

Offen blieb die Reihenfolge: Speech früh integrieren oder erst Agent, Datenhaltung und Darstellung fertigstellen. Auch bei „erst planen, dann bauen“ gegenüber schrittweiser Umsetzung gab es unterschiedliche Vorstellungen. Ein vollständiger Implementierungsplan, feste Zuständigkeiten und belastbare Zeitbudgets sind aus dem Gespräch nicht ableitbar (40:28–41:49; 49:00–50:02).

## 5. Nachträglicher Abgleich mit dem vorhandenen Repo

Geprüft wurde der lokale Snapshot **cb51a6f2e357db743b0c8b2b377fe902ee3ced13**. Diese Feststellungen korrigieren keine Äußerungen im Transkript, sondern ordnen sie ein.

| Gesprächsthema | Was sich bereits belegen lässt | Was offen bleibt |
|---|---|---|
| Datensplits | Train: 200 Gebäude/517 Benchmarkfragen; Dev: 40/138; Test: 40/145. Train und Dev enthalten Antworten, Test nicht. | Konkrete Sonntags-Auslieferung und Fristen. |
| Abgabe | Die 145 Testantworten sind Teil der Einreichung. Zusätzlich kommt ein neues Sonntagsgebäude mit Fragen; dessen Lauf soll ohne manuelle Zwischenschritte funktionieren und in BENCHMARK.md dokumentiert werden. | Gewicht der einzelnen Prüfungen innerhalb der 55 Funktionspunkte; exaktes Sonntagsformat. |
| Fragenumfang | Die README nennt neun Benchmark-Arten: largest_room, floor_area_total, errand, wide_delivery_count, step_free_reachable_count, room_stacked, shared_walls_count, straight_line_3d, what_if_door. Die sechs Warm-up-Arten sind davon getrennt. | Ob zusätzliche, bisher nicht dokumentierte Arten geprüft werden. |
| Eigenes Modelltraining | Kein eigenes Training ist vorgeschrieben. Der Starter verwendet ein fertiges LLM mit deterministischen Tools. Die README fordert Generalisierung und automatisch erzeugte Antworten statt manueller Testantworten oder gebäudespezifischem Hardcoding. | Ob ihr für euren Ansatz einen messbaren Nutzen durch Fine-Tuning findet; das ist eine interne Entscheidung. |
| JSON und Graph | JSON enthält Geometrie, Räume, Öffnungen, Verbindungen und Assets. building_map.py baut daraus bereits einen NetworkX-MultiGraph und berechnet Dijkstra-Routen. Ein zusätzliches Graph-Dateiformat wird dafür nicht benötigt. | Welche zusätzlichen Eigenschaften und Operationen eure Benchmark-Tools benötigen. |
| PNG/SVG | Für die mitgelieferten Gebäude lädt der Starter building.json. viewer.py zeichnet daraus 2D-Routenbilder. Die bloße Existenz von PNGs verpflichtet diesen Ladepfad nicht zu Bilderkennung. | Anforderungen an den Import eines wirklich neuen Plans ohne fertiges JSON. Exakte Gleichheit aller Bilddetails wurde nicht geprüft. |
| Level 4 „Build“ | Die Aufgabenbeschreibung nennt ausdrücklich neue Gebäude oder Updates aus Floorplans per Gespräch. Der Starter kann lediglich als Anfang eine Tür hinzufügen und das geänderte JSON speichern. Vollständiger Planimport fehlt. | Zulässiger Input, erlaubte Rückfragen/Korrekturen, Genauigkeit und Prüfumfang. |
| Stand des Starters | Suche, mehrgeschossige Routen, Sperrungen, Türergänzung und statische PNG-Ausgabe sind vorhanden. Die README berichtet unter 5 % auf dem eigentlichen Benchmark; hier wurde kein eigener Benchmarklauf durchgeführt. | Euer Ergebnis nach Erweiterung der Tools. Ein leicht erreichter Top-vier-Platz ist bislang eine Annahme. |
| Bewertung | 55 Funktion, 25 Interaktion, 10 Kreativität, 10 Submission-Demo. Vier Track-Finalisten; dort drei Minuten Pitch plus eine Minute Q&A. | Bewertungsverfahren und Gewichtung im gemeinsamen Finale. |
| Voice und AR | Voice zählt zur Interaktion. AR ist eine optionale Erweiterung. Die README empfiehlt zunächst einen durchgängigen Ablauf auf einem Floor und erlaubt eine flache 2D-Darstellung als Start. | Testgeräte, Browser und Erwartungen an Live-Positionierung. |

## 6. Entscheidungen für die nächste Teamabsprache

Diese Punkte waren am Ende noch offen:

1. Welcher vollständige Nutzerablauf ist euer verbindlicher erster Meilenstein?
2. Welche Werkzeuge decken die neun Benchmark-Arten zuverlässig ab, und wer betreut deren Umsetzung und Dev-Auswertung?
3. Wie viel Zeit reserviert ihr für Planimport, sobald dessen Anforderungen bestätigt sind?
4. Genügt zunächst JSON beziehungsweise Dateiablage, oder braucht ihr sofort eine gemeinsame Datenbank?
5. Nutzt ihr ElevenLabs zur Agent-Orchestrierung oder als Sprachschicht um einen eigenen Text-Agent? Wann wird der erste Sprachdurchlauf getestet?
6. Welche **eine** Erweiterung rechtfertigt ihren Aufwand? Kameralokalisation/AR braucht einen klaren Abbruchpunkt und eine einfachere Ersatzlösung.
7. Wer verantwortet Integration, Benchmark-Abgabe, Demo und das Festhalten der Organisatoren-Antworten?

**Redaktioneller Vorschlag für den nächsten Schritt:** Zuerst die priorisierten Jurorenfragen klären. Parallel kann das Team den vorhandenen Routingkern und die Dev-Fragen verstehen. Danach einen gemeinsamen Ablauf aus Daten laden, Frage beantworten und Route anzeigen festlegen und in kleinen überprüfbaren Schritten integrieren. Benchmark und App sollten dieselben Rechenfunktionen verwenden; die Bewertung muss ohne Mikrofon oder UI ausführbar sein. Das ist eine Empfehlung aus dem Quellenabgleich, kein im Meeting gefasster Beschluss.

## Quellen zum Repo-Abgleich

- [README: Levels, Bewertung und Einreichungsprozess](https://github.com/Synera-GmbH/industrial-agents-hackathon-2026/blob/cb51a6f2e357db743b0c8b2b377fe902ee3ced13/README.md#L43-L112).
- [README: Daten und Fragen](https://github.com/Synera-GmbH/industrial-agents-hackathon-2026/blob/cb51a6f2e357db743b0c8b2b377fe902ee3ced13/README.md#L116-L281).
- [README: Evaluation, Submission und Regeln](https://github.com/Synera-GmbH/industrial-agents-hackathon-2026/blob/cb51a6f2e357db743b0c8b2b377fe902ee3ced13/README.md#L285-L362).
- Starter-Dokumentation, Routingkern, Tools und Viewer aus `starter_agent/` (inzwischen entfernt, siehe Git-Historie) und [Evaluator](../../benchmark/evaluate.py).
