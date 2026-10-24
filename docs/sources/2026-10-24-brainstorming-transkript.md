# Hackathon-Brainstorming — bereinigtes Transkript

- **Datum:** 24. Oktober 2026, Beginn laut Fireflies 14:08:59 Uhr (Europe/Berlin).
- **Meetingtitel:** „Oct 24, 02:08 PM“.
- **Dauer laut Metadaten:** ca. 50 Minuten 9 Sekunden.
- **Quelle:** [Fireflies-Aufzeichnung](https://app.fireflies.ai/view/01M5PX0WV7MKXJ3VN6CXRAQH74).
- **Transkript-ID:** 01M5PX0WV7MKXJ3VN6CXRAQH74.
- **Verfügbarer Text:** 521 Segmente von 00:03 bis 50:08, einschließlich kurzer Zwischenrufe und Nebenunterhaltungen.

## Hinweise zur Bereinigung

Dies ist eine behutsam bereinigte Lesefassung des von Fireflies gelieferten Textes, kein anhand der Audiodatei geprüftes Wortprotokoll. Zeichensetzung, eindeutige Fachbegriffe und schwer lesbare Satzbauten wurden geglättet. Direkt aufeinanderfolgende Äußerungen derselben Sprecherkennung sind zum Teil zusammengeführt; die Zeitbereiche bleiben erhalten. Alle 521 gelieferten Segmente sind in der Lesefassung berücksichtigt.

Fireflies liefert fünf Sprecherkennungen, aber keine verifizierte Zuordnung zu Personen. Deshalb bleiben „Sprecher 1–5“ anonym; die Kennungen können bei Zwischenrufen oder Sprecherwechseln falsch sein. Unverständliche Formulierungen, unvollständige Sätze und unsichere Modellnamen sind markiert. Ergänzungen in eckigen Klammern sind redaktionell. Gesprächsannahmen und sachliche Irrtümer werden hier nicht nachträglich korrigiert; der Abgleich mit dem Repo steht separat in der Zusammenfassung.

Der Connector meldet „Partial results“ wegen zwei Fehlern bei nicht näher bezeichneten Feldern. Der Text reicht nahezu bis zur angegebenen Aufnahmedauer; seine Vollständigkeit ist dennoch nicht unabhängig bestätigt. Audio und Video wurden nicht bereitgestellt. Die Themenüberschriften sind redaktionelle Orientierungshilfen.

## Gespräch
### 00:00 — Bewertung, Vorauswahl und mögliche Finalstrategie

**[00:03–00:30] Sprecher 1:** Ich würde damit anfangen, so wie ich es verstanden habe, zu paraphrasieren, was die Challenge ist. Dann kann jeder seine Idee einbringen, damit wir erst einmal auf demselben Stand sind, was wir überhaupt machen müssen. Genau, mach ich noch das Ding hier auf. Also hier ist ja alles beschrieben. Auf dem Meta-Level habe ich es so verstanden, dass wir erst einmal nur die drei, vier Leute …

**[00:32–00:32] Sprecher 2:** Von.

**[00:32–01:40] Sprecher 1:** … von Synera davon überzeugen müssen, dass wir diese Kriterien erfüllt haben. Erst einmal „Does it work“, „Interaction“, „Creativity“ und „Submission Demo“. Falls wir unter die vier Finalisten kommen, geht es noch einmal separat weiter: Dann kommen von den anderen zwei Companies und von den zwei anderen Partnern Leute dazu, insgesamt fünf. Da machen wir diese vier Minuten Demo. Die wissen eigentlich noch nicht so viel darüber, was wir machen, und hören den Pitch auch mehrmals. Diese genannten Punkte werden dann von der Gewichtung her komplett geändert, weil sie gar nicht mehr testen können: Funktioniert der Code? Das ist dann scheißegal. Da geht es vielmehr um die Demo: Versteht ein Laie, was wir machen? Im Zweifel pitchen noch drei andere genau das Gleiche. Den Creativity- und Demo-Part müssen wir dann komplett aufblasen und darauf optimieren. Das erst einmal auf Demo-Level. So habe ich es verstanden. Ich habe auch mit Hendrik, der das organisiert, darüber gequatscht, und so hat er es designt.

**[01:41–01:57] Sprecher 1:** Deswegen müssen wir initial diese drei, vier Leute davon überzeugen, dass unser Ding den Standard erfüllt, beziehungsweise … Das einmal auf dem Meta-Level. Hat das jemand anders verstanden?

### 02:00 — Sprachinteraktion und Fragen-Benchmark

**[02:01–03:15] Sprecher 1:** Dann zum System. [Satzteil unklar.] Wir haben den User und die Systeminteraktion. So wie ich es verstanden habe, erfolgt der Input eigentlich nur über Voice, nicht über Tippen. Dann geht es in das System rein. Das Interessante an der Challenge ist: Es gibt einmal die Interaktion mit dem User und einmal die Fragen. Beim Interaction-Part gehen wir mit Voice rein und bekommen Voice zurück, wahrscheinlich auch ein Bild dazu: eine schöne Animation oder eine isometrische Ansicht, die zeigt, wie man sich auf dem Floor von dort nach dort bewegt und den Lift nimmt. Idealerweise kommt Voice dazu. Das ist die Grundinteraktion. Zusätzlich gibt es dieses Fragenfile. Wir müssen uns genau ansehen, welche Fragen sie stellen, und herausfinden, ob die späteren Fragen ähnlich sind. Wir hatten schon darüber gesprochen: Wahrscheinlich sind es ähnliche Fragen — oder komplett neue Fragen? [Satzbezug unklar.]

**[03:18–03:30] Sprecher 1:** Genau diese vier unterschiedlichen Fragentypen. Wahrscheinlich kommen ähnliche Fragen auch in den Benchmark. [Satzende unvollständig.]

### 03:31 — Train, Dev, Test und die Frage nach Modelltraining

**[03:31–04:03] Sprecher 3:** Wir haben drei Datensets: Dev, Test und Train. Dev und Train enthalten die richtigen Antworten. Test hat keine Antworten; die müssen wir am Ende abgeben. Das sind unsere Submissions, so habe ich …

**[04:03–04:05] Sprecher 1:** … es nicht verstanden. Ich hatte es so verstanden …

**[04:05–04:05] Sprecher 2:** Die nehmen …

**[04:11–04:14] Sprecher 3:** … in der README steht — oder vielleicht doch … [Satzfragment.]

**[04:14–04:19] Sprecher 1:** Kann sein, dass wir die Questions schon haben. Okay, das wäre interessant zu wissen.

**[04:20–04:23] Sprecher 4:** Was ist der Unterschied zwischen Test und Train?

**[04:28–04:34] Sprecher 1:** Bei Train haben wir schon die Antwort, das heißt daran können wir schon mal sehen, okay, was wäre denn eine gute Antwort für Buildings, die wir schon kennen?

**[04:34–04:35] Sprecher 4:** Yes.

**[04:40–04:51] Sprecher 2:** So, you are in the Industrial Agents team, right? Your name was mentioned in another team as well, like Anshu, Raj and Fa. [Names uncertain.]

**[04:52–04:56] Sprecher 4:** “We’re rejecting them, should have communicated.” [Wortlaut/Sinn der Antwort unklar.]

**[04:59–05:00] Sprecher 2:** Okay, cool.

**[05:09–05:35] Sprecher 3:** Also nochmal zu train, dev und test. Train hat 200 Gebäude mit Fragen und Antworten. Dev hat 40 Gebäude: „same as train; use for self-evaluation“. Test hat 40 Gebäude ohne …

**[05:37–05:37] Sprecher 2:** Das.

**[05:37–05:39] Sprecher 3:** Müssen wir dann auch abgeben …

**[05:41–05:52] Sprecher 4:** Aber das heißt … Dev and Train. … Gebäude, zwei unterschiedliche. [Satzfragment.]

**[05:54–05:59] Sprecher 2:** Guys, Anthropic keys are released, check your manager. “Oh, I can more platform.” [Unklar.]

**[06:02–06:08] Sprecher 1:** Machen wir später. Aber ich verstehe immer noch nicht den Unterschied zwischen Train und Dev.

**[06:09–06:21] Sprecher 3:** Train ist zum Trainieren eines ML-Modells. Dev ist dafür da, das trainierte Modell auf einen getrennten Datensatz anzuwenden, weil du …

**[06:21–06:34] Sprecher 1:** Ach so, zum Testen, damit du nicht auf die Trainingsdaten overfittest. Okay, verstehe. Vielleicht hätten sie irgendwie Test und Evaluation.

**[06:34–06:36] Sprecher 4:** Nehmen sollen oder whatever, wir werden es dann raus.

**[06:36–07:07] Sprecher 1:** Gut, okay, dann ist das ja schon mal klar, aber diese ganzen Informationen sollten wir noch bestätigen, also dass wir da jetzt keine falschen Annahmen haben, aber das klingt erstmal logisch. Wenn ich es richtig verstehe und wir die Fragen haben, auch die Fragen für die Evaluation, können wir komplett auf diese Fragen trainieren. Wenn wir kein Modell trainieren, sondern nur Prompting machen, können wir den Prompt schon dafür bauen, etwa einen Skill für jede einzelne Frage.

**[07:07–07:10] Sprecher 3:** Ich denke, wir haben jetzt alle nicht so ML Experience.

**[07:13–07:19] Sprecher 1:** Im Zweifel kriegen wir auch ein bisschen Post-Training hin. [Satzanfang unklar.] Also ich hab's noch nie gemacht, aber.

**[07:19–07:24] Sprecher 5:** Mit Tokens auslesen oder so habe ich einmal etwas gemacht. [Wortlaut teilweise unklar.]

**[07:24–07:28] Sprecher 1:** Das war schon ein bisschen, ja, keine Ahnung. Claude muss es können.

**[07:29–07:34] Sprecher 4:** Ich glaube nicht, dass es ein Bottleneck sein wird, diesen Benchmark zu erreichen.

**[07:34–07:35] Sprecher 1:** Das sollte kein Problem sein.

**[07:36–07:39] Sprecher 4:** Wir [unklar: „meisten“] die Top vier, und dann müssen wir bei der Präsentation …

**[07:42–08:03] Sprecher 1:** Die Frage ist halt, wie schwer die neuen Gebäude sind und was es da Besonderheiten gibt und sowas. Das können wir auch noch machen, das müssen wir auch noch rausfinden, wie viel anders die sind. Kommt da plötzlich eine Space Station als neues Gebäude … … oder auch ein Gebäude mit Fahrstühlen? Kann jemand die Fragen aufschreiben, die wir dann stellen? [Satz teilweise abgebrochen.]

**[08:03–08:10] Sprecher 3:** Die wir dann den Leuten stellen. Es wird sowieso aufgenommen. Wir können dann … Das stimmt.

### 08:13 — Level 4: neue Gebäude, Updates und Eingabeformate

**[08:13–08:28] Sprecher 1:** Okay, das okay und dann, okay, also haben wir erstmal die Grundlage verstanden. Jetzt wollen wir uns nochmal die, ich meine im Prinzip, also die haben es ja auch geschrieben. Was heißt „Locate“, „Scale“ noch einmal?

**[08:49–08:58] Sprecher 1:** Das ist tatsächlich interessant. Bei Conversation. Das wäre das eine.

**[09:15–09:47] Sprecher 1:** Also wir können sowohl die, also das Building machen wir ja mit Voice anscheinend. „By conversation. A new building should … minutes …“ [Unvollständig vorgelesen.] Wir bekommen also nicht nur ein Gebäude und Fragen dazu, sondern müssen ad hoc ein neues Gebäude erstellen und dazu Fragen beantworten können — wahrscheinlich idealerweise dieselben Fragen.

**[09:47–10:15] Sprecher 4:** Das sollte man abklären, weil das ist glaube ich ein enormer Unterschied, ob man nur updatet oder ein ganz neues macht. Updaten würde ich so verstehen: Du verschiebst eine Maschine auf dem Floor von Reihe vier in Reihe zwei. Aber wenn du ein ganzes Gebäude … Ja, aber das steht ja hier basically. Ja schon, oder?

**[10:15–10:17] Sprecher 1:** [Unklar: „From fort cockern“.] Ja, die müssen das Gebäude dann.

**[10:18–10:20] Sprecher 4:** Vielleicht sollte man das klären.

**[10:20–10:24] Sprecher 5:** Ich meinte dasselbe. [Rest unklar: „Ich habe mich vorhin schon gemacht“.] Du kannst ja nicht ein ganzes Gebäude reinsprechen.

**[10:25–10:28] Sprecher 1:** Nein, das machst du dann mit [unklar: „Brok, aber Biker“].

**[10:28–10:31] Sprecher 5:** Aber du kriegst ein random Gebäude dann später als Frage.

**[10:32–11:18] Sprecher 1:** Also wie es jetzt wahrscheinlich ist. Du hast erst ein Gebäude, kriegst du hin, kriegst du von denen. Dazu kannst du jetzt per Conversation sagen, okay, by the way, in dem Building, so wie wir die Daten bekommen haben, ist es falsch. Das Equipment ist jetzt doch an einer anderen Stelle. Das machst du über Voice und dann kannst du zusätzlich noch einen Floorplan einladen und sagst, okay, dieses Unternehmen hat jetzt doch noch eine Zweigstelle. Hier ist der Floorplan von der Zweigstelle. Beantwortet dazu mal die Fragen, die wir haben. Floorplan … [Rest unklar: „sonst machst du ja keinen Flo“.] Es ändert sich jetzt. Also ich weiß nicht, das könnte auch sein, dass sie das wollen. Wir haben zwar dieses Modell unserer Firma, aber in einem Gebäude wurde viel abgerissen. Jetzt brauchen wir es neu, und hier ist der neue Floorplan. Also das weiß ich nicht. Vielleicht reicht auch das, ne?

**[11:18–11:21] Sprecher 4:** Das sollten wir relativ am Anfang klären.

**[11:23–11:30] Sprecher 1:** Da steht ja: „A new building should take minutes … days.“ [Im Transkript unvollständig wiedergegeben.] Das heißt ja nicht, dass. Also mit new building verstehe ich jetzt nicht, dass man dann Gebäude update.

**[11:31–11:41] Sprecher 3:** Okay, Also wir haben das Zeitfenster ist jetzt nicht einfach nur Sekunden oder halt innerhalb von sprichst rein Und dann in 10 Sekunden ist es da, sondern minutes.

**[11:41–11:46] Sprecher 1:** Das heißt, das Ding kann zehn Minuten rödeln und [unklar: „Astra laufen lassen“].

**[11:46–11:47] Sprecher 3:** Okay, also das ist schon mal gut. Das ist gut.

**[11:49–11:59] Sprecher 4:** Es ist doch kein realistischer Workflow, alles mit Voice zu erstellen. Ne, nicht mit Voice, aber mit Flo Plan, mit Floorplan. Aber das kann ja innerhalb von zwei Minuten oder so.

**[11:59–12:02] Sprecher 1:** Weiß ich nicht, wie lange Blender braucht. Ich hab's noch nicht ausprobiert.

**[12:02–12:04] Sprecher 3:** Du brauchst keinen Blender oder keine Ahnung …

**[12:04–12:08] Sprecher 1:** Welches Fileformat wir nehmen, um das zu erstellen.

### 12:08 — JSON, PNG und SVG als Daten- und Darstellungsformate

**[12:08–12:17] Sprecher 1:** Also das finde ich sowieso. Die sagen die ganze Zeit JSON. Aber kannst du ein ganzes Gebäude in JSON abspeichern?

**[12:17–12:20] Sprecher 4:** Ja klar, die Polygone und was auch immer.

**[12:20–12:21] Sprecher 1:** Okay, das ist alles in JSON.

**[12:23–12:24] Sprecher 4:** Also das hat Claude scheinbar.

**[12:24–12:26] Sprecher 3:** Ja, aber es basiert auf denselben Daten.

**[12:27–12:57] Sprecher 4:** Okay, also okay, spannende Treppe, aber geil. SVG und PNG sind auch dort, aber das bringt nicht so viel. Das kannst du eigentlich [unklar: „verspannen“]. Keine Maßstäbe. Vielleicht für Visualisierungszwecke: Du klickst auf den Raum, und dann zeigt er das als Floorplan.

**[12:59–13:05] Sprecher 3:** Sind die Daten in SVG und JSON exakt gleich? Hoffentlich. Dann brauchen wir die Bilder praktisch gar nicht.

**[13:06–13:08] Sprecher 4:** Sag mal deinen Meister, wenn die sowieso.

**[13:09–13:29] Sprecher 3:** Sind die Daten in den SVGs und PNGs genau dieselben wie die Daten in den JSONs? Also heißt das bräuchten wir eigentlich die Bilddateien gar nicht und könnten alles aus den JSON-Dateien rekonstruieren?

**[13:30–13:39] Sprecher 1:** Ne, also mit Sicherheit nicht, aber frag ihn. Mit Sicherheit wollen sie, dass wir auch mit PNGs arbeiten. [Rest unklar: „mit Chat Transmit“.]

**[13:39–13:41] Sprecher 3:** „Type Whisper“ — heißt das so? [Produktname unklar.]

**[13:41–13:44] Sprecher 4:** „Wie Type“, was ihr alle macht? [Unklar.]

**[13:47–13:49] Sprecher 3:** Oder ist es [unklar: „Close Global“]?

**[13:50–13:53] Sprecher 4:** Du kannst das auch mit [unklar: „Chat schon global“] machen.

**[13:53–13:55] Sprecher 3:** Ja, aber das fand ich nicht so gut.

**[13:58–14:07] Sprecher 4:** Ich habe es mir selbst gemacht. Ich habe es mir mit [unklar: „Germany“] gemacht. Du machst jeden Monat ein neues Ding.

**[14:12–14:25] Sprecher 1:** Gut, das haben wir. So und dann, also diese ganzen Fragen müssen wir erstmal klären. Aber ich sag mal, wenn die da PNG Datei reindroppen, dann wollen die mit Sicherheit auch, dass wir mit PNG Dateien arbeiten, auch wenn das painful ist, dann.

**[14:25–14:27] Sprecher 4:** Klickst du auf den Raum und dann zeigt er die PNG an.

**[14:27–14:40] Sprecher 3:** Ja, aber wie gesagt, wenn wir die Daten alle in JSON haben, dann würde ich lieber die JSON-Daten nehmen und es rekonstruieren, als die PNG Daten nehmen, die wir nicht manipulieren können. Das ist halt das Problem. JSON-Daten können wir manipulieren und ganz einfach neue Objekte [hinzufügen; Satzende unvollständig].

**[14:42–14:53] Sprecher 1:** Am Ende muss alles in JSON sein. Die Frage ist: Bekommen wir wahrscheinlich PNG und müssen diese Informationen nutzen, um sie in JSON umzuwandeln? Aber Working Format wird am Ende JSON bleiben, so wie ich das jetzt sehe.

**[14:58–15:12] Sprecher 5:** Ich weiß nicht genau, wie es geht. Aus dem Gedächtnis: Man könnte die Bilder als Kontext an die KI geben, damit sie weiß, welches JSON zu welchem Bild gehört. [Formulierung im Original teilweise unklar.]

**[15:14–15:15] Sprecher 1:** So, das ist das eine.

### 15:17 — Grundarchitektur: Agent, Datenbank und mögliche Erweiterungen

**[15:17–15:36] Sprecher 1:** Gut, und dann, okay, also das sind Grundlagen. Bei den Add-ins explodieren jetzt die Köpfe: Was können wir zusätzlich machen? Es gab „Moving Tools“, also dass sich Dinge plötzlich bewegen. Schon interessant, wie man das überhaupt in JSON abspeichert.

**[15:37–15:42] Sprecher 3:** Wollen wir alles einzeln durchgehen und schon einmal Ideen [sammeln]?

**[15:44–15:45] Sprecher 4:** Das machen wir mal fertig.

**[15:45–16:03] Sprecher 1:** Also jetzt direkt. Wir können erst Ideen zu den Grundlagen sammeln. Habt ihr spezielle Ideen, wie wir diese ersten vier Sachen besonders machen?

**[16:03–16:34] Sprecher 3:** Ich habe eine Idee bzw. Mein genereller Ansatz wäre: Ich nehme das JSON, speichere es in einer Datenbank und gebe einem Agent, einem LLM, Zugriff darauf. Dieses LLM ist das Brain des Speech-Modells. Also wir sprechen mit einem Speech Modell, dahinter steckt ein LLM, dahinter steckt die Datenbank.

**[16:34–16:35] Sprecher 1:** Kannst du das einmal wirklich auf …

**[16:41–16:42] Sprecher 5:** Unser Repo heißt … [Satzfragment.]

**[16:42–16:45] Sprecher 3:** Aber ich würde tatsächlich mit dem gegebenen hier schon anfangen.

**[16:45–16:48] Sprecher 5:** Das kann man ja klonen und dann damit weiterbauen, weißt du, dann haben wir ja ein bisschen.

**[16:55–16:55] Sprecher 1:** Genau …

**[16:57–17:06] Sprecher 4:** Was ist das für ein. App?

**[17:09–17:23] Sprecher 3:** Dann haben wir hier, sagen wir, ein … Und dann.

**[17:27–17:42] Sprecher 4:** Was ist unser Ansatz? Legen wir jetzt die technische Architektur fest oder erst einmal, wie die User Experience sein sollte? Hier stand auch „Multiplayer“, also mehrere Company-Accounts sozusagen.

**[17:42–17:43] Sprecher 1:** Genau, das wird noch als Add in …

**[17:44–17:45] Sprecher 4:** Macht ja auch einen Unterschied.

**[17:45–17:58] Sprecher 1:** Ich glaube, genau, also da können wir auch noch mal gleich drüber reden. Es ging erst einmal darum, die ersten vier Steps zu klären: wie wir es in der UI und unter der Haube machen wollen. [Ein Wort im Original unklar: „Kunden“.]

**[17:59–18:05] Sprecher 4:** Ich würde Under the Hood loslaufen lassen. Und schauen, was da cleverer Stand der Technik ist. [Wortlaut teilweise unklar.]

**[18:06–18:14] Sprecher 1:** Ich weiß nicht, wie gut man … Am Ende kommt es wahrscheinlich nur auf eine Seite. [Satzbezug unklar.] Also es ist jetzt nicht super wichtig.

**[18:16–18:17] Sprecher 4:** Ich finde, es klingt super sexy zu …

**[18:17–18:23] Sprecher 1:** … sagen, ja, wir haben [unklar: „nur bei einem“]. Wenn das scheiße ist, dann [unklar: „trinkt das“].

**[18:24–18:26] Sprecher 3:** So stelle ich mir das ungefähr vor.

### 18:28 — Fine-Tuning, Mobile first und zwei Nutzergruppen

**[18:28–18:29] Sprecher 4:** Was trainierst du jetzt für …?

**[18:31–18:37] Sprecher 1:** Du nimmst irgendein Open-Weight-Modell, gibst die ganzen Daten hinein und trainierst es auf diesen Daten.

**[18:37–18:38] Sprecher 3:** Ja, du brauchst ja aber Daten.

**[18:38–18:42] Sprecher 1:** Warum geben sie uns denn sonst Daten? Und dann nochmal Testdaten.

**[18:43–18:50] Sprecher 5:** Du brauchst Testdaten, wie gesagt, zum Testen, zum Trainieren und dann hast du die richtigen Daten separat damit du kannst.

**[18:51–19:01] Sprecher 1:** Genau, damit es nicht overfittet. Aber wenn sie das schon so liefern: Wollen sie von uns nur ein bisschen Prompt Engineering? Klingt für mich nicht so, aber wenn.

**[19:01–19:02] Sprecher 3:** Es am Ende das Bessere ist.

**[19:03–19:05] Sprecher 1:** Ja, wenn es besser ist, dann müssen wir das nehmen.

**[19:05–19:08] Sprecher 3:** Okay, also ich stelle es mir so vor, wir haben hier, die machen einmal.

**[19:09–19:17] Sprecher 4:** Prompt Engineering oder mit Skills oder was? Zum Beispiel [Modellnamen/Versionen unklar: „5 von 5 versus unser Quen 3.8“].

**[19:17–19:40] Sprecher 1:** Wir könnten zumindest jemanden daraufsetzen, das Trainieren eines Modells auszuprobieren: Werden wir damit besser? Oder wenigstens darüber nachdenken, ob ein Modelltraining sinnvoll ist. Wenn Claude gleich sagt: „Never ever, damit werdet ihr nicht besser“, können wir es lassen. Aber also ich sag mal, es klingt super sexy, es klingt viel viel besser als Ah ja, wir haben …

**[19:42–19:53] Sprecher 3:** Okay, also ich stelle es mir grundlegend so vor. Wir haben die Mobile App mit dieser Rekonstruktion, die auf der Datenbank basiert.

**[19:56–19:57] Sprecher 1:** Mobile first machen.

**[19:57–20:00] Sprecher 3:** In der JSON steht das so.

**[20:00–20:04] Sprecher 1:** Du läufst nicht mit deinem Computer durch die Fabrik.

**[20:05–20:07] Sprecher 5:** Achso, ich dachte, das wären so Bildschirme überall.

**[20:08–20:11] Sprecher 1:** Wie soll das aussehen? Wo sind eigentlich mein Bauteile?

**[20:11–20:17] Sprecher 5:** Ich meine riesige Bildschirme, und das ganze Gebäude ist ein Riesenbildschirm.

**[20:18–20:19] Sprecher 1:** Ich denke, das ist ein wichtiger realistischer Punkt.

**[20:19–20:21] Sprecher 4:** Wie machen es die in der Company? [Satz abgebrochen.]

**[20:21–20:28] Sprecher 1:** Die haben Kunden. Die werden in ihrer Fabrik mit Sicherheit am Handy sein. [Satzbau im Original unklar.] Der Arbeiter wird mit diesem Handy …

**[20:28–20:49] Sprecher 4:** Dann eine Web-App. Das Erstellen mit Floorplan sollen sie über die Web-App machen. Wir haben zwei Nutzergruppen, sagen wir einfach. In der Mobile App hast du einfach nur Navigation. [Letztes Wort im Original unklar: „gefüllt“.]

**[20:52–20:59] Sprecher 3:** Stell dir am Gebäudeeingang einen QR-Code vor. Du scannst ihn und kommst auf die Website. Das funktioniert genauso wie die Mobile App.

**[21:00–21:02] Sprecher 1:** Genau, das können wir auch wenn das.

**[21:02–21:02] Sprecher 3:** Wir brauchen gar keine … Das kann ja …

**[21:02–21:05] Sprecher 1:** Eine Site sein, also nur eine Website.

**[21:06–21:20] Sprecher 3:** Brauchen wir gar keine Mobile App. Keine App. Steht da hier Web Application.

**[21:20–21:26] Sprecher 1:** Web-App, einmal für den Bildschirm, etwa um etwas Neues zu erstellen. [Formulierung teilweise unklar.] Einmal ein Browser Version.

### 21:28 — Lese-/Schreibzugriff und die Rolle der Planbilder

**[21:28–22:20] Sprecher 3:** Die Idee: eine mobile Web-App mit einem Realtime-Conversation-Speech-Modell, mit dem der User sprechen kann. Dahinter steckt das eigentliche Brain: ein LLM-Agent mit Zugriff auf die Datenbank. Read and write. Read primär für die Frageaufgaben, Write für das Erstellen von Dingen. Genau, die Datenbank, die speichert das Ganze. Das JSON liegt im Git-Repo. Wir können alles rekonstruieren. Deswegen brauchen wir meiner Meinung nach die Bilder nicht: In den Bildern ist dasselbe wie in den Daten. Daraus können wir wieder [unklar: „reden“].

**[22:21–22:23] Sprecher 1:** Das geht. Was wir dann bekommen, sind da auch.

**[22:24–22:26] Sprecher 4:** Das ist eine gute Frage.

**[22:26–22:29] Sprecher 1:** Das, was wir erstellen müssen, Wir kriegen ein neues Gebäude.

**[22:29–22:30] Sprecher 4:** Wie bekommen wir es?

**[22:30–22:48] Sprecher 1:** Bekommen wir es in JSON? Ist es nur JSON, oder auch [unklar: „Python“]? Ja, genau. Wir können nicht sagen: „PNG haben wir ignoriert, weil es uns nicht wichtig erschien.“ Sondern wir müssen sagen: „PNG-Dateien, alles klar.“. Wir haben natürlich einen Agent, der die PNG-Dateien sofort in die Datenbank einspeist und die wichtigen Daten herausholt, aber …

**[22:48–22:49] Sprecher 3:** Dieselben Daten, die schon im JSON sind …

**[22:50–22:51] Sprecher 1:** Das kann man abgleichen.

**[22:51–22:53] Sprecher 4:** Aber hast du schon gefragt, JSON ist.

**[22:53–22:59] Sprecher 5:** JSON ist nicht so groß … damit du auch das Visuelle hast und weißt, ob ein Zimmer verschoben ist oder [unklar: „als PK“].

**[23:03–23:07] Sprecher 3:** Also du, wir.

**[23:07–23:09] Sprecher 1:** … schmeißen die weg und sagen: „Ah, darüber haben wir nicht nachgedacht.“ [Satzanfang fehlt.]

**[23:11–23:14] Sprecher 5:** Hier sind nämlich auch die Zimmer Nummern und.

**[23:14–23:17] Sprecher 4:** So und dann hat jedes Zimmer noch eine eigene.

**[23:17–23:24] Sprecher 1:** Kannst du mal so ein PNG noch, Das ist eine PNG. Ja.

**[23:24–23:28] Sprecher 4:** Und jetzt frag mal den Meister, was der Unterschied zwischen dem SVG und dem PNG ist.

**[23:32–23:35] Sprecher 1:** Es gibt auch eine SVG Datei, das.

**[23:35–23:36] Sprecher 4:** Das eine ist vektorbasiert, und das andere ist …

**[23:36–23:37] Sprecher 1:** Einfach …

**[23:39–23:40] Sprecher 4:** Das heißt, PNG ist, kannst du wegwerfen.

**[23:43–23:54] Sprecher 3:** Also hier steht, es ist sogar mehr Daten in den JSON-Dateien. Ich habe noch einmal nachgefragt: Wir können die Bilder deterministisch aus dem JSON rekonstruieren. Das heißt …

**[23:57–24:06] Sprecher 1:** Dann ist auch die Frage, warum gibt es denn, ja, okay, das müssen wir trotzdem noch fragen. Warum gibt es denn so einen Scheiß? Warum Geben Sie uns PNG Dateien, also als Bild, wenn wir sowieso SVGs haben?

**[24:06–24:08] Sprecher 3:** Also, ja, um mich zu verwirren …

**[24:11–24:12] Sprecher 1:** Alles klar.

**[24:23–24:30] Sprecher 4:** Ja, ist wirklich Spaß am Anfang. Das ist kein Bottleneck bei uns. Das wird schon …

**[24:33–24:35] Sprecher 5:** Wenn es zehn Minuten geht, bis …

**[24:39–24:40] Sprecher 4:** Die einzige Frage ist.

**[24:47–24:48] Sprecher 1:** Da jetzt schon viele Details.

### 24:52 — ElevenLabs, LLM und API-Anbindung

**[24:52–25:08] Sprecher 4:** Hier ist die Datenbank, hier sitzt ElevenLabs. Für die normalen Dinge müssen wir testen; vielleicht kann man ein schnelles Modell nehmen, zum Beispiel „Google Gemini 3.8 Flash“ oder so. [Modellversion im Transkript unsicher.]

**[25:08–25:11] Sprecher 3:** Ist, Haiku oder Sonnet.

**[25:17–25:49] Sprecher 4:** Möglichst schnell. Warum wollen wir jetzt schnell sein? Die Frage ist, wie das hier interagiert. [Bezug vermutlich auf die gezeigte Architektur; aus dem Text nicht eindeutig.] Das wird sich dann noch zeigen. Bei meinen letzten zwei Hackathons habe ich immer ElevenLabs verwendet. Ich hatte noch nicht [unklarer Satzteil zur Datenbank], wo du davor über ein …

**[25:49–25:53] Sprecher 3:** … LLM gehst, sondern direkt … Ich habe die …

**[25:53–25:56] Sprecher 4:** … Instructions direkt beim LLM in ElevenLabs gehabt.

**[25:56–26:00] Sprecher 3:** Und dann hat ElevenLabs selbst Eleven Labs hat dann selber ein LLM.

**[26:00–26:02] Sprecher 4:** Da ist Gemini, aber ich glaube …

**[26:02–26:02] Sprecher 1:** Nicht, dass es reicht.

**[26:02–26:03] Sprecher 3:** Ne, das reicht nicht.

**[26:04–26:22] Sprecher 1:** Das ist ganz nice, aber das zentrale Ding ist unser [Satzteil fehlt], das dann über die Claude-API [läuft; Satz unvollständig]. Vielleicht haben wir mehrere Modelle, eines für [2D/3D unklar], also diese Rekonstruktion.

**[26:29–26:30] Sprecher 3:** Ich denke, das ist einfach nur …

**[26:33–26:33] Sprecher 1:** Ich.

**[26:33–26:36] Sprecher 3:** Denke tatsächlich nicht, dass es doch, sie.

**[26:36–26:37] Sprecher 1:** Sie haben uns irgendeinen [unklar: „Age“] …

**[26:38–26:40] Sprecher 3:** Ja, ich denke es ist einfach nur LLM.

**[26:46–26:54] Sprecher 1:** Alright, go to this repo and visualize what they have given us so far. Use your picture generation model.

### 27:11 — User Experience, strukturierte Ausgaben und Rechentools

**[27:11–27:17] Sprecher 1:** Ich glaube, damit haben wir die Grundarchitektur besprochen, oder? Ganz unklar ist …

**[27:18–27:27] Sprecher 3:** Ich hatte noch eine. … visualisiert, wie ich es mir ganz am Anfang vorgestellt hatte. [Satzanfang unvollständig.]

**[27:28–27:37] Sprecher 4:** Wir sollten vielleicht noch darüber sprechen, wie wir uns das User Experience vorstellen. Das ist die mobile Ansicht.

**[27:37–27:40] Sprecher 3:** Ja, ungefähr. Kanntest du vorher schon …?

**[27:40–27:42] Sprecher 4:** Die Challenge einfach bei Google, ne? [Wortlaut/Satzbezug unklar.]

**[27:42–28:49] Sprecher 3:** Ich hatte das PDF, das gab es Ab, ich glaube, 11 Uhr oder so. Achso, und dann habe ich halt meine Idee einfach reingemacht. Da sieht man „Voice first“. Man kann auch tippen, das kann man auch weglassen. Visualisierung beziehungsweise … Kamera, wenn es geht, wenn wir es hinbekommen. Ansonsten einfach eine [2D/3D unklar] Rekonstruktion. Dann sieht man ungefähr, wo man ist, über den Agent, der das etwas festlegt. Die Navigation kann er als JSON ausgeben: Structured Data Output. Dann kann er es so machen. Wir müssen viel berechnen: Wie groß ist ein Gebäude oder ein Raum, wie lang ein Weg? Dafür würde ich dem Agent ein weiteres Tool geben. Da würde ich dem Agent einfach ein weiteres Tool geben. Er kann immer aus der Datenbank lesen, und dann [unklar: „brechen wir“].

**[28:49–28:53] Sprecher 4:** Der Meister wird so viele Tools am Ende haben, das werden wir gar nicht alles wissen.

**[28:56–29:01] Sprecher 3:** Wir brauchen eigentlich nicht mehr Tools, nur die drei: Calculate, [vermutlich Read] und Write. [Im Ausgangstext: „Calculate not write“.]

**[29:01–29:02] Sprecher 1:** Wir brauchen auf jeden Fall noch Skills.

**[29:02–29:06] Sprecher 4:** Für das [unklar: „M um“] stellen wir noch Fragen.

**[29:06–29:07] Sprecher 1:** Mal noch Fragen.

**[29:08–29:10] Sprecher 4:** Und dann wird ja vermutlich eh alles anders.

### 29:20 — Kamera, Positionierung, AR und Demo-Ideen

**[29:20–29:29] Sprecher 1:** Ich glaube wir sind jetzt schon dabei. Also wir können jetzt mal über die Add-ins sprechen. Also was wir dann on top noch machen, um uns dann vor allen Dingen in der Demo am Ende zu differentiaten …

**[29:29–30:01] Sprecher 4:** Wenn du die mobile Ansicht nimmst. Also so werden wir es auch umsetzen. Es muss nur mit der Kamera funktionieren, ohne LiDAR-Sensor, weil die Jury keine iPhones hat. Das habe ich vorher [Satzteil unklar]. Keine iPhones. Das heißt, wenn du eine mobile App, dann muss wirklich Ökosystem offen sein. Es muss mit Android und [Satz abgebrochen] gehen. Im Browser, aber du gehst nicht mit dem Browser durchs …

**[30:01–30:03] Sprecher 1:** Gebäude, du gehst auf den Browser, öffnest die.

**[30:04–30:05] Sprecher 4:** Ja, ja, ich habe jetzt gemeint …

**[30:13–30:13] Sprecher 3:** Wir.

**[30:13–30:34] Sprecher 4:** Wir können auch eine Flutter-Mobile-App machen. Ich meine: Du gehst nur mit der Kamera, ohne andere [Sensoren; Satzfragment]. Dann müssen wir aus [unklar: „statischen Chasing“] die Position auf der Map rekonstruieren. Das kann schwer werden, wenn wir das können, dann ist es sehr, finde ich.

**[30:34–30:38] Sprecher 1:** Sehr gut, aber ich glaube dafür brauchst du gar keine Mobile App. Das kannst du immer noch mit im Browser.

**[30:40–30:58] Sprecher 3:** Ich hatte aufgeschrieben: einen [3D?] Gaussian Splat des Gebäudes über die Kamera machen, eine [3D?] Repräsentation über Vektoren. [Ziffern im Ausgangstext fehlen.]

**[31:02–31:02] Sprecher 1:** Mit der Kamera.

**[31:07–31:26] Sprecher 3:** Man hat das normale Modell des Gebäudes und dann noch die eigene [unklar: „Ripple“] des Users, während er durchläuft. Die beiden werden übereinander gelegt und dann wird herausgefunden, wo ist der User zu dem Zeitpunkt. Versteht ihr? Welche Informationen hast du am Anfang?

**[31:28–31:31] Sprecher 4:** Wir kennen das Gebäude ja nicht [Rest unklar: „davon“].

**[31:32–31:55] Sprecher 3:** Doch, das wäre Idee. Wenn wir das Gebäude scannen, zum Beispiel einmal mit der Kamera durchgehen, haben wir [unklar: „Scorch Display“; Bezug auf die zuvor genannte Rekonstruktion]. Das können wir vergleichen, wenn der User selbst durchgeht. Wir bauen einmal eine eigene [3D?] Szene auf. Wenn der User durchgeht, vergleichen wir sie mit einer neuen [3D?] Szene. Dann wissen wir seine Position.

**[31:57–31:59] Sprecher 1:** Das können wir hier machen und ein Video davon aufnehmen, wie es klappt.

**[32:00–32:06] Sprecher 3:** Ja, das wäre eine Idee. Der Nutzer nimmt seine Kamera, das ist.

**[32:06–32:07] Sprecher 1:** Auch noch mal eine ganz andere Sache.

**[32:08–32:52] Sprecher 3:** Eine Linie wird auf seinem Screen gezeichnet, die die Route zeigt. Minimap, okay, das hatten wir schon gesagt. [Satzbau leicht geglättet.] Dann so ein [unklar: „Rockbot“] Avatar. Diese Dinger habt ihr bestimmt schon gesehen. Vielleicht habe ich auch noch im Browser offen. Die sehen einfach sehr flashy aus, Lebendig. Wenn man die hier daneben …

**[32:58–32:59] Sprecher 4:** Und dann spricht sie.

**[33:02–33:13] Sprecher 3:** Eigentlich nur so UI Feature, Das haben wir schon durch.

### 33:15 — Einreichungsvideos und Recherche bestehender Projekte

**[33:15–33:44] Sprecher 1:** Wir müssen unbedingt klären, was sie in diesen zwei Minuten sehen wollen: einmal im Technical- und einmal im Functionality-Teil. Also einmal im Technical und einmal in der Functionality. Wie soll das aussehen? Was stellen Sie sich da vor? Wollen sie die Files sehen? Die Funktionalität sehen sie ansonsten schon in den Benchmark-Tests, ob die Gebäude [Satzende unklar]. Wir müssen fragen: Was würdet ihr gerne sehen? In einer Minute kann man viel abdecken.

**[33:45–33:55] Sprecher 3:** Wenn wir das so umsetzen, dann zeigen wir im Technical- und Functionality-Teil, wie wir dorthin kommen und was wir am Ende zeigen können. [Formulierung im Original teilweise unklar.]

**[34:01–34:07] Sprecher 4:** Einmal die Person, die das Ganze über einen Mac [unklar: „Sangware“] anlegt, und die andere, die durch das Gebäude läuft.

**[34:11–34:12] Sprecher 1:** Beides Funktionalität.

**[34:31–34:34] Sprecher 4:** Wir schauen mal nach anderen Projekten, wir sind ja nicht die Ersten, die das machen.

**[34:34–34:37] Sprecher 3:** Ja, werde ich auch noch einmal, weil ich …

**[34:37–35:31] Sprecher 4:** … glaube, dass es besser ist, eineinhalb Stunden nach anderen [Projekten zu suchen; Satzende unvollständig]. Die haben das Problem schon seit 24 Stunden oder viel länger bearbeitet. [Wortlaut teilweise unklar.] Dann können wir Code übernehmen. Da sind auch Funktionen und Dinge drin, an die du gar nicht gedacht hast, wenn du deinen Agent für das ganze Repo promptest. Das dachte ich mir schon bei den Hackathons: Heute starten wir mit ChatGPT und Claude einfach los. Man sollte erst suchen, was andere schon gemacht haben. [Satzbau geglättet.]

**[35:31–35:35] Sprecher 1:** How big ist das Repo in terms of Megabytes Gigabyte?

**[35:35–35:37] Sprecher 4:** Ich habe es heruntergezogen. [Rest unklar: „das ist nicht zufrieden“.]

**[35:40–35:41] Sprecher 1:** Die Anzahl an Files ist egal.

**[35:50–35:52] Sprecher 4:** 106 Megabyte.

**[35:53–35:55] Sprecher 3:** Ja meistens halt die Bilder.

**[36:03–36:04] Sprecher 4:** Hat es nicht alles gezogen …

**[36:06–36:18] Sprecher 1:** Also die Files hat es dann nicht gezogen. Oder 300 MB. Kann man deine GitHub natürlich, ich habe.

**[36:18–36:21] Sprecher 3:** Bei mir in meinem [unklar: „Y“] vier GB.

**[36:23–36:23] Sprecher 5:** Oder.

**[36:26–36:28] Sprecher 1:** Machst du auch direkt über …?

**[36:36–36:40] Sprecher 4:** Ja, frag das mal an. Da musst du zuerst anfragen, was auf.

**[36:40–36:41] Sprecher 5:** Discord …

**[36:45–36:47] Sprecher 4:** Da ist ein Link zum Anklicken.

**[36:51–36:54] Sprecher 3:** Du kannst … Ist ja auch risky unterwegs. [Satzfragment.]

**[36:54–37:00] Sprecher 4:** Mit Full Access immer Full Access. Bei mir reicht es auch mit, was habe ich eingestellt?

**[37:07–37:26] Sprecher 3:** Du kannst mal nach vergleichbaren Projekten, Ich such mal nach einem Agent oder so, der das kann. Navigatum ist einfach nur so ein User Interface.

**[37:34–37:50] Sprecher 4:** Es gibt schon richtig gute Architektur-Repos, in denen man ein ganzes Haus mit Floorplänen visualisiert. Wenn wir so etwas haben, haben wir schon die Hälfte des Tracks.

**[37:57–38:04] Sprecher 3:** Es gibt auch sehr viele AI Models, die aus Bildern oder Videos rekonstruieren können, wie das Gebäude aussieht.

**[38:16–38:17] Sprecher 4:** Hier zum Beispiel sowas.

**[38:29–38:30] Sprecher 3:** Das ist stark, das ist stark.

### 38:31 — Gemeinsame Ablage, Visualisierung und Umsetzungsplanung

**[38:31–38:51] Sprecher 3:** Das ist echt … Haben wir einen Discord-Channel oder etwas anderes, wo wir interessante Sachen reinposten können? Ja, mach mal eine page.

**[38:53–38:54] Sprecher 4:** New page.

**[38:55–38:55] Sprecher 3:** Ja und dann.

**[39:25–39:40] Sprecher 3:** Was ist mit dem [unklar: „Pink“]? Ist das ein Knoten, Polygon im Sinne von …? Was gibt … [Satzfragment.]

**[39:44–39:45] Sprecher 4:** Eine Route?

**[39:51–39:56] Sprecher 3:** Es sieht ein bisschen aus, als wäre es misplaced, wenn …

**[39:56–40:02] Sprecher 4:** Du verstehst: Es geht aus diesem Raum zu dem Punkt und dann hier zurück zu dem …

**[40:17–40:19] Sprecher 1:** Was habe ich verpasst? Was machen wir gerade.

**[40:21–40:22] Sprecher 3:** Prompt.

**[40:24–40:26] Sprecher 1:** Macht … Habe … [Unverständliches Satzfragment.]

**[40:26–40:28] Sprecher 3:** Ich habe gerade gefragt, ob es dieses … [Satzfragment.]

**[40:28–40:52] Sprecher 4:** Wir müssen unsere Agents ordentlich [Satzfragment]. Er hat hier zwanzig, vierzig Repos gefunden. Relevant sind vielleicht sechs, die als Vorlage für einzelne Features dienen können. Dann brauchen wir einen schönen Plan und lassen den umsetzen.

**[40:53–40:55] Sprecher 1:** Ich würde es trotzdem iterativ machen.

**[40:55–40:59] Sprecher 4:** Ne, würde ich nicht. Den Plan iterativ [unklar: „verstecken“], aber dann erst umsetzen.

**[40:59–41:01] Sprecher 3:** Die Umsetzung würde ich nicht one-shotten.

**[41:02–41:06] Sprecher 4:** Es wird ohnehin nicht one-shot. Erst den Plan fertig machen und dann umsetzen. [Satzende unvollständig.]

**[41:06–41:24] Sprecher 1:** Ja genau, das ist absolut richtig Ansatz. Du kannst nicht iterativ irgendwas entwickeln. Funktioniert nie, weil der Agent beim nächsten Lauf alles vorherige wegschmeißt und sagt: „By the way, wir haben festgestellt, das ist kacke.“. Machen wir nicht. Machen wir nicht. Also das macht absolut Sinn.

**[41:26–41:29] Sprecher 3:** Aber das wäre zumindest stepwise.

**[41:31–41:32] Sprecher 4:** Der committed.

**[41:32–41:32] Sprecher 1:** Automatisch.

**[41:34–41:38] Sprecher 3:** Eher die Erfahrung gemacht in React gar nicht oder halt immer nur am Ende.

**[41:39–41:49] Sprecher 4:** Das ist problematisch, ne? Wenn wir den Plan ordentlich aufsetzen, haben wir am Ende zweihundert Commits und [unklar: „deine Republik“]. Dann kannst du alles zurückrollen.

**[41:50–41:57] Sprecher 3:** Also. Das sieht schon mal gut aus.

### 42:16 — Tech Stack und Verständnis des vorhandenen Starters

**[42:16–42:23] Sprecher 4:** Frag ihn einmal: Wenn du ElevenLabs V[Version im Transkript fehlt] verwendest, was soll ich fahren? ElevenLabs V[Version im Transkript fehlt].

**[42:25–42:26] Sprecher 1:** Willst du was einsprechen?

**[42:28–43:01] Sprecher 4:** Ist das auf Englisch? Mach in diesem Kontext ganz kurz den Tech Stack, wirklich nur auf der obersten Ebene. Wenn du ElevenLabs V[Version fehlt] als Engine für den Agent einplanst: Wir müssen trotzdem auf Claude beim LLM setzen, weil Anthropic beim Hackathon [Wortlaut unklar; mutmaßlich Sponsorbezug]. Das hatte ich vorher übersehen.

**[43:03–43:04] Sprecher 1:** Die sind nicht in der Jury.

**[43:04–43:09] Sprecher 4:** Ne, das nicht. Wird ja immer gern gesehen, wenn du auf den Tech Stack setzt.

**[43:10–44:14] Sprecher 1:** Am Ende sind die sowieso die Besten. Also macht schon Sinn. Mach die. Building overview, search building, find route. Was heißt denn „add door“? Okay, also, Okay, interessant. Das ist die Visualisierung davon, wie das Repo bisher aussieht, also wie sie es machen. Die Route geben sie nicht in einer App aus, sondern in Bildern. Sie erstellen dir eine Route als Bilder. Irgendwie kacke, aber geht auch.

**[44:14–44:43] Sprecher 1:** Sie nehmen das JSON-Format, machen ein [2D/3D unklar] Konstrukt daraus und stellen den Weg der Route dar. Zumindest verstehe ich ihren Agent aktuell so. Das ist alles, was sie gebaut haben. Und dann haben sie so Tools wie Add Door. Okay, dann kann man irgendwas zusätzlich hinzufügen. Was ist das denn?

**[44:43–44:43] Sprecher 2:** Hä?

**[44:43–44:46] Sprecher 1:** Ich gehe doch nicht durch ein Gebäude und stelle fest, dass plötzlich eine weitere Tür da ist.

**[44:47–44:48] Sprecher 4:** Ne, das …

**[44:51–44:55] Sprecher 1:** Also was meinen sie denn damit? Core.

**[44:58–45:05] Sprecher 4:** Vermutlich haben sie einfach einen Agent für alles gemacht: Navigation und Floor[plan- …; Satzende unklar].

**[45:05–45:23] Sprecher 1:** … kleine Stellen. [Im Kontext möglicherweise Fortsetzung des vorherigen Satzes; unklar.] Ja, können wir ja auch machen, einfach mit Tools. Ich versuche zu verstehen, wie sie sich das Repo gedacht haben. Auf dieser Grundlage will ich spezifische Fragen stellen, weil es teilweise noch einmal andere Ansätze hat.

### 45:25 — Nächste Fragen, Graphmodell und zusätzliche Constraints

**[45:25–45:37] Sprecher 1:** Als Nächstes sollten wir uns Fragen überlegen, losgehen, die Leute ausquetschen und die Fragen stellen. Ich lasse gleich das Transkript hier einmal laufen.

**[45:38–45:38] Sprecher 3:** Das ist echt …

**[45:42–45:45] Sprecher 4:** Wo kommen die Striche? Ist das dieses Gaussian …?

**[45:45–45:52] Sprecher 3:** Nein, das sind unterschiedliche Features. Hier ist zum Beispiel [unklar: „groundroop“].

**[45:54–45:56] Sprecher 4:** Das ist [unklar: „Ground Roof“], und das wird …

**[45:56–46:10] Sprecher 3:** … gematcht. Die einzelnen Punkte werden gematcht, und durch Triangulation oder wie auch immer weiß man, wo der User steht, und kann es anzeigen. Das ist Smart man.

**[46:11–46:12] Sprecher 1:** Okay, aber wie stellen sie sich das denn hier vor?

**[46:12–46:27] Sprecher 3:** Das funktioniert auch, wenn es Nacht ist, Es ist Tag, das ist auch krass. Okay, das ist echt, echt gut. Ich markiere das mal. Hast du jetzt so einen Space erstellt?

**[46:33–46:36] Sprecher 1:** Sind im JSON schon Graphen enthalten?

**[46:36–46:40] Sprecher 3:** Kannst du alles da drin rekonstruieren? Die Koordinaten stehen schon …

**[46:40–46:49] Sprecher 1:** … drin, die Objekte auch. Sie sagen, wir sollen mit einem Graph arbeiten, was Sinn ergibt. Ist der Graph schon im JSON eingebettet, oder müssen wir ihn erst ableiten?

**[46:51–46:53] Sprecher 4:** Im JSON ist grundsätzlich der Floorplan.

**[46:54–46:57] Sprecher 1:** Ja, genau. Wo alles ist, da haben wir im Zweifel ja noch keinen Graph drin.

**[46:57–47:04] Sprecher 3:** Jeder Raum ist ein Node; die Kanten sind die Wege zwischen den Räumen.

**[47:04–47:05] Sprecher 1:** Ja, safe.

**[47:05–47:11] Sprecher 3:** Kein visueller Graph, sondern ein [unklar: „hierarchischer“] Graph oder … Kein visueller Graph, sondern ein [unklar: „hierarchischer“] Graph oder …

**[47:15–47:31] Sprecher 1:** Auf jeden Fall ein Graph. Wenn zwei Räume nebeneinanderliegen, aber keine Tür dazwischen ist, gibt es keine Connection. Genau, gibt es keine Connection. Haben wir dafür ein extra Dateiformat, in dem wir das abspeichern, oder steckt das schon im JSON? Oder ist das in dem JSON schon drin?

**[47:32–47:33] Sprecher 4:** Die Türen sind.

**[47:34–47:42] Sprecher 1:** Die Türen. Ja, aber schon die Grafstruktur. Kann ich meinen Algorithmus über das JSON laufen lassen, und da …

**[47:42–47:44] Sprecher 3:** Kommt halt das raus, Da sind die Türen drin …

**[47:46–47:46] Sprecher 4:** Mehr oder weniger.

**[47:46–47:56] Sprecher 3:** Ja, okay, gut. Ich habe meine API.

**[47:57–48:00] Sprecher 4:** Sehr gut hast du bekommen.

**[48:00–48:02] Sprecher 3:** Habt ihr angefangen?

**[48:02–48:03] Sprecher 1:** Ich hab's noch nicht.

**[48:03–48:05] Sprecher 5:** Du musst die Mails durchschauen.

**[48:10–48:11] Sprecher 4:** Jetzt wissen sie mein team.

**[48:15–48:16] Sprecher 1:** Door-width constraints.

**[48:16–48:17] Sprecher 4:** Okay.

**[48:17–48:21] Sprecher 1:** Reachability. Okay. Den Graph müssen wir also noch mit zusätzlichen Daten anreichern.

**[48:22–48:26] Sprecher 4:** Wenn sich jemand im Rollstuhl durchs Gebäude bewegt …

**[48:27–48:40] Sprecher 3:** Die Türbreite steht schon drin. Wenn der Agent die Daten aus der Datenbank holt, sieht er: Die Tür ist weniger als einen Meter breit, er kommt nicht durch. Dann suche ich einen anderen Weg. Dann suche ich nach einem anderen Weg.

**[48:40–48:51] Sprecher 1:** Die Daten, die wir in den Graph packen oder die schon darin sind, müssen vielleicht für die gestellten Fragen noch angereichert werden.

**[48:51–48:54] Sprecher 3:** Das wird der Agent selbst … Wir packen es in den Prompt, und der Agent …

**[48:56–48:57] Sprecher 1:** Oder wir entwickeln …

### 49:00 — Featureumfang und Reihenfolge der Sprachintegration

**[49:00–49:05] Sprecher 4:** Am Ende müssen wir wissen, welche Features und welche Funktionalität wir wollen. Dann legen wir das fest.

**[49:06–49:11] Sprecher 3:** Also ich fände diese Architektur jetzt somit am besten.

**[49:11–49:14] Sprecher 1:** Macht erst einmal intuitiv Sinn. Und dass wir …

**[49:14–49:17] Sprecher 3:** Speech würde ich am Ende machen. [Satzanfang unklar.]

**[49:19–49:22] Sprecher 4:** Ich würde Speech von Anfang an machen, aber …

**[49:22–49:28] Sprecher 3:** Wir können ja immer … Das kann modular [sein].

**[49:28–49:39] Sprecher 5:** Als Question kann man es einfach ersetzen. [Satzanfang im Original unklar.] Du kannst zunächst dazuschreiben, was es später sein soll. Du kannst erst einmal einen Lückenfüller [verwenden].

**[49:41–50:02] Sprecher 3:** Ich würde erst das Setup aus LLM-Agent, Datenbank und [2D/3D unklar] Rekonstruktion machen. Dann binden wir Speech an, damit es conversational wird. Wenn ElevenLabs das LLM schon dahinter hat, können wir es auch so verwenden. Ist auch sehr, sehr clean dann.

**[50:06–50:08] Sprecher 1:** Ich würde jetzt einmal kurz das Recording stoppen, dann.
