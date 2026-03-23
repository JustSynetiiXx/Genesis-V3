mod config;
mod interpreter;
mod welt;

use std::collections::HashSet;
use std::time::Instant;

use rand::rngs::SmallRng;
use rand::{Rng, SeedableRng};
use serde_json::json;

use config::Config;
use interpreter::{abiogenese, Pointer};
use welt::Welt;

const OPCODE_NAMEN: [&str; 11] = [
    "NOOP", "LESEN", "SCHREIBEN", "ADDIEREN", "VERGL_SPR",
    "KOPIEREN", "LESEN_EXT", "SELBST", "SETZEN", "ENDE", "SCHR_EXT",
];

fn genom_laenge(speicher: &[u8], startadresse: usize, groesse: usize, max_zell: usize) -> usize {
    for i in (0..max_zell).step_by(4) {
        let pos = (startadresse + i) % groesse;
        if speicher[pos] == 9 {
            return i + 4;
        }
    }
    max_zell
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let cfg = Config::from_args(&args);

    let mut rng = SmallRng::from_entropy();
    let mut welt = Welt::new(cfg.clone());

    // Nahrung vorfüllen
    welt.vorfuellen(&mut rng);

    // Ur-Replikator einsetzen
    let start_adr = abiogenese(&mut welt, &mut rng);
    let mut pointer_liste: Vec<Pointer> = vec![Pointer::new(start_adr)];
    let mut belegte_adressen: HashSet<usize> = HashSet::new();
    belegte_adressen.insert(start_adr);

    let mut tick: u64 = 0;
    let mut geburten_gesamt: u64 = 0;
    let mut tode_gesamt: u64 = 0;
    let mut ops_zaehler: [u64; 11] = [0; 11];

    let startzeit = Instant::now();
    let mut letzte_ausgabe = Instant::now();

    eprintln!("Genesis v3.1 — Rust Core");
    eprintln!("Speicher: {} Bytes", cfg.speicher_groesse);
    eprintln!("Population-Limit: {}", cfg.population_limit);
    eprintln!("Spawn-Energie: {}", cfg.spawn_energie);

    loop {
        tick += 1;

        // 1. Nahrung streuen
        welt.nahrung_streuen(&mut rng);

        // 2. Verfall
        welt.verfall(&mut rng);

        // 3. Blitz
        if pointer_liste.len() > cfg.blitz_min_pop && rng.gen_range(1..=cfg.blitz_chance) == 1 {
            welt.blitz(&mut rng);
        }

        // 4. Tick für jeden Pointer + neue_pointer sammeln
        let mut alle_neuen: Vec<usize> = Vec::new();

        for p in pointer_liste.iter_mut() {
            p.tick(&mut welt, &mut rng, &mut ops_zaehler);

            // Neue Pointer sammeln VOR aktiv-Check
            for &adr in &p.neue_pointer {
                alle_neuen.push(adr);
            }
            p.neue_pointer.clear();
            p.mutationen.clear();

            // Leerlauf-Tod
            if p.aktiv && p.leerlauf_ticks >= cfg.leerlauf_tod_ticks {
                p.aktiv = false;
            }
        }

        // 5. Neue Pointer hinzufügen
        let platz_frei = cfg.population_limit.saturating_sub(pointer_liste.len());
        let mut hinzugefuegt = 0;
        for adr in alle_neuen {
            if hinzugefuegt >= platz_frei {
                break;
            }
            if belegte_adressen.contains(&adr) {
                continue;
            }
            pointer_liste.push(Pointer::new(adr));
            belegte_adressen.insert(adr);
            geburten_gesamt += 1;
            hinzugefuegt += 1;
        }

        // 6. Inaktive entfernen
        let vorher = pointer_liste.len();
        let mut i = 0;
        while i < pointer_liste.len() {
            if !pointer_liste[i].aktiv {
                belegte_adressen.remove(&pointer_liste[i].startadresse);
                pointer_liste.swap_remove(i);
            } else {
                i += 1;
            }
        }
        tode_gesamt += (vorher - pointer_liste.len()) as u64;

        // 7. Abiogenese
        if pointer_liste.is_empty() {
            let adr = abiogenese(&mut welt, &mut rng);
            pointer_liste.push(Pointer::new(adr));
            belegte_adressen.insert(adr);
            geburten_gesamt += 1;
        }

        // JSON-Ausgabe alle 2 Sekunden
        if letzte_ausgabe.elapsed().as_secs_f64() >= 2.0 {
            let elapsed = startzeit.elapsed().as_secs_f64();
            let tps = tick as f64 / elapsed.max(0.001);

            let g = welt.groesse();
            let max_zell = cfg.max_zellgroesse;
            let speicher = &welt.speicher;

            let nahrung = welt.nahrung_zaehlen();
            let belegt = welt.belegt_zaehlen();
            let pop = pointer_liste.len();

            // Genomlängen
            let mut laengen: Vec<usize> = pointer_liste.iter()
                .filter(|p| p.aktiv)
                .map(|p| genom_laenge(speicher, p.startadresse, g, max_zell))
                .collect();
            if laengen.is_empty() {
                laengen.push(0);
            }
            let avg = laengen.iter().sum::<usize>() as f64 / laengen.len() as f64;
            let min_l = *laengen.iter().min().unwrap_or(&0);
            let max_l = *laengen.iter().max().unwrap_or(&0);

            // Ops snapshot
            let ops_snapshot = ops_zaehler;
            ops_zaehler = [0; 11];
            let ops_total: u64 = ops_snapshot.iter().sum();

            let mut ops_map = serde_json::Map::new();
            for (i, name) in OPCODE_NAMEN.iter().enumerate() {
                ops_map.insert(name.to_string(), json!(ops_snapshot[i]));
            }

            let output = json!({
                "tick": tick,
                "population": pop,
                "nahrung_anzahl": nahrung,
                "nahrung_prozent": (nahrung as f64 / g as f64 * 100.0 * 100.0).round() / 100.0,
                "genom_laenge_avg": (avg * 10.0).round() / 10.0,
                "genom_laenge_min": min_l,
                "genom_laenge_max": max_l,
                "speicher_belegt_prozent": (belegt as f64 / g as f64 * 100.0 * 100.0).round() / 100.0,
                "geburten_gesamt": geburten_gesamt,
                "tode_gesamt": tode_gesamt,
                "ticks_pro_sekunde": (tps * 10.0).round() / 10.0,
                "ausgefuehrte_ops": ops_map,
                "ausgefuehrte_ops_total": ops_total,
            });
            println!("{}", output);

            letzte_ausgabe = Instant::now();
        }
    }
}
