# Weitere Aufnahmen vom 24.10.2026 — relevante Informationen zum Hackathon

**Zweck:** Bereinigte Ergänzung zu unserem Brainstorming für Track 01 „Talk to Your Building“. Enthalten sind nur Informationen aus den drei weiteren heute auffindbaren Fireflies-Aufnahmen, die unseren Umfang, unsere Architektur, Bewertung oder Organisation betreffen. Dies ist eine Zusammenfassung, kein Volltranskript.

**Einordnung:** Die Sprecherzuordnung zu Personen ist in Fireflies nicht verifiziert. „Challenge-Vorstellung“ und „Q&A“ beschreiben den erkennbaren Gesprächskontext; sie sind keine unabhängig bestätigten Rollen einzelner Sprecher. Alle drei Abrufe melden teilweise fehlende Felder. Fachbegriffe wurden vorsichtig bereinigt, unklare Namen und Modellbezeichnungen nicht als Fakten übernommen. Audio wurde nicht geprüft; einzelne Textenden liegen vor der angegebenen Aufnahmedauer.

## 1. Durchgesehene Quellen

Zeiten in Europe/Berlin; Zeitmarken in den folgenden Abschnitten sind relativ zur jeweiligen Aufnahme.

| Quelle | Originaltitel / Beginn | Dauer laut Fireflies | Relevanter Inhalt |
|---|---|---|---|
| [A — Fireflies](https://app.fireflies.ai/view/01M5PGDZKDZZ2PHNGSCG6ZZTVJ) | „Oct 24, 10:28 AM“, ca. 10:28 Uhr | ca. 45:10 | Synera-Vorstellung und Challenge bis ca. 07:45; allgemeine Jury-, Plattform- und Organisationshinweise ab ca. 33:16. |
| [B — Fireflies](https://app.fireflies.ai/view/01M5PKW4MCA9JB3H5CMT3M0AM8) | „Oct 24, 11:29 AM“, ca. 11:29 Uhr | ca. 08:37 | Challenge-Q&A zu Datensatz, räumlichem Denken, Implementierungsfreiheit und Evaluation. |
| [C — Fireflies](https://app.fireflies.ai/view/01M5PMCG1BH826ZQ6W0PD2DQCS) | „Oct 24, 11:38 AM“, ca. 11:38 Uhr | ca. 07:56 | Fortgesetzte Q&A: Nutzwert und UX, Selbstbewertung, freie Ansätze und Wi-Fi als optionale Idee. |

Die vierte heute auffindbare Aufnahme, das 50-minütige Brainstorming ab 14:08 Uhr, ist bereits [separat zusammengefasst](2026-10-24-brainstorming-zusammenfassung.md) und wird hier nicht erneut ausgewertet. Die Präsentationen der anderen Tracks wurden ebenfalls durchgesehen; deren spezifische Regeln werden nicht auf Track 01 übertragen.

## 2. Die wichtigsten zusätzlichen Erkenntnisse

### Nutzwert und Interaktion sind ein zentraler Teil der Aufgabe

Die Challenge wird als zugängliches Beispiel für die Interaktion mit technischen Systemen erklärt: nicht bloß Analysefähigkeit zeigen, sondern herausfinden, was einem Nutzer wirklich hilft. Kontextbezogene Änderungen, verständliche visuelle Rückmeldung und ein Agent, mit dem man das System bedienen kann, werden betont. Eine reine Zahl oder eine isolierte Chat-Antwort deckt diese Erwartung nicht vollständig ab. [Quelle C](https://app.fireflies.ai/view/01M5PMCG1BH826ZQ6W0PD2DQCS), 00:17–01:33 und 02:48–03:07.

**Für unsere Idee:** Mobile Navigation und Verwaltungsansicht sollten konkrete Handlungen ermöglichen: Ort finden, Einschränkung nennen, Route sehen, Änderung verständlich bestätigen. Das passt zur vorgeschlagenen Kombination aus Sprache und Karte. Dies ist eine Ableitung für unser Produkt, kein zusätzlich angekündigtes Pflichtfeature.

### Die Grundstufen bleiben Locate → Route → Scale → Build

In der Vorstellung wird der Ablauf beschrieben: erst Dinge finden, dann dorthin navigieren, anschließend mehrere Etagen beziehungsweise Gebäude unterstützen und schließlich neue Gebäude ergänzen oder das System pflegen. Als industrieller Kontext werden auch gelieferte beziehungsweise künftig eintreffende Materialien genannt. Voice, AR und Wi-Fi werden anschließend als mögliche Richtungen genannt. [Quelle A](https://app.fireflies.ai/view/01M5PGDZKDZZ2PHNGSCG6ZZTVJ), 04:37–06:57.

**Einordnung:** Die Materialbeispiele zeigen den gewünschten Praxisbezug. Sie belegen keine zusätzlich vorgeschriebene Lager- oder Lieferdatenintegration. Der genaue Testumfang von Build bleibt auch nach diesen Aufnahmen offen.

### Wi-Fi-Positionierung wird ausdrücklich nicht erwartet

Auf die Frage, woher Daten zur Wi-Fi-Triangulation kommen sollen und ob man diese annehmen dürfe, folgt keine Zusage eines Datensatzes. Die Idee sei als Anregung genannt worden; später wird ausdrücklich gesagt, dass Wi-Fi nicht erwartet werde. [Quelle C](https://app.fireflies.ai/view/01M5PMCG1BH826ZQ6W0PD2DQCS), 04:14–04:53 und 05:11–05:12.

**Konsequenz:** Wi-Fi-Tracking ist keine Voraussetzung. Die Frage legitimiert auch keine erfundenen Positionsdaten als echte Messung. Kamera, AR und kontinuierliche Lokalisierung bleiben mögliche Erweiterungen; die vorliegenden Aufnahmen liefern dafür keine fertige Datenbasis oder validierte Lösung.

### Python, RAG und ein bestimmter Lösungsweg sind nicht vorgeschrieben

Der Starter wird als bewusst einfaches Python-Beispiel mit begrenzten Tools beschrieben. Andere Programmiersprachen und Ansätze werden ausdrücklich zugelassen. Ein Graph mit kürzesten Wegen wird als möglicher Ansatz genannt. Auf „Spatial RAG“ wird sinngemäß geantwortet: RAG oder ein anderer Ansatz, die Umsetzung liegt beim Team. [Quelle B](https://app.fireflies.ai/view/01M5PKW4MCA9JB3H5CMT3M0AM8), 04:23–05:04; [Quelle C](https://app.fireflies.ai/view/01M5PMCG1BH826ZQ6W0PD2DQCS), 03:09–03:32.

**Konsequenz:** Unsere Python-/Graph-Architektur passt, eigenes Modelltraining oder ein Vektorspeicher sind dadurch aber nicht gefordert. Ein konkretes Datenbankprodukt oder zusätzliches LLM-Framework lässt sich aus den Aussagen nicht ableiten.

### Räumliche Fragen gehen deutlich über Navigation hinaus

Die Q&A nennt neben Raumflächen ausdrücklich What-if-Änderungen an Türen und Fragen zu Wasserlecks zwischen Räumen beziehungsweise Etagen. Betont werden räumliches Denken, Geometrie und dreidimensionales Verständnis. Die Daten werden als 2D-Pläne beschrieben, die man zu einer 3D-Ansicht weiterverarbeiten kann. Planbilder in PNG und SVG, Equipment mit Positionen sowie JSON-Layouts werden als verfügbar beschrieben. [Quelle B](https://app.fireflies.ai/view/01M5PKW4MCA9JB3H5CMT3M0AM8), 03:15–04:50 und 05:47–07:06.

**Konsequenz:** Unsere Tools müssen Flächen, Nachbarschaften, Etagenbeziehungen und veränderte Erreichbarkeit abdecken. Eine schöne 3D-Ansicht allein löst diese Aufgaben nicht. Der in der Aufnahme undeutlich erwähnte externe Spatial-Benchmark und Modellranglisten werden mangels eindeutigem Namen hier nicht als belastbare Referenz übernommen.

### Automatische Antworten und Generalisierung werden hervorgehoben

Bekannte Testlayouts und Fragen sind verfügbar, deren Antworten werden zurückgehalten. Zusätzlich wird eine verdeckte Evaluation erwähnt. Manuelles Betrachten einzelner Fragen beziehungsweise Graphen und anschließendes Eintragen der Antworten wird ausdrücklich als ungeeignet beziehungsweise unzulässig beschrieben; die Lösung soll skalierbar durch das System entstehen. Vor Overfitting wird gewarnt. [Quelle B](https://app.fireflies.ai/view/01M5PKW4MCA9JB3H5CMT3M0AM8), 05:04–05:46; [Quelle C](https://app.fireflies.ai/view/01M5PMCG1BH826ZQ6W0PD2DQCS), 04:57–05:09.

**Einordnung:** Das bestätigt den Grundgedanken des Repo-Benchmarks. Eine grobe mündliche Angabe von „etwa 700 Fragen“ ersetzt keine Submission-Spezifikation: Maßgeblich für den geprüften Repo-Snapshot sind die 145 veröffentlichten Testfragen und die dort angekündigte zusätzliche Sonntagsprüfung.

### Selbstbewertung ist vorgesehen; die Gesamtbewertung bleibt breiter

Auf die Frage nach einer Scoring-Plattform wird auf die vorhandenen Validierungsdaten und die Möglichkeit zur eigenen Auswertung verwiesen. Gleichzeitig wird erklärt, dass Genauigkeit nur ein Teil der Bewertung ist; Interaktion und Herangehensweise zählen ebenfalls. Ein reines Leaderboard würde diese Aspekte nicht vollständig abbilden. [Quelle C](https://app.fireflies.ai/view/01M5PMCG1BH826ZQ6W0PD2DQCS), 01:58–03:07.

**Konsequenz:** Dev-Auswertung und eine glaubwürdige Nutzerdemo parallel entwickeln. Die Aussage liefert keine neue Gewichtung und ersetzt die dokumentierten 55/25/10/10 Punkte nicht.

## 3. Organisation und Unterstützung, die für uns relevant sind

- **Zentrale Plattform:** „Hack and More“ wird als Zugang für Briefs, Challenges, API-Zugänge beziehungsweise Credits und Einreichung beschrieben. Discord dient für Ankündigungen, Kommunikation und Rückfragen. Die konkrete Portaladresse ist aus dem Text nicht zuverlässig rekonstruierbar. [Quelle A](https://app.fireflies.ai/view/01M5PGDZKDZZ2PHNGSCG6ZZTVJ), 37:54–38:24 und 40:18–41:08.
- **Credits:** Im Kickoff werden 150 US-Dollar Anthropic-Guthaben pro Team sowie zusätzliche ElevenLabs- und Lovable-Credits angekündigt. Das ist eine aufgezeichnete Ankündigung, keine Prüfung unseres tatsächlich verfügbaren Kontingents. [Quelle A](https://app.fireflies.ai/view/01M5PGDZKDZZ2PHNGSCG6ZZTVJ), 37:54–38:22.
- **Andere Modellanbieter:** In der Q&A klingt an, dass andere Anbieter genutzt werden können, hierfür aber keine Credits gestellt werden. Der Wortlaut ist teilweise beschädigt; eine exklusive Claude-Pflicht ergibt sich daraus nicht. Konkrete Providerregeln und eigene Kosten bei Bedarf bestätigen lassen. [Quelle B](https://app.fireflies.ai/view/01M5PKW4MCA9JB3H5CMT3M0AM8), 07:08–07:19.
- **Einreichung:** Es wird ein zentrales Formular mit Artefakten und je nach Track zusätzlicher Abgabe beschrieben. Für bestimmte Artefakte wird Google Drive als möglicher Übertragungsweg genannt. Welche Felder und Freigaben genau für Track 01 gelten, muss im eigenen Formular geprüft werden. Eine im Vortrag gezeigte Beispiel-Deadline ist ausdrücklich eine Plattformdemo. [Quelle A](https://app.fireflies.ai/view/01M5PGDZKDZZ2PHNGSCG6ZZTVJ), 38:27–39:18 und 42:19–43:02.
- **Orte und Ablauf:** Tacto ist für Kickoff und Finale vorgesehen, Munich Urban Colab für das Arbeiten. Für Sonntag, 25. Oktober, wird ein gemeinsamer Rückweg um 14:30 Uhr angekündigt. Das ist der Stand der Aufnahme; aktuelle Zeiten und Code Freeze im Portal beziehungsweise Discord prüfen. Eine allgemeine Erwähnung von 13:00 Uhr ist im Transkript lückenhaft und wird hier nicht als bestätigte Abgabefrist übernommen. [Quelle A](https://app.fireflies.ai/view/01M5PGDZKDZZ2PHNGSCG6ZZTVJ), 35:53–36:35 und 38:27–38:45.
- **Gemischte Finaljury:** Angekündigt werden Perspektiven aus Venture Capital, Industrial AI und den Technikleitungen der Startups. Das spricht für eine auch außerhalb unseres Tracks verständliche Demo. Die exakten Namen und die Gewichtung lassen sich aus der Aufnahme nicht zuverlässig bestimmen. [Quelle A](https://app.fireflies.ai/view/01M5PGDZKDZZ2PHNGSCG6ZZTVJ), 33:16–33:58.
- **Fragen stellen:** Partner-Office-Hours und Discord werden als Unterstützungswege genannt. Für technische Plattformfragen stellt sich Sid vor; weitere Namen sind teilweise unklar. [Quelle A](https://app.fireflies.ai/view/01M5PGDZKDZZ2PHNGSCG6ZZTVJ), 36:42–37:12 und 40:18–40:25; [Quelle B](https://app.fireflies.ai/view/01M5PKW4MCA9JB3H5CMT3M0AM8), 08:15–08:20.

## 4. Was dadurch bei unseren offenen Fragen klarer wird

| Bisherige Frage | Neuer Informationsstand | Noch zu klären |
|---|---|---|
| Müssen wir Wi-Fi oder automatische Lokalisierung bauen? | Wi-Fi ausdrücklich nicht erwartet; Erweiterungen als Anregung. | Welche Startpositionswahl für den konkreten Interaktionstest akzeptiert wird. |
| Müssen wir Python, RAG oder eigenes Training verwenden? | Sprache und Ansatz flexibel; kein solches Muss aus der Q&A. | Providerbedingungen, falls wir vom bereitgestellten Angebot abweichen. |
| Sind Testfragen und Layouts schon bekannt? | Ja, die vorhandenen Fragen und Layouts; Antworten bleiben verborgen. Zusätzlich wird verdeckte Evaluation erwähnt. | Exakte Auslieferung und Limits des Sonntagslaufs. |
| Ist der Benchmark alles? | Nein, Nutzwert, UX und Interaktion werden wiederholt betont. | Aufteilung der Funktionspunkte und genaue Finalkriterien. |
| Müssen wir für bekannte Gebäude PNG analysieren? | Bilder und JSON werden gemeinsam als verfügbare Eingaben erklärt. | Daraus folgt keine eindeutige Bildanalysepflicht; Build aus einem neuen Plan separat klären. |
| Welche UI-Richtung passt? | Verständliche Visualisierung und natürliche Bedienung werden begrüßt; 3D wird als mögliche Erweiterung beschrieben. | Geräte, Browser, Sprache, Live-/Videoformat und Zeitlimits der Bewertung. |

Die vorhandenen Dateien [Zusammenfassung](2026-10-24-brainstorming-zusammenfassung.md) und [Jurorenfragen](docs/archive/2026-10-24-fragen-an-juroren.md) bleiben als ursprünglicher Gesprächsstand erhalten. Dieses Dokument ergänzt den Wissensstand; es behauptet keine bereits eingeholten Antworten auf alle Jurorenfragen.

## 5. Konsequenzen für unseren nächsten Schritt

Die folgenden Punkte sind redaktionelle Ableitungen, keine neu gefassten Team-Beschlüsse:

1. Den gemeinsamen Gebäudekern aus der [initialen Architektur](docs/archive/2026-10-24-tech-stack-initial.png) beibehalten: automatisierte räumliche Tools für App und Benchmark, statt Antworten nur durch Prompting oder manuelle Bearbeitung zu erzeugen.
2. Einen vollständigen Nutzerablauf mit sichtbarer Route und verständlicher Rückmeldung priorisieren. Voice und Visualisierung sollen dieselben verlässlichen Ergebnisse nutzen.
3. Keine Wi-Fi-Datenbeschaffung einplanen, bevor eine optionale Erweiterung bewusst gewählt wurde. Bei Kamera/AR zuerst Machbarkeit und Aufwand begrenzen.
4. Bei den nächsten Rückfragen auf **Build-Input und Mindestumfang, Sonntagsformat und Laufzeit, Funktionsgewichtung, Interaktionstest sowie Final-/Einreichungsformat** fokussieren. Diese Lücken schließen die weiteren Aufnahmen nicht.
5. Konkrete Fristen, nutzbare Credits und die Track-01-Abgabefelder im Portal prüfen. Keine Angaben aus den anderen Tracks übernehmen.

## Abgrenzung und Quellenrang

Die Certivity-Vorgaben zu Regulationsdokumenten, F2-Score, eigenem Uploadsystem und einer Veröffentlichung am Morgen sowie die Tacto-Vorgaben zu Verhandlungsagenten, Turnierzeit und Finalistenzahl gehören zu anderen Tracks. Sie sind keine Regeln für unsere Gebäude-Challenge. Preise, allgemeine Firmenkennzahlen, Team-Matching-Demos und Nebenunterhaltungen wurden weggelassen, soweit sie keine Entscheidung für unsere Challenge verändern.

Bei Abweichungen zwischen groben mündlichen Beispielen und den präzisen Datenspezifikationen bleibt der [geprüfte Repo-Stand](https://github.com/Synera-GmbH/industrial-agents-hackathon-2026/blob/cb51a6f2e357db743b0c8b2b377fe902ee3ced13/README.md) die dokumentierte technische Grundlage. Spätere verbindliche Organisatoren-Updates können ihn ergänzen; solche Updates wurden für diese Extraktion nicht zusätzlich aus Discord oder dem Portal abgerufen.
