# Produkt und UX

Primäre Datei für **was der Nutzer erlebt**: die zwei Ansichten, AR, Add-ons aus Hagens User Journey und die Demo. Technik steht in [`architecture.md`](architecture.md), Schnittstellen in [`contracts.md`](contracts.md).

## 1. Eine Web-App, zwei Ansichten, keine native App

**Mobile (Navigation unterwegs):**
- Ziel: schnell herausfinden, wohin ich gehen muss, und dorthin kommen. Fokus auf dem Voice-Agenten.
- Vor dem Start wähle ich die Art der Führung: **Karte**, **Wegbeschreibung** oder **AR** (Kamerabild mit Weganweisungen, später).
- Start auch über einen QR-Code aus der Desktop-Ansicht. Der Link öffnet die Mobile-Ansicht mit dem Objekt als Ziel, als Add-on auch mit einer ganzen Tour. QR-Codes dienen nicht zur Ortung.
- Vorlage ist Lenards Prototyp in `web/mobile/` (Vollbildkamera, Route oben, Minimap oben rechts, Agent unten, Blobatar `alain00`). Regeln dazu in `web/mobile/AGENTS.md`.

**Desktop (Verwaltung und Planung):**
- Gebäude ansehen, Teile und Räume suchen, ihren Ort auf der Karte zeigen.
- Elemente und Objekte verschieben, zum Beispiel eine Maschine in einen anderen Raum. Bereiche sperren. Jede Änderung mit Vorschau, Bestätigung und Undo.
- Voice- und Chat-Layer.
- **Multi-User nur als Mock:** Andere Nutzer, Anwesenheit und Aktivitäten sehen echt aus, sind aber nicht implementiert. Die App soll wie ein vollständiges Produkt wirken. Die Änderungen selbst sind echt und erscheinen sofort auf allen Geräten.
- Klick auf ein Objekt, zum Beispiel eine Maschine, zeigt einen **QR-Code**. Mit dem Handy gescannt, startet er die Mobile-Ansicht mit Navigation zu diesem Objekt.
- **Neues Gebäude:** Import einer `building.json`. Danach funktionieren Ansicht und alle Tools sofort. Kein Bild-, PDF- oder SVG-Import.

## 2. Gesprächsverhalten

Die Regeln für beide Voice-Agents stehen in [`elevenlabs-agent-config.md`](elevenlabs-agent-config.md) §3. Sie gelten auch für den Textchat.

## 3. AR per Kamera (späteres Add-on)

Nach den Phasen 1, 2, A und B. Keine Tiefen- oder Abstandssensoren. Ablauf aus Lenards Codex-Test:
- Einmalig: Video des Gebäudes aufnehmen, Referenzbilder auswählen, pro Bild einen MegaLoc-Suchvektor und SuperPoint-Merkmale speichern.
- Live: Das Handy schickt 1–2 klare Bilder pro Sekunde an den Server. [hloc](https://github.com/cvg/Hierarchical-Localization) sucht mit MegaLoc die ähnlichsten Referenzbilder, LightGlue gleicht nur diese ab, eine geometrische Prüfung verwirft unsichere Treffer. „Keine sichere Position“ ist ein gültiges Ergebnis.
- Die Position geht direkt an Routenplanung und Anzeige. Der Voice-Agent bekommt Raum- und Etagenwechsel als Kontext-Update. Laut ElevenLabs unterbricht ein solches Update keine laufende Antwort.
- **Stand:** Offline auf dem Mac getestet. Ein Foto fand das passende Videobild mit 180 geprüften Punkten, 1,2 s Rechenzeit auf der CPU. Es fehlt noch die Zuordnung der Referenzbilder zu Koordinaten im Grundriss.
- Grenzen: Eine Web-App hat ohne WebXR keine Bewegungsverfolgung zwischen zwei Ortungen. iPhone Safari unterstützt kein WebXR `immersive-ar`.
- **Eigener Dienst in Python** (`localizer`), getrennt vom TypeScript-Stack, weil hloc ein Python-Projekt ist. Code: `floor-localizer` im Codex-Workspace.
- **Kamerabilder:** Bis AR kommt, verlassen keine Bilder den Browser. Mit AR schickt das Handy Bilder nur im AR-Modus und nur an unseren eigenen Ortungsdienst. Der Dienst speichert sie nicht.

## 4. Add-ons aus Hagens User Journey

Nach den Phasen 1, 2, A und B.
- **Tour mit mehreren Teilen:** Am Desktop mehrere Teile wählen, das System schlägt eine gute Reihenfolge vor. Der QR-Code bringt die ganze Tour aufs Handy. Bis 7 Stopps rechnen wir alle Reihenfolgen durch, darüber eine Heuristik, die wir als solche benennen.
- **Störung während der Tour:** Ein Lift wird in der Verwaltung gesperrt. Das Handy bekommt das Ereignis über den WebSocket, sagt es an und berechnet die restliche Tour neu. Mit Rollstuhlprofil wird daraus nie still eine Treppenroute. „Keine Route“ ist eine gültige Antwort.
- **Teile bewegen sich:** kleine Animation in der Verwaltungsansicht, keine echte Ortung.

## 5. Demo-Story (Live-Demo 3–5 Minuten, 25 Interaktionspunkte)

**Regeln:** Die Demo läuft live und ohne Neustart (README 1.1.0). Kein Deploy vor der Demo, ein vollständiger Probelauf auf der öffentlichen URL, Textchat als Fallback, wenn das Mikrofon versagt. Dieselbe Geschichte nutzen wir für das Video.

Fabrikhalle, drei Nutzer auf zwei Geräten, eine Karte, alles per Stimme:
1. **Techniker** am Handy (Mobile-Ansicht, gestartet über den QR-Code an der Maschine im Desktop): „Welche Presse ist Linie 4, wie komme ich hin?“ Der Agent antwortet mit Landmarken, die Route ist animiert, die nächsten Schritte kommen auf „weiter“.
2. **Facility Manager** am Laptop: „Der Ostlift ist in Wartung.“ Der Agent zeigt eine Vorschau mit den betroffenen Routen und wartet auf ein „Ja“. Danach aktualisiert sich die Karte **sofort auch auf dem Handy des Technikers**.
3. **Gabelstaplerfahrer:** „Gang 4 ist blockiert, schnellster Weg zu Dock B?“ Die Route nutzt nur Öffnungen ab 3 m und fährt nicht durch die Produktion.
4. Aufklappbare Ansicht „So habe ich das berechnet“ mit dem Tool-Trace. Das ist Syneras Linie: *„Das LLM interpretiert, die Regeln entscheiden.“*
5. Am Ende kurz der Benchmark-Score und die Kosten pro Frage als Beleg für Effizienz.

**Erweiterung, wenn die Add-ons stehen:** Manfred ist neu in der Fabrik und muss fünf Teile holen. Er wählt sie am Desktop, scannt den QR-Code und läuft die Tour mit dem Handy. Unterwegs fällt ein Lift aus, und die App führt ihn über die Treppe weiter.
