use std::sync::{Arc, Mutex};
use std::thread;
use std::collections::HashMap;

use base64::Engine;
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
    pub nahrung_prozent: f64,
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
            nahrung_prozent: 0.0,
            ticks_pro_sekunde: 0.0,
            laufzeit_sekunden: 0.0,
            ausgefuehrte_ops: [0; 11],
            ausgefuehrte_ops_total: 0,
            top_genome: Vec::new(),
            operations_verteilung: [0; 11],
            speicher_snapshot: vec![0u8; speicher_groesse],
            pointer_positionen: Vec::new(),
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
        "nahrung_prozent": state.nahrung_prozent,
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
        "nahrung_prozent": state.nahrung_prozent,
        "ticks_pro_sekunde": state.ticks_pro_sekunde,
        "laufzeit_sekunden": state.laufzeit_sekunden,
        "ausgefuehrte_ops": ops_to_json(&state.ausgefuehrte_ops),
        "ausgefuehrte_ops_total": state.ausgefuehrte_ops_total,
    })
}

fn build_weltkarte(state: &SimState) -> serde_json::Value {
    let b64 = base64::engine::general_purpose::STANDARD.encode(&state.speicher_snapshot);
    let positionen: Vec<serde_json::Value> = state.pointer_positionen.iter().map(|&(adr, len)| {
        json!({"adresse": adr, "laenge": len})
    }).collect();
    json!({
        "speicher_base64": b64,
        "groesse": state.speicher_snapshot.len(),
        "pointer_positionen": positionen,
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
