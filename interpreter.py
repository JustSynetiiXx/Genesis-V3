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

    def schritt(self, welt: Welt) -> bool:
        """Eine Operation ausführen. False wenn gestoppt."""
        if not self.aktiv or self.energie <= 0:
            return False

        # Tick-Limit: maximal 500 Schritte pro Tick
        if self._schritte_im_tick >= 500:
            return False
        self._schritte_im_tick += 1

        self.energie -= 1

        adr = self.adresse % SPEICHER_GROESSE
        befehl = welt.lesen(adr)
        arg1 = welt.lesen(adr + 1)
        arg2 = welt.lesen(adr + 2)
        arg3 = welt.lesen(adr + 3)

        if befehl < 11:
            ausgefuehrte_ops[befehl] += 1

        r = self.register

        if befehl == NOOP:
            pass

        elif befehl == LESEN:
            quell_adr = r[arg1 % 4] % SPEICHER_GROESSE
            r[arg3 % 4] = welt.lesen(quell_adr)
            self.sinnvolle_ops += 1

        elif befehl == SCHREIBEN:
            welt.schreiben(r[arg3 % 4] % SPEICHER_GROESSE, r[arg1 % 4] & 0xFF)
            self.sinnvolle_ops += 1

        elif befehl == ADDIEREN:
            r[arg3 % 4] = r[arg1 % 4] + r[arg2 % 4]
            self.sinnvolle_ops += 1

        elif befehl == VERGLEICHEN_SPRINGEN:
            sprung_tmp = arg3 if arg3 < 128 else arg3 - 256
            if sprung_tmp != 0:
                self.sinnvolle_ops += 1
            if r[arg1 % 4] != r[arg2 % 4]:
                self.adresse += sprung_tmp * ANWEISUNG_GROESSE
                return True

        elif befehl == KOPIEREN:
            anzahl = min(r[arg1 % 4], 1024)  # Max 1024 Bytes pro Kopie
            quelle = r[arg2 % 4]
            ziel_adr = r[arg3 % 4]
            # Energie-Kosten: 1 Energie pro 4 kopierte Bytes, Minimum 1
            kopier_kosten = max(anzahl // 4, 1)
            # Bei zu wenig Energie: nur so viel kopieren wie Energie reicht
            if kopier_kosten > self.energie:
                anzahl = self.energie * 4
                kopier_kosten = max(anzahl // 4, 1)
            self.energie -= kopier_kosten
            for i in range(anzahl):
                ziel_pos = (ziel_adr + i) % SPEICHER_GROESSE
                # Materie-Exklusion: nur auf leere Bytes schreiben
                if welt.lesen(ziel_pos) not in (0, 42):
                    continue
                byte_original = welt.lesen((quelle + i) % SPEICHER_GROESSE)
                byte = byte_original
                if random.randint(1, MUTATIONSRATE) == 1:
                    byte = random.randint(0, 255)
                    if byte != byte_original:
                        self.mutationen.append((i, quelle, ziel_adr, byte_original, byte))
                welt.schreiben(ziel_pos, byte)
            # Physik: Kopierter Code >= 20 Bytes wird lebendig
            if anzahl >= 20:
                self.neue_pointer.append(ziel_adr % SPEICHER_GROESSE)
                self.kopier_events += 1
            self.sinnvolle_ops += 1

        elif befehl == LESEN_EXTERN:
            extern_adr = (self._zellende + r[arg1 % 4]) % SPEICHER_GROESSE
            r[arg3 % 4] = welt.lesen(extern_adr)
            if r[arg3 % 4] == 42:
                self.energie += 20
                welt.schreiben(extern_adr, 0)
            self.sinnvolle_ops += 1

        elif befehl == SELBST:
            r[arg3 % 4] = self.startadresse
            self.sinnvolle_ops += 1

        elif befehl == SETZEN:
            r[arg3 % 4] = arg1
            self.sinnvolle_ops += 1

        elif befehl == ENDE:
            self.aktiv = False
            return False

        elif befehl == 10:  # SCHREIBEN_EXTERN
            extern_adr = (self._zellende + r[arg3 % 4]) % SPEICHER_GROESSE
            welt.schreiben(extern_adr, r[arg1 % 4] & 0xFF)  # KEINE Materie-Exklusion
            self.sinnvolle_ops += 1

        # Ungültiger Opcode (> 10): tue nichts, verbrauche Energie

        self.adresse += ANWEISUNG_GROESSE
        return True

    def tick(self, welt, energie=30):
        """100 Spawn-Energie, Rest durch Fressen."""
        self.energie = energie
        self.sinnvolle_ops = 0
        self._schritte_im_tick = 0
        # Zellgrenze scannen: finde ENDE ab Startadresse
        self._zellende = self.startadresse
        for i in range(0, 1024, 4):
            pos = (self.startadresse + i) % SPEICHER_GROESSE
            if welt.lesen(pos) == ENDE:
                self._zellende = (self.startadresse + i + 4) % SPEICHER_GROESSE
                break
        else:
            self._zellende = (self.startadresse + 1024) % SPEICHER_GROESSE
        while self.schritt(welt):
            # Bounds-Check: Kein Wraparound erlaubt
            if self.adresse < 0 or self.adresse >= SPEICHER_GROESSE:
                self.aktiv = False
                break
        if self.sinnvolle_ops == 0:
            self.leerlauf_ticks += 1
        else:
            self.leerlauf_ticks = 0
