use rand::Rng;
use crate::config::{Config, NahrungModus};

#[inline]
fn torus_distanz_sq(x1: usize, y1: usize, x2: usize, y2: usize, breite: usize, hoehe: usize) -> f32 {
    let dx_raw = (x1 as isize - x2 as isize).unsigned_abs();
    let dx = dx_raw.min(breite - dx_raw);
    let dy_raw = (y1 as isize - y2 as isize).unsigned_abs();
    let dy = dy_raw.min(hoehe - dy_raw);
    (dx * dx + dy * dy) as f32
}

pub struct Welt {
    pub speicher: Vec<u8>,
    pub config: Config,
}

impl Welt {
    pub fn new(config: Config) -> Self {
        let size = config.speicher_groesse;
        Welt {
            speicher: vec![0u8; size],
            config,
        }
    }

    #[inline(always)]
    pub fn groesse(&self) -> usize {
        self.config.speicher_groesse
    }

    pub fn nahrung_streuen(&mut self, rng: &mut impl Rng) {
        match (&self.config.nahrung_modus, self.config.grid_dims()) {
            (NahrungModus::Gradient { zentren }, Some((breite, hoehe))) => {
                let wert = self.config.nahrung_wert;
                let radius_sq = {
                    let r = breite as f32 / 6.0;
                    2.0 * r * r
                };

                for _ in 0..self.config.nahrung_pro_tick {
                    for _versuch in 0..3 {
                        let x = rng.gen_range(0..breite);
                        let y = rng.gen_range(0..hoehe);
                        let pos = y * breite + x;
                        if self.speicher[pos] != 0 {
                            continue;
                        }

                        // Gewicht berechnen
                        let mut summe = 0.0f32;
                        for &(ox, oy, staerke) in zentren.iter() {
                            let d_sq = torus_distanz_sq(x, y, ox, oy, breite, hoehe);
                            // Approximation: 1.0 / (1.0 + d²/(2r²))
                            summe += staerke / (1.0 + d_sq / radius_sq);
                        }
                        let gewicht = (0.3 + summe).min(1.0);

                        if rng.gen::<f32>() < gewicht {
                            self.speicher[pos] = wert;
                            break;
                        }
                    }
                }
            }
            _ => {
                // Gleichverteilt (oder Linear)
                let g = self.groesse();
                let wert = self.config.nahrung_wert;
                for _ in 0..self.config.nahrung_pro_tick {
                    let pos = rng.gen_range(0..g);
                    if self.speicher[pos] == 0 {
                        self.speicher[pos] = wert;
                    }
                }
            }
        }
    }

    pub fn verfall(&mut self, rng: &mut impl Rng) {
        let g = self.groesse();
        for _ in 0..self.config.verfall_pro_tick {
            let pos = rng.gen_range(0..g);
            self.speicher[pos] = 0;
        }
    }

    pub fn blitz(&mut self, rng: &mut impl Rng) {
        match self.config.grid_dims() {
            Some((breite, hoehe)) => {
                // Rechteckiges Gebiet löschen (~blitz_prozent des Speichers)
                let g = self.groesse();
                let target_bytes = (g as f32 * self.config.blitz_prozent) as usize;
                let seite = (target_bytes as f64).sqrt() as usize;
                let bx = seite.max(1).min(breite);
                let by = seite.max(1).min(hoehe);
                let sx = rng.gen_range(0..breite);
                let sy = rng.gen_range(0..hoehe);
                for dy in 0..by {
                    let y = (sy + dy) % hoehe;
                    for dx in 0..bx {
                        let x = (sx + dx) % breite;
                        self.speicher[y * breite + x] = 0;
                    }
                }
            }
            None => {
                // Linear: zufällige Positionen
                let g = self.groesse();
                let bytes = (g as f32 * self.config.blitz_prozent) as usize;
                for _ in 0..bytes {
                    let pos = rng.gen_range(0..g);
                    self.speicher[pos] = 0;
                }
            }
        }
    }

    pub fn vorfuellen(&mut self, rng: &mut impl Rng) {
        match (&self.config.nahrung_modus, self.config.grid_dims()) {
            (NahrungModus::Gradient { zentren }, Some((breite, hoehe))) => {
                let wert = self.config.nahrung_wert;
                let g = self.groesse();
                let anzahl = (g as f32 * self.config.nahrung_vorfuellung) as usize;
                let radius_sq = {
                    let r = breite as f32 / 6.0;
                    2.0 * r * r
                };

                for _ in 0..anzahl {
                    for _versuch in 0..3 {
                        let x = rng.gen_range(0..breite);
                        let y = rng.gen_range(0..hoehe);
                        let pos = y * breite + x;
                        if self.speicher[pos] != 0 {
                            continue;
                        }
                        let mut summe = 0.0f32;
                        for &(ox, oy, staerke) in zentren.iter() {
                            let d_sq = torus_distanz_sq(x, y, ox, oy, breite, hoehe);
                            summe += staerke / (1.0 + d_sq / radius_sq);
                        }
                        let gewicht = (0.3 + summe).min(1.0);
                        if rng.gen::<f32>() < gewicht {
                            self.speicher[pos] = wert;
                            break;
                        }
                    }
                }
            }
            _ => {
                let g = self.groesse();
                let wert = self.config.nahrung_wert;
                let anzahl = (g as f32 * self.config.nahrung_vorfuellung) as usize;
                for _ in 0..anzahl {
                    let pos = rng.gen_range(0..g);
                    if self.speicher[pos] == 0 {
                        self.speicher[pos] = wert;
                    }
                }
            }
        }
    }

    pub fn nahrung_zaehlen(&self) -> usize {
        self.speicher.iter().filter(|&&b| b == self.config.nahrung_wert).count()
    }

    pub fn belegt_zaehlen(&self) -> usize {
        self.speicher.iter().filter(|&&b| b != 0).count()
    }
}
