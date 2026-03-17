"""
Genesis v3 — Interpreter
Der dumme Ausführer. Liest, führt aus, geht weiter. Versteht nichts.

Anweisungsformat: [BEFEHL, ARG1, ARG2, ARG3] — 4 Bytes pro Anweisung.

10 Operationen:
  0 NOOP:                 Tue nichts
  1 LESEN:                Speicher[Register[ARG1]] → Register[ARG3]
  2 SCHREIBEN:            Register[ARG1] → Speicher[Register[ARG3]]
  3 ADDIEREN:             Register[ARG1] + Register[ARG2] → Register[ARG3]
  4 VERGLEICHEN_SPRINGEN: Wenn Register[ARG1] != Register[ARG2], springe ARG3
                          Anweisungen (vorzeichenbehaftet: 0-127 vorwärts, 128-255 rückwärts)
  5 KOPIEREN:             Kopiere Register[ARG1] Bytes von Speicher[Register[ARG2]]
                          nach Speicher[Register[ARG3]].
                          Spawnt neuen Execution Pointer wenn >= 20 Bytes kopiert.
  6 LESEN_EXTERN:         Wie LESEN (in v3.0 identisch, Unterscheidung kommt später)
  7 SELBST:               Eigene Startadresse → Register[ARG3] (Propriozeption)
  8 SETZEN:               ARG1 (Literal) → Register[ARG3]
  9 ENDE:                 Stoppt Ausführung
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

ANWEISUNG_GROESSE = 4


class ExecutionPointer:
    def __init__(self, startadresse: int):
        self.adresse = startadresse
        self.startadresse = startadresse
        self.register = [0, 0, 0, 0]
        self.energie = 0
        self.aktiv = True
        self.neue_pointer = []  # Spawn-Requests von KOPIEREN

    def schritt(self, welt: Welt) -> bool:
        """Eine Operation ausführen. False wenn gestoppt."""
        if not self.aktiv or self.energie <= 0:
            return False

        self.energie -= 1

        adr = self.adresse % SPEICHER_GROESSE
        befehl = welt.lesen(adr)
        arg1 = welt.lesen(adr + 1)
        arg2 = welt.lesen(adr + 2)
        arg3 = welt.lesen(adr + 3)

        r = self.register

        if befehl == NOOP:
            pass

        elif befehl == LESEN:
            r[arg3 % 4] = welt.lesen(r[arg1 % 4] % SPEICHER_GROESSE)

        elif befehl == SCHREIBEN:
            welt.schreiben(r[arg3 % 4] % SPEICHER_GROESSE, r[arg1 % 4] & 0xFF)

        elif befehl == ADDIEREN:
            r[arg3 % 4] = r[arg1 % 4] + r[arg2 % 4]

        elif befehl == VERGLEICHEN_SPRINGEN:
            if r[arg1 % 4] != r[arg2 % 4]:
                sprung = arg3 if arg3 < 128 else arg3 - 256
                self.adresse += sprung * ANWEISUNG_GROESSE
                return True

        elif befehl == KOPIEREN:
            anzahl = r[arg1 % 4]
            quelle = r[arg2 % 4]
            ziel_adr = r[arg3 % 4]
            for i in range(anzahl):
                byte = welt.lesen((quelle + i) % SPEICHER_GROESSE)
                if random.randint(1, MUTATIONSRATE) == 1:
                    byte = random.randint(0, 255)
                welt.schreiben((ziel_adr + i) % SPEICHER_GROESSE, byte)
            # Physik: Kopierter Code >= 20 Bytes wird lebendig
            if anzahl >= 20:
                self.neue_pointer.append(ziel_adr % SPEICHER_GROESSE)

        elif befehl == LESEN_EXTERN:
            r[arg3 % 4] = welt.lesen(r[arg1 % 4] % SPEICHER_GROESSE)

        elif befehl == SELBST:
            r[arg3 % 4] = self.startadresse

        elif befehl == SETZEN:
            r[arg3 % 4] = arg1

        elif befehl == ENDE:
            self.aktiv = False
            return False

        self.adresse += ANWEISUNG_GROESSE
        return True

    def tick(self, welt: Welt):
        """100 Energie, dann ausführen bis leer."""
        self.energie = 100
        while self.schritt(welt):
            pass
