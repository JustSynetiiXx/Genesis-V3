"""
Genesis v3 — Test: Ur-Replikator mit SELBST + Pointer-Spawning
Prüft generationsübergreifende Replikation:
  1. Ur-Replikator an Adresse 0 kopiert sich nach Adresse 56
  2. Neuer Pointer wird an Adresse 56 gespawnt
  3. Kopie an Adresse 56 kopiert sich nach Adresse 112
  → Replikation funktioniert über Generationen
"""

import interpreter
from welt import Welt
from interpreter import ExecutionPointer
from ur_replikator import erzeuge_ur_replikator, groesse


def test_replikation():
    """Grundtest: Ur-Replikator kopiert sich korrekt."""
    # Mutation deaktivieren für deterministischen Test
    original_rate = interpreter.MUTATIONSRATE
    interpreter.MUTATIONSRATE = 999_999_999

    try:
        welt = Welt()
        code = erzeuge_ur_replikator()
        code_len = len(code)

        # Ur-Replikator an Adresse 0 einsetzen
        for i, byte in enumerate(code):
            welt.schreiben(i, byte)

        print(f"Ur-Replikator: {code_len} Bytes ({code_len // 4} Anweisungen)")

        # Execution Pointer an Adresse 0
        pointer = ExecutionPointer(0)
        pointer.energie = 200

        while pointer.schritt(welt):
            pass

        print(f"Schritte ausgeführt, Pointer Adresse: {pointer.adresse}")
        print(f"Register: R0={pointer.register[0]} R1={pointer.register[1]} "
              f"R2={pointer.register[2]} R3={pointer.register[3]}")

        # Prüfe: Identische Kopie direkt nach dem Original
        original = bytes(welt.speicher[0:code_len])
        kopie = bytes(welt.speicher[code_len:code_len * 2])

        if original == kopie:
            print(f"=== PASS === Kopie an Adresse {code_len} ist identisch")
        else:
            print(f"=== FAIL === Kopie stimmt nicht überein!")
            for i in range(code_len):
                if original[i] != kopie[i]:
                    print(f"  Byte {i}: Original={original[i]}, Kopie={kopie[i]}")
            return False

        return True
    finally:
        interpreter.MUTATIONSRATE = original_rate


def test_pointer_spawning():
    """Prüft dass KOPIEREN einen neuen Execution Pointer spawnt."""
    original_rate = interpreter.MUTATIONSRATE
    interpreter.MUTATIONSRATE = 999_999_999

    try:
        welt = Welt()
        code = erzeuge_ur_replikator()
        code_len = len(code)

        for i, byte in enumerate(code):
            welt.schreiben(i, byte)

        pointer = ExecutionPointer(0)
        pointer.energie = 200

        while pointer.schritt(welt):
            pass

        # Prüfe Spawn-Request
        if len(pointer.neue_pointer) >= 1 and pointer.neue_pointer[0] == code_len:
            print(f"=== PASS === Pointer-Spawn an Adresse {code_len} registriert")
            return True
        else:
            print(f"=== FAIL === Kein Spawn-Request! neue_pointer={pointer.neue_pointer}")
            return False
    finally:
        interpreter.MUTATIONSRATE = original_rate


def test_generationen():
    """Der Haupttest: Replikation über Generationen.
    Gen 0 (Adresse 0) → Gen 1 (Adresse 56) → Gen 2 (Adresse 112)
    """
    original_rate = interpreter.MUTATIONSRATE
    interpreter.MUTATIONSRATE = 999_999_999

    try:
        welt = Welt()
        code = erzeuge_ur_replikator()
        code_len = len(code)

        # Gen 0 an Adresse 0
        for i, byte in enumerate(code):
            welt.schreiben(i, byte)

        alle_pointer = [ExecutionPointer(0)]

        print(f"Ur-Replikator: {code_len} Bytes")
        print(f"Gen 0 an Adresse 0")

        # === Generation 0 → 1 ===
        alle_pointer[0].energie = 200
        while alle_pointer[0].schritt(welt):
            pass

        # Spawn-Request verarbeiten
        assert len(alle_pointer[0].neue_pointer) >= 1, \
            f"Gen 0 hat keinen Pointer gespawnt! neue_pointer={alle_pointer[0].neue_pointer}"
        spawn_adr = alle_pointer[0].neue_pointer[0]
        assert spawn_adr == code_len, \
            f"Spawn-Adresse {spawn_adr} != erwartet {code_len}"
        alle_pointer[0].neue_pointer.clear()

        # Neuen Pointer erstellen
        gen1_pointer = ExecutionPointer(spawn_adr)
        alle_pointer.append(gen1_pointer)
        print(f"Gen 1 gespawnt an Adresse {spawn_adr}")

        # Prüfe Kopie Gen 1
        original = bytes(welt.speicher[0:code_len])
        kopie1 = bytes(welt.speicher[code_len:code_len * 2])
        assert original == kopie1, "Gen 1 ist keine exakte Kopie von Gen 0!"
        print(f"Gen 1 Kopie verifiziert ✓")

        # === Generation 1 → 2 ===
        gen1_pointer.energie = 200
        while gen1_pointer.schritt(welt):
            pass

        # Spawn-Request verarbeiten
        assert len(gen1_pointer.neue_pointer) >= 1, \
            f"Gen 1 hat keinen Pointer gespawnt! neue_pointer={gen1_pointer.neue_pointer}"
        spawn_adr2 = gen1_pointer.neue_pointer[0]
        erwartet_adr2 = code_len * 2
        assert spawn_adr2 == erwartet_adr2, \
            f"Gen 2 Spawn-Adresse {spawn_adr2} != erwartet {erwartet_adr2}"

        # Prüfe Kopie Gen 2
        kopie2 = bytes(welt.speicher[erwartet_adr2:erwartet_adr2 + code_len])
        assert original == kopie2, "Gen 2 ist keine exakte Kopie!"
        print(f"Gen 2 gespawnt an Adresse {spawn_adr2}")
        print(f"Gen 2 Kopie verifiziert ✓")

        print()
        print("=== PASS === Generationsübergreifende Replikation funktioniert!")
        print(f"  Gen 0: Adresse 0")
        print(f"  Gen 1: Adresse {code_len}")
        print(f"  Gen 2: Adresse {erwartet_adr2}")
        print(f"  Jede Generation ist eine exakte Kopie.")
        print(f"  Jede Generation kennt ihre eigene Position (SELBST).")
        return True

    except AssertionError as e:
        print(f"=== FAIL === {e}")
        return False
    finally:
        interpreter.MUTATIONSRATE = original_rate


if __name__ == "__main__":
    print("=" * 60)
    print("Test 1: Grundreplikation")
    print("=" * 60)
    ok1 = test_replikation()
    print()

    print("=" * 60)
    print("Test 2: Pointer-Spawning")
    print("=" * 60)
    ok2 = test_pointer_spawning()
    print()

    print("=" * 60)
    print("Test 3: Generationsübergreifende Replikation")
    print("=" * 60)
    ok3 = test_generationen()
    print()

    alle_ok = ok1 and ok2 and ok3
    print("=" * 60)
    print(f"Ergebnis: {'ALLE TESTS BESTANDEN' if alle_ok else 'TESTS FEHLGESCHLAGEN'}")
    print("=" * 60)
    exit(0 if alle_ok else 1)
