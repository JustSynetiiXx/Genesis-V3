"""
Genesis v3 — Dashboard (Schicht 3)
Web-Server auf Port 8080. Startet die Simulation im Hintergrund.
Starten: python3 dashboard.py
"""

import json
import time
import threading
import random
import os
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler

from welt import Welt, SPEICHER_GROESSE
from interpreter import ExecutionPointer, ENDE
from ur_replikator import erzeuge_ur_replikator
from beobachter import Beobachter

# === Simulations-Parameter ===
MAX_POINTER = 2000
VERFALL_RATE = 100
ANALYSE_INTERVALL = 2  # Sekunden

# === Globaler Zustand ===
sim_lock = threading.Lock()
welt = None
pointer = []
sim_daten = {
    "tick": 0,
    "geburten_gesamt": 0,
    "tode_gesamt": 0,
    "max_pointer": MAX_POINTER,
    "startzeit": 0,
}
letztes_ergebnis = {}
historie = []  # Letzte 900 Datenpunkte (30 min bei 2s)
sim_laeuft = True
letzter_blitz = None  # {"tick": ..., "zeitstempel": ..., "population_vor": ...}


def simulation_thread():
    """Simulation läuft in eigenem Thread."""
    global welt, pointer, sim_laeuft

    welt_obj = Welt()
    code = erzeuge_ur_replikator()
    for i, byte in enumerate(code):
        welt_obj.schreiben(i, byte)

    pointer_liste = [ExecutionPointer(0)]
    belegte_adressen = {0}

    with sim_lock:
        welt = welt_obj
        pointer.clear()
        pointer.extend(pointer_liste)
        sim_daten["startzeit"] = time.time()

    tick = 0

    while sim_laeuft:
        tick += 1
        neue_pointer = []
        platz_frei = MAX_POINTER - len(pointer_liste)

        for p in pointer_liste:
            energie_pro_org = 400000 // max(len(pointer_liste), 1)
            p.tick(welt_obj, energie_pro_org)

            if not p.aktiv:
                sim_daten["tode_gesamt"] += 1
                belegte_adressen.discard(p.startadresse)
                continue

            if p.leerlauf_ticks >= 10:
                p.aktiv = False
                sim_daten["tode_gesamt"] += 1
                belegte_adressen.discard(p.startadresse)
                continue

            if p.kopier_events > 0:
                p.kopier_events = 0

            p.mutationen.clear()

            for adr in p.neue_pointer:
                if adr in belegte_adressen:
                    continue
                if platz_frei - len(neue_pointer) <= 0:
                    break
                neuer = ExecutionPointer(adr)
                neue_pointer.append(neuer)
                belegte_adressen.add(adr)
                sim_daten["geburten_gesamt"] += 1
            p.neue_pointer.clear()

        pointer_liste = [p for p in pointer_liste if p.aktiv]
        pointer_liste.extend(neue_pointer)

        # Verfall
        for _ in range(VERFALL_RATE):
            welt_obj.schreiben((blitz_start + i) % SPEICHER_GROESSE, 0)

        # Katastrophen-Physik: Blitz
        if random.randint(1, 3000) == 1:
            pop_vor = len(pointer_liste)
            blitz_bytes = SPEICHER_GROESSE // 15
            blitz_start = random.randint(0, SPEICHER_GROESSE - 1)
            for i in range(blitz_bytes):
                welt_obj.schreiben((blitz_start + i) % SPEICHER_GROESSE, 0)
            global letzter_blitz
            letzter_blitz = {
                "tick": tick,
                "zeitstempel": time.strftime("%Y-%m-%d %H:%M:%S"),
                "population_vor": pop_vor,
            }
            # Meilenstein loggen
            try:
                meilenstein_pfad = "meilensteine.json"
                meilensteine = []
                if os.path.exists(meilenstein_pfad):
                    with open(meilenstein_pfad, "r") as f:
                        meilensteine = json.load(f)
                meilensteine.append({
                    "typ": "blitz",
                    "tick": tick,
                    "zeitstempel": letzter_blitz["zeitstempel"],
                    "population_vor": pop_vor,
                    "beschreibung": f"Blitz bei Tick {tick}: {pop_vor} Organismen vor dem Einschlag. Verluste in folgenden Ticks sichtbar.",
                })
                with open(meilenstein_pfad, "w") as f:
                    json.dump(meilensteine, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        sim_daten["tick"] = tick

        # Pointer-Referenz aktualisieren für Beobachter
        with sim_lock:
            pointer.clear()
            pointer.extend(pointer_liste)


def analyse_thread():
    """Analysiert alle ANALYSE_INTERVALL Sekunden."""
    global letztes_ergebnis

    while sim_laeuft:
        time.sleep(ANALYSE_INTERVALL)

        if welt is None:
            continue

        try:
            with sim_lock:
                pointer_kopie = list(pointer)

            beobachter = Beobachter(welt, pointer_kopie, sim_daten)
            ergebnis = beobachter.analysiere()

            laufzeit = time.time() - sim_daten["startzeit"]
            ergebnis["laufzeit_sekunden"] = round(laufzeit, 1)
            ergebnis["ticks_pro_sekunde"] = round(
                ergebnis["tick_nummer"] / max(laufzeit, 0.001), 0
            )

            letztes_ergebnis = ergebnis

            # Historie speichern (kompakt)
            historie.append({
                "tick": ergebnis["tick_nummer"],
                "zeit": round(laufzeit, 1),
                "population": ergebnis["population"],
                "geburten": ergebnis["geburten_gesamt"],
                "tode": ergebnis["tode_gesamt"],
                "diversitaet": ergebnis["diversitaet"],
                "shannon": ergebnis["diversitaet_shannon"],
                "genom_laenge_avg": ergebnis["genom_laenge_avg"],
                "speicher_prozent": ergebnis["speicher_belegt_prozent"],
                "lesen_extern": ergebnis["lesen_extern_anteil"],
                "schreiben_extern": ergebnis.get("schreiben_extern_anteil", 0),
            })

            # Max 360 Einträge behalten
            while len(historie) > 900:
                historie.pop(0)

        except Exception as e:
            print(f"Analyse-Fehler: {e}")


# === HTML Dashboard ===
DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>Genesis v3</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0a0a;color:#e0e0e0;font-family:'Courier New',monospace;font-size:14px;overflow-x:hidden}
.header{background:#111;padding:12px 16px;border-bottom:1px solid #222;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100}
.header h1{color:#00ffcc;font-size:18px;font-weight:bold}
.header .status{color:#666;font-size:12px}
.tabs{display:flex;background:#111;border-bottom:1px solid #222;overflow-x:auto;-webkit-overflow-scrolling:touch}
.tabs button{background:none;border:none;color:#666;padding:10px 16px;font-family:inherit;font-size:13px;cursor:pointer;white-space:nowrap;border-bottom:2px solid transparent}
.tabs button.active{color:#00ffcc;border-bottom-color:#00ffcc}
.tabs button:hover{color:#aaa}
.content{padding:16px;max-width:900px;margin:0 auto}
.panel{display:none}
.panel.active{display:block}
.card{background:#151515;border:1px solid #222;border-radius:8px;padding:16px;margin-bottom:12px}
.card h3{color:#00ffcc;font-size:14px;margin-bottom:10px;text-transform:uppercase;letter-spacing:1px}
.big-number{font-size:48px;color:#00ffcc;text-align:center;padding:20px 0;font-weight:bold}
.big-label{text-align:center;color:#666;font-size:12px;text-transform:uppercase;letter-spacing:2px}
.stat-row{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #1a1a1a}
.stat-row:last-child{border-bottom:none}
.stat-label{color:#888}
.stat-value{color:#e0e0e0;font-weight:bold}
.stat-value.cyan{color:#00ffcc}
.stat-value.warn{color:#ff6b6b}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.grid-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px}
.mini-card{background:#151515;border:1px solid #222;border-radius:6px;padding:12px;text-align:center}
.mini-card .val{font-size:24px;color:#00ffcc;font-weight:bold}
.mini-card .lbl{font-size:10px;color:#666;text-transform:uppercase;letter-spacing:1px;margin-top:4px}
.weltkarte-grid{display:grid;grid-template-columns:repeat(32,1fr);gap:1px;background:#000;border:1px solid #222;border-radius:4px;overflow:hidden;aspect-ratio:1}
.weltkarte-cell{aspect-ratio:1}
.bar-container{display:flex;align-items:center;gap:8px;margin:4px 0}
.bar-label{width:80px;text-align:right;color:#888;font-size:11px;flex-shrink:0}
.bar-track{flex:1;height:16px;background:#1a1a1a;border-radius:2px;overflow:hidden}
.bar-fill{height:100%;background:#00ffcc;border-radius:2px;transition:width 0.3s}
.bar-value{width:50px;color:#e0e0e0;font-size:11px;flex-shrink:0}
.genom-item{background:#111;border:1px solid #222;border-radius:4px;padding:10px;margin-bottom:8px;font-size:12px}
.genom-hex{color:#00ffcc;word-break:break-all;margin:6px 0}
.genom-stats{color:#888;font-size:11px}
canvas{width:100%;background:#111;border:1px solid #222;border-radius:4px}
.chart-container{margin-bottom:12px}
.chart-label{color:#666;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}
.btn{background:#1a1a1a;border:1px solid #333;color:#00ffcc;padding:10px 20px;border-radius:6px;font-family:inherit;font-size:13px;cursor:pointer;display:inline-block;text-decoration:none;margin:4px}
.btn:hover{background:#222;border-color:#00ffcc}
.legend{display:flex;gap:16px;margin:8px 0;font-size:11px;color:#888;flex-wrap:wrap}
.legend-dot{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px;vertical-align:middle}
.trace-table{width:100%;border-collapse:collapse;font-size:11px;margin-top:8px}
.trace-table th{background:#1a1a1a;color:#888;padding:4px 6px;text-align:left;border-bottom:1px solid #333}
.trace-table td{padding:4px 6px;border-bottom:1px solid #1a1a1a}
.trace-lesen-ext{background:#2a1a3a}
.trace-vergl-spr{background:#3a2a1a}
@media(max-width:600px){
 .grid-2{grid-template-columns:1fr}
 .big-number{font-size:36px}
 .header h1{font-size:15px}
}
</style>
</head>
<body>

<div class="header">
 <h1>GENESIS v3</h1>
 <div class="status" id="hdr-status">Verbinde...</div>
</div>

<div class="tabs" id="tabs">
 <button class="active" onclick="showTab('home')">HOME</button>
 <button onclick="showTab('weltkarte')">WELTKARTE</button>
 <button onclick="showTab('population')">POPULATION</button>
 <button onclick="showTab('genome')">GENOME</button>
 <button onclick="showTab('analyse')">ANALYSE</button>
 <button onclick="showTab('export')">EXPORT</button>
</div>

<!-- HOME -->
<div class="content">
<div class="panel active" id="tab-home">
 <div class="card">
  <div class="big-number" id="pop-count">—</div>
  <div class="big-label">Lebende Organismen</div>
 </div>
 <div class="grid-3" id="home-grid">
  <div class="mini-card"><div class="val" id="h-geburten">—</div><div class="lbl">Geburten</div></div>
  <div class="mini-card"><div class="val" id="h-tode">—</div><div class="lbl">Tode</div></div>
  <div class="mini-card"><div class="val" id="h-diversitaet">—</div><div class="lbl">Arten</div></div>
  <div class="mini-card"><div class="val" id="h-shannon">—</div><div class="lbl">Shannon</div></div>
  <div class="mini-card"><div class="val" id="h-speicher">—</div><div class="lbl">Speicher %</div></div>
  <div class="mini-card"><div class="val" id="h-genomlen">—</div><div class="lbl">Genom Avg</div></div>
  <div class="mini-card"><div class="val" id="h-lesen-ext">—</div><div class="lbl">LESEN_EXT %</div></div>
  <div class="mini-card"><div class="val" id="h-schreiben-ext">—</div><div class="lbl">SCHR_EXT %</div></div>
  <div class="mini-card"><div class="val" id="h-ticks">—</div><div class="lbl">Ticks</div></div>
  <div class="mini-card"><div class="val" id="h-tickrate">—</div><div class="lbl">Ticks/s</div></div>
 </div>
 <div class="card" style="margin-top:12px">
  <h3>Laufzeit</h3>
  <div class="stat-row"><span class="stat-label">Laufzeit</span><span class="stat-value" id="h-laufzeit">—</span></div>
  <div class="stat-row"><span class="stat-label">Population Max</span><span class="stat-value" id="h-popmax">—</span></div>
  <div class="stat-row"><span class="stat-label">Genom Min</span><span class="stat-value" id="h-genommin">—</span></div>
  <div class="stat-row"><span class="stat-label">Genom Max</span><span class="stat-value" id="h-genommax">—</span></div>
  <div class="stat-row" id="h-blitz-row" style="display:none"><span class="stat-label">Letzter Blitz</span><span class="stat-value" id="h-blitz" style="color:#ff6b6b">—</span></div>
 </div>
</div>

<!-- WELTKARTE -->
<div class="panel" id="tab-weltkarte">
 <div class="card">
  <h3>Weltkarte — 1 MB Speicher</h3>
  <div class="legend">
   <span><span class="legend-dot" style="background:#0a0a0a;border:1px solid #333"></span> Leer</span>
   <span><span class="legend-dot" style="background:#0a4a2a"></span> Teilweise</span>
   <span><span class="legend-dot" style="background:#00ffcc"></span> Voll</span>
   <span><span class="legend-dot" style="background:#ff6b6b"></span> Pointer</span>
  </div>
  <div class="weltkarte-grid" id="weltkarte"></div>
 </div>
</div>

<!-- POPULATION -->
<div class="panel" id="tab-population">
 <div class="card">
  <h3>Population</h3>
  <div class="chart-container"><canvas id="chart-pop" height="180"></canvas></div>
 </div>
 <div class="card">
  <h3>Geburten & Tode (kumulativ)</h3>
  <div class="chart-container"><canvas id="chart-demografie" height="180"></canvas></div>
 </div>
 <div class="card">
  <h3>Diversitaet (Arten)</h3>
  <div class="chart-container"><canvas id="chart-diversitaet" height="180"></canvas></div>
 </div>
 <div class="card">
  <h3>Durchschnittliche Genomlaenge</h3>
  <div class="chart-container"><canvas id="chart-genomlen" height="180"></canvas></div>
 </div>
</div>

<!-- GENOME -->
<div class="panel" id="tab-genome">
 <div class="card">
  <h3>LESEN_EXTERN Anteil</h3>
  <div class="big-number" id="g-lesen-ext">—</div>
  <div class="big-label">Prozent aller Opcodes — Zeigt ob Wahrnehmung entsteht</div>
 </div>
 <div class="card">
  <h3>Operations-Verteilung</h3>
  <div id="ops-bars"></div>
 </div>
 <div class="card">
  <h3>Top 10 Genome</h3>
  <div id="top-genome"></div>
 </div>
</div>

<!-- ANALYSE -->
<div class="panel" id="tab-analyse">
 <div class="card">
  <div class="big-number" id="a-count">—</div>
  <div class="big-label" id="a-label">Organismen mit Wahrnehmungs-Muster</div>
 </div>
 <div class="card">
  <h3>Top 5 Organismen mit Wahrnehmungs-Muster</h3>
  <div id="a-top5"><div style="color:#666">Keine Daten</div></div>
 </div>
 <div id="a-traces"></div>
 <div class="card">
  <h3>Meilenstein-Log</h3>
  <div id="a-meilensteine"><div style="color:#666">Keine Meilensteine</div></div>
 </div>
</div>

<!-- EXPORT -->
<div class="panel" id="tab-export">
 <div class="card">
  <h3>Daten Export</h3>
  <p style="color:#888;margin-bottom:16px">Lade einen Snapshot aller aktuellen Daten herunter.</p>
  <button class="btn" onclick="exportJSON()">JSON Snapshot</button>
  <button class="btn" onclick="exportSpeicher()">Speicher-Dump (Base64)</button>
 </div>
 <div class="card">
  <h3>API Endpoints</h3>
  <div class="stat-row"><span class="stat-label">Status</span><span class="stat-value">GET /api/status</span></div>
  <div class="stat-row"><span class="stat-label">Weltkarte</span><span class="stat-value">GET /api/weltkarte</span></div>
  <div class="stat-row"><span class="stat-label">Genome</span><span class="stat-value">GET /api/genome</span></div>
  <div class="stat-row"><span class="stat-label">Export</span><span class="stat-value">GET /api/export</span></div>
  <div class="stat-row"><span class="stat-label">Historie</span><span class="stat-value">GET /api/history</span></div>
  <div class="stat-row"><span class="stat-label">Analyse</span><span class="stat-value">GET /api/analyse</span></div>
  <div class="stat-row"><span class="stat-label">Analyse Export</span><span class="stat-value">GET /api/export_analyse</span></div>
  <div class="stat-row"><span class="stat-label">Trace</span><span class="stat-value">GET /api/trace</span></div>
 </div>
</div>
</div>

<script>
let currentTab='home';
let historyData=[];
let pointerBlocks=new Set();

let traceLoaded=false;
function showTab(name){
 currentTab=name;
 document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
 document.getElementById('tab-'+name).classList.add('active');
 document.querySelectorAll('.tabs button').forEach((b,i)=>{
  b.classList.toggle('active',['home','weltkarte','population','genome','analyse','export'][i]===name);
 });
 if(name==='population')drawCharts();
 if(name==='analyse'){traceLoaded=false;loadTrace();}
}
async function loadTrace(){
 if(traceLoaded)return;
 try{
  let res=await fetch('/api/trace');
  let d=await res.json();
  traceLoaded=true;
  renderTraces(d.traces||[]);
 }catch(e){}
}
function renderTraces(traces){
 let el=document.getElementById('a-traces');
 if(!traces.length){el.innerHTML='';return;}
 let html='';
 traces.forEach(t=>{
  html+='<div class="card"><h3>Trace Organismus @'+t.adresse+' ('+t.genom_laenge+' Bytes)</h3>';
  html+='<div style="overflow-x:auto"><table class="trace-table"><tr><th>#</th><th>Operation</th><th>R0</th><th>R1</th><th>R2</th><th>R3</th><th>Details</th></tr>';
  t.schritte.forEach(s=>{
   let cls='';
   if(s.ist_lesen_extern)cls=' class="trace-lesen-ext"';
   else if(s.ist_vergleichen_springen)cls=' class="trace-vergl-spr"';
   html+='<tr'+cls+'><td>'+s.schritt+'</td><td>'+s.operation+'</td>';
   html+='<td>'+s.register_nachher[0]+'</td><td>'+s.register_nachher[1]+'</td>';
   html+='<td>'+s.register_nachher[2]+'</td><td>'+s.register_nachher[3]+'</td>';
   html+='<td>'+s.details+'</td></tr>';
  });
  html+='</table></div></div>';
 });
 el.innerHTML=html;
}

function fmt(n){
 if(n===undefined||n===null)return'—';
 if(typeof n==='number'&&n>=1000)return n.toLocaleString('de-DE');
 return String(n);
}

function fmtTime(s){
 if(!s)return'—';
 let h=Math.floor(s/3600);
 let m=Math.floor((s%3600)/60);
 let sec=Math.floor(s%60);
 if(h>0)return h+'h '+m+'m';
 if(m>0)return m+'m '+sec+'s';
 return sec+'s';
}

function updateHome(d){
 document.getElementById('pop-count').textContent=fmt(d.population);
 document.getElementById('h-geburten').textContent=fmt(d.geburten_gesamt);
 document.getElementById('h-tode').textContent=fmt(d.tode_gesamt);
 document.getElementById('h-diversitaet').textContent=fmt(d.diversitaet);
 document.getElementById('h-shannon').textContent=d.diversitaet_shannon!==undefined?d.diversitaet_shannon.toFixed(2):'—';
 document.getElementById('h-speicher').textContent=d.speicher_belegt_prozent!==undefined?d.speicher_belegt_prozent.toFixed(1):'—';
 document.getElementById('h-genomlen').textContent=d.genom_laenge_avg!==undefined?d.genom_laenge_avg.toFixed(0):'—';
 document.getElementById('h-lesen-ext').textContent=d.lesen_extern_anteil!==undefined?d.lesen_extern_anteil.toFixed(2):'—';
 document.getElementById('h-schreiben-ext').textContent=d.schreiben_extern_anteil!==undefined?d.schreiben_extern_anteil.toFixed(2):'—';
 document.getElementById('h-ticks').textContent=fmt(d.tick_nummer);
 document.getElementById('h-tickrate').textContent=fmt(d.ticks_pro_sekunde);
 document.getElementById('h-laufzeit').textContent=fmtTime(d.laufzeit_sekunden);
 document.getElementById('h-popmax').textContent=fmt(d.population_max);
 document.getElementById('h-genommin').textContent=fmt(d.genom_laenge_min);
 document.getElementById('h-genommax').textContent=fmt(d.genom_laenge_max);
 document.getElementById('hdr-status').textContent='Tick '+fmt(d.tick_nummer)+' | '+fmt(d.population)+' Org.';
 if(d.letzter_blitz){
  document.getElementById('h-blitz-row').style.display='';
  document.getElementById('h-blitz').textContent='Tick '+fmt(d.letzter_blitz.tick)+' ('+d.letzter_blitz.population_vor+' Org. vorher)';
 }
}

function updateWeltkarte(d){
 let grid=document.getElementById('weltkarte');
 if(!grid.children.length){
  for(let i=0;i<1024;i++){
   let cell=document.createElement('div');
   cell.className='weltkarte-cell';
   grid.appendChild(cell);
  }
 }
 pointerBlocks.clear();
 if(d.pointer_positionen){
  d.pointer_positionen.forEach(a=>{pointerBlocks.add(Math.floor(a/1024));});
 }
 let karte=d.weltkarte||[];
 let cells=grid.children;
 for(let i=0;i<1024;i++){
  let v=karte[i]||0;
  let base;
  if(v===2){base='#00ffcc';}
  else if(v===1){base='#0a4a2a';}
  else{base='#0a0a0a';}
  if(pointerBlocks.has(i)){
   cells[i].style.background='linear-gradient('+base+','+base+'),linear-gradient(rgba(255,255,255,0.45),rgba(255,255,255,0.45))';
   cells[i].style.backgroundBlendMode='normal';
   cells[i].style.background=base;
   cells[i].style.boxShadow='inset 0 0 6px 2px rgba(255,255,255,0.7)';
  }else{
   cells[i].style.background=base;
   cells[i].style.boxShadow='none';
  }
 }
}

function updateGenome(d){
 // LESEN_EXTERN
 let el=document.getElementById('g-lesen-ext');
 el.textContent=d.lesen_extern_anteil!==undefined?d.lesen_extern_anteil.toFixed(2)+'%':'—';

 // Operations-Verteilung
 let ops=d.operations_verteilung||{};
 let maxOp=Math.max(1,...Object.values(ops));
 let barsHtml='';
 let namen=["NOOP","LESEN","SCHREIBEN","ADDIEREN","VERGL_SPR","KOPIEREN","LESEN_EXT","SELBST","SETZEN","ENDE","SCHR_EXT"];
 namen.forEach(name=>{
  let val=ops[name]||0;
  let pct=(val/maxOp*100).toFixed(0);
  let color=(name==='LESEN_EXT'||name==='SCHR_EXT')?'#ff6b6b':'#00ffcc';
  barsHtml+='<div class="bar-container">';
  barsHtml+='<span class="bar-label">'+name+'</span>';
  barsHtml+='<div class="bar-track"><div class="bar-fill" style="width:'+pct+'%;background:'+color+'"></div></div>';
  barsHtml+='<span class="bar-value">'+fmt(val)+'</span>';
  barsHtml+='</div>';
 });
 document.getElementById('ops-bars').innerHTML=barsHtml;

 // Top Genome
 let genomes=d.top_genome||[];
 let gHtml='';
 genomes.forEach((g,i)=>{
  gHtml+='<div class="genom-item">';
  gHtml+='<strong>#'+(i+1)+'</strong> — '+g.anzahl+'x ('+g.anteil+'%)';
  gHtml+='<div class="genom-hex">'+g.hex+'</div>';
  gHtml+='<div class="genom-stats">Laenge: '+g.laenge+' Bytes</div>';
  gHtml+='</div>';
 });
 document.getElementById('top-genome').innerHTML=gHtml||'<div style="color:#666">Keine Daten</div>';
}

function drawLine(ctx,w,h,data,key,color,maxV){
 if(!data.length)return;
 let vals=data.map(d=>d[key]||0);
 if(!maxV)maxV=Math.max(1,...vals);
 ctx.strokeStyle=color;
 ctx.lineWidth=2;
 ctx.beginPath();
 for(let i=0;i<vals.length;i++){
  let x=(i/(vals.length-1||1))*w;
  let y=h-((vals[i]/maxV)*h*0.85)-h*0.05;
  if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);
 }
 ctx.stroke();
 // Labels
 ctx.fillStyle='#666';ctx.font='10px monospace';
 ctx.fillText(fmt(Math.round(maxV)),4,14);
 ctx.fillText('0',4,h-4);
 if(data.length>0){
  ctx.fillText('T'+fmt(data[0].tick),4,h-14);
  ctx.textAlign='right';
  ctx.fillText('T'+fmt(data[data.length-1].tick),w-4,h-14);
  ctx.textAlign='left';
 }
}

function drawCharts(){
 let data=historyData;
 if(!data.length)return;

 // Population
 let c1=document.getElementById('chart-pop');
 let ctx1=c1.getContext('2d');
 c1.width=c1.offsetWidth;c1.height=180;
 ctx1.clearRect(0,0,c1.width,c1.height);
 drawLine(ctx1,c1.width,c1.height,data,'population','#00ffcc');

 // Demografie
 let c2=document.getElementById('chart-demografie');
 let ctx2=c2.getContext('2d');
 c2.width=c2.offsetWidth;c2.height=180;
 ctx2.clearRect(0,0,c2.width,c2.height);
 let maxDem=Math.max(1,...data.map(d=>Math.max(d.geburten||0,d.tode||0)));
 drawLine(ctx2,c2.width,c2.height,data,'geburten','#00ffcc',maxDem);
 drawLine(ctx2,c2.width,c2.height,data,'tode','#ff6b6b',maxDem);

 // Diversitaet
 let c3=document.getElementById('chart-diversitaet');
 let ctx3=c3.getContext('2d');
 c3.width=c3.offsetWidth;c3.height=180;
 ctx3.clearRect(0,0,c3.width,c3.height);
 drawLine(ctx3,c3.width,c3.height,data,'diversitaet','#00ffcc');

 // Genomlaenge
 let c4=document.getElementById('chart-genomlen');
 let ctx4=c4.getContext('2d');
 c4.width=c4.offsetWidth;c4.height=180;
 ctx4.clearRect(0,0,c4.width,c4.height);
 drawLine(ctx4,c4.width,c4.height,data,'genom_laenge_avg','#00ffcc');
}

function blobDownload(data,filename){
 let str=JSON.stringify(data,null,2);
 let blob=new Blob([str],{type:'application/json'});
 let url=URL.createObjectURL(blob);
 let a=document.createElement('a');
 a.href=url;a.download=filename;
 document.body.appendChild(a);a.click();
 document.body.removeChild(a);
 URL.revokeObjectURL(url);
}

async function exportJSON(){
 try{
  let res=await fetch('/api/export');
  let data=await res.json();
  blobDownload(data,'genesis_export.json');
 }catch(e){alert('Export fehlgeschlagen');}
}

async function exportSpeicher(){
 try{
  let res=await fetch('/api/export?speicher=1');
  let data=await res.json();
  blobDownload(data,'genesis_speicher.json');
 }catch(e){alert('Export fehlgeschlagen');}
}

function updateAnalyse(d){
 document.getElementById('a-count').textContent=d.anzahl+' ('+d.prozent+'%)';
 document.getElementById('a-label').textContent=d.anzahl+' Organismen mit Wahrnehmungs-Muster ('+d.prozent+'%)';
 let top5=d.top5||[];
 let html='';
 if(top5.length===0){html='<div style="color:#666">Kein Organismus mit Wahrnehmungs-Muster gefunden</div>';}
 else{top5.forEach((o,i)=>{
  html+='<div class="genom-item">';
  html+='<strong>#'+(i+1)+'</strong> Adresse: '+o.adresse+' ('+o.genom_laenge+' Bytes)';
  html+='<div class="genom-hex">'+o.code_ausschnitt+'</div>';
  html+='</div>';
 });}
 document.getElementById('a-top5').innerHTML=html;
 let ms=d.meilensteine||[];
 let mHtml='';
 if(ms.length===0){mHtml='<div style="color:#666">Keine Meilensteine</div>';}
 else{ms.forEach(m=>{
  mHtml+='<div class="stat-row"><span class="stat-label">'+m.zeitstempel+' (Tick '+fmt(m.tick)+')</span><span class="stat-value">'+m.beschreibung+'</span></div>';
 });}
 document.getElementById('a-meilensteine').innerHTML=mHtml;
}

async function refresh(){
 try{
  let [statusRes,histRes,analyseRes]=await Promise.all([
   fetch('/api/status'),
   fetch('/api/history'),
   fetch('/api/analyse')
  ]);
  let d=await statusRes.json();
  let h=await histRes.json();
  let a=await analyseRes.json();
  historyData=h;
  updateHome(d);
  updateWeltkarte(d);
  updateGenome(d);
  updateAnalyse(a);
  if(currentTab==='population')drawCharts();
 }catch(e){
  document.getElementById('hdr-status').textContent='Verbindungsfehler';
 }
}

refresh();
setInterval(refresh,2000);
</script>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Kein Access-Log

    def _json_response(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _html_response(self, html):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        query = self.path.split("?")[1] if "?" in self.path else ""

        if path == "/":
            self._html_response(DASHBOARD_HTML)

        elif path == "/api/status":
            daten = dict(letztes_ergebnis) if letztes_ergebnis else {}
            if letzter_blitz:
                daten["letzter_blitz"] = letzter_blitz
            self._json_response(daten)

        elif path == "/api/weltkarte":
            karte = letztes_ergebnis.get("weltkarte", [])
            positionen = letztes_ergebnis.get("pointer_positionen", [])
            self._json_response({"weltkarte": karte, "pointer_positionen": positionen})

        elif path == "/api/genome":
            self._json_response({
                "top_genome": letztes_ergebnis.get("top_genome", []),
                "operations_verteilung": letztes_ergebnis.get("operations_verteilung", {}),
                "lesen_extern_anteil": letztes_ergebnis.get("lesen_extern_anteil", 0),
            })

        elif path == "/api/export":
            daten = dict(letztes_ergebnis) if letztes_ergebnis else {}
            daten["historie"] = list(historie)
            if "speicher=1" in query and welt is not None:
                daten["speicher_base64"] = base64.b64encode(
                    bytes(welt.speicher)
                ).decode("ascii")
            self._json_response(daten)

        elif path == "/api/history":
            self._json_response(list(historie))

        elif path == "/api/analyse":
            try:
                with sim_lock:
                    pointer_kopie = list(pointer)
                if welt is not None:
                    beobachter = Beobachter(welt, pointer_kopie, sim_daten)
                    ergebnis = beobachter.analyse_wahrnehmung()
                    self._json_response(ergebnis)
                else:
                    self._json_response({"anzahl": 0, "gesamt": 0, "prozent": 0, "top5": [], "meilensteine": []})
            except Exception as e:
                self._json_response({"error": str(e)})

        elif path == "/api/trace":
            try:
                with sim_lock:
                    pointer_kopie = list(pointer)
                if welt is not None:
                    beobachter = Beobachter(welt, pointer_kopie, sim_daten)
                    ergebnis = beobachter.trace_organismen()
                    self._json_response(ergebnis)
                else:
                    self._json_response({"traces": []})
            except Exception as e:
                self._json_response({"error": str(e), "traces": []})

        elif path == "/api/export_analyse":
            try:
                with sim_lock:
                    pointer_kopie = list(pointer)
                if welt is not None:
                    beobachter = Beobachter(welt, pointer_kopie, sim_daten)
                    ergebnis = beobachter.analyse_wahrnehmung()
                else:
                    ergebnis = {"anzahl": 0, "gesamt": 0, "prozent": 0, "top5": [], "meilensteine": []}
                body = json.dumps(ergebnis, ensure_ascii=False, indent=2).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Disposition", 'attachment; filename="genesis_analyse.json"')
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self._json_response({"error": str(e)})

        else:
            self.send_response(404)
            self.end_headers()


def main():
    global sim_laeuft

    print("=" * 60)
    print("  Genesis v3 — Dashboard")
    print("  http://0.0.0.0:8080")
    print("=" * 60)
    print()
    print("Simulation startet im Hintergrund...")

    # Simulation starten
    t_sim = threading.Thread(target=simulation_thread, daemon=True)
    t_sim.start()

    # Analyse starten
    t_ana = threading.Thread(target=analyse_thread, daemon=True)
    t_ana.start()

    # HTTP Server
    server = HTTPServer(("0.0.0.0", 8080), DashboardHandler)
    print("Dashboard bereit auf Port 8080")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sim_laeuft = False
        server.server_close()
        print()
        print(f"Gestoppt. Tick: {sim_daten['tick']:,}")


if __name__ == "__main__":
    main()
