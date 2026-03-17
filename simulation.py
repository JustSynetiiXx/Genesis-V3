"""
Genesis v3 — Simulation (Schritt 1)
Erstellt die Welt, setzt den Ur-Replikator, startet Execution Pointer.
Keine Mutation in diesem Schritt.
Loggt alle 10 Sekunden: aktive Pointer, Hex-Dump der ersten 100 Bytes.
"""

import time
from welt import Welt
from interpreter import ExecutionPointer
from ur_replikator import erzeuge_ur_replikator

ANZAHL_POINTER = 10
LOG_INTERVALL = 10  # Sekunden


def hex_dump(speicher: bytearray, start: int, laenge: int) -> str:
    """Hex-Dump eines Speicherbereichs."""
    zeilen = []
    for offset in range(0, laenge, 16):
        adr = start + offset
        hex_bytes = " ".join(f"{speicher[adr + i]:02x}" for i in range(min(16, laenge - offset)))
        zeilen.append(f"  {adr:06x}: {hex_bytes}")
    return "\n".join(zeilen)


def main():
    # Welt erstellen
    welt = Welt()

    # Ur-Replikator an Adresse 0 einsetzen
    code = erzeuge_ur_replikator()
    for i, byte in enumerate(code):
        welt.schreiben(i, byte)

    print(f"Genesis v3 — Simulation gestartet")
    print(f"Speicher: {len(welt.speicher)} Bytes")
    print(f"Ur-Replikator: {len(code)} Bytes an Adresse 0")

    # Execution Pointer erstellen
    # Pointer 0 startet am Ur-Replikator, die anderen an zufälligen Stellen
    # (die anderen zeigen auf Nullen = NOOPs, werden schnell inaktiv durch ENDE/Energieverlust)
    pointer = []
    pointer.append(ExecutionPointer(0))  # Der mit sinnvollem Code
    for i in range(1, ANZAHL_POINTER):
        startadr = i * (len(welt.speicher) // ANZAHL_POINTER)
        pointer.append(ExecutionPointer(startadr))

    print(f"Pointer: {len(pointer)} (Adressen: {[p.adresse for p in pointer]})")
    print()

    # Hauptloop
    tick = 0
    letzter_log = time.time()

    try:
        while True:
            tick += 1

            # Jeden Pointer einen Tick geben
            neue = []
            for p in pointer:
                if p.aktiv:
                    p.tick(welt)
                    # Pointer-Spawning: Kopierter Code wird lebendig
                    for adr in p.neue_pointer:
                        neue.append(ExecutionPointer(adr))
                    p.neue_pointer.clear()
            pointer.extend(neue)

            # Logging alle 10 Sekunden
            jetzt = time.time()
            if jetzt - letzter_log >= LOG_INTERVALL:
                aktive = sum(1 for p in pointer if p.aktiv)
                print(f"--- Tick {tick} | Aktive Pointer: {aktive}/{len(pointer)} ---")
                print(f"Hex-Dump (Bytes 0-99):")
                print(hex_dump(welt.speicher, 0, 100))
                print()
                letzter_log = jetzt

    except KeyboardInterrupt:
        print(f"\nSimulation gestoppt nach {tick} Ticks.")
        aktive = sum(1 for p in pointer if p.aktiv)
        print(f"Aktive Pointer: {aktive}/{len(pointer)}")
        print(f"Hex-Dump (Bytes 0-99):")
        print(hex_dump(welt.speicher, 0, 100))


if __name__ == "__main__":
    main()
