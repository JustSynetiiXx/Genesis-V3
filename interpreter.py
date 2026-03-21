"""
Genesis v3 — Interpreter
Der dumme Ausführer. Liest, führt aus, geht weiter. Versteht nichts.

Anweisungsformat: [BEFEHL, ARG1, ARG2, ARG3] — 4 Bytes pro Anweisung.

11 Operationen:
  0 NOOP:                 Tue nichts
  1 LESEN:                Speicher[Register[ARG1]] → Register[ARG3]
  2 SCHREIBEN:            Register[ARG1] → Speicher[Register[ARG3]]
  3 ADDIEREN:             Register[ARG1] + Register[ARG2] → Register[ARG3]
  4 VERGLEICHEN_SPRINGEN: Wenn Register[ARG1] != Register[ARG2], springe ARG3
                          Anweisungen (vorzeichenbehaftet: 0-127 vorwärts, 128-255 rückwärts)
  5 KOPIEREN:             Kopiere Register[ARG1] Bytes von Speicher[Register[ARG2]]
                          nach Speicher[Register[ARG3]].
                          Spawnt neuen Execution Pointer wenn >= 20 Bytes kopiert.
  6 LESEN_EXTERN:         Speicher[Zellende + Register[ARG1]] → Register[ARG3]
                          Liest AUSSERHALB der eigenen Zelle (ab ENDE-Markierung).
  7 SELBST:               Eigene Startadresse → Register[ARG3] (Propriozeption)
  8 SETZEN:               ARG1 (Literal) → Register[ARG3]
  9 ENDE:                 Stoppt Ausführung
 10 SCHREIBEN_EXTERN:     Register[ARG1] → Speicher[Zellende + Register[ARG3]]
                          Schreibt AUSSERHALB der eigenen Zelle. Ignoriert Materie-Exklusion.
"""

import random

from welt import Welt, SPEICHER_GROESSE

MUTATIONSRATE = 500  # 1 Fehler pro N kopierte Bytes

NOOP = 0
LESEN = 1
SCHREIBEN = 2
ADDIEREN = 3
VERGLEICHEN_SPRINGEN = 4
KOPIEREN = 5
LESEN_EXTERN = 6
SELBST = 7
SETZEN = 8
ENDE = 9
SCHREIBEN_EXTERN = 10

ANWEISUNG_GROESSE = 4

# Globaler Zähler: Welche Opcodes werden tatsächlich ausgeführt?
# Wird pro Tick von allen Organismen gemeinsam befüllt.
ausgefuehrte_ops = [0] * 11


class ExecutionPointer:
    def __init__(self, startadresse: int):
        self.adresse = startadresse
        self.startadresse = startadresse
        self.register = [0, 0, 0, 0]
        self.energie = 0
        self.aktiv = True
        self.neue_pointer = []  # Spawn-Requests von KOPIEREN
        self.mutationen = []    # [(byte_index, quelle, ziel, alt, neu)]
        self.kopier_events = 0  # Anzahl KOPIEREN >= 20 Bytes
        self.sinnvolle_ops = 0  # Nicht-NOOP Ops pro Tick
        self.leerlauf_ticks = 0 # Aufeinanderfolgende Ticks ohne sinnvolle Ops

    def tick(self, welt, energie=100):
        """Inline-Hauptschleife. Kein schritt()-Aufruf mehr für Performance."""
        # Lokale Variablen sind ~30% schneller als self.xxx
        speicher = welt.speicher
        GROESSE = SPEICHER_GROESSE
        adresse = self.adresse
        startadresse = self.startadresse
        r = self.register
        energie_lokal = energie
        sinnvolle_ops = 0
        schritte = 0
        neue_pointer = self.neue_pointer
        mutationen = self.mutationen
        kopier_events = 0
        aktiv = True
        _randint = random.randint
        _ausgefuehrte_ops = ausgefuehrte_ops

        # Zellgrenze scannen
        zellende = startadresse
        for i in range(0, 1024, 4):
            pos = (startadresse + i) % GROESSE
            if speicher[pos] == 9:  # ENDE
                zellende = (startadresse + i + 4) % GROESSE
                break
        else:
            zellende = (startadresse + 1024) % GROESSE

        # Hauptschleife — KEIN Methodenaufruf pro Schritt
        while aktiv and energie_lokal > 0 and schritte < 500:
            energie_lokal -= 1
            schritte += 1

            adr = adresse % GROESSE
            befehl = speicher[adr]
            arg1 = speicher[(adr + 1) % GROESSE]
            arg2 = speicher[(adr + 2) % GROESSE]
            arg3 = speicher[(adr + 3) % GROESSE]

            # Ausführungszähler
            if befehl < 11:
                _ausgefuehrte_ops[befehl] += 1

            if befehl == 0:  # NOOP
                pass

            elif befehl == 1:  # LESEN
                quell_adr = r[arg1 % 4] % GROESSE
                wert = speicher[quell_adr]
                r[arg3 % 4] = wert
                if wert == 42:
                    energie_lokal += 20
                    speicher[quell_adr] = 0
                sinnvolle_ops += 1

            elif befehl == 2:  # SCHREIBEN
                speicher[r[arg3 % 4] % GROESSE] = r[arg1 % 4] & 0xFF
                sinnvolle_ops += 1

            elif befehl == 3:  # ADDIEREN
                r[arg3 % 4] = r[arg1 % 4] + r[arg2 % 4]
                sinnvolle_ops += 1

            elif befehl == 4:  # VERGLEICHEN_SPRINGEN
                sinnvolle_ops += 1
                if r[arg1 % 4] != r[arg2 % 4]:
                    sprung = arg3 if arg3 < 128 else arg3 - 256
                    adresse += sprung * 4
                    if adresse < 0 or adresse >= GROESSE:
                        aktiv = False
                        break
                    continue

            elif befehl == 5:  # KOPIEREN
                anzahl = min(r[arg1 % 4], 1024)
                quelle = r[arg2 % 4]
                ziel_adr = r[arg3 % 4]
                kopier_kosten = max(anzahl // 4, 1)
                if kopier_kosten > energie_lokal:
                    anzahl = energie_lokal * 4
                    kopier_kosten = max(anzahl // 4, 1)
                energie_lokal -= kopier_kosten
                for i in range(anzahl):
                    ziel_pos = (ziel_adr + i) % GROESSE
                    if speicher[ziel_pos] != 0:
                        continue
                    byte_original = speicher[(quelle + i) % GROESSE]
                    byte_val = byte_original
                    if _randint(1, MUTATIONSRATE) == 1:
                        byte_val = _randint(0, 255)
                        if byte_val != byte_original:
                            mutationen.append((i, quelle, ziel_adr, byte_original, byte_val))
                    speicher[ziel_pos] = byte_val
                if anzahl >= 20:
                    neue_pointer.append(ziel_adr % GROESSE)
                    kopier_events += 1
                sinnvolle_ops += 1

            elif befehl == 6:  # LESEN_EXTERN
                extern_adr = (zellende + r[arg1 % 4]) % GROESSE
                wert = speicher[extern_adr]
                r[arg3 % 4] = wert
                if wert == 42:
                    energie_lokal += 20
                    speicher[extern_adr] = 0
                sinnvolle_ops += 1

            elif befehl == 7:  # SELBST
                r[arg3 % 4] = startadresse
                sinnvolle_ops += 1

            elif befehl == 8:  # SETZEN
                r[arg3 % 4] = arg1
                sinnvolle_ops += 1

            elif befehl == 9:  # ENDE
                aktiv = False
                break

            elif befehl == 10:  # SCHREIBEN_EXTERN
                extern_adr = (zellende + r[arg3 % 4]) % GROESSE
                speicher[extern_adr] = r[arg1 % 4] & 0xFF
                sinnvolle_ops += 1

            # Ungültiger Opcode: nichts tun

            adresse += 4
            if adresse < 0 or adresse >= GROESSE:
                aktiv = False
                break

        # Zurückschreiben
        self.adresse = adresse
        self.aktiv = aktiv
        self.energie = energie_lokal
        self.kopier_events = kopier_events
        if sinnvolle_ops == 0:
            self.leerlauf_ticks += 1
        else:
            self.leerlauf_ticks = 0
