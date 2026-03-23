#[derive(Clone, Debug)]
pub enum Topologie {
    Linear,
    Grid { breite: usize, hoehe: usize },
}

#[derive(Clone, Debug)]
pub enum NahrungModus {
    Gleichverteilt,
    Gradient { zentren: Vec<(usize, usize, f32)> },
}

#[derive(Clone, Debug)]
pub struct Config {
    pub speicher_groesse: usize,
    pub population_limit: usize,
    pub nahrung_wert: u8,
    pub nahrung_pro_tick: usize,
    pub nahrung_vorfuellung: f32,
    pub spawn_energie: i32,
    pub schritt_cap: usize,
    pub kopier_kosten_divisor: usize,
    pub mutationsrate: usize,
    pub verfall_pro_tick: usize,
    pub blitz_chance: usize,
    pub blitz_min_pop: usize,
    pub blitz_prozent: f32,
    pub leerlauf_tod_ticks: usize,
    pub min_kopier_groesse: usize,
    pub max_zellgroesse: usize,
    pub anweisung_groesse: usize,
    pub fress_energie: i32,
    pub topologie: Topologie,
    pub nahrung_modus: NahrungModus,
}

impl Default for Config {
    fn default() -> Self {
        Config {
            speicher_groesse: 1_048_576,
            population_limit: 2000,
            nahrung_wert: 42,
            nahrung_pro_tick: 200,
            nahrung_vorfuellung: 0.2,
            spawn_energie: 30,
            schritt_cap: 500,
            kopier_kosten_divisor: 4,
            mutationsrate: 500,
            verfall_pro_tick: 100,
            blitz_chance: 3000,
            blitz_min_pop: 500,
            blitz_prozent: 0.07,
            leerlauf_tod_ticks: 10,
            min_kopier_groesse: 20,
            max_zellgroesse: 1024,
            anweisung_groesse: 4,
            fress_energie: 20,
            topologie: Topologie::Linear,
            nahrung_modus: NahrungModus::Gleichverteilt,
        }
    }
}

impl Config {
    pub fn from_args(args: &[String]) -> Self {
        let mut cfg = Config::default();
        let mut i = 1;
        while i < args.len() {
            match args[i].as_str() {
                "--speicher" => { i += 1; cfg.speicher_groesse = args[i].parse().unwrap(); }
                "--population-limit" => { i += 1; cfg.population_limit = args[i].parse().unwrap(); }
                "--nahrung-pro-tick" => { i += 1; cfg.nahrung_pro_tick = args[i].parse().unwrap(); }
                "--spawn-energie" => { i += 1; cfg.spawn_energie = args[i].parse().unwrap(); }
                "--schritt-cap" => { i += 1; cfg.schritt_cap = args[i].parse().unwrap(); }
                "--mutationsrate" => { i += 1; cfg.mutationsrate = args[i].parse().unwrap(); }
                "--verfall" => { i += 1; cfg.verfall_pro_tick = args[i].parse().unwrap(); }
                "--blitz-chance" => { i += 1; cfg.blitz_chance = args[i].parse().unwrap(); }
                "--fress-energie" => { i += 1; cfg.fress_energie = args[i].parse().unwrap(); }
                "--nahrung-vorfuellung" => { i += 1; cfg.nahrung_vorfuellung = args[i].parse().unwrap(); }
                _ => { eprintln!("Unbekannter Parameter: {}", args[i]); }
            }
            i += 1;
        }
        cfg
    }
}
