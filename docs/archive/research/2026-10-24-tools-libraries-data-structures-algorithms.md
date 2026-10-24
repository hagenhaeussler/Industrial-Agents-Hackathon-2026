# Technologie-Research: Tools, Bibliotheken, Datenstrukturen und Algorithmen

**Stand:** 24.10.2026. **Untersuchter Team-Stand:** `30dc8b438684050549cc8138fd142f0c6ba29909` auf `main`; vor dem Schreiben erneut mit GitHub synchronisiert. **Ziel:** konkrete technische Verbesserungen für „Talk to Your Building“, priorisiert für den Hackathon. Dieser Bericht ergänzt den [Plan-Review](<../codex reviewed plan suggestions .md>) und den [vorigen Research zu Repositories und Skills](2026-10-24-repositories-und-agent-skills.md). Hier geht es um Verfahren und Komponenten; es wurden keine weiteren Repository- oder Skill-Kataloge zusammengestellt.

**Empfehlung:** Zuerst Tool-Verträge und fachliche Regeln absichern, Geometrie und Graphen versioniert cachen und Mengenfragen mit gemeinsamen Graphdurchläufen lösen. Das verbessert die vorhandene Architektur unmittelbar. Ein anderer Graph-Kernel ist eine messbare Option, aber erst nach diesen Schritten sinnvoll. Für geometrische Navigation und AR ist die richtige mathematische Repräsentation wichtiger als eine zusätzliche Agentenplattform.

## 1. Ausgangslage und Reihenfolge

Maßgeblich sind die Teamentscheidungen im [Review der beiden User Experiences](../2026-10-24-plan-review-zwei-ux.md): **Railway**, ein FastAPI-Service mit gebautem React-/TypeScript-Frontend, SQLite und Uploads auf `/state`, unveränderliche Kit-Daten im Image, ElevenLabs für Voice, derselbe deterministische Core für Anwendung und lokalen Benchmark. Laptop-UX: Gebäude importieren und bearbeiten. Smartphone-UX: QR-Start, Karte und Voice; kamerabasierte Navigation braucht zusätzliche Registrierung und Gerätetests.

Der geprüfte Stand enthält Planungsdokumente, Transkripte, Daten und Startercode. Die beschriebenen Verzeichnisse `core/`, `server/` und `web/` sind dort noch nicht implementiert. Deshalb sind Integrationsvorschläge unten ein Bauplan, keine Behauptung über bereits laufende Funktionen.

Die 280 Gebäudedatensätze enthalten 22.725 Räume. Aus Benchmark und Warm-up sind 2.930 Fragen in sechs Clustern vorhanden. Besonders relevant: Flächen und räumliche Beziehungen machen zusammen 104 der 145 vorhandenen Testfragen aus; daraus lassen sich keine künftigen Jurygewichte ableiten. Die Dokumente beschreiben außerdem zwei unterschiedliche Routenmodelle: veröffentlichte Raumanker-Kosten und angekündigte geometrische Wege durch Räume. **Jeder Algorithmus und jeder Cache braucht ein ausdrücklich gewähltes Kostenprofil.** Die Auswahl erfolgt durch Server beziehungsweise Benchmarklauf, nicht durch eine Vermutung des Sprachmodells.

### Priorisierte Entscheidungen

„Klein“ bedeutet hier etwa 30–90 Minuten für einen begrenzten Baustein, „mittel“ mehrere Stunden inklusive fachlicher Abnahme. Das sind Schätzungen bei vorhandenem Grundgerüst, keine Lieferzusagen und keine addierbare vollständige Projektplanung.

| Rang | Baustein | Konkreter Nutzen | Aufwand / Entscheidung |
|---|---|---|---|
| 1 | Typisierte Anfragen, semantische Validatoren und Ergebnisbelege | Verhindert falsche IDs, falsches Profil und plausible, aber unbelegte Antworten. | Klein bis mittel; sofort vor neue Agentenfunktionen setzen. |
| 2 | Unveränderliche Gebäudebasis, vorberechnete Geometrie, versionierter LRU-Cache | Vermeidet wiederholtes Polygon- und Graphbauen; isoliert Vorschau und Benchmark. | Klein bis mittel; im Experiment klarer Nutzen. |
| 3 | BFS beziehungsweise Single-/Multi-Source-Dijkstra pro Mengenfrage | Erreichbarkeit und nächste Ziele mit einem Durchlauf statt vielen Einzelrouten. | Klein; hoher Nutzen bei C4 und C6. |
| 4 | Differenzielle Tests und mathematische Invarianten | Entdeckt Fehler bei Sperren, parallelen Türen, Skalierung und What-if früh. | Klein bis mittel; als Entwicklungswerkzeug einsetzen. |
| 5 | Portalgraph mit tatsächlichen Kanten- und Weg-IDs | Backend, Karte und Navigation verwenden dieselbe Tür und denselben Pfad. Grundlage der Geodäsie. | Mittel; fachlich notwendig für geometrische Routen. |
| 6 | SQLite-Transaktionen, Versionsprüfung und Idempotenz | Zwei Clients können Änderungen bestätigen, ohne still gegenseitig Zustand zu überschreiben. | Mittel; für Admin-UX verbindlich. |
| 7 | Maßstabs- und Koordinatenkalibrierung | Macht Bildimport metrisch brauchbar und eine Kameraüberlagerung räumlich nachvollziehbar. | Mittel bis hoch; eigener Geräte-/Import-Abnahmepunkt. |
| 8 | NumPy/SciPy mit korrekt gebautem CSR-Graph | Sehr schnelle numerische Distanzabfragen; zusätzliche Adapterarbeit nötig. | Nur bei gemessenem Engpass übernehmen. |
| 9 | SQLite FTS5 für längere Betriebsdokumente | Lokale, nachvollziehbare Textsuche ohne weiteren Dienst. | Später, sobald echte Dokumentfragen existieren. |
| 10 | ALT, D* Lite, OR-Tools | Beschleunigung vieler dynamischer Routen oder echte Touren-/Ressourcenoptimierung. | Nach dem Pflichtpfad; heutige Fragen brauchen überwiegend einfachere Verfahren. |

## 2. Tools und Fähigkeiten für den Agenten

### 2.1 Strukturierte Recherche und Informationsextraktion

Für Raum-, Asset- und Routenfragen ist die Gebäudedatei die Wissensquelle. Eine passende Abfragekette ist:

1. Exakte ID oder eindeutige Raumreferenz nachschlagen.
2. Kandidaten über Etage, Raumtyp und Assettyp einschränken.
3. Erst danach Namen und Synonyme unscharf vergleichen; Mehrdeutigkeit als Rückfrage zurückgeben.
4. Nur die aufgelösten IDs an den Core übergeben.

Der Starter besitzt bereits ID-Dictionaries, durchsucht Namen und Referenzen aber überwiegend linear. Zusätzliche Alias- und Mengenindizes sind deshalb konkreter als ein allgemeiner Wissensgraph. Eine Suchfunktion sollte auch erklären können, warum ein Treffer passt: exakte Referenz, Namensalias oder unscharfer Vorschlag. Ein hoher Ähnlichkeitswert allein bestätigt keine Identität.

Für spätere Fragen zu Handbüchern, Betriebsnotizen oder Raumhinweisen eignet sich **FTS5/BM25 in der vorgesehenen SQLite-Datei**. Treffer sollten Dokument-ID, Abschnitt und Gebäudebezug zurückgeben. Exakte Bezeichnungen wie `Office 0.21` zusätzlich separat indexieren; Tokenisierung kann Satzzeichen aufteilen. Bei FTS5 bedeutet ein kleinerer BM25-Wert eine bessere Platzierung. Verfügbarkeit im tatsächlichen SQLite-Build prüfen. Für die jetzigen strukturierten Fragen reicht zunächst der direkte Index. [SQLite FTS5](https://sqlite.org/fts5.html).

Bild-/Vision-Extraktion bekommt einen anderen Vertrag: Polygone, Öffnungen und Labels sind **Vorschläge mit Herkunft und Prüfstatus**. Ein Validator prüft Referenzen, gültige Polygone, Etagen und Öffnungspositionen; eine Overlayansicht ermöglicht Korrekturen. Die Bildauswertung darf keinen unbekannten Maßstab durch eine scheinbar präzise Zahl ersetzen.

### 2.2 Typisierter Query-Plan und begrenzte Orchestrierung

Ein kleines Anfrageobjekt ist die wichtigste neue Agentenschnittstelle:

```text
QueryPlan
  kind, building_id, resolved_entity_ids, filters, constraints

ServerExecutionContext
  request_id, session_id, base_hash, building_version, cost_profile

ToolResult
  status, value, units, entity_ids, used_edge_ids, polyline_ids
  request_id, building_version, cost_profile, provenance
```

Das Modell schlägt `kind` und Parameter vor. Der Server ergänzt seinen Ausführungskontext, prüft erlaubte Operationen und ruft die passende Python-Funktion auf. **Pydantic v2** kann Typen und strukturelle Grenzen prüfen; Strict Mode reduziert unerwünschte Typumwandlung. Ob zwei IDs zum selben Gebäude gehören, eine Etage existiert oder eine Tür zulässig ist, muss zusätzlich fachlich validiert werden. [Pydantic Strict Mode](https://pydantic.dev/docs/validation/latest/concepts/strict_mode/).

Für zusammengesetzte Fragen genügt ein expliziter kleiner Ablaufgraph. Beispiel `errand`: Kandidaten finden → Distanzen vom Start → nächsten Pickup auswählen → größten Zielraum bestimmen → zweite Route → Ergebnis formatieren. Unabhängige Leseaufgaben können parallel laufen; Schreibschritte bleiben in der vorgegebenen Reihenfolge. Ein begrenzter Reparaturversuch bei ungültigen Argumenten ist sinnvoll; danach gezielt nachfragen. Das verhindert unkontrollierte Tool-Schleifen.

Für Edits eine Zustandsmaschine verwenden: `proposed → confirmed → committed`, mit gesondertem Zustand für verworfene oder veraltete Vorschläge. Eine Bestätigung muss sich auf die konkrete Vorschau beziehen. Ein neuer Route-Aufruf zählt nicht als Bestätigung einer früher vorgeschlagenen Tür.

**LangGraph** bietet Checkpoints für mehrstufige Agentenabläufe; sein Thread-Zustand und ein sitzungsübergreifender Store erfüllen unterschiedliche Aufgaben. Das wäre bei langen, unterbrechbaren Arbeitsabläufen prüfenswert. Für unsere überschaubaren Tools würde ein zweiter Persistenzmechanismus neben SQLite zunächst Abstimmungsarbeit erzeugen. Eine typisierte Python-Zustandsmaschine genügt als Start. [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence).

### 2.3 Gedächtnis und Kontext gezielt trennen

| Kontext | Inhalt | Gültigkeit und Speicher |
|---|---|---|
| Gebäudewissen | Räume, Polygone, Öffnungen, Assets, feste Referenzen | Unveränderliche Basis plus versionierte Änderungen. |
| Sitzung | Gewähltes Gebäude, bestätigter QR-Standort, zuletzt aufgelöste IDs, offene Rückfrage | Pro Sitzung; Standort kann veralten und braucht einen Zeit-/Bestätigungsbezug. |
| Vorschlag | Konkreter Edit, Vorschau, erwartete Version, Bestätigung | SQLite, bis Commit oder Verwerfung. |
| Berechnungswissen | Graphen, Geometrien, Distanzfelder | Begrenzter Cache; vollständig aus gültiger Basis rekonstruierbar. |
| Gesprächszusammenfassung | Verkürzter sprachlicher Verlauf | Hilft bei Referenzen; ersetzt keine Geometrie oder bestätigte Position. |

Dem LLM reichen aktuelle IDs, relevante Treffer und das letzte verifizierte Tool-Ergebnis. Das vollständige Gebäude oder alle Transkripte bei jeder Nachricht erneut zu senden erhöht Aufwand und erschwert die Auswahl maßgeblicher Fakten. Für Benchmarkfragen wird die Sitzung frisch angelegt; zwischen Fragen wiederverwendbare Caches dürfen nur aus dem jeweiligen Gebäudemodell abgeleitete, unveränderte Werte enthalten.

### 2.4 Rechnen, Ausführen und externe Aufrufe

Die benötigten Rechenwerkzeuge sind normale Core-Funktionen: Flächen, Abstände, Überdeckungen, gefilterte Erreichbarkeit, kürzeste Wege und isolierte Änderungen. Das ist eine kleine, kontrollierbare Menge mathematischer Operationen. Beliebiger vom LLM erzeugter Python-Code würde für diese Fragen einen zusätzlichen Laufzeit- und Fehlerpfad eröffnen. Falls später freie Analysen erforderlich sind, wäre dafür ein eigener begrenzter Ausführungsdienst zu entwerfen; er ist kein notwendiger Teil des Hackathon-Cores.

Für Anthropic-/ElevenLabs-HTTP-Aufrufe vorhandene langlebige SDK-Clients beziehungsweise **HTTPX-Clients mit Connection Pooling** verwenden. Timeouts und eine begrenzte Zahl gleichzeitiger Requests verhindern, dass wartende APIs alle Arbeit blockieren. [HTTPX Clients](https://www.python-httpx.org/advanced/clients/).

Wiederholungen nur für passende vorübergehende Fehler, mit maximaler Versuchszahl, Gesamtzeitlimit und zufälliger Verzögerung. Vor einer zusätzlichen Retry-Bibliothek prüfen, was das SDK bereits wiederholt. Ein mutierender Tool-Aufruf benötigt eine stabile `operation_id`, damit ein Netzwerkwiederholungsversuch dieselbe Änderung nicht doppelt ausführt. **Tenacity** kann solche Regeln ausdrücken, ist aber optional; ungegrenzte Standard-Retries nicht übernehmen. [Tenacity](https://tenacity.readthedocs.io/en/latest/).

### 2.5 Testen, Verifizieren und Debuggen als Agentenwerkzeuge

Eine kleine strukturierte Spur pro Anfrage ist zunächst ausreichend: aufgelöster Fragetyp, IDs, Profil/Version, Cachetreffer, Zeiten für Extraktion/Graphbau/Solver/Formatierung, Ergebnis und Fehlerklasse. Das hilft, einen falschen Textparser von einer falschen Geometrieberechnung zu unterscheiden. Ein Trace sollte keine API-Schlüssel oder vollständigen Audiodaten enthalten.

**Hypothesis** eignet sich für zufällige gültige Graphen und Geometrien sowie für Folgen wie Vorschlag → Commit → Wiederholung → Undo. Stateful Testing erzeugt auch Aktionssequenzen und sucht nach problematischen Kombinationen. Besonders wertvoll ist der Vergleich gegen ein einfaches Referenzmodell. [Hypothesis Stateful Testing](https://hypothesis.readthedocs.io/en/latest/stateful.html).

Die Abnahme muss drei Dinge getrennt zeigen: Core mit bekannten Eingaben, Intent-Extraktion aus der tatsächlichen Frage und den gesamten Text-/Voice-Pfad. Gold-`inputs` belegen allein keinen funktionierenden Sprachagenten. Den vorhandenen Scorer einschließlich letzter `Answer:`-Zeile für den Benchmark beibehalten; die UI darf zusätzlich erläuternde Belege anzeigen.

Für Latenzmessung `perf_counter()` nutzen; mit `cProfile` zunächst teure Aufrufstellen suchen. Profiler vergleichen Python- und native Bibliotheksarbeit wegen unterschiedlicher Instrumentierung nicht unverzerrt. Falls mehrere Dienste oder externe Aufrufe schwer nachvollziehbar werden, können **OpenTelemetry-Spans** dieselben Request-IDs über HTTP und Core weitertragen. Dafür muss jetzt kein zusätzlicher Monitoringdienst aufgebaut werden. [Python Profiling](https://docs.python.org/3.12/library/profile.html), [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/instrumentation/).

## 3. Softwarebibliotheken: konkrete Auswahl

NetworkX und Shapely sind bereits direkte Abhängigkeiten. Die folgende Liste unterscheidet deren gezielte Nutzung von tatsächlich zusätzlichem Integrationsaufwand. Nur NumPy/SciPy/NetworkX/Shapely wurden in den mitgelieferten Experimenten ausgeführt; die übrigen Empfehlungen beruhen auf Dokumentation und Architekturabgleich.

| Bibliothek / Modul | Aufgabe in unserem System | Empfehlung und Grenze |
|---|---|---|
| **Pydantic v2** | Gemeinsame Anfrage-/Ergebnismodelle, Schemaexport, Validatoren. | Früh einbauen; fachliche Existenz-, Profil- und Zustandsprüfungen ergänzen. Kein zusätzlicher Pydantic-AI-Agent erforderlich. |
| **NetworkX**, vorhanden | Lesbarer Referenzgraph, Dijkstra, BFS, Komponenten, Graphdiagnostik. | Zunächst behalten und cachen. Der korrekte Graphvertrag ist wertvoller als ein voreiliger Backendwechsel. |
| **Shapely 2**, vorhanden | Polygonfläche, Schwerpunkt, Schnittflächen, räumlicher Index, wiederholte Prädikate. | Geometrien einmal aufbauen. `prepare` kann wiederholte topologische Tests beschleunigen; neue Geometrien erneut vorbereiten. [Prepared Geometry](https://shapely.readthedocs.io/en/stable/reference/shapely.prepare.html). |
| **NumPy** | Kompakte Koordinaten-, Flächen-, Distanz- und Maskenarrays; vektorisierte Auswertung. | Direkte Abhängigkeit deklarieren, wenn eigener Code sie importiert. `float64` als Start; keine Python-Objektarrays für Zahlen. [NumPy Arrays](https://numpy.org/doc/stable/reference/arrays.ndarray.html). |
| **SciPy `sparse.csgraph`** | Wiederholte numerische Distanzfelder auf statischem gefiltertem CSR-Graph. | Im Experiment schnell; nur mit geprüftem Parallelkanten-/Nullkantenadapter übernehmen. Gibt nicht automatisch unsere Portalidentität zurück. [Dijkstra API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.dijkstra.html). |
| **`functools`, `heapq`, `collections`, `sqlite3`**, Standardbibliothek | Begrenzte Caches, Queue/Heap, Indizes und persistenter Zustand. | Bevorzugter einfacher Anfang. Bestehende Bibliotheksalgorithmen verwenden, statt Dijkstra selbst neu zu schreiben. [Heap-Dokumentation für Python 3.12](https://docs.python.org/3.12/library/heapq.html). |
| **cachetools** | LRU/TTL mit Größenbudget und expliziter Cachekontrolle. | Bei Bedarf; Shared Cache synchronisieren und Einträge nicht mutieren. TTL ersetzt keine Gebäudeversion. [cachetools](https://cachetools.readthedocs.io/en/latest/). |
| **HTTPX / vorhandene SDK-Clients** | Gepoolte externe Requests, Timeouts und begrenzte Parallelität. | Für Voice-/Text-Brücke passend. Keine zusätzlichen Clients pro Tool-Aufruf erzeugen. |
| **Hypothesis + pytest**, nur Entwicklung | Invarianten, zufällige Randfälle, Vergleich zweier Implementierungen, Zustandsfolgen. | Früh für den mathematischen Core nutzen; Tests benötigen keine kostenpflichtigen LLM-Aufrufe. |
| **OpenCV `calib3d`** | Planfoto entzerren, Markerpose aus Punktkorrespondenzen schätzen. | Nur beim konkreten Import-/AR-Pfad; Python ggf. als Headless-Paket. Verfügbarkeit der benötigten Funktionen im gewählten Browser-/WASM-Build separat prüfen. [Kalibrierung](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html). |
| **SciPy `linalg` / `spatial.transform`** | Ausrichtung mehrerer Messpunkte, Rotationen und Transformationsrechnung. | Nur wenn manuelle Zweipunktkalibrierung nicht reicht. Nicht allein wegen einer Matrixmultiplikation SciPy einführen. |
| **OpenTelemetry** | Verteilte Zeit- und Fehlerverfolgung. | Optional nach einfacher Request-Spur; keine Voraussetzung für eine funktionierende Demo. |
| **rustworkx** | Weiterer nativer Graph-Kernel mit Python-Schnittstelle. | Spätere Alternative bei breiteren Graphoperationen; hier nicht gemessen. Keine dritte Graphdarstellung neben NetworkX und SciPy gleichzeitig einführen. [Dokumentation](https://www.rustworkx.org/). |
| **OR-Tools** | Freie Tourreihenfolgen, Zeitfenster, Ressourcen- und Zuordnungsprobleme. | Für eine spätere Logistikerweiterung. Die vorhandene geordnete `tour` und die fest definierte `errand`-Auswahl benötigen keinen TSP-Solver. [Routing](https://developers.google.com/optimization/routing/tsp). |

Ein allgemeiner Vektorindex, eine Graphdatenbank, GPU-Routing oder ein vollständiger Tabellen-DataFrame-Stack ist für die hier gemessenen Gebäudegrößen kein erster Schritt. Es gibt im untersuchten Stand keinen nachgewiesenen Engpass, der diese zusätzliche Infrastruktur rechtfertigt. Für einfache JSON-/CSV-Verarbeitung reichen die vorhandenen Strukturen und Standardmodule.

## 4. Datenstrukturen: Repräsentation, Komplexität und Speicher

Notation: `V` Knoten, `E` Kanten einschließlich paralleler Alternativen, `n` Räume/Objekte, `p` Polygonpunkte, `k` Treffer beziehungsweise geänderte Einträge. Die Komplexitäten beschreiben übliche Algorithmenmodelle; tatsächliche Laufzeit hängt auch von Geometrie, Python-Objekten und Cachezustand ab. Hashzugriffe sind erwartete, keine garantierten konstanten Zeiten.

| Struktur | Einsatz / Vorteil gegenüber aktuellem Vorgehen | Aufwand und Speicher | Praktischer Nachteil |
|---|---|---|---|
| **Hashindex plus invertierte Mengen** | `id → object`, `alias → set[ID]`, `(floor_id, room_type) → set[ID]`, `asset_type → set[space_id]`; ergänzt vorhandene ID-Dictionaries. | Aufbau insgesamt linear in Einträgen; exakter Lookup erwartet `O(1)` plus Treffer. Mengenfilter statt vollständigem Textscan; Speicher linear in Indexeinträgen. | Aliase können mehrfach vorkommen; Mehrdeutigkeit erhalten. Bei Änderungen betroffene Indizes aktualisieren. |
| **Adjazenzlisten als MultiGraph** | Türen, Treppen und Lifte behalten ihre Attribute und parallelen Alternativen. Gut lesbarer fachlicher Referenzgraph. | `O(V+E)` Struktur; Python-Dictionaries verursachen zusätzlichen Objektbedarf. | Jede Route baut ihn im Starter erneut auf. Erst dieses Wiederholen entfernen, bevor die Darstellung ersetzt wird. |
| **CSR mit Integer-Knotenindex und separaten Kantenmetadaten** | Kompakte statische Nachbarschaft für native numerische Algorithmen. | `O(V+E')`, mit `E'` gespeicherten gerichteten Einträgen. Zeilenscan proportional zum Knotengrad. | Änderungen am Sparsity-Muster teuer; Attribute und Parallelkantenregeln brauchen Adapter. Fehlende und kostenlose Kante unterscheiden. |
| **STRtree pro Etage** | Kandidaten für Raumzuordnung, Überdeckung und gemeinsame Wände statt Vergleich mit jedem Raum. | Typisch etwa `O(n log n)` Aufbau, günstige Anfrage oft `O(log n+k)`; ungünstige überlappende Bounding Boxes können lineare Suche verursachen. Zusätzlicher Indexspeicher ungefähr linear. | Bounding Boxes liefern Kandidaten, keine exakte Raumbeziehung. Statischer Index wird nach Geometrieänderung neu gebaut. |
| **Dichte Bitmasken / Bitsets** | `reachable & floor_mask & eligible_room_mask`, anschließend Bits zählen. | Pro Maske ungefähr `V/8` Byte reine Bits; Operation `O(V/W)` für Maschinenwortbreite `W`, plus Objektverwaltung. | IDs müssen stabil auf Bitpositionen abgebildet sein. Die Erreichbarkeitsmenge muss vorher trotzdem berechnet werden. Python-Sets sind für kleine Mengen einfacher. |
| **Komponentenlabels / Disjoint Set** | Unerreichbare Paare schnell ausschließen; Gruppen bei rein additiven Änderungen pflegen. | Ungerichtete Komponenten `O(V+E)` vorab, Vergleich danach `O(1)`. Union-Find amortisiert nahezu konstant, `O(α(V))`. | Eine Türsperre kann eine Komponente teilen. Einfaches Union-Find unterstützt solche Löschungen nicht; keine gerichtete Erreichbarkeit ableiten. |
| **Min-Heap plus Vorgängerstruktur** | Nächsten Dijkstra-Kandidaten auswählen und tatsächlichen Weg rekonstruieren. | Heap-Operation `O(log H)` bei `H` Einträgen; Vorgänger je Knoten `O(V)`. Lazy Updates können zusätzliche veraltete Heap-Einträge erzeugen. | Eindeutigen Tie-Breaker verwenden. Vorgängerknoten allein benennt bei Parallelkanten keine Tür. Bibliotheksimplementierung bevorzugen. |
| **Basis + flaches Änderungs-Overlay** | Vorschau/What-if mit wenigen Overrides und Tombstones, ohne die Gebäudebasis zu mutieren. | Delta-Speicher `O(k)`; Lookup über Basis und flaches Overlay erwartet `O(1)`. Vollständiges Materialisieren bleibt `O(n+k)`. | Ein kleiner Delta-Speicher macht Graph- und Geometrieupdates nicht automatisch inkrementell. Zunächst abgeleitete Strukturen neu berechnen. |
| **B-Tree-Indizes in SQLite** | Vorschläge nach ID, Events nach Gebäude/Version, eindeutige Operationen. | Punkt-/Bereichszugriff typischerweise `O(log n)` plus gelieferte Datensätze; zusätzliche Indizes benötigen Platz und Schreibarbeit. | Nicht jedes JSON-Feld indexieren. Version und Idempotenz müssen in derselben Transaktion geprüft werden. |

Shapelys **STRtree ist abfragbar, aber nach dem Aufbau nicht veränderbar und ignoriert Z-Werte**. Daher Etagenzugehörigkeit außerhalb des Index mitführen und `room_stacked` gezielt gegen die relevante andere Etage prüfen. Bei Punktfragen die Randregel festlegen: `covers` schließt einen Punkt auf der Raumgrenze ein; eine gemeinsame Tür kann mehrere Räume liefern und braucht Auflösung. [STRtree](https://shapely.readthedocs.io/en/stable/strtree.html), [Shapely covers](https://shapely.readthedocs.io/en/stable/reference/shapely.covers.html).

### 4.1 Ein Cache braucht fachliche Identität

Der Starter berechnet in `BuildingMap.graph()` für jede Anfrage Raumanker und den Graphen erneut. Empfohlen sind getrennte Caches:

- **Geometrie:** Basis-Hash und Geometrieversion → Polygone, Flächen, Schwerpunkte, Raumanker und Etagenindizes.
- **Lokaler Raumweg:** Raumgeometrie, Clearance-Regel und Portalpaar → Länge und Polyline.
- **Routinggraph:** Basis-/Zustandsversion, Kostenprofil und normalisierte Constraints → gefilterter Graph.
- **Distanzfeld:** Graphidentität, Quellenmenge und Richtung → Distanzen, bei Bedarf Vorgänger.

Ein Schlüssel könnte `building_id, base_hash, geometry_version, state_version, cost_profile, constraint_fingerprint` enthalten. Relevante Parameter wie Mindestbreite, `step_free`, Sperren und gegebenenfalls zielabhängige Regeln gehören zum Fingerprint. Die Quellenmenge kommt beim Distanzfeld hinzu. Ein bloßes `building_id` oder ein 60-Sekunden-TTL liefert nach einer Sperre möglicherweise falsche Wege.

Mit wenigen zuletzt verwendeten Gebäuden anfangen und beim ersten Zugriff laden. Nicht alle 280 Gebäude oder alle Paardistanzen beim Serverstart vorberechnen. LRU begrenzt die Zahl beziehungsweise Größe gespeicherter Werte. Native Geometriespeicher werden durch ein einfaches `sys.getsizeof()` nicht vollständig erfasst; Speicherbudgets deshalb messen oder zunächst über eine kleine Eintragszahl begrenzen.

Mehrere gleichzeitige erste Zugriffe sollten denselben Aufbau teilen: kurze Synchronisierung pro Cache-Schlüssel, anschließend ein unveränderliches Ergebnis veröffentlichen. Ein globaler Lock um LLM-Anfragen würde dagegen alle Sitzungen ausbremsen. `cachetools` verlangt bei gemeinsamem Threadzugriff ausdrücklich Synchronisierung; Cachewerte nicht nachträglich verändern. [cachetools](https://cachetools.readthedocs.io/en/latest/).

### 4.2 Drei Fallen bei Sparse-Graphen

**Parallelkanten werden standardmäßig summiert.** `nx.to_scipy_sparse_array()` bildet bei mehreren Kanten zwischen zwei Knoten deren Summe. Für kürzeste Wege ist dagegen die billigste **zulässige** Alternative relevant. Im Experiment wurden aus Kanten mit Kosten 1 und 4 fälschlich Kosten 5. Erst alle Breiten-/Sperr-/Treppenregeln anwenden, dann das Minimum wählen und die ID der gewählten Kante mitführen. Andernfalls könnte eine schnelle Treppe bereits einen ebenfalls vorhandenen Lift verdrängt haben, bevor „step-free“ geprüft wird. Auch doppelte COO-Einträge vor CSR-Konvertierung nicht ungeprüft addieren lassen. [NetworkX-Konvertierung](https://networkx.org/documentation/stable/reference/generated/networkx.convert_matrix.to_scipy_sparse_array.html).

**Gespeicherte Nullen sind echte Kanten.** Das veröffentlichte Modell enthält kostenlose Verbindungen zum gemeinsamen `outside`-Knoten. In einer Sparse-Darstellung müssen diese explizit gespeichert bleiben. `eliminate_zeros()` und ein unbedachter Umweg über eine dichte Matrix können die Bedeutung verändern. Im Test erhöhte allein das Löschen einer Nullkante den optimalen Weg von 1 auf 5. Fehlende Kante und Kante mit Kosten null sind unterschiedliche Zustände.

**Knotenfolge ist nicht Kantenfolge.** Ein Vorgängerarray benennt nur das vorherige Knotenpaar. Eine zusätzliche Zuordnung muss die ausgewählte Tür/den Connector und seine Polyline identifizieren. Bei gleichen Kosten eine stabile Auswahlregel verwenden. Die Anwendung braucht eine gültige, konsistente Route; es ist nicht erforderlich, bei mehreren Optima jede beliebige Bibliotheks-Tie-Break-Regel nachzuahmen.

### 4.3 Portalgraph statt ausschließlich Raumgraph

Für das veröffentlichte Ankerprofil die dokumentierten Knoten und Kosten unverändert reproduzieren. Für echte Wege durch konkave Räume ist ein **Portalgraph** passender:

```text
Knoten: (space_id, portal_id) und gegebenenfalls Start-/Zielzustand
Raumkante: zulässiger Innenraumweg zwischen zwei Portalen + gespeicherte Polyline
Übergang: konkrete Tür, Öffnung, Treppe oder Lift
Ergebnis: Raumfolge + Portal-/Kantenfolge + Polylines + Kostenprofil + Version
```

Zwei Portalseiten können dieselbe physische Tür referenzieren. Türdurchgang und Raumweg bleiben getrennt, damit Breite und Sperre genau einmal und an der richtigen Stelle geprüft werden. Der Viewer soll die verwendete Tür übernehmen; er darf nicht nachträglich die erste beliebige Öffnung zwischen zwei Räumen suchen.

Auch Kosten, die von der bisherigen Route abhängen, brauchen expliziten Zustand. Falls die Jury **einmalige** Liftwartezeit je zusammenhängender Fahrt meint, sind Boarding-Kanten mit Wartekosten und Fahrtkanten mit Höhenkosten ein geeignetes Modell. Eine Folge normaler Etagenkanten mit je 15 m Wartekosten wäre dafür falsch. Im veröffentlichten Profil ist genau diese wiederholte Kostenform jedoch dokumentiert; sie darf nicht still korrigiert werden. Ob und wie das angekündigte Modell die Wartezeit ansetzt, bleibt zu bestätigen.

## 5. Algorithmen und mathematische Verfahren

### 5.1 Geometrie zuerst deterministisch auswerten

**Fläche:** Für einen einfachen Polygonring mit aufeinanderfolgenden Punkten gilt die Shoelace-Formel

`A = 1/2 · |Σ(x_i y_(i+1) − x_(i+1) y_i)|`.

Die Berechnung ist `O(p)`. Löcher und mehrere Flächenbestandteile korrekt behandeln; dafür Shapely verwenden, statt einen nur für Rechtecke funktionierenden Helfer zu schreiben. Danach sind Maximum oder Summe über passende Räume linear in deren Anzahl. Flächen einmal pro Geometrieversion speichern, Zwischenergebnisse nicht vorzeitig runden. Ungültige Polygone beim Import melden; eine automatische Reparatur kann Fläche und Typ verändern und braucht eine bestätigte Importregel.

**Gerade 3D-Distanz:** Die Frage verlangt Polygon-Schwerpunkte und tatsächliche Etagenhöhen:

`d = sqrt((cx₁−cx₂)² + (cy₁−cy₂)² + (elevation₁−elevation₂)²)`.

Das ist nach vorberechneten Schwerpunkten eine konstante Rechnung. Der Schwerpunkt kann außerhalb eines konkaven Raums liegen und ist trotzdem der gefragte Schwerpunkt. Ihn nicht durch den im Routing verwendeten inneren `representative_point()` ersetzen. Ebenso keine angenommene Standardhöhe pro Stockwerk einsetzen.

**Direkt darüber/darunter:** Auf der nächsten relevanten Etage den Raum mit größter Schnittfläche `area(P ∩ Q)` bestimmen. STRtree reduziert nur die Kandidaten; die Schnittfläche entscheidet. Gleiche Raumnummern oder nächste Schwerpunkte liefern keinen allgemeinen Ersatz. Gemeinsames XY-Koordinatensystem prüfen; der README weist auf nicht ausgerichtete Swiss-Dwellings-Etagen hin.

**Gemeinsame Wand:** Etage und zählbare Raumtypen filtern, Kandidatenbox um 0,35 m erweitern und anschließend den im Fragenvertrag verlangten mindestens 1 m langen Randverlauf prüfen. Ein Abstand der Polygone kleiner als 0,35 m allein beweist keine gemeinsame Wand. Puffer-/Randlängenverfahren müssen an Eckkontakten, mehreren Randabschnitten und Wänden mit Dicke gegen Dev-Beispiele geprüft werden; ohne veröffentlichten Oracle-Code ist die genaue Behandlung solcher Grenzfälle nicht bewiesen. Quelle für diese Fachregeln: [README, Benchmarkdefinitionen](../README.md#benchmark-questions-questionsjsonl-this-is-what-is-scored).

### 5.2 Für Mengenfragen den passenden Graphdurchlauf wählen

| Frage | Verfahren | Warum besser als viele Einzelrouten? |
|---|---|---|
| Nur erreichbar / Anzahl erreichbarer Räume | BFS oder DFS nach Anwendung aller Constraints. | Ein Durchlauf `O(V+E)`; Gewichte werden für reine Erreichbarkeit nicht benötigt. |
| Nächster passender Pickup vom Start | Ein Single-Source-Dijkstra, dann Minimum über Kandidaten. | Alle Kandidaten teilen denselben Lauf; keine Route je Asset notwendig. |
| Entfernung aller Räume zum nächsten Ausgang | Multi-Source-Dijkstra ab allen erlaubten Ausgängen im ungerichteten Graphen. | Ein gemeinsames Distanzfeld statt einer Suche pro Raum. |
| Dasselbe in gerichteter Darstellung | Ab Ausgängen auf dem **umgekehrten** Graphen suchen. | Gesucht ist Raum→Ausgang, nicht Ausgang→Raum. |
| Vorgegebene Stoppreihenfolge | Kürzeste Wege der aufeinanderfolgenden Teilstrecken addieren. | Keine kombinatorische Suche über Reihenfolgen. |

Standard-Dijkstra mit geeigneter Priority Queue liegt für den üblichen nichtnegativen Graphen im Bereich `O((V+E) log V)`; bei einer Lazy-Heap-Implementierung ist die zusätzliche Zahl gespeicherter Kandidaten mitzudenken. Gegenüber `r` separaten vollständigen Suchen entfällt bei einer gemeinsamen Abfrage grob der Faktor `r`. Negative Kosten würden andere Verfahren erfordern und gehören nicht in dieses Routenmodell.

SciPy bietet eine Quellenliste und `min_only=True` für das nächste Element einer Quellenmenge. Nur benötigte Distanzfelder anfordern; eine vollständige `V×V`-Ausgabe ist für diese Fragen unnötig. [SciPy Dijkstra](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.dijkstra.html).

Zwei fachliche Grenzen beachten: Bei breiter Lieferung auch den benannten Eintritt prüfen, damit der Start am Raumanker keine unzulässige Eingangstür umgeht. Und gemeinsame Distanzfelder setzen denselben zulässigen Übergangsgraphen voraus. Wenn Produktionsbays nur als Endpunkte erlaubt sind, müssen Start-/Zielregeln in der Graphdarstellung beziehungsweise Expansion berücksichtigt werden; ein beliebiges universelles Distanzfeld ist sonst nicht äquivalent.

Für `errand` gilt weiterhin: erst den **vom Start aus nächsten** passenden Pickup wählen, dann zum größten verlangten Zielraum laufen. Eine andere Abholstelle mit kürzerer Gesamttour wäre eine andere Aufgabe. Falls zwei Kandidaten gleichwertig sind, die fachliche Tie-Regel ausdrücklich festlegen.

### 5.3 A* nur mit nachgewiesener unterer Schranke

**Eine euklidische Heuristik ist im veröffentlichten Modell nicht allgemein zulässig.** Dort können weit auseinanderliegende Eingänge über `outside` kostenlos verbunden sein. Die Luftlinie kann daher größer sein als die tatsächlich verbleibenden Graphkosten. NetworkX warnt ausdrücklich, dass eine überschätzende Heuristik einen nichtoptimalen Weg liefern kann. [A*-Dokumentation](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.shortest_paths.astar.astar_path.html).

Reproduziertes Gegenbeispiel mit Punkten `s=(0,0)`, `a=(0,1)`, `b=(100,0)`, `t=(100,1)`:

```text
s ───────────── 100,005 ───────────── t
│                                      │
1                                      1
│                                      │
a ─────── 0, kostenloser Übergang ───── b
```

Optimal sind Kosten 2 über `s,a,b,t`. Euklidisches A* gab im Experiment die direkte Kante mit etwa 100,005 zurück. Das Beispiel zeigt eine fehlende allgemeine Garantie; es behauptet nicht, dass jede vorhandene Benchmarkfrage diesen Fehler auslöst. Laut README wurden die veröffentlichten Fragen so gewählt, dass der Außen-Shortcut dort keinen Unterschied macht.

**Entscheidung:** Mit Dijkstra beziehungsweise `h=0` starten. Für ein separates geometrisches Profil kann die Luftlinie erst verwendet werden, wenn alle Übergangskosten und Koordinaten ihre Zulässigkeit sichern. Die Wahl „A* ist immer schneller“ wäre weder korrekt noch gemessen.

### 5.4 Geometrische Innenraumwege: Visibility Graph oder Navmesh

Die Route-Ankündigung verlangt Wege innerhalb der Raumumrisse mit ungefähr 15 cm Wandabstand. Eine gerade Verbindung zwischen Raumanker und Tür kann bei konkaven Räumen durch eine Wand laufen. Eine feinere Raumfolge allein behebt das nicht.

**Bevorzugter begrenzter Ansatz: Visibility Graph je Raum.** Gültigen begehbaren Polygonbereich bestimmen, Portale einfügen, sichtbare Punktpaare verbinden und auf diesen Kanten einen kürzesten Weg suchen. Bei polygonalen Grenzen können kürzeste Wege an deren Ecken abknicken. Länge **und** Polyline gemeinsam speichern, dann lokale Portalwege zum Gebäudegraph zusammensetzen. Den vorhandenen Research zum lokalen Raumrouter als Implementierungsansatz heranziehen; hier ist die mathematische Schnittstelle entscheidend.

Bei `n` betrachteten Eck-/Portalpunkten können `O(n²)` Sichtkanten entstehen. Eine naive Prüfung jedes Segments gegen alle `n` Randsegmente kann bis `O(n³)` Aufbauarbeit verursachen. Räumliche Indizes und vorbereitete Geometrien können praktisch helfen; sie garantieren nicht, dass der ganze Aufbau linear wird. Im untersuchten größten Gebäude hat ein einzelner Raum bereits 56 Öffnungen; vollständige Portalpaare daher pro Raum und bei Bedarf berechnen, nicht global blind ausmultiplizieren.

Clearance ist fachlich heikel: Ein negativer Polygonpuffer kann schmale Bereiche trennen oder ganz löschen. Türpunkte auf der ursprünglichen Wand liegen anschließend außerhalb des verkleinerten Raums und brauchen eine definierte Anbindung. Löcher, mehrere verbleibende Komponenten, Eckrundung und Start-/Zielposition müssen ausdrücklich behandelt werden. Ein beliebiges `buffer(-0.15)` ist deshalb noch kein vollständiger, zur Jury passender Router.

**Alternative: Constrained Delaunay Triangulation → Dreiecksgraph → Funnel.** Ein Navmesh beschreibt zusammenhängende begehbare Dreiecke; der Funnel strafft einen gewählten Portalkorridor. Die klassische lineare Funnel-Auswertung setzt einen entsprechenden triangulierten Korridor voraus; Triangulation und Korridorwahl kommen hinzu. Der so gestraffte Weg ist im gewählten Korridor optimal, aber eine Suche über Dreiecksmittelpunkte beweist nicht automatisch die global kürzeste geometrische Route über alle Korridore. [Hershberger/Snoeyink, Mindestwege vorgegebener Homotopieklasse](https://www.sciencedirect.com/science/article/pii/0925772194900108).

Shapely bietet eine **constrained** Triangulation, die Polygonkanten berücksichtigt. Eine unbeschränkte Delaunay-Triangulation nur der Eckpunkte kann dagegen Kanten über Raumgrenzen erzeugen. Ein Dreiecksgraph plus Funnel ist eine ernsthafte spätere Alternative, aber kein kostenloser Ersatz für die fachlichen Tür-, Clearance- und Komponentenregeln. [Shapely constrained triangulation](https://shapely.readthedocs.io/en/stable/reference/shapely.constrained_delaunay_triangles.html).

### 5.5 What-if: vollständige Neuberechnung zuerst, exakte Deltaformel bei passendem Modell

Die sichere erste Implementierung lautet: Basis und Constraints fixieren → ursprüngliche Ausgangsdistanzen berechnen → neue Tür in isolierter Kopie an der **gemeinsamen Wandmitte** einsetzen → Distanzen erneut berechnen → relevante Räume mit Verbesserung **strikt größer als 1 m** zählen. `nearest_points()` aus dem Starter liefert nicht allgemein diese Wandmitte. Nicht nur die beiden verbundenen Räume betrachten: Die Verbesserung kann andere Geschosse betreffen.

**Eine mathematisch interessante Optimierung:** Für einen ungerichteten Graphen mit nichtnegativen Kosten, unveränderten bisherigen Kanten und genau einer zusätzlichen effektiven Kante `(a,b,w)` gilt für jeden Knoten `v`:

```text
d(v)  = bisherige Entfernung von v zum nächsten erlaubten Ausgang
da(v) = bisherige Entfernung von a nach v
db(v) = bisherige Entfernung von b nach v

d_neu(v) = min(
    d(v),
    da(v) + w + d(b),
    db(v) + w + d(a)
)
```

Begründung: Es gibt einen optimalen Weg, der die neue Kante gar nicht oder höchstens einmal in einer der beiden Richtungen verwendet; nichtnegative Zyklen sind entfernbar. Die drei Ausdrücke decken diese Fälle ab. Das ist eine eigene Herleitung für diese begrenzte Änderung, keine behauptete universelle dynamische Routingformel.

Im veröffentlichten Raumanker-Modell lässt sich ein neuer Türknoten mit genau zwei Anschlüssen unter passenden unveränderten Regeln als solche effektive Kante zwischen den Raumankern ausdrücken. Bei einem geodätischen Portalgraphen kann eine neue Tür mehrere lokale Verbindungen erzeugen oder Geometrie verändern; die einfache Formel ist dann nicht ohne weiteren Nachweis anwendbar. Ebenso gilt sie nicht unverändert für gerichtete Regeln, geänderte Clearance oder zusätzliche Kostenänderungen.

Mit schon gespeicherten `d`, `da` und `db` kostet die Auswertung pro Kandidat nur `O(V)`. Müssen die drei Felder erst berechnet werden, ist das für einen einzigen Vorschlag nicht automatisch besser als zwei vollständige Läufe vor/nach der Änderung. Der Nutzen liegt in vielen wiederholten Türvarianten mit wiederverwendeten Endpunkten. Im beigefügten Experiment stimmte die Formel für 450 Knotenprüfungen auf 25 kleinen Graphen mit vollständiger Neuberechnung überein, einschließlich Nullkosten und unerreichbarer Knoten.

Beim abschließenden Zählen `∞−∞` vermeiden. Ob „zuvor unerreichbar, danach erreichbar“ als Verbesserung zählt, muss der fachliche Vertrag festlegen; das nicht durch zufälliges Float-Verhalten entscheiden. Der What-if-Aufruf bleibt ohne Commit und darf spätere Benchmarkfragen nicht verändern.

### 5.6 Kalibrierung: Maßstab, Registrierung und Fehlerbudget

Für einen maßstäblich unverzerrten Plan reicht zunächst eine vom Nutzer bestätigte bekannte Länge `L` zwischen zwei Bildpunkten `p₁,p₂`:

`s = L / ||p₂−p₁||`, anschließend `x_m = s · R · x_bild + t`.

`R` beschreibt die gewünschte Achsenausrichtung, `t` den Ursprung. Bild-Y nach unten und Karten-Y nach oben ausdrücklich behandeln. Alle Räume, Türen und Marker müssen dieselbe Transformation verwenden. Bei mehreren gemessenen Punktpaaren kann eine Least-Squares-/SVD-Anpassung Messfehler verteilen. SciPys `orthogonal_procrustes` liefert nur eine orthogonale Abbildung, **keine** vollständige Schätzung von Translation und Maßstab; auch sein Rückgabewert `scale` ist nicht einfach unser Meter-pro-Pixel-Faktor. [SciPy Procrustes](https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.orthogonal_procrustes.html).

Ein schräg fotografierter **ebener Grundriss** benötigt gegebenenfalls eine Homographie statt einer einzigen Skalierung. Dafür mindestens vier gut verteilte passende Punkte ohne entartete Anordnung; RANSAC kann Ausreißer zurückweisen. Die verbleibende Reprojektionsabweichung prüfen. Eine Homographie eines Planblatts rekonstruiert keine beliebige dreidimensionale Fabrikszene. [OpenCV Kalibrierung und Homographie](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html).

Für metrische **AR-Verankerung** reichen QR-ID und bekannter Raum nicht. Benötigt werden etwa bekannte Markerabmessungen, seine Bild-Eckpunkte, Kamerakalibrierung und die Markerpose im Gebäude. PnP schätzt daraus eine Objekt→Kamera-Transformation. Planare Marker können Mehrdeutigkeiten und schlechte Winkel erzeugen; Reprojektion und plausible Orientierung prüfen. Achsenkonventionen, Transformationsrichtung und ein späterer Wechsel in den WebXR-Raum müssen zusammenpassen. Ein initial erkannter Marker beweist keine dauerhafte Position hinter der nächsten Ecke. [OpenCV PnP](https://docs.opencv.org/4.x/d5/d1f/calib3d_solvePnP.html).

Homogene 4×4-Matrizen sind hierfür eine geeignete Datenstruktur. Mit der Konvention `T_AB` bildet von Koordinatensystem B nach A ab; dann gilt `T_building_camera = T_building_marker · T_marker_camera`. Eine PnP-Ausgabe `T_camera_marker` muss für diesen Ausdruck invertiert werden. Namen wie `transform` ohne Richtung laden zu schwer sichtbaren Fehlern ein. Bei fehlenden Intrinsics oder nicht gelungener Registrierung bleibt eine bestätigte Kartenposition mit relativer Richtung der belastbarere Zwischenstand.

Auch der Import braucht ein Fehlerbudget: Bei kleinem relativem Maßstabsfehler `ε` ändern sich rein geometrische Längen ungefähr um `ε`, Flächen um `2ε`. Beispielsweise bedeuten 2 % Maßstabsfehler etwa 4 % Flächenfehler. Das ist eine Sensitivitätsrechnung, keine gemessene Genauigkeit unseres Imports. Fachliche Kosten mit festem Liftwarteanteil skalieren nicht vollständig wie geometrische Längen. Eine Zentimeteranzeige kann eine ungenaue Kalibrierung nicht verbessern.

### 5.7 Weiterführende Verfahren mit klarer Einsatzschwelle

| Verfahren | Wann es wirklich helfen könnte | Voraussetzung / Entscheidung für diesen Hackathon |
|---|---|---|
| **ALT: A* mit Landmark-Distanzen** | Sehr viele Punkt-zu-Punkt-Anfragen auf weitgehend festem Graphen. | Im ungerichteten Fall `h(v)=max_L abs(d(L,t)−d(L,v))`; folgt der Dreiecksungleichung des Graphen, auch bei Nullkanten. `l` Landmark-Felder kosten `O(lV)` Speicher und `l` Vorberechnungsläufe. Erst nach gemessenem Engpass. |
| **D* Lite / Lifelong Planning A*** | Wiederholte Navigation bei lokal wechselnden Kanten und bewegtem Start. | Verwendet Suchzustand erneut; Implementierung und Invalidierung aufwendiger. Bei unseren Größen zunächst neu rechnen. |
| **Artikulationspunkte und Brücken** | Erklären, welche Tür oder welcher Bereich eine Verbindung besonders verwundbar macht. | Linearer Graphdurchlauf möglich; parallele Türen korrekt berücksichtigen. Diagnose eines Graphmodells, kein Nachweis realer Evakuierungskapazität. |
| **Min-Cut / Max-Flow** | Künftige Fragen nach mehreren unabhängigen Verbindungen oder Kapazitätsengpässen. | Erfordert fachlich begründete Kapazitäten. Türbreite allein ist noch kein validiertes Personenstrommodell. Für aktuelle Distanzen unnötig. |
| **Held-Karp / TSP-/VRP-Solver** | Frei wählbare Reihenfolge vieler Lieferstopps; später Zeitfenster und mehrere Fahrzeuge. | Held-Karp für kleine Stopmengen: `O(k²·2^k)` Zeit, `O(k·2^k)` Speicher. Die heutige `tour` gibt Reihenfolge vor; dafür bei Teilrouten bleiben. |
| **CP-SAT / ganzzahlige Optimierung** | Maschinen-/Teamzuordnung, Terminplanung und kombinierte diskrete Regeln. | Modellieren, wenn solche Anforderungen tatsächlich entstehen. Solverstatus und Zeitlimit ausgeben; „zulässig“ ist kein Optimalitätsbeweis. |

Bei der genannten TSP-Dynamik speichert `dp[S,j]` den besten Weg über die Stopmenge `S` mit letztem Stopp `j`. Höchstens `k·2^k` Zustände mit jeweils bis zu `k` Übergängen erklären die angegebenen Zeit- und Speichergrenzen; sie zeigen zugleich, warum das Verfahren nur für kleine Stopmengen passt. Hintergrund: [Held/Karp, Dynamic Programming Approach to Sequencing Problems](https://epubs.siam.org/doi/10.1137/0110015).

**ALT-Details:** Nichtendliche Landmark-Distanzen nicht voneinander subtrahieren; pro Komponente geeignete Landmarken oder `h=0` verwenden. Ein Profil mit nur gesperrten Kanten oder erhöhten Gewichten hat keine kürzeren Distanzen als die Basis; deren gültige untere Schranke bleibt daher zulässig. Neue Türen oder gesenkte Kosten können diese Garantie zerstören. Gerichtete Graphen benötigen die passenden gerichteten Distanzschranken statt der ungerichteten Absolutdifferenz. Das Verfahren stammt aus [Goldberg/Harrelson, MSR-TR-2004-24](https://www.microsoft.com/en-us/research/publication/computing-the-shortest-path-a-search-meets-graph-theory/).

**D* Lite** ist für verwandte aufeinanderfolgende Suchaufgaben entwickelt, nicht als allgemeines Versprechen konstanter Updatekosten. Eine kleine Änderung kann große Teile eines kürzesten Wegebaums betreffen. Die jetzigen lokalen Millisekundenmessungen begründen seinen Integrationsaufwand noch nicht. [Koenig/Likhachev, AAAI 2002](https://publications.ri.cmu.edu/d-lite).

**OR-Tools:** Bei späteren Touren tatsächliche, constraintgerechte Graphdistanzen zwischen Stopps verwenden. Euklidische Distanzen würden Wände und Etagen umgehen. Der Routing-Solver arbeitet mit ganzzahligen Kosten; Skalierung und Rundung müssen passend zur Genauigkeitsanforderung gewählt werden. CP-SAT verlangt ebenfalls ganzzahlige Modellterme und unterscheidet unter anderem `FEASIBLE`, `OPTIMAL` und `UNKNOWN`. [Routing/TSP](https://developers.google.com/optimization/routing/tsp), [CP-SAT](https://developers.google.com/optimization/cp/cp_solver).

## 6. Nachvollziehbare Experimente

Zur Absicherung wurden begrenzte Experimente in einer separaten Python-Umgebung ausgeführt. Es wurden keine Gebäudedaten verändert und keine LLM-API aufgerufen. Der Produktcode und seine Abhängigkeiten bleiben durch diesen Research unverändert.

**Mitgeliefert:** [Experimentcode](experiments/2026-10-24-methods-audit.py) und [vollständige Messdaten](experiments/2026-10-24-methods-audit-results.json). Umgebung: Python 3.12.14, macOS 26.3 ARM64, NumPy 2.5.4, SciPy 1.18.0, NetworkX 3.7, Shapely 2.2.0. Diese Versionsangaben beschreiben die Untersuchung und sind keine pauschale Aufforderung, alle Projektabhängigkeiten zu aktualisieren.

### 6.1 Cache und Sparse-Kernel am realen Gebäude

Aus allen 280 JSONs wurde das Gebäude mit der größten Summe aus Räumen und Öffnungen ausgewählt: `data/dev/osm-way27917482/building.json`. Sein veröffentlichter Startergraph hat **3.423 Knoten und 3.697 Multikanten**. Gemessen wurden zwölf feste Raumquellen mit jeweils vollständigem Single-Source-Distanzfeld.

| Variante | Median für dieselben zwölf Quellen | Was darin steckt |
|---|---:|---|
| NetworkX, Graph je Quelle neu bauen | **183,92 ms** | Zwölfmal Geometrie-/Graphaufbau plus zwölf Suchen. |
| NetworkX, vorhandenen Graph wiederverwenden | **36,50 ms** | Zwölf Suchen; Graphaufbau außerhalb der Messschleife. |
| SciPy, vorhandenen CSR wiederverwenden | **2,63 ms** | Gebündelte numerische Suchen; Aufbau und Export außerhalb der Messschleife. |

Ein separat gemessener einzelner Graphaufbau dauerte 10,98 ms, der Minimum-Kosten-CSR-Export 2,87 ms; das sind Einzelmessungen. Die Tabellenmediane beruhen auf drei Wiederholungen für die erste und fünf für die beiden anderen Varianten. Unterschiedliche Warmzustände und lokale Systemlast bleiben möglich.

**Interpretation:** Allein Graphwiederverwendung reduzierte diesen lokalen Zwölf-Quellen-Workload ungefähr um Faktor 5. Der zusätzliche Sparse-Kernel war gegenüber dem gecachten NetworkX-Lauf ungefähr Faktor 14 schneller. **Das sind keine Faktoren für die gesamte App:** Sprache, Netzwerk, UI, geodätische Vorberechnung, Serialisierung und Nebenläufigkeit wurden nicht gemessen. Eine normale Route mit nur einem Ziel kann zudem früher abbrechen als die hier gemessenen vollständigen Distanzfelder.

Alle **41.076 verglichenen Distanzen** stimmten zwischen NetworkX und dem korrekt aggregierten CSR innerhalb `rtol=1e-12, atol=1e-10` überein, einschließlich unerreichbarer Knoten. Der Adapter ist absichtlich rein numerisch: Er beweist keine korrekte Portal-/Polyline-Ausgabe und deckt keine neuen geodätischen Regeln ab. Für einen Produktadapter müssten diese Informationen und sämtliche Constraints separat geprüft werden. Im Experiment wurde der ungerichtete Graph symmetrisch gespeichert und mit `directed=True` ausgewertet, ohne asymmetrische Gewichte über `directed=False` zu interpretieren.

### 6.2 Speicher

| Darstellung dieses Graphen | Speicher |
|---|---:|
| Dichte `float64`-Matrix mit `3.423²` Einträgen | **93.735.432 Byte ≈ 89,4 MiB** |
| CSR: Werte, Spaltenindizes und Zeilenzeiger für 7.394 gespeicherte gerichtete Einträge | **102.424 Byte ≈ 100,0 KiB** |

Der CSR-Wert schließt Knoten-IDs, Kantenmetadaten, Polylines, Python-Objekte und Solverausgaben **nicht** ein. Er ist daher kein vollständiger RAM-Vergleich mit NetworkX oder dem Server. Für eine einzelne `float64`-Distanzzeile fallen hier zusätzlich 27.384 Byte an; viele gespeicherte Quellen benötigen entsprechend `O(qV)` Speicher. Das spricht für begrenztes Caching nach tatsächlichem Bedarf.

### 6.3 Korrektheitsfälle

| Experiment | Beobachtung | Bedeutung |
|---|---|---|
| Vier-Knoten-Beispiel mit kostenlosem Fernübergang | Euklidisches A*: ca. 100,005; Dijkstra: 2. | Geometrische Heuristik ist nicht ohne Modellbeweis zulässig. |
| MultiGraph mit zwei Parallelkanten 1 und 4 | Standardexport: 5; Minimum-Adapter: 1. | Ein naiver Backendwechsel verändert das Problem. |
| Explizite Nullkante im CSR | Route vor Entfernen: 1; danach: 5. | Sparse-Bereinigung darf Nullkostenkanten nicht löschen. |
| Eine neue Kante in 25 kleinen Graphen, fester Seed | 450 Knotenprüfungen der Deltaformel stimmen mit Neuberechnung überein. | Stützt die Implementierung des begrenzten Falls; ersetzt weder den Beweis noch Tests des realen What-if-Tools. |

Reproduktion vom Repository-Root, Beispiel für eine separate Unix-Umgebung:

```bash
python3.12 -m venv /tmp/hackathon-methods-research
/tmp/hackathon-methods-research/bin/python -m pip install \
  'numpy==2.5.4' 'scipy==1.18.0' 'networkx==3.7' 'shapely==2.2.0'
/tmp/hackathon-methods-research/bin/python \
  research/experiments/2026-10-24-methods-audit.py \
  --repo . --output /tmp/hackathon-methods-results.json
```

Andere Hardware oder Bibliotheksversionen können andere Zeiten und gleichwertige Tie-Breaks ergeben. Der Lauf schreibt nur die angegebene Ergebnisdatei; er greift lesend auf den Starter und die Gebäudedaten zu.

## 7. Empfohlene Umsetzung und Abnahme

### Nächste Bausteine im bestehenden Railway-Plan

1. **Vertrag festziehen:** Serverseitiges Kostenprofil, typisierte Anfragen/Ergebnisse, IDs auflösen, fachliche Validatoren und Ergebnisbelege. Zunächst Texttool direkt aufrufen; danach dieselbe Funktion über ElevenLabs anbinden.
2. **Core wiederverwendbar machen:** Unveränderliche Basis, Geometrie einmal vorberechnen, Graph pro Version/Constraintprofil cachen. Profile müssen unterschiedliche Schlüssel haben. CPU-lastige Arbeit aus asynchronen Requestpfaden auslagern; ein Threadpool garantiert dabei keine schnellere Python-Rechnung. Dauer und Reaktionsfähigkeit messen.
3. **Cluster vollständig bedienen:** C3-Flächen und C5-Geometrie berechnen; C4-Erreichbarkeit mit BFS, C6-Auswahl mit gemeinsamen Distanzfeldern. Nicht allein die am häufigsten vorkommenden Warm-up-Routen optimieren.
4. **Edits korrekt persistieren:** SQLite-Versionsprüfung, eindeutige Operationen und Undo als neues Event. `what_if` und Vorschau bleiben isoliert. Kurze Transaktionen; kein Warten auf ein LLM innerhalb eines Schreib-Locks.
5. **Geodäsie als eigenen überprüfbaren Router einbauen:** Portalidentität, lokale Polylines, Clearance und Connector-Regeln. Karte und Voice beschreiben dasselbe Ergebnis. Das publizierte Referenzprofil bleibt separat reproduzierbar.
6. **Import/AR kalibrieren:** Metrischen Maßstab und Koordinatenvertrag zuerst nachweisen; anschließend Pose und Gerätetest. Ein korrekt verankerter kurzer Demonstrationsweg ist ein sinnvoller erster Prüfgegenstand.
7. **Erst anschließend einen Kernel wechseln:** SciPy nur übernehmen, wenn gemessene Core-Zeit oder viele Distanzfelder den Aufwand rechtfertigen. Alle Profile, Nullkanten, Sperren und Pfadmetadaten gegen den Referenzrouter prüfen.

SQLite-WAL erlaubt konkurrierende Leser und einen Schreiber; mehrere gleichzeitige Schreiber werden dadurch nicht möglich. Für die geplante einzelne Serviceinstanz passt das zu kurzen Commits und getrennten Lesevorgängen. Verbindungshandhabung, Busy-Timeout und Transaktionsgrenzen ausdrücklich festlegen. WAL ist kein Ersatz für den vereinbarten Versionsvertrag. [SQLite WAL](https://sqlite.org/wal.html).

### Aussagekräftige Tests vor einer Übernahme

| Eigenschaft | Geltungsbereich |
|---|---|
| Zusätzliche Sperren können keine kürzere optimale Route erzeugen. | Unveränderte Knotenbedeutung, feste nichtnegative Kosten, nur Kanten/Knoten entfernen. |
| Eine zusätzliche zulässige Kante kann eine optimale Distanz nicht erhöhen. | Bestehende Kosten und Geometrie unverändert. |
| Strengere Breiten-/Step-free-Filter erzeugen keine zusätzlichen erreichbaren Räume. | Filter schränken ausschließlich dieselbe Ausgangsmenge zulässiger Übergänge ein. |
| Rotation und Translation erhalten Fläche und euklidische Distanzen. | Alle relevanten Geometrien und Koordinaten gemeinsam transformieren. |
| Einheitliche Skalierung um `s` verändert Fläche um `s²`. | Rein geometrische Größen; feste Liftwarte-Kosten sind davon ausgenommen. |
| Ausgegebene Polyline bleibt im erlaubten begehbaren Bereich. | Tatsächlich verwendete Clearance-, Portal- und Geschossregeln prüfen. |
| Zweiter Commit derselben `operation_id` erzeugt kein zweites Event. | Versionsprüfung und Idempotenz in gemeinsamer Transaktion. |
| What-if und Folgefrage beeinflussen die Basis nicht. | Auch gemeinsam verwendete Caches und Sessionzustand prüfen. |

Diese Tests ergänzen Dev-Beispiele, sie ersetzen keine fachliche Spezifikation. Beim Vergleich optimierter und einfacher Implementierung Distanzen, Zulässigkeit und Wegbelege prüfen; identische Knotenfolgen nur verlangen, wenn eine Tie-Regel Teil des Vertrags ist.

### Offene Voraussetzungen für technische Entscheidungen

Die bereits gespeicherten [Jurorenfragen](<../open questions for judge .md>) bleiben maßgeblich. Für die hier recherchierten Verfahren sind insbesondere vier Bestätigungen nötig:

- Welches Routenprofil gilt für welche Abgabe und Frage, einschließlich Start-/Zielpunkt und Außenwegen?
- Wird Liftwartezeit pro durchgehender Fahrt oder je Etagenabschnitt angesetzt?
- Wie sind 15-cm-Clearance, Türanbindung und Produktionsbays als Endpunkte exakt definiert?
- Welche Grenzfälle akzeptiert der Oracle bei gemeinsamer Wand, neuer Tür und zuvor unerreichbaren Räumen?

Die übrigen Bausteine können unabhängig davon entwickelt werden: typisierte Schnittstellen, Geometrieindizes, unveränderliche Basis, Transaktionen und profilgebundene Caches bleiben sinnvoll. Die ausstehende Bestätigung ist eine fachliche Abhängigkeit einzelner Solverregeln, kein Grund, alle Implementierung anzuhalten.

## 8. Quellenbasis und Grenzen

**Interne Grundlage:** [PLAN.md](../PLAN.md), [Codex-Review](<../codex reviewed plan suggestions .md>), [Teamentscheidungen zu beiden UX](../2026-10-24-plan-review-zwei-ux.md), [ElevenLabs-Konfiguration](../docs/elevenlabs-agent-config.md), [Architektur](../docs/architecture/README.md), [Frageübersicht](../docs/question-overview/README.md), [Brainstorming-Zusammenfassung](../2026-10-24-brainstorming-zusammenfassung.md), [bereinigtes Transkript](../docs/brainstorming/2026-10-24-transkript.md), [weitere Gesprächsnotizen](../2026-10-24-weitere-aufnahmen-relevante-infos.md), [Lead-Q&A](../2026-10-24-challenge-lead-qa.md), [Routenankündigung](../2026-10-24-route-scoring-specifications.md), [README](../README.md), [Starter-Core](../starter_agent/building_map.py), [Viewer](../starter_agent/viewer.py), [Scorer](../benchmark/score.py) sowie die vorhandenen Gebäude- und Fragendaten. Die früher ausgewerteten Challenge-PDFs gehen über die gespeicherten Reviews und Quelldokumente ein; es wurden keine neuen externen Juryantworten angenommen.

**Externe Grundlage:** offizielle Bibliotheksdokumentationen und die direkt verlinkten Forschungsarbeiten, am 24.10.2026 geprüft. Aufwand und Priorisierung sind eigene Einschätzungen. Die lokalen Experimente belegen die ausdrücklich beschriebenen Fälle; sie sind kein vollständiger Benchmark aller Gebäude, kein Test des Live-Agenten und keine Messung einer Railway-Deploymentinstanz. Dieser Commit liefert Research und reproduzierbare Untersuchungen, keine implementierten Produktfunktionen.
