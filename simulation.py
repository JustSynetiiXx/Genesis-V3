"""
Genesis v3 — Simulation
Die reine Physik. Kein Dashboard, kein Beobachter.
Erstellt die Welt, setzt den Ur-Replikator, lässt Evolution geschehen.

Starten: python3 simulation.py
Stoppen: Ctrl+C
"""

import time
import sys

from welt import Welt, SPEICHER_GROESSE
from interpreter import ExecutionPointer, ENDE
from ur_replikator import erzeuge_ur_replikator

LOG_INTERVALL = 10          # Sekunden
MAX_MUTATIONS_LOG = 100     # Erste N Mutationen einzeln loggen
MAX_EVENTS_LOG = 500        # Erste N Geburten/Tode einzeln loggen
MAX_POINTER = 2000          # Populationslimit — begrenzter Lebensraum


def genom_hex(speicher, adresse):
    """Liest Genom ab Adresse bis ENDE-Opcode, max 60 Hex-Zeichen."""
    daten = []
    for i in range(0, 120, 4):
        pos = adresse + i
        if pos + 3 >= SPEICHER_GROESSE:
            break
        opcode = speicher[pos]
        for j in range(4):
            daten.append(speicher[pos + j])
        if opcode == ENDE:
            break
    hex_str = " ".join(f"{b:02x}" for b in daten)
    if len(hex_str) > 60:
        return hex_str[:57] + "..."
    return hex_str


def speicher_nutzung(speicher):
    """Wie viel vom Speicher ist nicht-Null. Stichprobe alle 64 Bytes."""
    belegt = 0
    for i in range(0, SPEICHER_GROESSE, 64):
        if speicher[i] != 0:
            belegt += 1
    samples = SPEICHER_GROESSE // 64
    anteil = belegt / samples
    return int(anteil * SPEICHER_GROESSE), anteil * 100


def main():
    # === Welt erstellen ===
    welt = Welt()

    # === Ur-Replikator an Adresse 0 einsetzen ===
    code = erzeuge_ur_replikator()
    for i, byte in enumerate(code):
        welt.schreiben(i, byte)

    # === Ein Pointer an Adresse 0 ===
    pointer = [ExecutionPointer(0)]
    belegte_adressen = {0}

    print(f"{'='*60}")
    print(f"  Genesis v3 — Simulation")
    print(f"  Speicher: {SPEICHER_GROESSE:,} Bytes ({SPEICHER_GROESSE // 1024} KB)")
    print(f"  Ur-Replikator: {len(code)} Bytes an Adresse 0")
    print(f"  Mutationsrate: 1/500")
    print(f"  Energie pro Tick: 100")
    print(f"  Max Pointer: {MAX_POINTER}")
    print(f"{'='*60}")
    print()
    sys.stdout.flush()

    # === Zaehler ===
    tick = 0
    kopier_events_gesamt = 0
    kopier_events_log = 0
    mutationen_gesamt = 0
    mutationen_log = 0
    mutationen_geloggt = 0
    geburten_gesamt = 0
    geburten_log = 0
    tode_gesamt = 0
    tode_log = 0
    events_geloggt = 0

    letzter_log = time.time()
    startzeit = time.time()

    # === Hauptloop ===
    try:
        while True:
            tick += 1
            neue_pointer = []
            platz_frei = MAX_POINTER - len(pointer)

            for p in pointer:
                p.tick(welt)

                # --- Bounds-Check ---
                if not p.aktiv and (p.adresse < 0 or p.adresse >= SPEICHER_GROESSE):
                    tode_gesamt += 1
                    tode_log += 1
                    belegte_adressen.discard(p.startadresse)
                    if events_geloggt < MAX_EVENTS_LOG:
                        events_geloggt += 1
                        print(f"TOD: Pointer an Adresse {p.startadresse} entfernt "
                              f"(Grund: ausserhalb [{p.adresse}])")
                    continue

                # --- ENDE getroffen ---
                if not p.aktiv:
                    tode_gesamt += 1
                    tode_log += 1
                    belegte_adressen.discard(p.startadresse)
                    if events_geloggt < MAX_EVENTS_LOG:
                        events_geloggt += 1
                        print(f"TOD: Pointer an Adresse {p.startadresse} entfernt "
                              f"(Grund: ENDE)")
                    continue

                # --- Leerlauf-Check ---
                if p.leerlauf_ticks >= 10:
                    p.aktiv = False
                    tode_gesamt += 1
                    tode_log += 1
                    belegte_adressen.discard(p.startadresse)
                    if events_geloggt < MAX_EVENTS_LOG:
                        events_geloggt += 1
                        print(f"TOD: Pointer an Adresse {p.startadresse} entfernt "
                              f"(Grund: inaktiv)")
                    continue

                # --- Kopier-Events ---
                if p.kopier_events > 0:
                    kopier_events_gesamt += p.kopier_events
                    kopier_events_log += p.kopier_events
                    p.kopier_events = 0

                # --- Mutationen ---
                for byte_idx, quelle, ziel, alt, neu in p.mutationen:
                    mutationen_gesamt += 1
                    mutationen_log += 1
                    if mutationen_geloggt < MAX_MUTATIONS_LOG:
                        mutationen_geloggt += 1
                        print(f"MUTATION: Byte {byte_idx} bei Kopie von "
                              f"Adresse {quelle} nach {ziel} geaendert "
                              f"({alt}->{neu})")
                p.mutationen.clear()

                # --- Neue Pointer spawnen ---
                for adr in p.neue_pointer:
                    if adr in belegte_adressen:
                        continue
                    if platz_frei - len(neue_pointer) <= 0:
                        break
                    neuer = ExecutionPointer(adr)
                    neue_pointer.append(neuer)
                    belegte_adressen.add(adr)
                    geburten_gesamt += 1
                    geburten_log += 1
                    if events_geloggt < MAX_EVENTS_LOG:
                        events_geloggt += 1
                        print(f"GEBURT: Neuer Pointer an Adresse {adr} "
                              f"(Eltern-Adresse {p.startadresse})")
                p.neue_pointer.clear()

            # Tote entfernen, Neue hinzufuegen
            pointer = [p for p in pointer if p.aktiv]
            pointer.extend(neue_pointer)

            # === Periodisches Logging ===
            jetzt = time.time()
            if jetzt - letzter_log >= LOG_INTERVALL:
                laufzeit = jetzt - startzeit
                aktive = len(pointer)

                # Speicher-Nutzung
                belegt_bytes, belegt_prozent = speicher_nutzung(welt.speicher)

                # Genome finden (erste 3 verschiedene)
                gesehene = set()
                genome = []
                for p in pointer:
                    if len(genome) >= 3:
                        break
                    hex_str = genom_hex(welt.speicher, p.startadresse)
                    if hex_str not in gesehene:
                        gesehene.add(hex_str)
                        genome.append((p.startadresse, hex_str))

                print()
                print(f"--- Tick {tick:,} | {laufzeit:.0f}s | "
                      f"{tick / laufzeit:.0f} Ticks/s ---")
                print(f"  Pointer aktiv: {aktive} / {MAX_POINTER}")
                print(f"  Kopier-Events: +{kopier_events_log} "
                      f"(gesamt: {kopier_events_gesamt})")
                print(f"  Mutationen: +{mutationen_log} "
                      f"(gesamt: {mutationen_gesamt})")
                print(f"  Geburten: +{geburten_log} | "
                      f"Tode: +{tode_log} "
                      f"(gesamt: {geburten_gesamt} / {tode_gesamt})")
                print(f"  Speicher belegt: ~{belegt_bytes:,} Bytes "
                      f"({belegt_prozent:.1f}%)")
                if genome:
                    print(f"  Genome ({len(gesehene)} verschiedene):")
                    for adr, hex_str in genome:
                        print(f"    @{adr}: {hex_str}")
                print()
                sys.stdout.flush()

                kopier_events_log = 0
                mutationen_log = 0
                geburten_log = 0
                tode_log = 0
                letzter_log = jetzt

    except KeyboardInterrupt:
        laufzeit = time.time() - startzeit
        aktive = len(pointer)
        belegt_bytes, belegt_prozent = speicher_nutzung(welt.speicher)

        print()
        print(f"{'='*60}")
        print(f"  Simulation gestoppt nach {tick:,} Ticks ({laufzeit:.1f}s)")
        print(f"  Durchschnitt: {tick / max(laufzeit, 0.001):.0f} Ticks/s")
        print(f"  Pointer aktiv: {aktive}")
        print(f"  Kopier-Events gesamt: {kopier_events_gesamt}")
        print(f"  Mutationen gesamt: {mutationen_gesamt}")
        print(f"  Geburten gesamt: {geburten_gesamt}")
        print(f"  Tode gesamt: {tode_gesamt}")
        print(f"  Speicher belegt: ~{belegt_bytes:,} Bytes "
              f"({belegt_prozent:.1f}%)")
        print(f"{'='*60}")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
