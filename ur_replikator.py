"""
Genesis v3 — Ur-Replikator
Die einzige Kreatur die wir von Hand schreiben. Alles danach entsteht durch Evolution.

Der Ur-Replikator:
1. Frisst — LESEN_EXTERN in verschiedene Richtungen (Wert 42 = +20 Energie)
2. Repliziert sich — SELBST, SETZEN Größe, ADDIEREN Zieladresse, KOPIEREN
3. Loopt zurück zu Phase 1 (Endlosschleife)

Register-Nutzung:
  R0 — Startadresse (via SELBST) / temporär
  R1 — Offset zum Lesen / Genomgröße
  R2 — Gelesener Wert / Zieladresse
  R3 — Schleifensteuerung
"""

from interpreter import (
    NOOP, LESEN, SCHREIBEN, ADDIEREN,
    VERGLEICHEN_SPRINGEN, KOPIEREN, LESEN_EXTERN,
    SELBST, SETZEN, ENDE,
    ANWEISUNG_GROESSE,
)

R0, R1, R2, R3 = 0, 1, 2, 3


def erzeuge_ur_replikator() -> bytes:
    """Erzeugt den Bytecode des Ur-Replikators."""
    code = []

    def a(befehl, arg1=0, arg2=0, arg3=0):
        code.extend([befehl, arg1, arg2, arg3])

    # Phase 1: Fressen — R3 ist roamender Offset, wandert jede Runde weiter
    a(LESEN_EXTERN, R3, 0, R2)      #  0: Lies Speicher[Zellende+R3]
    a(SETZEN, 7, 0, R1)             #  1: R1 = 7 (Schrittweite)
    a(ADDIEREN, R3, R1, R3)         #  2: R3 += 7
    a(LESEN_EXTERN, R3, 0, R2)      #  3: Lies Speicher[Zellende+R3]
    a(ADDIEREN, R3, R1, R3)         #  4: R3 += 7
    a(LESEN_EXTERN, R3, 0, R2)      #  5: Lies Speicher[Zellende+R3]
    a(ADDIEREN, R3, R1, R3)         #  6: R3 += 7
    a(LESEN_EXTERN, R3, 0, R2)      #  7: Lies Speicher[Zellende+R3]
    a(ADDIEREN, R3, R1, R3)         #  8: R3 += 7
    a(LESEN_EXTERN, R3, 0, R2)      #  9: Lies Speicher[Zellende+R3]
    a(ADDIEREN, R3, R1, R3)         # 10: R3 += 7 (fuer naechsten Loop)

    # Phase 2: Replizieren
    a(SELBST, 0, 0, R0)             # 11: R0 = Startadresse
    a(SETZEN, 72, 0, R1)            # 12: R1 = 72 (Genomgroesse)
    a(ADDIEREN, R0, R1, R2)         # 13: R2 = Zieladresse
    a(KOPIEREN, R1, R0, R2)         # 14: Kopiere

    # Phase 3: Loop
    a(SETZEN, 0, 0, R1)             # 15: R1 = 0
    a(VERGLEICHEN_SPRINGEN, R3, R1, (-16) & 0xFF)  # 16: R3 != 0 → zu 0

    a(ENDE, 0, 0, 0)                # 17: ENDE

    return bytes(code)


def groesse() -> int:
    """Größe des Ur-Replikators in Bytes."""
    return len(erzeuge_ur_replikator())


if __name__ == "__main__":
    code = erzeuge_ur_replikator()
    namen = ["NOOP", "LESEN", "SCHREIBEN", "ADDIEREN",
             "VERGL_SPR", "KOPIEREN", "LESEN_EXT", "SELBST", "SETZEN", "ENDE", "SCHR_EXT"]
    print(f"Ur-Replikator: {len(code)} Bytes ({len(code) // 4} Anweisungen)\n")
    for i in range(0, len(code), 4):
        op = code[i]
        name = namen[op] if op < len(namen) else f"?({op})"
        print(f"  {i // 4:2d}: [{code[i]:3d}, {code[i+1]:3d}, {code[i+2]:3d}, {code[i+3]:3d}]  {name}")
