use std::sync::{Arc, Mutex};
use std::thread;
use std::collections::HashMap;

use serde_json::json;
use tiny_http::{Server, Response, Header};

use crate::OPCODE_NAMEN;

pub struct SimState {
    // Basis-Metriken
    pub tick: u64,
    pub population: usize,
    pub population_max: usize,
    pub geburten_gesamt: u64,
    pub tode_gesamt: u64,
    pub speicher_belegt_bytes: usize,
    pub speicher_belegt_prozent: f64,
    pub diversitaet: usize,
    pub diversitaet_shannon: f64,
    pub genom_laenge_avg: f64,
    pub genom_laenge_min: usize,
    pub genom_laenge_max: usize,
    pub nahrung_anzahl: usize,
    pub nahrung_a_anzahl: usize,
    pub nahrung_b_anzahl: usize,
    pub nahrung_prozent: f64,
    pub kopierbereit_prozent: f64,
    pub ticks_pro_sekunde: f64,
    pub laufzeit_sekunden: f64,

    // Ops
    pub ausgefuehrte_ops: [u64; 11],
    pub ausgefuehrte_ops_total: u64,

    // Top-Genome
    pub top_genome: Vec<TopGenom>,

    // Operations-Verteilung (statisch im Genom)
    pub operations_verteilung: [u64; 11],

    // Weltkarte
    pub speicher_snapshot: Vec<u8>,
    pub pointer_positionen: Vec<(usize, usize)>, // (adresse, laenge)

    // Analyse
    pub analyse_ergebnis: serde_json::Value,
    pub trace_ergebnis: serde_json::Value,
}

#[derive(Clone)]
pub struct TopGenom {
    pub hex: String,
    pub laenge: usize,
    pub anzahl: usize,
    pub anteil: f64,
}

impl SimState {
    pub fn new(speicher_groesse: usize) -> Self {
        SimState {
            tick: 0,
            population: 0,
            population_max: 0,
            geburten_gesamt: 0,
            tode_gesamt: 0,
            speicher_belegt_bytes: 0,
            speicher_belegt_prozent: 0.0,
            diversitaet: 0,
            diversitaet_shannon: 0.0,
            genom_laenge_avg: 0.0,
            genom_laenge_min: 0,
            genom_laenge_max: 0,
            nahrung_anzahl: 0,
            nahrung_a_anzahl: 0,
            nahrung_b_anzahl: 0,
            nahrung_prozent: 0.0,
            kopierbereit_prozent: 0.0,
            ticks_pro_sekunde: 0.0,
            laufzeit_sekunden: 0.0,
            ausgefuehrte_ops: [0; 11],
            ausgefuehrte_ops_total: 0,
            top_genome: Vec::new(),
            operations_verteilung: [0; 11],
            speicher_snapshot: vec![0u8; speicher_groesse],
            pointer_positionen: Vec::new(),
            analyse_ergebnis: json!({"anzahl": 0, "gesamt": 0, "prozent": 0.0, "top5": [], "meilensteine": []}),
            trace_ergebnis: json!({"traces": []}),
        }
    }
}

fn cors_header() -> Header {
    Header::from_bytes("Access-Control-Allow-Origin", "*").unwrap()
}

fn content_type_json() -> Header {
    Header::from_bytes("Content-Type", "application/json; charset=utf-8").unwrap()
}

fn ops_to_json(ops: &[u64; 11]) -> serde_json::Value {
    let mut map = serde_json::Map::new();
    for (i, name) in OPCODE_NAMEN.iter().enumerate() {
        map.insert(name.to_string(), json!(ops[i]));
    }
    serde_json::Value::Object(map)
}

fn genome_to_json(genome: &[TopGenom]) -> serde_json::Value {
    let arr: Vec<serde_json::Value> = genome.iter().map(|g| {
        json!({
            "hex": g.hex,
            "laenge": g.laenge,
            "anzahl": g.anzahl,
            "anteil": g.anteil,
        })
    }).collect();
    serde_json::Value::Array(arr)
}

fn build_export(state: &SimState) -> serde_json::Value {
    json!({
        "tick_nummer": state.tick,
        "population": state.population,
        "population_max": state.population_max,
        "geburten_gesamt": state.geburten_gesamt,
        "tode_gesamt": state.tode_gesamt,
        "speicher_belegt_bytes": state.speicher_belegt_bytes,
        "speicher_belegt_prozent": state.speicher_belegt_prozent,
        "diversitaet": state.diversitaet,
        "diversitaet_shannon": state.diversitaet_shannon,
        "genom_laenge_avg": state.genom_laenge_avg,
        "genom_laenge_min": state.genom_laenge_min,
        "genom_laenge_max": state.genom_laenge_max,
        "nahrung_anzahl": state.nahrung_anzahl,
        "nahrung_a_anzahl": state.nahrung_a_anzahl,
        "nahrung_b_anzahl": state.nahrung_b_anzahl,
        "nahrung_prozent": state.nahrung_prozent,
        "kopierbereit_prozent": state.kopierbereit_prozent,
        "ticks_pro_sekunde": state.ticks_pro_sekunde,
        "laufzeit_sekunden": state.laufzeit_sekunden,
        "ausgefuehrte_ops": ops_to_json(&state.ausgefuehrte_ops),
        "ausgefuehrte_ops_total": state.ausgefuehrte_ops_total,
        "top_genome": genome_to_json(&state.top_genome),
        "operations_verteilung": ops_to_json(&state.operations_verteilung),
    })
}

fn build_status(state: &SimState) -> serde_json::Value {
    json!({
        "tick_nummer": state.tick,
        "population": state.population,
        "population_max": state.population_max,
        "geburten_gesamt": state.geburten_gesamt,
        "tode_gesamt": state.tode_gesamt,
        "speicher_belegt_bytes": state.speicher_belegt_bytes,
        "speicher_belegt_prozent": state.speicher_belegt_prozent,
        "diversitaet": state.diversitaet,
        "diversitaet_shannon": state.diversitaet_shannon,
        "genom_laenge_avg": state.genom_laenge_avg,
        "genom_laenge_min": state.genom_laenge_min,
        "genom_laenge_max": state.genom_laenge_max,
        "nahrung_anzahl": state.nahrung_anzahl,
        "nahrung_a_anzahl": state.nahrung_a_anzahl,
        "nahrung_b_anzahl": state.nahrung_b_anzahl,
        "nahrung_prozent": state.nahrung_prozent,
        "kopierbereit_prozent": state.kopierbereit_prozent,
        "ticks_pro_sekunde": state.ticks_pro_sekunde,
        "laufzeit_sekunden": state.laufzeit_sekunden,
        "ausgefuehrte_ops": ops_to_json(&state.ausgefuehrte_ops),
        "ausgefuehrte_ops_total": state.ausgefuehrte_ops_total,
    })
}

fn build_weltkarte(state: &SimState) -> serde_json::Value {
    let speicher = &state.speicher_snapshot;
    let g = speicher.len();
    let block_size = g / 1024;

    let mut weltkarte = Vec::with_capacity(1024);
    for i in 0..1024 {
        let start = i * block_size;
        let end = start + block_size;
        let non_zero = speicher[start..end].iter().filter(|&&b| b != 0).count();
        if non_zero == 0 {
            weltkarte.push(0);
        } else if non_zero > block_size / 2 {
            weltkarte.push(2);
        } else {
            weltkarte.push(1);
        }
    }

    let positionen: Vec<usize> = state.pointer_positionen.iter().map(|&(adr, _)| adr).collect();
    json!({
        "weltkarte": weltkarte,
        "pointer_positionen": positionen,
        "groesse": g,
    })
}

fn json_response(data: serde_json::Value) -> Response<std::io::Cursor<Vec<u8>>> {
    let body = data.to_string();
    let mut resp = Response::from_data(body.into_bytes());
    resp.add_header(cors_header());
    resp.add_header(content_type_json());
    resp
}

pub fn start_http_server(state: Arc<Mutex<SimState>>) {
    thread::spawn(move || {
        let server = match Server::http("0.0.0.0:8081") {
            Ok(s) => s,
            Err(e) => {
                eprintln!("HTTP-Server konnte nicht starten: {}", e);
                return;
            }
        };
        eprintln!("HTTP-API bereit auf Port 8081");

        for request in server.incoming_requests() {
            let path = request.url().split('?').next().unwrap_or("/");

            match path {
                "/api/export" => {
                    let s = state.lock().unwrap();
                    let data = build_export(&s);
                    drop(s);
                    let _ = request.respond(json_response(data));
                }
                "/api/status" => {
                    let s = state.lock().unwrap();
                    let data = build_status(&s);
                    drop(s);
                    let _ = request.respond(json_response(data));
                }
                "/api/weltkarte" => {
                    let s = state.lock().unwrap();
                    let data = build_weltkarte(&s);
                    drop(s);
                    let _ = request.respond(json_response(data));
                }
                "/api/analyse" => {
                    let s = state.lock().unwrap();
                    let data = s.analyse_ergebnis.clone();
                    drop(s);
                    let _ = request.respond(json_response(data));
                }
                "/api/trace" => {
                    let s = state.lock().unwrap();
                    let data = s.trace_ergebnis.clone();
                    drop(s);
                    let _ = request.respond(json_response(data));
                }
                _ => {
                    let resp = Response::from_string("Not Found")
                        .with_status_code(404);
                    let _ = request.respond(resp);
                }
            }
        }
    });
}

/// Berechnet top_genome, diversitaet, diversitaet_shannon, operations_verteilung
/// aus den aktuellen Pointern und dem Speicher.
pub fn berechne_genom_stats(
    speicher: &[u8],
    pointer_positionen: &[(usize, usize)], // (startadresse, genom_laenge)
    groesse: usize,
) -> (Vec<TopGenom>, usize, f64, [u64; 11]) {
    let pop = pointer_positionen.len();
    if pop == 0 {
        return (Vec::new(), 0, 0.0, [0; 11]);
    }

    // Hash -> (count, bytes, laenge)
    let mut hash_counts: HashMap<u64, (usize, Vec<u8>, usize)> = HashMap::new();
    let mut ops_verteilung: [u64; 11] = [0; 11];

    for &(start, laenge) in pointer_positionen {
        // Genom-Bytes lesen
        let len = laenge.min(1024);
        let mut bytes = Vec::with_capacity(len);
        for i in 0..len {
            let b = speicher[(start + i) % groesse];
            bytes.push(b);
        }

        // Statische Opcode-Verteilung im Genom
        for i in (0..len).step_by(4) {
            let opcode = bytes[i] as usize;
            if opcode < 11 {
                ops_verteilung[opcode] += 1;
            }
        }

        // Einfacher Hash
        let mut h: u64 = 0xcbf29ce484222325;
        for &b in &bytes {
            h ^= b as u64;
            h = h.wrapping_mul(0x100000001b3);
        }

        hash_counts.entry(h)
            .and_modify(|(count, _, _)| *count += 1)
            .or_insert((1, bytes, len));
    }

    // Diversitaet
    let diversitaet = hash_counts.len();

    // Shannon-Index
    let shannon = if pop > 0 {
        let mut entropy = 0.0f64;
        for (count, _, _) in hash_counts.values() {
            let p = *count as f64 / pop as f64;
            if p > 0.0 {
                entropy -= p * p.ln();
            }
        }
        (entropy * 100.0).round() / 100.0
    } else {
        0.0
    };

    // Top-10 nach Anzahl sortiert
    let mut sorted: Vec<_> = hash_counts.into_values().collect();
    sorted.sort_by(|a, b| b.0.cmp(&a.0));
    sorted.truncate(10);

    let top_genome: Vec<TopGenom> = sorted.into_iter().map(|(anzahl, bytes, laenge)| {
        let hex_bytes: Vec<String> = bytes.iter().take(32).map(|b| format!("{:02X}", b)).collect();
        let hex = hex_bytes.join(" ");
        TopGenom {
            hex,
            laenge,
            anzahl,
            anteil: ((anzahl as f64 / pop as f64) * 10000.0).round() / 100.0,
        }
    }).collect();

    (top_genome, diversitaet, shannon, ops_verteilung)
}

/// Prüft ob ein Organismus ein Wahrnehmungs-Muster hat.
/// LESEN_EXTERN (6) gefolgt innerhalb von 3 Anweisungen von VERGL_SPR (4) oder SCHR_EXT (10).
fn hat_wahrnehmungs_muster(genom: &[u8]) -> bool {
    let n_instr = genom.len() / 4;
    for i in 0..n_instr {
        if genom[i * 4] == 6 {
            // Prüfe die nächsten 3 Anweisungen
            for j in 1..=3 {
                let idx = i + j;
                if idx >= n_instr {
                    break;
                }
                let op = genom[idx * 4];
                if op == 4 || op == 10 {
                    return true;
                }
            }
        }
    }
    false
}

/// Berechnet Wahrnehmungs-Analyse für alle Pointer.
pub fn berechne_analyse(
    speicher: &[u8],
    pointer_positionen: &[(usize, usize)], // (startadresse, genom_laenge)
    groesse: usize,
) -> serde_json::Value {
    let gesamt = pointer_positionen.len();
    let mut mit_muster: Vec<(usize, usize, Vec<u8>)> = Vec::new(); // (adresse, laenge, bytes)

    for &(start, laenge) in pointer_positionen {
        let len = laenge.min(1024);
        let mut bytes = Vec::with_capacity(len);
        for i in 0..len {
            bytes.push(speicher[(start + i) % groesse]);
        }
        if hat_wahrnehmungs_muster(&bytes) {
            mit_muster.push((start, len, bytes));
        }
    }

    let anzahl = mit_muster.len();
    let prozent = if gesamt > 0 {
        ((anzahl as f64 / gesamt as f64) * 10000.0).round() / 100.0
    } else {
        0.0
    };

    let top5: Vec<serde_json::Value> = mit_muster.iter().take(5).map(|(adr, len, bytes)| {
        let hex: Vec<String> = bytes.iter().take(32).map(|b| format!("{:02X}", b)).collect();
        json!({
            "adresse": adr,
            "genom_laenge": len,
            "code_ausschnitt": hex.join(" "),
        })
    }).collect();

    json!({
        "anzahl": anzahl,
        "gesamt": gesamt,
        "prozent": prozent,
        "top5": top5,
        "meilensteine": [],
    })
}

fn opcode_name(op: u8) -> String {
    if (op as usize) < OPCODE_NAMEN.len() {
        OPCODE_NAMEN[op as usize].to_string()
    } else {
        format!("?({op})")
    }
}

/// Simuliert bis zu 50 Schritte read-only für einen Organismus.
fn trace_organismus(
    speicher: &[u8],
    startadresse: usize,
    genom_laenge: usize,
    groesse: usize,
    spawn_energie: i32,
    fress_energie: i32,
    nahrung_wert: u8,
) -> serde_json::Value {
    let mut r: [u64; 4] = [0; 4];
    let mut adresse = startadresse;
    let mut energie = spawn_energie;

    // Zellende berechnen
    let max_zell = genom_laenge.min(1024);
    let mut zellende = startadresse;
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

    let mut schritte: Vec<serde_json::Value> = Vec::new();

    for schritt_nr in 1..=50 {
        if energie <= 0 || adresse >= groesse {
            break;
        }
        energie -= 1;

        let adr = adresse % groesse;
        let befehl = speicher[adr];
        let arg1 = speicher[(adr + 1) % groesse];
        let arg2 = speicher[(adr + 2) % groesse];
        let arg3 = speicher[(adr + 3) % groesse];

        let ist_lesen_extern = befehl == 6;
        let ist_vergleichen_springen = befehl == 4;
        let mut details = String::new();

        match befehl {
            0 => { /* NOOP */ }

            1 => { // LESEN
                let quell_adr = (r[(arg1 % 4) as usize] as usize) % groesse;
                r[(arg3 % 4) as usize] = speicher[quell_adr] as u64;
                details = format!("Gelesen: {} von Adresse {}", speicher[quell_adr], quell_adr);
            }

            2 => { // SCHREIBEN — read-only, nicht ausführen
                let ziel = (r[(arg3 % 4) as usize] as usize) % groesse;
                let wert = r[(arg1 % 4) as usize] & 0xFF;
                details = format!("Schreiben: {} nach Adresse {} (simuliert)", wert, ziel);
            }

            3 => { // ADDIEREN
                r[(arg3 % 4) as usize] = r[(arg1 % 4) as usize].wrapping_add(r[(arg2 % 4) as usize]);
                details = format!("R{} = R{} + R{} = {}",
                    arg3 % 4, arg1 % 4, arg2 % 4, r[(arg3 % 4) as usize]);
            }

            4 => { // VERGLEICHEN_SPRINGEN
                if r[(arg1 % 4) as usize] != r[(arg2 % 4) as usize] {
                    let sprung = if arg3 < 128 { arg3 as i32 } else { arg3 as i32 - 256 };
                    let new_addr = adresse as i64 + (sprung as i64) * 4;
                    details = format!("R{}({}) != R{}({}) → Sprung {}",
                        arg1 % 4, r[(arg1 % 4) as usize],
                        arg2 % 4, r[(arg2 % 4) as usize], sprung * 4);
                    schritte.push(json!({
                        "schritt": schritt_nr,
                        "operation": opcode_name(befehl),
                        "register_nachher": [r[0], r[1], r[2], r[3]],
                        "details": details,
                        "ist_lesen_extern": ist_lesen_extern,
                        "ist_vergleichen_springen": ist_vergleichen_springen,
                    }));
                    if new_addr < 0 || new_addr >= groesse as i64 {
                        break;
                    }
                    adresse = new_addr as usize;
                    continue;
                } else {
                    details = format!("R{}({}) == R{}({}) → kein Sprung",
                        arg1 % 4, r[(arg1 % 4) as usize],
                        arg2 % 4, r[(arg2 % 4) as usize]);
                }
            }

            5 => { // KOPIEREN — read-only, nicht ausführen
                let anzahl = std::cmp::min(r[(arg1 % 4) as usize] as usize, 1024);
                let quelle = r[(arg2 % 4) as usize];
                let ziel_adr = r[(arg3 % 4) as usize];
                details = format!("Kopieren: {} Bytes von {} nach {} (simuliert)",
                    anzahl, quelle, ziel_adr);
            }

            6 => { // LESEN_EXTERN
                let extern_adr = ((zellende as u64).wrapping_add(r[(arg1 % 4) as usize]) as usize) % groesse;
                let wert = speicher[extern_adr];
                r[(arg3 % 4) as usize] = wert as u64;
                if wert == nahrung_wert {
                    energie += fress_energie; // Simuliert, Nahrung bleibt
                }
                details = format!("Extern gelesen: {} von Adresse {}", wert, extern_adr);
            }

            7 => { // SELBST
                r[(arg3 % 4) as usize] = startadresse as u64;
                details = format!("Startadresse {} → R{}", startadresse, arg3 % 4);
            }

            8 => { // SETZEN
                r[(arg3 % 4) as usize] = arg1 as u64;
                details = format!("{} → R{}", arg1, arg3 % 4);
            }

            9 => { // ENDE
                details = "Programm beendet".to_string();
                schritte.push(json!({
                    "schritt": schritt_nr,
                    "operation": opcode_name(befehl),
                    "register_nachher": [r[0], r[1], r[2], r[3]],
                    "details": details,
                    "ist_lesen_extern": ist_lesen_extern,
                    "ist_vergleichen_springen": ist_vergleichen_springen,
                }));
                break;
            }

            10 => { // SCHREIBEN_EXTERN — read-only
                let extern_adr = ((zellende as u64).wrapping_add(r[(arg3 % 4) as usize]) as usize) % groesse;
                let wert = r[(arg1 % 4) as usize] & 0xFF;
                details = format!("Extern schreiben: {} nach Adresse {} (simuliert)", wert, extern_adr);
            }

            _ => {
                details = format!("Unbekannter Opcode {}", befehl);
            }
        }

        schritte.push(json!({
            "schritt": schritt_nr,
            "operation": opcode_name(befehl),
            "register_nachher": [r[0], r[1], r[2], r[3]],
            "details": details,
            "ist_lesen_extern": ist_lesen_extern,
            "ist_vergleichen_springen": ist_vergleichen_springen,
        }));

        adresse += 4;
        if adresse >= groesse {
            break;
        }
    }

    json!({
        "adresse": startadresse,
        "genom_laenge": genom_laenge,
        "schritte": schritte,
    })
}

/// Berechnet Traces für bis zu 3 Organismen mit Wahrnehmungs-Muster.
pub fn berechne_traces(
    speicher: &[u8],
    pointer_positionen: &[(usize, usize)],
    groesse: usize,
    spawn_energie: i32,
    fress_energie: i32,
    nahrung_wert: u8,
) -> serde_json::Value {
    let mut traces: Vec<serde_json::Value> = Vec::new();
    let mut gefunden = 0;

    for &(start, laenge) in pointer_positionen {
        if gefunden >= 3 {
            break;
        }
        let len = laenge.min(1024);
        let mut bytes = Vec::with_capacity(len);
        for i in 0..len {
            bytes.push(speicher[(start + i) % groesse]);
        }
        if hat_wahrnehmungs_muster(&bytes) {
            traces.push(trace_organismus(
                speicher, start, laenge, groesse,
                spawn_energie, fress_energie, nahrung_wert,
            ));
            gefunden += 1;
        }
    }

    json!({"traces": traces})
}
