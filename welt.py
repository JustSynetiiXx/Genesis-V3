"""
Genesis v3 — Welt
Ein zusammenhängender Speicherblock. Nichts weiter.
"""

SPEICHER_GROESSE = 1_048_576  # 1 MB


class Welt:
    def __init__(self):
        self.speicher = bytearray(SPEICHER_GROESSE)

    def lesen(self, adresse: int) -> int:
        return self.speicher[adresse % SPEICHER_GROESSE]

    def schreiben(self, adresse: int, wert: int):
        self.speicher[adresse % SPEICHER_GROESSE] = wert & 0xFF
