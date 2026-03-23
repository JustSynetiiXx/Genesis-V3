use rand::Rng;
use crate::config::Config;

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
        let g = self.groesse();
        let wert = self.config.nahrung_wert;
        for _ in 0..self.config.nahrung_pro_tick {
            let pos = rng.gen_range(0..g);
            if self.speicher[pos] == 0 {
                self.speicher[pos] = wert;
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
        let g = self.groesse();
        let bytes = (g as f32 * self.config.blitz_prozent) as usize;
        for _ in 0..bytes {
            let pos = rng.gen_range(0..g);
            self.speicher[pos] = 0;
        }
    }

    pub fn vorfuellen(&mut self, rng: &mut impl Rng) {
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

    pub fn nahrung_zaehlen(&self) -> usize {
        self.speicher.iter().filter(|&&b| b == self.config.nahrung_wert).count()
    }

    pub fn belegt_zaehlen(&self) -> usize {
        self.speicher.iter().filter(|&&b| b != 0).count()
    }
}
