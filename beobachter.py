"""
Genesis v3 — Beobachter (Schicht 2)
Read-Only Analyse des Speichers. Verändert NICHTS.
Wie ein Mikroskop — beobachtet, aber beeinflusst nicht.
"""

import math
from collections import Counter

from welt import SPEICHER_GROESSE

OPCODE_NAMEN = [
    "NOOP", "LESEN", "SCHREIBEN", "ADDIEREN",
    "VERGL_SPR", "KOPIEREN", "LESEN_EXT", "SELBST", "SETZEN", "ENDE"
]


class Beobachter:
    def __init__(self, welt, pointer_liste, sim_daten):
        """
        welt: Welt-Objekt (read-only Zugriff auf .speicher)
        pointer_liste: Liste der aktiven ExecutionPointer
        sim_daten: Dict mit Simulations-Zählern (geburten_gesamt, tode_gesamt, tick, etc.)
        """
        self.welt = welt
        self.pointer_liste = pointer_liste
        self.sim_daten = sim_daten

    def _extrahiere_genom(self, adresse):
        """Genom ab Adresse: Anweisung für Anweisung bis ENDE oder max 256 Anweisungen."""
        speicher = self.welt.speicher
        genom = []
        for i in range(0, 1024, 4):
            pos = (adresse + i) % SPEICHER_GROESSE
            opcode = speicher[pos]
            for j in range(4):
                genom.append(speicher[(pos + j) % SPEICHER_GROESSE])
            if opcode == 9:  # ENDE
                break
        return bytes(genom)

    def _shannon_index(self, genome_counter):
        """Shannon-Diversitäts-Index H = -sum(p_i * ln(p_i))"""
        total = sum(genome_counter.values())
        if total == 0:
            return 0.0
        h = 0.0
        for count in genome_counter.values():
            if count > 0:
                p = count / total
                h -= p * math.log(p)
        return round(h, 4)

    def _weltkarte(self):
        """1024 Werte: jeder repräsentiert 1024 Bytes Speicher.
        0=leer, 1=teilweise belegt, 2=voll belegt."""
        speicher = self.welt.speicher
        karte = bytearray(1024)
        for block in range(1024):
            start = block * 1024
            belegt = 0
            # Stichprobe: jeden 8. Byte prüfen (128 Samples pro Block)
            for i in range(0, 1024, 8):
                if speicher[start + i] != 0:
                    belegt += 1
            if belegt == 0:
                karte[block] = 0
            elif belegt >= 120:  # ~94% der Samples belegt
                karte[block] = 2
            else:
                karte[block] = 1
        return karte

    def _operations_verteilung(self, genome_liste):
        """Zählt Opcodes 0-9 über alle Genome."""
        verteilung = [0] * 10
        gesamt = 0
        for genom in genome_liste:
            for i in range(0, len(genom), 4):
                opcode = genom[i]
                if opcode < 10:
                    verteilung[opcode] += 1
                gesamt += 1
        return verteilung, gesamt

    def analysiere(self):
        """Hauptanalyse — gibt Dict mit allen Metriken zurück."""
        pointer = self.pointer_liste
        speicher = self.welt.speicher

        # --- Genome extrahieren ---
        genome_liste = []
        for p in pointer:
            if p.aktiv:
                genom = self._extrahiere_genom(p.startadresse)
                genome_liste.append(genom)

        # --- Genom-Statistiken ---
        genom_counter = Counter(genome_liste)
        laengen = [len(g) for g in genome_liste] if genome_liste else [0]

        # --- Top 10 Genome ---
        top_genome = []
        for genom, count in genom_counter.most_common(10):
            hex_str = " ".join(f"{b:02x}" for b in genom[:32])
            if len(genom) > 32:
                hex_str += "..."
            top_genome.append({
                "hex": hex_str,
                "laenge": len(genom),
                "anzahl": count,
                "anteil": round(count / max(len(genome_liste), 1) * 100, 1)
            })

        # --- Operations-Verteilung ---
        ops_verteilung, ops_gesamt = self._operations_verteilung(genome_liste)
        lesen_extern_count = ops_verteilung[6] if len(ops_verteilung) > 6 else 0
        lesen_extern_anteil = round(
            lesen_extern_count / max(ops_gesamt, 1) * 100, 2
        )

        # --- Speicher-Belegung ---
        null_bytes = speicher.count(0)
        belegt = SPEICHER_GROESSE - null_bytes
        belegt_prozent = round(belegt / SPEICHER_GROESSE * 100, 2)

        # --- Weltkarte ---
        karte = self._weltkarte()

        # --- Pointer-Positionen ---
        pointer_positionen = [p.startadresse for p in pointer if p.aktiv]

        return {
            "population": len([p for p in pointer if p.aktiv]),
            "population_max": self.sim_daten.get("max_pointer", 0),
            "geburten_gesamt": self.sim_daten.get("geburten_gesamt", 0),
            "tode_gesamt": self.sim_daten.get("tode_gesamt", 0),
            "speicher_belegt_bytes": belegt,
            "speicher_belegt_prozent": belegt_prozent,
            "diversitaet": len(genom_counter),
            "diversitaet_shannon": self._shannon_index(genom_counter),
            "genom_laenge_avg": round(sum(laengen) / max(len(laengen), 1), 1),
            "genom_laenge_min": min(laengen),
            "genom_laenge_max": max(laengen),
            "top_genome": top_genome,
            "operations_verteilung": {
                OPCODE_NAMEN[i]: ops_verteilung[i]
                for i in range(10)
            },
            "lesen_extern_anteil": lesen_extern_anteil,
            "weltkarte": list(karte),
            "pointer_positionen": pointer_positionen,
            "tick_nummer": self.sim_daten.get("tick", 0),
        }
