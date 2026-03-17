"""
Genesis v3 — Ur-Replikator
Die einzige Kreatur die wir von Hand schreiben. Alles danach entsteht durch Evolution.

Der Ur-Replikator:
1. Weiß wo er ist (SELBST)
2. Vermisst sich selbst (sucht ENDE-Markierung)
3. Kopiert sich direkt hinter sich
4. Springt zum Anfang (Endlosschleife)

Register-Nutzung:
  R0 — Arbeit (gelesener Wert, temporär, Schrittweite)
  R1 — Scan-Offset / Gesamtgröße in Bytes
  R2 — ENDE-Opcode (9) zum Vergleichen / dann Zieladresse
  R3 — Eigene Startadresse (via SELBST)
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

    # === Phase 1: Wisse wo du bist ===
    a(SELBST, 0, 0, R3)                                #  0: R3 = eigene Startadresse

    # === Phase 2: Vermesse dich selbst ===
    a(SETZEN, 0, 0, R1)                                #  1: R1 = 0 (Scan-Offset)
    a(SETZEN, ENDE, 0, R2)                              #  2: R2 = 9 (ENDE-Opcode)

    # --- Scan-Loop: Lies jede 4. Stelle bis ENDE gefunden ---
    a(ADDIEREN, R3, R1, R0)                             #  3: R0 = Startadresse + Offset
    a(LESEN, R0, 0, R0)                                 #  4: R0 = Speicher[R0]
    a(SETZEN, ANWEISUNG_GROESSE, 0, R3)                 #  5: R3 = 4 (temporär für Inkrement)
    a(ADDIEREN, R1, R3, R1)                             #  6: R1 += 4
    a(SELBST, 0, 0, R3)                                 #  7: R3 = Startadresse (wiederherstellen)
    a(VERGLEICHEN_SPRINGEN, R0, R2, (-5) & 0xFF)        #  8: R0 != ENDE? → zu 3

    # R1 = Gesamtgröße in Bytes (inkl. ENDE-Anweisung)
    # R3 = Startadresse

    # === Phase 3: Zieladresse + Kopieren ===
    a(ADDIEREN, R3, R1, R2)                             #  9: R2 = Start + Größe (Zieladresse)
    a(KOPIEREN, R1, R3, R2)                             # 10: Kopiere R1 Bytes [R3]→[R2]

    # === Phase 4: Endlosschleife ===
    a(SETZEN, 0, 0, R0)                                 # 11: R0 = 0
    a(VERGLEICHEN_SPRINGEN, R0, R1, (-12) & 0xFF)       # 12: 0 != Größe → zu 0

    # === Markierung ===
    a(ENDE, 0, 0, 0)                                    # 13: ENDE

    return bytes(code)


def groesse() -> int:
    """Größe des Ur-Replikators in Bytes."""
    return len(erzeuge_ur_replikator())


if __name__ == "__main__":
    code = erzeuge_ur_replikator()
    namen = ["NOOP", "LESEN", "SCHREIBEN", "ADDIEREN",
             "VERGL_SPR", "KOPIEREN", "LESEN_EXT", "SELBST", "SETZEN", "ENDE"]
    print(f"Ur-Replikator: {len(code)} Bytes ({len(code) // 4} Anweisungen)\n")
    for i in range(0, len(code), 4):
        op = code[i]
        name = namen[op] if op < len(namen) else f"?({op})"
        print(f"  {i // 4:2d}: [{code[i]:3d}, {code[i+1]:3d}, {code[i+2]:3d}, {code[i+3]:3d}]  {name}")
