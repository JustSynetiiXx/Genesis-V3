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

    # === Phase 1: Fressen — LESEN_EXTERN in verschiedene Offsets ===
    a(SETZEN, 10, 0, R1)           #  0: R1 = 10
    a(LESEN_EXTERN, R1, 0, R2)    #  1: R2 = Speicher[Zellende+10]
    a(SETZEN, 30, 0, R1)           #  2: R1 = 30
    a(LESEN_EXTERN, R1, 0, R2)    #  3: R2 = Speicher[Zellende+30]
    a(SETZEN, 60, 0, R1)           #  4: R1 = 60
    a(LESEN_EXTERN, R1, 0, R2)    #  5: R2 = Speicher[Zellende+60]
    a(SETZEN, 100, 0, R1)          #  6: R1 = 100
    a(LESEN_EXTERN, R1, 0, R2)    #  7: R2 = Speicher[Zellende+100]
    a(SETZEN, 150, 0, R1)          #  8: R1 = 150
    a(LESEN_EXTERN, R1, 0, R2)    #  9: R2 = Speicher[Zellende+150]

    # === Phase 2: Replizieren ===
    a(SELBST, 0, 0, R0)            # 10: R0 = Startadresse
    a(SETZEN, 68, 0, R1)           # 11: R1 = 68 (Genomgröße in Bytes)
    a(ADDIEREN, R0, R1, R2)        # 12: R2 = Start + Größe (Zieladresse)
    a(KOPIEREN, R1, R0, R2)        # 13: Kopiere R1 Bytes [R0]→[R2]

    # === Phase 3: Loop zurück ===
    a(SETZEN, 0, 0, R3)            # 14: R3 = 0
    a(VERGLEICHEN_SPRINGEN, R0, R3, (-16) & 0xFF)  # 15: R0 != 0 → zu 0

    # === Markierung ===
    a(ENDE, 0, 0, 0)               # 16: ENDE

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
