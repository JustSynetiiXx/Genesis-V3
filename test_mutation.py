"""
Genesis v3 — Test: Mutation beim Kopieren
Setzt Mutationsrate auf 1/10 (hoch), lässt den Ur-Replikator 5 Mal kopieren,
prüft dass mindestens eine Kopie sich vom Original unterscheidet.
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

        # Pointer starten, genug Energie für 5 Kopier-Zyklen
        pointer = ExecutionPointer(0)
        pointer.energie = 5000
        while pointer.schritt(welt):
            pass

        # Prüfe die ersten 5 Kopien
        original = list(code)
        gefundene_mutationen = 0
        mindestens_eine_kopie_anders = False

        for kopie_nr in range(5):
            start = code_len * (kopie_nr + 1)
            kopie = [welt.speicher[start + i] for i in range(code_len)]

            unterschiede = []
            for i in range(code_len):
                if original[i] != kopie[i]:
                    unterschiede.append((i, original[i], kopie[i]))

            if unterschiede:
                mindestens_eine_kopie_anders = True

            gefundene_mutationen += len(unterschiede)

            print(f"Kopie {kopie_nr + 1} (Bytes {start}-{start + code_len - 1}): "
                  f"{len(unterschiede)} Mutation(en)")
            for byte_pos, alt, neu in unterschiede:
                print(f"  Byte {byte_pos}: {alt} → {neu}")

        print(f"\nGesamt: {gefundene_mutationen} Mutationen in 5 Kopien")

        if mindestens_eine_kopie_anders:
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
