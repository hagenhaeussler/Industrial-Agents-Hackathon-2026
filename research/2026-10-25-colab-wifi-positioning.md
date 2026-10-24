# Colab: reale Positionierung mit Android, iPhone und Laptop

Stand: **25. Oktober 2026**. Neue Nutzerentscheidung: Positionierung ist für diese Colab-Erweiterung ausdrücklich gewünscht; die frühere Wi-Fi-Ausklammerung im Masterplan ist hier überholt. Verfügbar sind Android und iPhone. AP-Positionen, Router-Administration und reale Radio-Messungen liegen uns derzeit nicht vor.

## Empfehlung und Grenzen

**Praktischer erster Versuch: Android erfasst echte Wi-Fi-Fingerprints an bekannten Punkten auf Etage 3 und 4; das Backend vergleicht neue Messungen mit dieser Radio-Karte; alle Browser zeigen denselben, als ungenau gekennzeichneten Gerätestandort.** Dafür braucht man keine Router-Koordinaten. iPhone und Desktop können das Android verfolgen. Das lokalisiert das iPhone selbst noch nicht.

Das Ergebnis ist zunächst eine **grobe Zuordnung zum ähnlichsten vermessenen Referenzpunkt**, keine kontinuierliche zentimetergenaue Bewegung. Das Grundprinzip einer Radio-Karte aus gemessenen Signalstärken an bekannten Orten ist wissenschaftlich etabliert; die Genauigkeit für diese Geräte und dieses Gebäude muss trotzdem vor Ort gemessen werden. [Microsoft Research: RADAR](https://www.microsoft.com/en-us/research/project/radar/)

Die App überträgt Positionen unabhängig davon über WLAN **oder mobile Daten**. Die Wahl der Internetverbindung erzeugt keine Innenraumposition. Für den heutigen Einsatz bleibt QR-/manuelle Bestätigung ein hilfreicher unabhängiger Rückfallweg.

## Welche Verfahren passen?

| Verfahren | Was es tatsächlich liefert | Voraussetzungen / heutige Entscheidung |
|---|---|---|
| Browser-Geolocation | OS-Schätzung in WGS84, Genauigkeitsradius und Zeit; optionale Höhe, aber keine Gebäuderaum-ID | Für einen groben Gebäudestandort probierbar. Eine georeferenzierte Transformation zum lokalen Plan fehlt; Stockwerk nicht aus unzuverlässiger Höhe raten. Kein Ersatz der Indoor-Kalibrierung. |
| Android-Wi-Fi-Fingerprints | RSSI-Muster sichtbarer AP-Radios, Vergleich mit gemessenen Referenzorten | **Erster Versuch.** Native API/Termux-Begleiter, Berechtigungen, frische Scans und reale Radio-Karte erforderlich. |
| RSSI-Trilateration | Aus Signalstärke geschätzte Distanzen | **Nicht implementiert.** AP-Koordinaten, Sendeleistung und Ausbreitungsmodell fehlen; Wände, Reflexionen und Körperabschattung machen die Umrechnung instabil. |
| Wi-Fi RTT/FTM | Native Funk-Laufzeitmessungen zu kompatiblen APs | Erst prüfen, ob Telefon und mindestens drei APs das unterstützen und AP-Orte bekannt sind. Keine bestätigte Infrastruktur hier. |
| Mobilfunkzellen / 5G-Netzpositionierung | Native Zellinformationen oder koordinierter Netz-Ortungsdienst | Kein schneller Ersatz ohne Netz-/Standortinformationen, APIs und Betreiberintegration. Mobile Daten bleiben ein guter Transportweg. |
| BLE-Beacons | Nähe/RSSI-Fingerprints; spezielle Hardware kann Winkel messen | Nur bei bereits vorhandenen Beacons und nativer App sinnvoll. Beacon-Koordinaten bzw. Survey weiterhin nötig; Safari-Web-App ist kein allgemeiner BLE-Scanner. |
| QR/Bildmarker + visuelle Bewegung | Bekannter Referenzpunkt; ein geeignetes AR-System kann relative Bewegung weiterverfolgen | Schnellster belastbarer Anker für beide Geräte. Ein gelesener QR allein ist kein kontinuierliches Tracking; AR benötigt Registrierung, Maßstab und Drift-/Re-Anker-Behandlung. |
| IMU/Schrittzähler/Barometer | Relative Bewegung bzw. Höhenänderung | Mögliche spätere Fusion; benötigt Startpunkt und Kalibrierung, driftet und ersetzt keine absolute Raumposition. |

Die Browser-Geolocation-Spezifikation definiert geographische Koordinaten, Zeit und Genauigkeit; `enableHighAccuracy` ist eine Anforderung, keine Genauigkeitsgarantie. Höhe kann fehlen und bezieht sich auf das WGS84-Ellipsoid. Eine Stockwerksnummer gehört nicht zum API-Vertrag. [W3C Geolocation](https://w3c.github.io/geolocation/)

GNSS wird durch Abschattung und Mehrwegeausbreitung in bzw. nahe Gebäuden schlechter. Deshalb ist ein im Browser sichtbarer blauer Punkt noch kein Nachweis, dass eine der beiden Colab-Etagen erkannt wird. [GPS.gov: GPS Accuracy](https://www.gps.gov/gps-accuracy)

## Browser, iOS und Android: entscheidende Unterschiede

**Browser:** Die Network Information API liefert Verbindungseigenschaften, keine Liste benachbarter BSSIDs samt RSSI. Ihr `rtt` ist eine grob gerundete **Anwendungsnetzwerk-Latenz**; es ist ausdrücklich nicht das Funk-Ranging der Wi-Fi-RTT-API. HTTPS-Pingzeiten lassen sich deshalb nicht sinnvoll zu Metern zum Router umrechnen. [Network Information API](https://wicg.github.io/netinfo/)

**iPhone/iPad:** Apple bietet keine allgemeine Wi-Fi-Scan-API. `NEHotspotHelper` ist ein besonders berechtigter Hotspot-Integrationsweg und nicht für Wi-Fi-Ortung bestimmt. `NEHotspotNetwork.fetchCurrent` liefert unter Voraussetzungen die aktuelle SSID/BSSID/Sicherheitsart, keine vollständige Signalstärkenkarte. Die offizielle Empfehlung für allgemeine Position ist Core Location. Folgerung für uns: weder Safari noch eine kleine beliebige iOS-App versprechen unabhängig verfügbare Nachbar-WLAN-RSSI-Scans. [Apple TN3111](https://developer.apple.com/documentation/technotes/tn3111-ios-wifi-api-overview), [fetchCurrent](https://developer.apple.com/documentation/networkextension/nehotspotnetwork/fetchcurrent(completionhandler:))

**Android:** Ein nativer Scanner kann `WifiManager` verwenden. `getScanResults()`/`startScan()` benötigen passende Wi-Fi-/Standortberechtigungen und aktivierte Standortdienste; unter aktuellen Ziel-SDKs ist präziser Standort erforderlich. Android 13s `NEARBY_WIFI_DEVICES` ersetzt bei diesen Scan-APIs nicht pauschal `ACCESS_FINE_LOCATION`. Da wir tatsächlich Ortung betreiben, ist `neverForLocation` keine zutreffende Deklaration. Vordergrund-Scans sind üblicherweise auf vier innerhalb von zwei Minuten begrenzt, Hintergrund-Scans aller Apps zusammen noch stärker. Ein neuer HTTP-Upload bedeutet daher nicht automatisch einen neuen Funkscan. [Android Scan-Ablauf](https://developer.android.com/develop/connectivity/wifi/wifi-scan), [Berechtigungen](https://developer.android.com/develop/connectivity/wifi/wifi-permissions)

**Termux-Sonderfall:** `termux-wifi-scaninfo` liest den letzten OS-Scan; es fordert keinen neuen Scan an. Der Java-Adapter exportiert `ScanResult.timestamp`. Diese Zahl ist laut Android **Mikrosekunden seit Boot**, nicht Unix-Zeit und nicht Millisekunden. Unser Collector vergleicht sie mit `CLOCK_BOOTTIME`, übernimmt das Alter jeder Messung und verwirft alte oder unplausible Einträge. Frische Empfangszeit allein frischt Cache-Daten nicht auf. [Termux-Implementierung](https://github.com/termux/termux-api/blob/master/app/src/main/java/com/termux/api/apis/WifiAPI.java), [Android ScanResult](https://developer.android.com/reference/android/net/wifi/ScanResult#timestamp)

**Laptop:** Linux `iw dev <interface> scan` liefert AP-Daten; Berechtigungen und WLAN-Hardware müssen funktionieren. Der Collector startet kein `sudo` und ändert keine Netzwerkeinstellungen. macOS hat CoreWLAN, doch BSSIDs können durch fehlende Standortberechtigung redigiert sein. Ein optionaler PyObjC-Adapter ist vorbereitet, die tatsächliche App-/Terminal-Berechtigung muss auf dem Mac geprüft werden. [Linux iw](https://wireless.docs.kernel.org/en/latest/en/users/documentation/iw.html), [Apple CoreWLAN](https://developer.apple.com/documentation/corewlan/cwinterface/scanfornetworks(withssid:includehidden:)), [Apple DTS zu CoreWLAN/Core Location](https://developer.apple.com/forums/thread/710812)

## Mobile Daten, Mobilfunk und alternative Funktechniken

Androids `getAllCellInfo()` benötigt präzisen Standort und unterstützt nur vorhandene Telefonie-Funkfunktionen. Ab Android Q liefert es Cache-Daten; angeforderte Updates sind begrenzt und nicht garantiert. Die Zellenkennung und Empfangsleistung sind noch keine bekannten Innenraumanker. Ein eigener Mobilfunk-Fingerprint-Versuch hätte weiterhin Survey und Frische-/Geräteprobleme und ist für unsere zwei Etagen nicht nachweislich besser. [Android TelephonyManager](https://developer.android.com/reference/android/telephony/TelephonyManager#getAllCellInfo())

5G-Positionierung existiert, ist aber ein koordiniertes Netzverfahren: Die Location Management Function verarbeitet UE-/RAN-Messungen innerhalb der Netzarchitektur. Daraus folgt kein allgemein nutzbarer JavaScript-Endpunkt für präzise Colab-Ortung. Für eine spätere Betreiberlösung müssten verfügbarer Dienst, Berechtigung, Abdeckung und lokale Koordinaten geklärt werden. [ETSI/3GPP TS 29.572, Abschnitt 4](https://www.etsi.org/deliver/etsi_ts/129500_129599/129572/18.10.00_60/ts_129572v181000p.pdf)

Wi-Fi RTT misst dagegen Funklaufzeiten, benötigt kompatible Geräte/APs und bekannte Ankerorte für Multilateration. Die Android-Dokumentation nennt für geeignete Konfigurationen typischerweise 1–2 m; diese Zahl ist **kein hier gemessenes Ergebnis**. Wir haben weder Kompatibilität noch Ankerorte bestätigt und implementieren darum kein scheinbar fertiges RTT-Modul. [Android Wi-Fi RTT](https://developer.android.com/develop/connectivity/wifi/wifi-rtt)

BLE-RSSI kann für Nähe/Fingerprints dienen. Präziseres Bluetooth Direction Finding benötigt unter anderem Antennenarrays an den passenden Sendern/Empfängern; vorhandenes Bluetooth im Telefon reicht dafür nicht. Web Bluetooths dokumentierter Weg verbindet nach Nutzerauswahl mit GATT-Geräten und ist keine verlässliche plattformübergreifende Hintergrund-Ortung für unsere Safari-Zielgeräte. [Bluetooth SIG Direction Finding](https://www.bluetooth.com/learn-about-bluetooth/feature-enhancements/direction-finding/), [Chrome Web Bluetooth](https://developer.chrome.com/docs/capabilities/bluetooth)

## In etwa 60–90 Minuten vor Ort: Entscheidungstest statt Genauigkeitsversprechen

Dies ist eine **Arbeitsschätzung**, abhängig von vorhandenen Installationen und Scanfreigaben.

1. **Erste 10–15 Minuten:** Android-Modell/Version notieren, Termux und Termux:API aus derselben Quelle installieren. Auf [F-Droid Termux](https://f-droid.org/en/packages/com.termux/) und [F-Droid Termux:API](https://f-droid.org/en/packages/com.termux.api/) sind beide verfügbar. Unterschiedlich signierte Quellen nicht mischen. Bestehende Installationen nicht ungeprüft löschen. [Offizielle Installationsregeln](https://github.com/termux/termux-app#installation)
2. Android-Einstellungen: WLAN und Standort aktivieren; Termux:API die benötigte präzise Standortfreigabe geben. Dann im Termux-Terminal:

   ```sh
   pkg install python termux-api
   termux-wifi-scaninfo
   python scripts/colab_wifi_collector.py --source termux --count 1
   ```

   Das Skript muss zuvor als Datei auf das Telefon übertragen werden. Keine Router-Passwörter sind nötig. Bei leerem Ergebnis, redigierten BSSIDs oder alten Zeitstempeln zuerst Berechtigungen/OS-Scans prüfen. Ein dauerhaft wiederholter Cache ist kein Tracking. Einen eventuell angebotenen Entwickler-Schalter zur Scan-Drosselung nur bewusst für das Testgerät verwenden; unser Skript verändert ihn nicht.
3. **10–20 bekannte Punkte auf Etage 3 und 4** wählen: nahe Lift/Treppe, Flurverzweigungen, markante Räume. An jedem Ort mehrere *verschiedene frische* Scans aufnehmen, möglichst in mehreren Körper-/Telefonorientierungen. Doppelt gelesene Cache-Samples zählen nicht als neue Messung. Kartepunkt und echte Standposition müssen übereinstimmen; der schematische Colab-Plan setzt der metrischen Genauigkeit eine weitere Grenze.
4. Admin erzeugt im Pairing-Ablauf einen Empfangstoken für dieses Android. Nur diesen kurzlebigen Token als `COLAB_TRACKING_TOKEN` setzen, nicht den Admincode. Upload ist optional und explizit:

   ```sh
   python scripts/colab_wifi_collector.py --source termux \
     --device-id PAIRING_DEVICE_ID --label 'Survey Android' \
     --endpoint https://YOUR-APP/api/colab/wifi/scans \
     --count 120 --interval 30
   ```

   Token über einen sicheren Eingabedialog bzw. Umgebungsmechanismus setzen, nicht als CLI-Argument/URL in die History schreiben. Die Paarungs-ID muss zur Tokenbindung passen. Das Intervall fordert keine neuen OS-Scans an.
5. Über `POST /api/colab/wifi/capture` mit Adminfreigabe den letzten **frischen** Gerätescan an den bestätigten Kartenpunkt binden. Erst mindestens zwei räumlich verschiedene Referenzen ermöglichen dem Modul einen Vergleich; das ist eine Software-Mindestanforderung, keine ausreichende Venue-Abdeckung. Im echten Survey deutlich mehr Punkte sammeln.
6. **Abnahme mit zurückgehaltenen Messungen:** Punkte erneut anlaufen, die nicht als derselbe Scan gespeichert wurden; nach Möglichkeit weitere Zwischenpunkte testen. Richtige Etage/Raum, Fehlerdistanz zur tatsächlichen Position, fehlende Fixes, Zeit seit letzter echter Messung und Verzögerung bis zur zweiten Anzeige protokollieren. Telefon drehen, Treppe/Lift wechseln, Verbindungsunterbrechung simulieren. Erst daraus eine Genauigkeitsangabe ableiten.
7. Wenn frische Scans oder trennbare Muster fehlen: Position als unbekannt anzeigen, QR-/manuelle Quelle nutzen. Keine weiche Animation eines alten Punkts als neue Messung ausgeben.

## Implementierter, bewusst kleiner Vertrag

`core/localization.py` ist reine Python-Logik, ohne Funkzugriff, Persistenz oder neue Abhängigkeit. `estimate_position(scan, calibration, now=...)` liefert `estimated`, `uncertain`, `insufficient_data`, `stale` oder `invalid`. `validate_calibration` prüft das Format; das Backend prüft zusätzlich Gebäude-/Raummitgliedschaft und Berechtigung.

- `scan`: `observed_at` mit Zeitzone, `readings: [{bssid, rssi_dbm, age_s?}]`, `synthetic`.
- `calibration`: `schema_version: 1`, `building_id`, `synthetic`, `fingerprints: [{id, floor_id, space_id, point:[x,y], readings}]`.
- Mindestens drei gemeinsame **BSSIDs** werden benötigt. Das sind Funk-IDs, nicht zwingend drei physisch getrennte APs; mehrere SSIDs/Bänder können vom selben Gerät kommen.
- Mediane für doppelte BSSID-Werte; begrenzte Korrektur kleiner Empfänger-Offsets, fehlende APs als Strafterm; großer Signalabstand oder ähnliche Kandidaten auf verschiedenen Etagen/Räumen ergeben keinen behaupteten Fix.
- Der ausgegebene Punkt ist der beste **surveyte Referenzpunkt**. Kein Mittelwert zwischen Räumen, der durch eine Wand liegen könnte. `confidence: low`; `uncertainty_radius_m` ist ausdrücklich `uncalibrated_heuristic`, kein Konfidenzintervall und keine gemessene 3-m-Genauigkeit.
- Daten älter als standardmäßig 20 s werden abgelehnt, ebenso unplausible zukünftige Zeitstempel. Einzelmessungsalter und Uploadverzögerung werden addiert. Die Anzeige muss alte Fixes ebenfalls sichtbar veralten lassen.
- Synthetische Kalibrierung oder Messung erzeugt keine reale Position. Beispiele unter `research/examples/colab-wifi-*.synthetic.json` enthalten ausschließlich erfundene Werte.
- Der Collector kann lokal ausgeben oder explizit hochladen. Er sendet keine SSID, private Client-MAC oder Router-Zugangsdaten. Backend-Fingerprints sind private Kalibrierung; öffentliche Positionsevents brauchen keine AP-IDs. JSON-Dateien behalten Zeit und Synthetic-Flag; kein automatischer Replay als Live-Messung.

Schnittstellen und Token-/Persistenzablauf: [`docs/colab-demo.md`](../docs/colab-demo.md). API-Transport, Empfangsberechtigung, Speicherung und Anzeige sind separate Integrationsaufgaben; das reine Modul authentifiziert keine physische Anwesenheit.

## Wiederverwendbare Projekte und fehlende Ressourcen

| Quelle | Nutzen / Grenze |
|---|---|
| [Termux:API](https://github.com/termux/termux-api), GPLv3 | Verwendetes externes Android-Werkzeug, kein kopierter Anwendungscode. Liefert RSSI/BSSID/Scan-Zeit; Cache-/Berechtigungsgrenzen bleiben. |
| [FIND3](https://github.com/schollz/find3), MIT | Referenz für Lernen/Tracken von Fingerprints mit separaten Scannern. Komplettes System würde heute einen zweiten Server-/ML-Stack einführen; unsere kleine Vergleichslogik bleibt leichter integrierbar. Keine übernommene Codebasis. |
| [Android WifiRttScan](https://github.com/android/connectivity-samples/tree/main/WifiRttScan), offizielles Sample | Gut zum Hardwaretest der RTT-Unterstützung. Das Repository ist seit Juli 2025 archiviert; vor Einsatz Build/SDK aktualisieren. Kein fertiger Venue-Lokalisierer. |
| [Linux iw](https://wireless.docs.kernel.org/en/latest/en/users/documentation/iw.html) / [CoreWLAN](https://developer.apple.com/documentation/corewlan) | Vorhandene Laptop-APIs statt eigener Treiber. Adapter ist vorbereitet; keine physischen Linux-/Mac-Radiotests dieses Reviews. |

**Jetzt benötigt:** funktionierender Android-Begleiter mit frischen Scans; 10–20 korrekt beschriftete Referenzorte; zugehörige echte RSSI-Werte; sichere Geräte-Paarung; reales Etagen-/Held-out-Protokoll. Android- und Laptop-Empfänger können unterschiedliche Pegel liefern, deshalb Hardwarewechsel gesondert testen bzw. neu kalibrieren.

**Falls AP-Koordinaten später gewünscht:** Venue-IT nach Controller-/Installationsplan mit AP-ID, **Radio-BSSID je Band**, Modell und physischer Montageposition fragen; vor Ort Beschriftung/BSSID-Zuordnung und Planmaßstab überprüfen. Die SSID allein ist keine eindeutige AP-Identität. Aus den stärksten RSSI-Werten keine vermeintlich exakten Router-Koordinaten erzeugen. Für RTT zusätzlich Geräte-/AP-FTM-Unterstützung und korrekte Höhen prüfen.

## Tatsächlich geprüft

Am 25.10.2026: `.venv/bin/python -m pytest -q tests/core/test_localization.py` → **24 bestanden**. Abgedeckt: eindeutige/mehrdeutige Fingerprints, Synthetic-Sperre, veraltete Messungen, Zukunftszeit, duplizierte APs, NaN/ungültige Pegel, extreme Zahlen/Koordinaten, Schema-/Gebäudeprüfung, Android-Mikrosekunden, alter Scan-Cache, Linux-Parser, unveränderte Datei-Zeit und HTTP-Zulassung. Das sind synthetische Softwaretests. **Keine echten Colab-Scans, keine Mobilfunk-Ortung, keine Genauigkeitsmessung und kein physischer Termux-/iPhone-/Laptop-Test wurden dadurch belegt.**
