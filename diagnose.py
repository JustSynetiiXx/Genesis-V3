"""
Genesis v3 — Diagnose-Tool
Laesst die Simulation 5.000 Ticks laufen und analysiert warum alles stirbt.
"""

import sys
from collections import defaultdict

import interpreter
from welt import Welt, SPEICHER_GROESSE
from interpreter import ExecutionPointer, ENDE
from ur_replikator import erzeuge_ur_replikator

TICKS = 3_000
MAX_POINTER = 300


def main():
    welt = Welt()
    code = erzeuge_ur_replikator()
    code_len = len(code)
    for i, byte in enumerate(code):
        welt.schreiben(i, byte)

    pointer = [ExecutionPointer(0)]
    belegte_adressen = {0}

    # === Tracking-Daten ===
    kopier_log = []          # (tick, eltern_adr, ziel_adr, laenge)
    tod_log = []             # (tick, adresse, grund)
    geburt_log = []          # (tick, eltern_adr, kind_adr)
    hat_kopiert = set()      # Adressen die mindestens 1x kopiert haben
    stammbaum = {}           # kind_adr -> eltern_adr
    ueberschreibungen = 0   # Ziel liegt in einem existierenden Organismus

    # Fuer O(1) Ueberschreibungs-Check: Welche 64-Byte-Bloecke sind belegt?
    belegte_bloecke = set()
    belegte_bloecke.add(0 // 64)

    print(f"Genesis v3 — Diagnose")
    print(f"Ur-Replikator: {code_len} Bytes, Ticks: {TICKS}")
    print(f"Mutationsrate: 1/{interpreter.MUTATIONSRATE}")
    print()
    sys.stdout.flush()

    # Population-Timeline
    pop_timeline = []  # (tick, anzahl_pointer)

    for tick in range(1, TICKS + 1):
        neue_pointer = []
        platz_frei = MAX_POINTER - len(pointer)

        for p in pointer:
            p.tick(welt)

            # --- Tod: Bounds ---
            if not p.aktiv and (p.adresse < 0 or p.adresse >= SPEICHER_GROESSE):
                tod_log.append((tick, p.startadresse, "bounds"))
                belegte_adressen.discard(p.startadresse)
                belegte_bloecke.discard(p.startadresse // 64)
                continue

            # --- Tod: ENDE ---
            if not p.aktiv:
                tod_log.append((tick, p.startadresse, "ende"))
                belegte_adressen.discard(p.startadresse)
                belegte_bloecke.discard(p.startadresse // 64)
                continue

            # --- Tod: Leerlauf ---
            if p.leerlauf_ticks >= 10:
                p.aktiv = False
                tod_log.append((tick, p.startadresse, "leerlauf"))
                belegte_adressen.discard(p.startadresse)
                belegte_bloecke.discard(p.startadresse // 64)
                continue

            # --- Kopier-Events tracken ---
            if p.kopier_events > 0:
                hat_kopiert.add(p.startadresse)
                p.kopier_events = 0

            # --- Kopier-Details ---
            for adr in p.neue_pointer:
                ziel = adr % SPEICHER_GROESSE
                kopier_laenge = p.register[1]  # R1 = Kopier-Laenge

                # O(1) Ueberschreibungs-Check via Block-Lookup
                ziel_block = ziel // 64
                if ziel_block in belegte_bloecke:
                    ueberschreibungen += 1

                kopier_log.append((tick, p.startadresse, ziel, kopier_laenge))

                if ziel not in belegte_adressen and platz_frei - len(neue_pointer) > 0:
                    neuer = ExecutionPointer(ziel)
                    neue_pointer.append(neuer)
                    belegte_adressen.add(ziel)
                    belegte_bloecke.add(ziel // 64)
                    stammbaum[ziel] = p.startadresse
                    geburt_log.append((tick, p.startadresse, ziel))

            p.neue_pointer.clear()
            p.mutationen.clear()

        pointer = [p for p in pointer if p.aktiv]
        pointer.extend(neue_pointer)

        # Timeline
        if tick % 100 == 0:
            pop_timeline.append((tick, len(pointer)))

        # Fortschritt
        if tick % 500 == 0:
            print(f"  Tick {tick:,}: {len(pointer)} Pointer aktiv, "
                  f"{len(kopier_log)} Kopien, {len(tod_log)} Tode")
            sys.stdout.flush()

    # === Analyse ===
    print()
    print(f"{'='*60}")
    print(f"  DIAGNOSE-ERGEBNIS ({TICKS:,} Ticks)")
    print(f"{'='*60}")
    print()

    # 1. Kopierfaehigkeit
    print(f"--- Replikation ---")
    print(f"  Organismen die sich mindestens 1x kopiert haben: {len(hat_kopiert)}")
    print(f"  Kopier-Events gesamt: {len(kopier_log)}")
    if kopier_log:
        laengen = [min(k[3], 1024) for k in kopier_log]  # Cap wie im Interpreter
        avg_laenge = sum(laengen) // len(laengen)
        print(f"  Kopier-Laenge: min={min(laengen)}, max={max(laengen)}, "
              f"avg={avg_laenge}")
        letzter_kopier_tick = max(k[0] for k in kopier_log)
        print(f"  Letzter Kopier-Event: Tick {letzter_kopier_tick}")
        # Kopien pro 500 Ticks
        kopien_buckets = defaultdict(int)
        for t, _, _, _ in kopier_log:
            kopien_buckets[(t-1)//500] += 1
        print(f"  Kopien pro 500 Ticks:")
        for b in sorted(kopien_buckets.keys()):
            start = b * 500 + 1
            ende = min((b + 1) * 500, TICKS)
            print(f"    Tick {start:>5}-{ende:>5}: {kopien_buckets[b]}")
    print()

    # 2. Todesursachen
    print(f"--- Todesursachen ---")
    gruende = defaultdict(int)
    for _, _, grund in tod_log:
        gruende[grund] += 1
    for grund, anzahl in sorted(gruende.items(), key=lambda x: -x[1]):
        print(f"  {grund}: {anzahl} ({100*anzahl/max(len(tod_log),1):.1f}%)")
    print(f"  Tode gesamt: {len(tod_log)}")
    print()

    # Tod-Timeline
    print(f"--- Tod-Timeline (pro 500 Ticks) ---")
    tod_buckets = defaultdict(int)
    for t, _, _ in tod_log:
        tod_buckets[(t-1)//500] += 1
    for b in sorted(tod_buckets.keys()):
        start = b * 500 + 1
        ende = min((b + 1) * 500, TICKS)
        print(f"  Tick {start:>5}-{ende:>5}: {tod_buckets[b]} Tode")
    print()

    # 3. Population-Timeline
    print(f"--- Population-Timeline (alle 100 Ticks) ---")
    for tick_nr, pop in pop_timeline:
        balken = "#" * min(pop // 20, 50)
        print(f"  Tick {tick_nr:>5}: {pop:>5} {balken}")
    print()

    # 4. Ueberschreibungen
    print(f"--- Ueberschreibungen ---")
    print(f"  Kopien die in einen belegten Block geschrieben haben: "
          f"{ueberschreibungen}")
    if kopier_log:
        print(f"  Anteil: {100*ueberschreibungen/len(kopier_log):.1f}% "
              f"aller Kopien")
    print()

    # 5. Stammbaum
    print(f"--- Stammbaum ---")
    print(f"  Geburten gesamt: {len(geburt_log)}")

    if stammbaum:
        # Generationstiefe iterativ berechnen (Zyklen-sicher)
        gen_cache = {}
        for adr in stammbaum:
            if adr in gen_cache:
                continue
            kette = []
            besucht = set()
            a = adr
            while a in stammbaum and a not in gen_cache and a not in besucht:
                besucht.add(a)
                kette.append(a)
                a = stammbaum[a]
            basis = gen_cache.get(a, 0)
            for i, k in enumerate(reversed(kette)):
                gen_cache[k] = basis + i + 1

        max_gen = max(gen_cache.values()) if gen_cache else 0
        max_gen_adr = max(gen_cache, key=gen_cache.get) if gen_cache else 0

        print(f"  Maximale Generationstiefe: {max_gen}")

        if max_gen > 0:
            print(f"  Erfolgreichster Stammbaum (bis Adresse {max_gen_adr}):")
            kette = []
            besucht = set()
            adr = max_gen_adr
            while adr in stammbaum and len(kette) < 20 and adr not in besucht:
                besucht.add(adr)
                kette.append(adr)
                adr = stammbaum[adr]
            kette.append(adr)
            kette.reverse()
            for i, a in enumerate(kette):
                lebt = "LEBT" if a in belegte_adressen else "TOT"
                print(f"    Gen {i}: Adresse {a:>8} [{lebt}]")
            if max_gen > 20:
                print(f"    ... ({max_gen - 20} weitere Generationen)")
    print()

    # 6. Ueberlebende
    print(f"--- Ueberlebende (Tick {TICKS}) ---")
    print(f"  Pointer aktiv: {len(pointer)}")
    for p in pointer[:10]:
        genom = []
        for i in range(0, 60, 4):
            pos = p.startadresse + i
            if pos >= SPEICHER_GROESSE:
                break
            opcode = welt.speicher[pos]
            for j in range(4):
                genom.append(welt.speicher[pos + j])
            if opcode == ENDE:
                break
        hex_str = " ".join(f"{b:02x}" for b in genom[:24])
        ist_null = all(b == 0 for b in genom[:24])
        status = "NUR NULLEN" if ist_null else "Code"
        print(f"  @{p.startadresse:>8}: [{status}] {hex_str}")
        print(f"    Leerlauf: {p.leerlauf_ticks}/10, Adresse: {p.adresse}")
    print()

    # 7. Speicher
    null_bytes = welt.speicher.count(0)
    belegt = SPEICHER_GROESSE - null_bytes
    print(f"--- Speicher ---")
    print(f"  Nicht-Null Bytes: {belegt:,} / {SPEICHER_GROESSE:,} "
          f"({100*belegt/SPEICHER_GROESSE:.1f}%)")


if __name__ == "__main__":
    main()
