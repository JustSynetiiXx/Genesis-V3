"""
Genesis v3 — Beobachter (Schicht 2)
Read-Only Analyse des Speichers. Verändert NICHTS.
Wie ein Mikroskop — beobachtet, aber beeinflusst nicht.
"""

import json
import math
import os
import time
from collections import Counter

from welt import SPEICHER_GROESSE

OPCODE_NAMEN = [
    "NOOP", "LESEN", "SCHREIBEN", "ADDIEREN",
    "VERGL_SPR", "KOPIEREN", "LESEN_EXT", "SELBST", "SETZEN", "ENDE", "SCHR_EXT"
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
        """Zählt Opcodes 0-10 über alle Genome."""
        verteilung = [0] * 11
        gesamt = 0
        for genom in genome_liste:
            for i in range(0, len(genom), 4):
                opcode = genom[i]
                if opcode < 11:
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
        schreiben_extern_count = ops_verteilung[10] if len(ops_verteilung) > 10 else 0
        schreiben_extern_anteil = round(
            schreiben_extern_count / max(ops_gesamt, 1) * 100, 2
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
                for i in range(11)
            },
            "lesen_extern_anteil": lesen_extern_anteil,
            "schreiben_extern_anteil": schreiben_extern_anteil,
            "weltkarte": list(karte),
            "pointer_positionen": pointer_positionen,
            "tick_nummer": self.sim_daten.get("tick", 0),
        }

    def analyse_wahrnehmung(self):
        """Scanne alle Genome nach Wahrnehmungs-Muster:
        LESEN_EXTERN (6) gefolgt von VERGLEICHEN_SPRINGEN (4) innerhalb der nächsten 3 Anweisungen (12 Bytes).
        """
        pointer = self.pointer_liste
        treffer = []

        for p in pointer:
            if not p.aktiv:
                continue
            genom = self._extrahiere_genom(p.startadresse)
            hat_muster = False
            code_ausschnitt = ""
            for i in range(0, len(genom) - 4, 4):
                if genom[i] == 6:  # LESEN_EXTERN
                    # Suche VERGLEICHEN_SPRINGEN oder SCHREIBEN_EXTERN in den nächsten 3 Anweisungen
                    for j in range(1, 4):
                        pos = i + j * 4
                        if pos < len(genom) and genom[pos] in (4, 10):  # VERGL_SPR oder SCHR_EXT
                            hat_muster = True
                            start = i
                            ende = min(pos + 4, len(genom))
                            code_ausschnitt = " ".join(f"{b:02x}" for b in genom[start:ende])
                            break
                    if hat_muster:
                        break
            if hat_muster:
                treffer.append({
                    "adresse": p.startadresse,
                    "code_ausschnitt": code_ausschnitt,
                    "genom_laenge": len(genom),
                })

        gesamt = len([p for p in pointer if p.aktiv])
        anzahl = len(treffer)
        prozent = round(anzahl / max(gesamt, 1) * 100, 2)

        # Meilenstein-Tracking
        meilensteine = []
        meilenstein_pfad = "meilensteine.json"
        if os.path.exists(meilenstein_pfad):
            try:
                with open(meilenstein_pfad, "r") as f:
                    meilensteine = json.load(f)
            except Exception:
                meilensteine = []

        if anzahl > 0:
            bereits_entdeckt = any(
                m.get("typ") == "wahrnehmung_erstmals" for m in meilensteine
            )
            if not bereits_entdeckt:
                meilensteine.append({
                    "typ": "wahrnehmung_erstmals",
                    "zeitstempel": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "tick": self.sim_daten.get("tick", 0),
                    "anzahl": anzahl,
                    "beschreibung": f"Erstmals Wahrnehmungs-Muster bei {anzahl} Organismus(en) entdeckt",
                })
                try:
                    with open(meilenstein_pfad, "w") as f:
                        json.dump(meilensteine, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass

        return {
            "anzahl": anzahl,
            "gesamt": gesamt,
            "prozent": prozent,
            "top5": treffer[:5],
            "meilensteine": meilensteine,
            "trace_verfuegbar": anzahl > 0,
        }

    def _trace_schritt(self, speicher, adresse, register, zellende):
        """Ein Schritt READ-ONLY simulieren. Gibt (neues_register, neue_adresse, details, aktiv) zurück."""
        adr = adresse % SPEICHER_GROESSE
        befehl = speicher[adr]
        arg1 = speicher[(adr + 1) % SPEICHER_GROESSE]
        arg2 = speicher[(adr + 2) % SPEICHER_GROESSE]
        arg3 = speicher[(adr + 3) % SPEICHER_GROESSE]
        r = list(register)
        details = ""
        aktiv = True
        neue_adresse = adresse + 4

        if befehl == 0:  # NOOP
            details = "Nichts"
        elif befehl == 1:  # LESEN
            quell_adr = r[arg1 % 4] % SPEICHER_GROESSE
            wert = speicher[quell_adr]
            r[arg3 % 4] = wert
            details = f"Gelesen: {wert} von Adresse {quell_adr}"
        elif befehl == 2:  # SCHREIBEN
            ziel_adr = r[arg3 % 4] % SPEICHER_GROESSE
            wert = r[arg1 % 4] & 0xFF
            details = f"Wuerde schreiben: {wert} an Adresse {ziel_adr}"
        elif befehl == 3:  # ADDIEREN
            ergebnis = r[arg1 % 4] + r[arg2 % 4]
            r[arg3 % 4] = ergebnis
            details = f"{r[arg1 % 4]}+{r[arg2 % 4]}={ergebnis}"
        elif befehl == 4:  # VERGLEICHEN_SPRINGEN
            va = r[arg1 % 4]
            vb = r[arg2 % 4]
            if va != vb:
                sprung = arg3 if arg3 < 128 else arg3 - 256
                neue_adresse = adresse + sprung * 4
                details = f"Sprung genommen: ja, {sprung:+d} Anweisungen (R{arg1%4}={va} != R{arg2%4}={vb})"
            else:
                details = f"Sprung genommen: nein (R{arg1%4}={va} == R{arg2%4}={vb})"
        elif befehl == 5:  # KOPIEREN
            anzahl = min(r[arg1 % 4], 1024)
            quell = r[arg2 % 4]
            ziel = r[arg3 % 4]
            details = f"Wuerde kopieren: {anzahl} Bytes von {quell} nach {ziel}"
        elif befehl == 6:  # LESEN_EXTERN
            extern_adr = (zellende + r[arg1 % 4]) % SPEICHER_GROESSE
            wert = speicher[extern_adr]
            r[arg3 % 4] = wert
            details = f"Extern gelesen: {wert} von Adresse {extern_adr}"
        elif befehl == 7:  # SELBST
            details = f"Startadresse"
        elif befehl == 8:  # SETZEN
            r[arg3 % 4] = arg1
            details = f"R{arg3%4} = {arg1}"
        elif befehl == 9:  # ENDE
            aktiv = False
            details = "ENDE erreicht"
        elif befehl == 10:  # SCHREIBEN_EXTERN
            extern_adr = (zellende + r[arg3 % 4]) % SPEICHER_GROESSE
            wert = r[arg1 % 4] & 0xFF
            details = f"Wuerde extern schreiben: {wert} an Adresse {extern_adr}"
        else:
            details = f"Unbekannter Opcode {befehl}"

        op_name = OPCODE_NAMEN[befehl] if befehl < len(OPCODE_NAMEN) else f"?({befehl})"

        return r, neue_adresse, details, aktiv, op_name, befehl

    def trace_organismen(self):
        """Trace bis zu 3 Organismen mit Wahrnehmungs-Muster. READ-ONLY."""
        pointer = self.pointer_liste
        speicher = self.welt.speicher
        traces = []

        # Finde Organismen mit dem Muster
        kandidaten = []
        for p in pointer:
            if not p.aktiv:
                continue
            genom = self._extrahiere_genom(p.startadresse)
            for i in range(0, len(genom) - 4, 4):
                if genom[i] == 6:  # LESEN_EXTERN
                    for j in range(1, 4):
                        pos = i + j * 4
                        if pos < len(genom) and genom[pos] in (4, 10):
                            kandidaten.append(p)
                            break
                    else:
                        continue
                    break
            if len(kandidaten) >= 3:
                break

        for p in kandidaten:
            genom = self._extrahiere_genom(p.startadresse)
            # Zellende berechnen (wie im Interpreter)
            zellende = p.startadresse
            for i in range(0, 1024, 4):
                pos = (p.startadresse + i) % SPEICHER_GROESSE
                if speicher[pos] == 9:  # ENDE
                    zellende = (p.startadresse + i + 4) % SPEICHER_GROESSE
                    break
            else:
                zellende = (p.startadresse + 1024) % SPEICHER_GROESSE

            # Kopiere Register und Adresse
            reg = list(p.register)
            adr = p.adresse
            schritte = []

            for schritt_nr in range(1, 51):
                reg_vorher = list(reg)
                reg, adr_neu, details, aktiv, op_name, opcode = self._trace_schritt(
                    speicher, adr, reg, zellende
                )
                schritte.append({
                    "schritt": schritt_nr,
                    "operation": op_name,
                    "opcode": opcode,
                    "adresse": adr % SPEICHER_GROESSE,
                    "register_vorher": reg_vorher,
                    "register_nachher": list(reg),
                    "details": details,
                    "ist_lesen_extern": opcode == 6,
                    "ist_vergleichen_springen": opcode == 4,
                })
                if not aktiv:
                    break
                adr = adr_neu

            traces.append({
                "adresse": p.startadresse,
                "genom_laenge": len(genom),
                "schritte": schritte,
            })

        return {"traces": traces}
