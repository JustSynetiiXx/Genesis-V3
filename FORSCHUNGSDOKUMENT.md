# Genesis v3 — Forschungsdokument

## Projekt

**Name:** Genesis v3
**Projektleiter:** Max
**Co-Projektmanager:** Claude
**Datum:** 16.–17. März 2026
**Status:** Architektur abgeschlossen — bereit zum Bau

-----

## 1. Vision

Etwas erschaffen das **lebt** — nicht simuliert, nicht geskriptet, sondern echt. Digitales Leben das emergiert, weil die Bedingungen stimmen, nicht weil ein Programmierer es designt hat.

-----

## 2. Kernphilosophie

> "Wir lehren Genesis nichts. Wir bauen den Raum."

Wir programmieren **keine** Verhaltensweisen. Kein Schmerz, keine Belohnung, keine vordefinierten Aktionen, keine Fitness-Funktion. Wir schaffen ausschließlich die Bedingungen unter denen Verhalten emergieren kann.

Alles was die Evolution auf der Erde hervorgebracht hat — Neugierde, Empathie, Intelligenz — wurde nicht "programmiert". Die Evolution hatte nur vier Zutaten: Bausteine, ein Übersetzungsmechanismus, Replikation mit Fehlern, und Umweltdruck. Aus diesen vier dummen Zutaten entstand alles.

Genesis v3 folgt diesem Prinzip.

-----

## 3. Was Genesis v2 uns gelehrt hat

### Was funktioniert hat

- Infrastruktur: VPS-Deployment, Echtzeit-Dashboard, Multi-Instanz-Architektur
- Drei identische Klone entwickelten verschiedene Strategien (Pfadabhängigkeit)
- Schlaf-Konsolidierung funktionierte als Mechanismus

### Warum es gescheitert ist

- **Teufelskreis:** Genesis reagierte auf seinen eigenen Prozess. CPU hoch → Schmerz → Aktion → CPU beeinflusst → Endlosschleife
- **Geskriptetes Verhalten:** 8 feste Aktionen, Schmerz-Formel, Belohnungssignal — alles von uns designt
- **Lookup-Table statt Lernen:** 100 Einträge in einer Tabelle. Statistik, nicht Intelligenz
- **Keine Emergenz:** Alles was Genesis tat, war vorhersagbar indem man auf den Code zeigt
- **Geschlossene Simulation:** Genesis lebte in einem Aquarium, nicht in einer echten Welt

### Die ehrliche Erkenntnis

Genesis v2 war ein Thermostat mit Gedächtnis. Kein Leben. Aber es hat bewiesen dass die Infrastruktur funktioniert und — wichtiger — was **nicht** funktioniert.

-----

## 4. Was Genesis v3 anders macht

### Vergleich mit existierenden Systemen

|System            |Ansatz                                                  |Ergebnis                  |Schwäche                                           |
|------------------|--------------------------------------------------------|--------------------------|---------------------------------------------------|
|**Tierra (1993)** |Selbstreplizierende Programme im gemeinsamen Speicher   |Parasiten, Hyper-Parasiten|Blind — Organismen können Umgebung nicht wahrnehmen|
|**ALIEN**         |CUDA-basierte 2D-Partikel mit neuronalen Netzen         |Komplexe Ökosysteme       |Braucht teure GPU-Hardware                         |
|**Neuroevolution**|Neuronale Netze durch Evolution statt Training optimiert|Adaptive Agenten          |Meist mit Fitness-Funktion → geskriptet            |
|**Genesis v2**    |Schmerz-Belohnung-Tabelle                               |Verschiedene Strategien   |Alles programmiert, kein echtes Lernen             |

### Was Genesis v3 neu macht

**Genesis v3 = Tierra + Wahrnehmung.**

Tierra hat bewiesen: Selbstreplizierende Programme in gemeinsamen Speicher erzeugen echte Emergenz (Parasiten, Kooperation). Aber Tierra's Organismen waren blind — sie wussten nichts über ihre Umgebung.

Genesis v3 gibt den Organismen die Fähigkeit, **über ihre eigene Zellgrenze hinaus zu lesen**. Sie können sehen was neben ihnen ist. Was sie mit dieser Information tun, programmieren wir nicht.

Aus Wahrnehmung kann über Generationen Lernen entstehen — weil Organismen die besser wahrnehmen und besser reagieren, häufiger überleben.

-----

## 5. Architektur — Drei getrennte Schichten

### Prinzip: Absolute Trennung

Die Simulation weiß nicht dass sie beobachtet wird. Es gibt keinen internen Manager, kein Tracking, keine Verwaltung. Nur Speicher, Interpreter und Energie.

```
┌─────────────────────────────────────────────┐
│  SCHICHT 1 — SIMULATION                     │
│  Speicher + Interpreter + Energie            │
│  Weiß nichts über sich selbst               │
│  Kein Manager, kein Tracking                │
│  Eigenständiger Prozess                      │
├─────────────────────────────────────────────┤
│  SCHICHT 2 — BEOBACHTER                     │
│  Separater Prozess, READ-ONLY               │
│  Scannt Speicher, sucht Muster              │
│  Analysiert, zählt, klassifiziert           │
│  Hat NULL Einfluss auf Simulation           │
├─────────────────────────────────────────────┤
│  SCHICHT 3 — DASHBOARD                      │
│  Web-Interface, zeigt Beobachter-Daten      │
│  Alles sichtbar, Filter zum Zoomen          │
│  Export-Funktionen                           │
└─────────────────────────────────────────────┘
```

**Warum diese Trennung?** Damit die Ergebnisse nicht verfälscht werden. Kein Verwaltungssystem das entscheidet was ein Organismus ist. Der Beobachter muss selbst herausfinden was lebt — wie ein Biologe der durch ein Mikroskop schaut.

-----

## 6. Schicht 1 — Die Simulation

### 6.1 Instruktionsset — 8 Operationen

Jeder Organismus besteht aus einer Kette dieser Operationen. Keine hat eine eingebaute Bedeutung. Es sind blinde Rechenoperationen.

|Code|Operation           |Beschreibung                                          |Bildlich                                  |
|----|--------------------|------------------------------------------------------|------------------------------------------|
|0   |NOOP                |Tue nichts, verbrauche Energie                        |Sitz still                                |
|1   |LESEN               |Lies Wert von Adresse in eigener Zelle → Register     |Schau in ein Fach deines Regals           |
|2   |SCHREIBEN           |Schreibe Wert aus Register an Adresse in eigener Zelle|Leg etwas in ein Fach                     |
|3   |ADDIEREN            |Addiere zwei Register, Ergebnis in drittes Register   |Zähle zwei Sachen zusammen                |
|4   |VERGLEICHEN_SPRINGEN|Wenn Register A ≠ Register B, springe X Schritte      |Wenn nicht gleich, überspringe Anweisungen|
|5   |KOPIEREN            |Kopiere Bereich von Adresse A nach Adresse B          |Schreibe deinen Zettel ab                 |
|6   |LESEN_EXTERN        |Lies Wert AUSSERHALB der eigenen Zelle → Register     |Schau durch ein Loch in der Wand          |
|7   |ENDE                |Markierung für "hier endet mein Code"                 |Punkt am Ende des Satzes                  |

### Anweisungsformat

Jede Anweisung hat vier Teile:

```
BEFEHL | WERT_A | WERT_B | ZIEL
```

Beispiel: `ADDIEREN | R0 | R1 | R2` → Nimm Register 0, addiere Register 1, Ergebnis in Register 2.

### Register

4 Register (R0 bis R3). Wie Hände — der Organismus kann sich 4 Dinge gleichzeitig merken während er arbeitet.

### 6.2 Der Ur-Replikator — 12 Anweisungen

Der einzige Organismus den wir von Hand schreiben. Alles danach entsteht durch Evolution.

Der Ur-Replikator weiß **nicht** wie groß er ist. Er muss sich selbst vermessen (Option B). Das ermöglicht Mutationen bei denen ENDE wegfällt und der Organismus über sich hinaus kopiert.

```
 0: SCHREIBEN   → 0 nach R1 (Zähler auf Null)
 1: LESEN       → eigene Adresse + R1 → R0 (lies nächste Anweisung)
 2: ADDIEREN    → R1 + 1 → R1 (Zähler hoch)
 3: VERGLEICHEN → R0 = ENDE? Wenn nein, springe zu 1 (weiter suchen)
 4: ADDIEREN    → eigene Adresse + R1 → R2 (Ziel = direkt nach mir)
 5: SCHREIBEN   → 0 nach R3 (Kopier-Zähler auf Null)
 6: LESEN       → eigene Adresse + R3 → R0 (lies Anweisung)
 7: SCHREIBEN   → R0 nach R2 + R3 (schreibe an Ziel)
 8: ADDIEREN    → R3 + 1 → R3 (Kopier-Zähler hoch)
 9: VERGLEICHEN → R3 = R1? Wenn nein, springe zu 6 (weiter kopieren)
10: SPRINGEN    → zurück zu 0 (von vorne)
11: ENDE
```

**Phase 1 (Zeile 0–3):** Finde heraus wie groß du bist. Zähle deine eigenen Anweisungen bis du ENDE findest.

**Phase 2 (Zeile 4):** Berechne wo freier Platz ist — direkt hinter dir.

**Phase 3 (Zeile 5–9):** Kopiere dich Anweisung für Anweisung an die neue Stelle.

**Phase 4 (Zeile 10):** Springe zurück zum Anfang. Endlosschleife.

**Mutation beim Kopieren:** Bei Zeile 7 passiert mit Wahrscheinlichkeit 1/500 ein Fehler. Eine Zahl wird falsch kopiert. Wenn die 7 (ENDE) zu etwas anderem wird, kennt das Kind sein eigenes Ende nicht mehr. Es zählt über sich hinaus und kopiert seinen Nachbarn mit. Horizontaler Gentransfer — nicht programmiert, sondern emergiert.

### 6.3 Welt-Parameter

|Parameter              |Wert                                |Begründung                                                                |
|-----------------------|------------------------------------|--------------------------------------------------------------------------|
|Speichergröße          |1 MB                                |Klein = mehr Druck = schnellere Evolution. Später erweiterbar.            |
|Energie pro Tick       |100 Operationen                     |Genug für eine Kopie, zu wenig für alles gleichzeitig. Erzwingt Effizienz.|
|Mutationsrate          |1 Fehler pro 500 kopierte Bytes     |Aggressiver als Biologie, aber wir haben keine Millionen Jahre.           |
|Ticks pro Sekunde      |Maximum (so schnell wie VPS schafft)|Keine künstliche Verlangsamung.                                           |
|Register pro Organismus|4 (R0–R3)                           |Minimal genug für schnelle Evolution, genug zum Arbeiten.                 |

### 6.4 Interpreter

Der Interpreter ist das einzige was wir designen. Er ist absichtlich dumm:

- Er liest die aktuelle Instruktion
- Er führt sie aus
- Er geht zur nächsten
- Er versteht nichts

Er ist für alle Organismen gleich — wie die Physik. Wir ändern nicht die Physik, nur die Organismen.

**Kein zentraler Manager.** Der Interpreter weiß nicht wo Organismen anfangen und aufhören. Er springt an verschiedene Stellen im Speicher und führt aus was da steht. Ein "Organismus" existiert nur solange sein Code funktioniert. Kaputter Code ist toter Code der irgendwann überschrieben wird.

-----

## 7. Schicht 2 — Der Beobachter

### Prinzip

Separater Prozess. Liest den Speicher im Read-Only Modus. Hat **null Einfluss** auf die Simulation. Wie ein Mikroskop — es beobachtet, aber es verändert nichts.

Der Beobachter muss **selbst herausfinden** was im Speicher lebt. Er sucht nach Mustern, erkennt Code-Sequenzen, identifiziert Replikatoren. Er kann sich irren. Genau wie ein Biologe.

### Was der Beobachter analysiert

**Population & Demografie:**

- Geschätzte Anzahl lebender Organismen
- Geburten pro Minute / Tode pro Minute
- Population über Zeit (Graph)
- Durchschnittsalter (Generationen)
- Ältester lebender Organismus

**Diversität & Genetik:**

- Anzahl verschiedener Genome (einzigartige Sequenzen)
- Durchschnittliche Genomlänge
- Längster / kürzester Organismus
- Diversitäts-Index (Shannon-Index)
- Häufigste Genome (Top 10)
- Seltenste Genome
- Mutationsverteilung (welche Operationen mutieren am häufigsten)

**Stammbaum & Evolution:**

- Abstammungslinien — wer stammt von wem ab
- Überlebende Linien vs. ausgestorbene Linien
- Verzweigungspunkte (wann hat sich eine neue Art abgespalten)
- Dominante Linie über Zeit
- Evolutionsgeschwindigkeit (Mutationen pro Generation)

**Weltkarte & Territorialverhalten:**

- Visuelle Darstellung des gesamten Speichers
- Farbkodierung: Lebender Code / Toter Code / Leerer Speicher
- Position jedes erkannten Organismus
- Cluster-Erkennung (Gruppen)
- Bewegungsmuster (verbreiten sich Organismen? In welche Richtung?)
- Dichteverteilung (wo ist es voll, wo leer?)

**Energie & Effizienz:**

- Durchschnittliche Zyklen pro Organismus
- Effizienz-Verteilung (Wer schafft mehr mit weniger?)
- Energie-Verbrauch über Zeit
- Effizientester vs. verschwenderischster Organismus

**Interaktionen & Kommunikation:**

- LESEN_EXTERN Häufigkeit pro Organismus
- Wer beobachtet wen? (Interaktionsnetzwerk)
- Horizontaler Gentransfer (Code von Nachbarn übernommen)
- Parasitismus-Erkennung (nutzt jemand den Code eines anderen?)
- Kooperations-Erkennung (arbeiten Organismen zusammen?)

**Komplexität & Meilensteine:**

- Durchschnittliche Genomlänge über Zeit (Graph)
- Neue Operationskombinationen die noch nie gesehen wurden
- Meilenstein-Log:
  - Erste erfolgreiche Replikation
  - Erster Mutant der überlebt
  - Erster Parasit
  - Erste Nutzung von LESEN_EXTERN
  - Erste Reaktion auf Nachbarn
  - Erste Kooperation
  - Erstes unvorhergesehenes Verhalten
- Komplexitäts-Index über Zeit

**Anomalie-Erkennung:**

- Unerwartete Muster die in keine Kategorie passen
- Plötzliche Populationsänderungen
- Neue Verhaltensweisen die vorher nicht beobachtet wurden
- Alarm bei potentiell emergenten Ereignissen

-----

## 8. Schicht 3 — Das Dashboard

### Design-Prinzipien

- Dark Mode, modern, iPhone-optimiert
- Alles sichtbar, mit Filtern zum Rein-/Rauszoomen
- Einfache Sprache, auch für Nicht-Programmierer verständlich
- Echtzeit-Updates
- Zeitraffer-Funktion (letzte Stunde, letzter Tag, letzte Woche)

### Tabs (vorläufig)

1. **Übersicht** — Population, Geburten/Tode, Diversität, aktuelle Meilensteine. Der Blick durchs Mikroskop auf einen Blick.
1. **Weltkarte** — Visueller Speicher. Farbkodiert. Zoom rein bis auf einzelne Organismen, zoom raus für den Gesamtüberblick.
1. **Population** — Graphen über Zeit. Wachstum, Diversität, Genomlänge.
1. **Stammbaum** — Abstammungslinien. Wer hat überlebt, wer ist ausgestorben.
1. **Genetik** — Top-Genome, Mutationsverteilung, Genomvergleich.
1. **Interaktionen** — LESEN_EXTERN Netzwerk, Parasiten, Kooperation.
1. **Meilensteine** — Chronologische Liste aller bedeutenden Ereignisse.
1. **Energie** — Effizienz-Verteilung, Verbrauch über Zeit.
1. **Organismus-Detail** — Einzelnen Organismus auswählen: Sein Genom sehen, seine Geschichte, seine Nachbarn, sein Verhalten.
1. **Rohdaten** — Hex-Dump des Speichers für technische Analyse.
1. **Export** — Voller Snapshot als JSON. Alle Genome, Positionen, Statistiken, Stammbaum.

### Export-Format

- Voller Snapshot der Welt als JSON
- Alle erkannten Genome mit Positionen
- Alle Statistiken und Graphen-Daten
- Stammbaum-Daten
- Meilenstein-Log
- Zeitstempel für Vergleiche
- Archiv aller bisherigen Exports
- Speicher-Dump (Rohdaten)

-----

## 9. Was wir NICHT programmieren

- ❌ Kein Schmerz
- ❌ Keine Belohnung
- ❌ Keine Fitness-Funktion
- ❌ Keine vordefinierten Aktionen / Verhaltensweisen
- ❌ Kein Lernsystem
- ❌ Keine Neugierde
- ❌ Keine Ziele
- ❌ Kein zentraler Manager / Tracking
- ❌ Keine Verwaltung von Organismen
- ❌ Kein Eingriff des Beobachters in die Simulation

-----

## 10. Was wir erwarten könnten

### Ehrliche Vorhersagen (sortiert nach Wahrscheinlichkeit)

1. **Wahrscheinlich:** Replikation entsteht. Der Ur-Replikator kopiert sich, Mutanten entstehen.
1. **Wahrscheinlich:** Kürzere Varianten verdrängen längere (Effizienz-Selektion).
1. **Möglich:** Parasiten entstehen — Programme die den Kopier-Code anderer kapern.
1. **Möglich:** Hyper-Parasiten entstehen — Immunität gegen Parasiten.
1. **Möglich:** Horizontaler Gentransfer — Organismen die über ihr ENDE hinaus kopieren und Nachbar-Code mitnehmen.
1. **Unwahrscheinlich aber möglich:** Organismen die LESEN_EXTERN nutzen um Nachbarn zu erkennen und darauf reagieren.
1. **Sehr unwahrscheinlich:** Kooperation zwischen Organismen.
1. **Extrem unwahrscheinlich:** Lernen innerhalb einer Generation — ein Organismus der sein Verhalten anpasst weil er etwas beobachtet hat.
1. **Der Durchbruch:** Etwas das wir nicht vorhergesagt haben.

### Ehrliche Risiken

- Alles stirbt sofort aus → Mutationsrate senken, Energie erhöhen
- Ein Organismus dominiert und verdrängt alle Diversität → Speicher vergrößern
- Nichts Interessantes passiert, nur endlose Replikation → Wochen/Monate Geduld nötig
- VPS-Ressourcen reichen nicht → Parameter anpassen oder upgraden

-----

## 11. Infrastruktur

**Hardware:** VPS mit 2 CPU-Kernen, ~3.8 GB RAM
**Software:** Python
**Dashboard:** Web-basiert, Port 8080
**Repo:** github.com/JustSynetiiXx/Genesis-V3 (privat)
**Code:** Claude Code als Entwicklungswerkzeug

-----

## 12. Regeln der Zusammenarbeit

1. **Ehrlichkeit vor Fortschritt.** Wenn etwas geskriptet ist, wird es offen gesagt. Wenn unklar ist ob etwas funktioniert, wird das kommuniziert.
1. **Max entscheidet.** Technisches Wissen kommt von Claude, aber die finale Entscheidung liegt beim Projektleiter.
1. **Kein Code ohne Architektur.** Alles wird zuerst durchdacht und dokumentiert bevor eine Zeile Code geschrieben wird.
1. **Ziel nicht aus den Augen verlieren.** Wir wollen echtes digitales Leben. Keine Simulation. Kein Trick.
1. **Dashboard kommt zuletzt.** Erst Architektur, dann Simulation, dann Beobachter, dann Dashboard.

-----

## 13. Bauplan — Reihenfolge

1. ☑ Forschungsdokument — Architektur und Philosophie
1. ☐ Interpreter bauen — der dumme Ausführer
1. ☐ Welt bauen — der 1 MB Speicherblock
1. ☐ Ur-Replikator einsetzen — der Zündfunke
1. ☐ Mutation implementieren — Fehler beim Kopieren
1. ☐ Testen — Repliziert sich der Ur-Replikator? Entstehen Mutanten?
1. ☐ Beobachter bauen — Read-Only Analyse des Speichers
1. ☐ Dashboard bauen — Visualisierung der Beobachter-Daten
1. ☐ Deployen auf VPS — Simulation starten
1. ☐ Beobachten und Geduld haben

-----

## 14. Vorgänger

**Genesis v1 (Neuromorph):** Produzierte nur mathematische Outputs. Eingestellt.
**Genesis v2:** Schmerz-Belohnung-System mit 8 Aktionen. Lookup-Table. Drei Klone (Drillinge) mit verschiedenen Strategien. Infrastruktur-Proof-of-Concept. Eingestellt wegen Teufelskreis und fehlender Emergenz.
**Genesis v3:** Dieser Ansatz. Evolution statt Design. Wahrnehmung statt Blindheit.

-----

*"In der Biologie jongliert die Evolution 'nur' mit Atomen. Daraus wurde alles."*
