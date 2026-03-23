use rand::Rng;
use crate::welt::Welt;

// Ur-Replikator: exakt aus Python erzeuge_ur_replikator() extrahiert
pub const UR_REPLIKATOR: [u8; 72] = [
    0x06, 0x03, 0x00, 0x02,  //  0: LESEN_EXT R3 → R2
    0x08, 0x07, 0x00, 0x01,  //  1: SETZEN 7 → R1
    0x03, 0x03, 0x01, 0x03,  //  2: ADD R3+R1 → R3
    0x06, 0x03, 0x00, 0x02,  //  3: LESEN_EXT R3 → R2
    0x03, 0x03, 0x01, 0x03,  //  4: ADD R3+R1 → R3
    0x06, 0x03, 0x00, 0x02,  //  5: LESEN_EXT R3 → R2
    0x03, 0x03, 0x01, 0x03,  //  6: ADD R3+R1 → R3
    0x06, 0x03, 0x00, 0x02,  //  7: LESEN_EXT R3 → R2
    0x03, 0x03, 0x01, 0x03,  //  8: ADD R3+R1 → R3
    0x06, 0x03, 0x00, 0x02,  //  9: LESEN_EXT R3 → R2
    0x03, 0x03, 0x01, 0x03,  // 10: ADD R3+R1 → R3
    0x07, 0x00, 0x00, 0x00,  // 11: SELBST → R0
    0x08, 0x48, 0x00, 0x01,  // 12: SETZEN 72 → R1
    0x03, 0x00, 0x01, 0x02,  // 13: ADD R0+R1 → R2
    0x05, 0x01, 0x00, 0x02,  // 14: KOPIEREN R1 von R0 nach R2
    0x08, 0x00, 0x00, 0x01,  // 15: SETZEN 0 → R1
    0x04, 0x03, 0x01, 0xf0,  // 16: VERGL_SPR R3!=R1 → -16
    0x09, 0x00, 0x00, 0x00,  // 17: ENDE
];

pub struct Pointer {
    pub startadresse: usize,
    pub adresse: usize,
    pub register: [u64; 4],
    pub energie: i32,
    pub aktiv: bool,
    pub leerlauf_ticks: usize,
    pub sinnvolle_ops: usize,
    pub neue_pointer: Vec<usize>,
    pub mutationen: Vec<(usize, u64, u64, u8, u8)>,
    pub kopier_events: usize,
}

impl Pointer {
    pub fn new(startadresse: usize) -> Self {
        Pointer {
            startadresse,
            adresse: startadresse,
            register: [0; 4],
            energie: 0,
            aktiv: true,
            leerlauf_ticks: 0,
            sinnvolle_ops: 0,
            neue_pointer: Vec::new(),
            mutationen: Vec::new(),
            kopier_events: 0,
        }
    }

    pub fn tick(&mut self, welt: &mut Welt, rng: &mut impl Rng, ops_zaehler: &mut [u64; 11]) {
        let cfg = &welt.config;
        let speicher = &mut welt.speicher;
        let groesse = cfg.speicher_groesse;
        let spawn_energie = cfg.spawn_energie;
        let schritt_cap = cfg.schritt_cap;
        let mutationsrate = cfg.mutationsrate;
        let fress_energie = cfg.fress_energie;
        let nahrung_wert = cfg.nahrung_wert;

        let startadresse = self.startadresse;
        let mut adresse = self.adresse;
        let r = &mut self.register;
        let mut energie: i32 = spawn_energie;
        let mut sinnvolle_ops: usize = 0;
        let mut schritte: usize = 0;
        let mut aktiv = true;
        let neue_pointer = &mut self.neue_pointer;
        let mutationen = &mut self.mutationen;
        let mut kopier_events: usize = 0;

        // Zellende scannen
        let mut zellende = startadresse;
        let max_zell = cfg.max_zellgroesse;
        let mut found_ende = false;
        for i in (0..max_zell).step_by(4) {
            let pos = (startadresse + i) % groesse;
            if speicher[pos] == 9 {
                zellende = (startadresse + i + 4) % groesse;
                found_ende = true;
                break;
            }
        }
        if !found_ende {
            zellende = (startadresse + max_zell) % groesse;
        }

        // Hauptschleife
        while aktiv && energie > 0 && schritte < schritt_cap {
            energie -= 1;
            schritte += 1;

            let adr = adresse % groesse;
            let befehl = speicher[adr];
            let arg1 = speicher[(adr + 1) % groesse];
            let arg2 = speicher[(adr + 2) % groesse];
            let arg3 = speicher[(adr + 3) % groesse];

            if (befehl as usize) < 11 {
                ops_zaehler[befehl as usize] += 1;
            }

            match befehl {
                0 => { /* NOOP */ }

                1 => { // LESEN — frisst NICHT
                    let quell_adr = (r[(arg1 % 4) as usize] as usize) % groesse;
                    r[(arg3 % 4) as usize] = speicher[quell_adr] as u64;
                    sinnvolle_ops += 1;
                }

                2 => { // SCHREIBEN
                    let ziel = (r[(arg3 % 4) as usize] as usize) % groesse;
                    speicher[ziel] = (r[(arg1 % 4) as usize] & 0xFF) as u8;
                    sinnvolle_ops += 1;
                }

                3 => { // ADDIEREN
                    r[(arg3 % 4) as usize] = r[(arg1 % 4) as usize].wrapping_add(r[(arg2 % 4) as usize]);
                    sinnvolle_ops += 1;
                }

                4 => { // VERGLEICHEN_SPRINGEN
                    sinnvolle_ops += 1;
                    if r[(arg1 % 4) as usize] != r[(arg2 % 4) as usize] {
                        let sprung = if arg3 < 128 { arg3 as i32 } else { arg3 as i32 - 256 };
                        let new_addr = adresse as i64 + (sprung as i64) * 4;
                        if new_addr < 0 || new_addr >= groesse as i64 {
                            aktiv = false;
                            break;
                        }
                        adresse = new_addr as usize;
                        continue;
                    }
                }

                5 => { // KOPIEREN
                    let mut anzahl = std::cmp::min(r[(arg1 % 4) as usize] as usize, 1024);
                    let quelle = r[(arg2 % 4) as usize];
                    let ziel_adr = r[(arg3 % 4) as usize];
                    let mut kopier_kosten = std::cmp::max(anzahl / cfg.kopier_kosten_divisor, 1) as i32;
                    if kopier_kosten > energie {
                        anzahl = (energie as usize) * cfg.kopier_kosten_divisor;
                        kopier_kosten = std::cmp::max(anzahl / cfg.kopier_kosten_divisor, 1) as i32;
                    }
                    energie -= kopier_kosten;
                    for i in 0..anzahl {
                        let ziel_pos = ((ziel_adr as usize) + i) % groesse;
                        if speicher[ziel_pos] != 0 && speicher[ziel_pos] != 42 {
                            continue;
                        }
                        let quell_pos = ((quelle as usize) + i) % groesse;
                        let byte_original = speicher[quell_pos];
                        let mut byte_val = byte_original;
                        if rng.gen_range(1..=mutationsrate) == 1 {
                            byte_val = rng.gen_range(0..=255u8);
                            if byte_val != byte_original {
                                mutationen.push((i, quelle, ziel_adr, byte_original, byte_val));
                            }
                        }
                        speicher[ziel_pos] = byte_val;
                    }
                    if anzahl >= cfg.min_kopier_groesse {
                        neue_pointer.push((ziel_adr as usize) % groesse);
                        kopier_events += 1;
                    }
                    sinnvolle_ops += 1;
                }

                6 => { // LESEN_EXTERN
                    let offset = r[(arg1 % 4) as usize];
                    let extern_adr = match cfg.grid_dims() {
                        Some((breite, hoehe)) => {
                            let xe = zellende % breite;
                            let ye = zellende / breite;
                            let dx = (offset as usize) % breite;
                            let dy = (offset as usize) / breite;
                            ((ye + dy) % hoehe) * breite + ((xe + dx) % breite)
                        }
                        None => ((zellende as u64).wrapping_add(offset) as usize) % groesse,
                    };
                    let wert = speicher[extern_adr];
                    r[(arg3 % 4) as usize] = wert as u64;
                    if wert == nahrung_wert {
                        energie += fress_energie;
                        speicher[extern_adr] = 0;
                    }
                    sinnvolle_ops += 1;
                }

                7 => { // SELBST
                    r[(arg3 % 4) as usize] = startadresse as u64;
                    sinnvolle_ops += 1;
                }

                8 => { // SETZEN
                    r[(arg3 % 4) as usize] = arg1 as u64;
                    sinnvolle_ops += 1;
                }

                9 => { // ENDE
                    aktiv = false;
                    break;
                }

                10 => { // SCHREIBEN_EXTERN
                    let offset = r[(arg3 % 4) as usize];
                    let extern_adr = match cfg.grid_dims() {
                        Some((breite, hoehe)) => {
                            let xe = zellende % breite;
                            let ye = zellende / breite;
                            let dx = (offset as usize) % breite;
                            let dy = (offset as usize) / breite;
                            ((ye + dy) % hoehe) * breite + ((xe + dx) % breite)
                        }
                        None => ((zellende as u64).wrapping_add(offset) as usize) % groesse,
                    };
                    speicher[extern_adr] = (r[(arg1 % 4) as usize] & 0xFF) as u8;
                    sinnvolle_ops += 1;
                }

                _ => { /* Ungültiger Opcode: nichts tun */ }
            }

            adresse += 4;
            if adresse >= groesse {
                aktiv = false;
                break;
            }
        }

        // Zurückschreiben
        self.adresse = adresse;
        self.aktiv = aktiv;
        self.energie = energie;
        self.kopier_events = kopier_events;
        if sinnvolle_ops == 0 {
            self.leerlauf_ticks += 1;
        } else {
            self.leerlauf_ticks = 0;
        }
        self.sinnvolle_ops = sinnvolle_ops;
    }
}

pub fn abiogenese(welt: &mut Welt, rng: &mut impl Rng) -> usize {
    let g = welt.groesse();
    let adresse = rng.gen_range(0..g);
    for (i, &byte) in UR_REPLIKATOR.iter().enumerate() {
        welt.speicher[(adresse + i) % g] = byte;
    }
    adresse
}

/// Platziert den Ur-Replikator in der Mitte des Grids.
pub fn abiogenese_grid_mitte(welt: &mut Welt, breite: usize, hoehe: usize) -> usize {
    let g = welt.groesse();
    let adresse = (hoehe / 2) * breite + (breite / 2);
    for (i, &byte) in UR_REPLIKATOR.iter().enumerate() {
        welt.speicher[(adresse + i) % g] = byte;
    }
    adresse
}
