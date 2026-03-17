"""
Genesis v3 — Test: Mutation beim Kopieren
Setzt Mutationsrate auf 1/10 (hoch), lässt den Ur-Replikator kopieren,
prüft dass die Kopie sich vom Original unterscheidet.

Hinweis: Durch Materie-Exklusion kann ein Pointer nur einmal an eine
leere Zieladresse kopieren. Danach sind die Bytes != 0 und werden
übersprungen. Der Test prüft daher nur die erste Kopie.
"""

import interpreter
from welt import Welt
from interpreter import ExecutionPointer
from ur_replikator import erzeuge_ur_replikator


def test_mutation():
    # Mutationsrate temporär auf 1/10 setzen
    original_rate = interpreter.MUTATIONSRATE
    interpreter.MUTATIONSRATE = 10

    try:
        welt = Welt()
        code = erzeuge_ur_replikator()
        code_len = len(code)

        # Ur-Replikator einsetzen
        for i, byte in enumerate(code):
            welt.schreiben(i, byte)

        print(f"Ur-Replikator: {code_len} Bytes")
        print(f"Mutationsrate: 1/{interpreter.MUTATIONSRATE}")
        print(f"Erwartete Mutationen pro Kopie: ~{code_len / interpreter.MUTATIONSRATE:.1f}\n")

        # Pointer starten — genug Energie für einen Kopier-Zyklus
        pointer = ExecutionPointer(0)
        pointer.energie = 200
        while pointer.schritt(welt):
            pass

        # Prüfe die erste Kopie
        original = list(code)
        start = code_len
        kopie = [welt.speicher[start + i] for i in range(code_len)]

        unterschiede = []
        for i in range(code_len):
            if original[i] != kopie[i]:
                unterschiede.append((i, original[i], kopie[i]))

        print(f"Kopie 1 (Bytes {start}-{start + code_len - 1}): "
              f"{len(unterschiede)} Mutation(en)")
        for byte_pos, alt, neu in unterschiede:
            print(f"  Byte {byte_pos}: {alt} → {neu}")

        # Prüfe auch die gemeldeten Mutationen vom Interpreter
        print(f"\nInterpreter-gemeldete Mutationen: {len(pointer.mutationen)}")
        for byte_idx, quelle, ziel, alt, neu in pointer.mutationen:
            print(f"  Byte {byte_idx}: {alt} → {neu} (Kopie von {quelle} nach {ziel})")

        if unterschiede:
            print("\n=== PASS === Mutationen wurden korrekt erzeugt!")
            return True
        else:
            print("\n=== FAIL === Keine einzige Mutation bei Rate 1/10 — extrem unwahrscheinlich!")
            return False

    finally:
        # Mutationsrate zurücksetzen
        interpreter.MUTATIONSRATE = original_rate
        print(f"\nMutationsrate zurückgesetzt auf 1/{interpreter.MUTATIONSRATE}")


if __name__ == "__main__":
    success = test_mutation()
    exit(0 if success else 1)
