"""
Dashboard profesional con ECharts interactivos.
Reemplaza los PNGs estaticos por graficos interactivos (barra, scatter, heatmap, dual-axis).
"""
import pandas as pd
import numpy as np
import os, json, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _theme import P, CAND_COLORS, FONT_FAMILY, FONT_MONO, FONT_MONO_JS
from _theme import CSS_RESET, CSS_CARD, CSS_BUTTON, CSS_INPUT, CSS_TABLE, CSS_BADGE, CSS_STAT_CARD, CSS_SECTION_NAV, CSS_ANIMATIONS, BP
from _theme import YLORRD, RDBU, PURPLES
from _utils import fix_name

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(BASE, 'data', 'processed')
OUT = os.path.join(BASE, 'outputs')
os.makedirs(OUT, exist_ok=True)

# ─── DATOS ───
votos = pd.read_csv(os.path.join(PROC, 'votos_por_upz.csv'))
votos['CANNOMBRE'] = votos['CANNOMBRE'].apply(fix_name)

total_votos = int(votos['VOTOS'].sum())
total_upzs = votos['UPLCODIGO'].nunique()
total_localidades = votos['LOCNOMBRE'].nunique()
total_candidatos = votos['CANNOMBRE'].nunique()

cand_order = (
    votos.groupby('CANNOMBRE')['VOTOS'].sum()
    .sort_values(ascending=False).index.tolist()
)
ganador_global = cand_order[0]

# ─── TABLA RESUMEN ───
resumen = []
for upz in votos['UPLCODIGO'].unique():
    sub = votos[votos['UPLCODIGO'] == upz]
    total = int(sub['TOTAL_UPZ'].iloc[0])
    uplnombre = sub['UPLNOMBRE'].iloc[0]
    locnombre = sub['LOCNOMBRE'].iloc[0]
    results = sub.sort_values('VOTOS', ascending=False)
    g = results.iloc[0]
    s = results.iloc[1]
    diff = int(g['VOTOS'] - s['VOTOS'])
    margen = round(diff / total * 100, 2) if total > 0 else 0
    if margen >= 20: cat = 'Seguro'
    elif margen >= 5: cat = 'Competido'
    else: cat = 'Empate'
    resumen.append({
        'cod': upz, 'nom': uplnombre, 'loc': locnombre,
        'total': total, 'ganador': g['CANNOMBRE'],
        'votos_g': int(g['VOTOS']), 'pct_g': round(g['PORCENTAJE'], 1),
        'segundo': s['CANNOMBRE'], 'votos_s': int(s['VOTOS']),
        'diff': diff, 'margen': margen, 'cat': cat,
    })
resumen.sort(key=lambda x: x['total'], reverse=True)
table_json = json.dumps(resumen, ensure_ascii=False)
localidades = sorted(set(r['loc'] for r in resumen))

# ─── DATOS PARA ECHARTS ───
# 1. Votos totales por candidato
stats_cand = []
for c in cand_order:
    sv = int(votos[votos['CANNOMBRE'] == c]['VOTOS'].sum())
    sp = round(sv / total_votos * 100, 1)
    stats_cand.append({'c': c, 'v': sv, 'p': sp})
stats_cand_json = json.dumps(stats_cand, ensure_ascii=False)

# 2. Top 10 UPZ - distribucion %
top10 = resumen[:10]
top_cands_short = cand_order[:5]
upz_dist = []
for r in top10:
    sub = votos[votos['UPLCODIGO'] == r['cod']]
    row = {'upz': r['nom']}
    otros = 0
    for c in top_cands_short:
        v = int(sub[sub['CANNOMBRE'] == c]['VOTOS'].sum())
        row[c] = round(v / r['total'] * 100, 1) if r['total'] > 0 else 0
        otros += v
    row['Otros'] = round((r['total'] - otros) / r['total'] * 100, 1) if r['total'] > 0 else 0
    upz_dist.append(row)
upz_dist_json = json.dumps(upz_dist, ensure_ascii=False)

# 3. Matriz candidato x localidad
loc_list = sorted(votos['LOCNOMBRE'].unique())
matriz = []
for i, cand in enumerate(cand_order):
    for j, loc in enumerate(loc_list):
        sub = votos[(votos['CANNOMBRE'] == cand) & (votos['LOCNOMBRE'] == loc)]
        if len(sub) > 0:
            pct = round(sub['PORCENTAJE'].mean(), 1)
        else:
            pct = 0
        matriz.append([j, i, pct])
matriz_json = json.dumps(matriz)
loc_list_json = json.dumps(loc_list, ensure_ascii=False)
cand_names_json = json.dumps(cand_order, ensure_ascii=False)

# 4. Brecha Cepeda vs Espriella por UPZ (top 30 sorted by diff)
brecha = []
for r in resumen:
    brecha.append({
        'upz': r['nom'],
        'cepeda': r['pct_g'] if r['ganador'] == cand_order[0] else round(r['votos_s'] / r['total'] * 100, 1) if r['total'] > 0 else 0,
        'espriella': r['pct_g'] if r['ganador'] == cand_order[1] else round(r['votos_s'] / r['total'] * 100, 1) if r['total'] > 0 else 0,
    })
brecha.sort(key=lambda x: abs(x['cepeda'] - x['espriella']), reverse=True)
brecha = brecha[:30]
brecha.sort(key=lambda x: x['cepeda'] - x['espriella'])
brecha_json = json.dumps(brecha, ensure_ascii=False)

# ─── COMPARATIVO 2022-2026 ───
comp_loc = json.load(open(os.path.join(PROC, 'comparativo_localidad.json'), encoding='utf-8'))
for r in comp_loc:
    r['delta_petro_1v_pp_pct'] = round(float(r.get('delta_petro_1v_pp', 0)) * 100, 1)
    r['votos_petro_1v22'] = int(r.get('votos_petro_1v22', 0))
    r['votos_cepeda_1v26'] = int(r.get('votos_cepeda_1v26', 0))
comp_loc.sort(key=lambda x: x['delta_petro_1v_pp_pct'])
comp_json = json.dumps(comp_loc, ensure_ascii=False)

# ─── SCATTER DATA: Petro2022 vs Cepeda2026 ───
scatter_data = [[
    round(r['pct_petro_1v22'] * 100, 1),
    round(r['pct_cepeda_1v26'] * 100, 1),
    r['delta_petro_1v_pp_pct'],
    r['Localidad']
] for r in comp_loc]
scatter_json = json.dumps(scatter_data)

# ─── DUAL-AXIS DATA: % por localidad ───
dual_data = [{
    'loc': r['Localidad'],
    'petro': round(r['pct_petro_1v22'] * 100, 1),
    'cepeda': round(r['pct_cepeda_1v26'] * 100, 1),
    'delta': r['delta_petro_1v_pp_pct'],
} for r in comp_loc]
dual_json = json.dumps(dual_data, ensure_ascii=False)

# ─── COMPARATIVO COMPLETO: todos los candidatos 2022 vs 2026 ───
# Pares comparables: [etiqueta, col22, col26]
COMP_PAIRS = [
    ('Petro 22 vs Cepeda 26', 'pct_petro_1v22', 'pct_cepeda_1v26'),
    ('Hernandez 22 vs Espriella 26', '% Hernández 1v', '% Espriella 26'),
    ('Gutierrez 22 vs Fajardo 26', '% Gutiérrez 1v', '% Fajardo 26'),
    ('Petro 2v 22 vs Cepeda 26', '% Petro 2v', 'pct_cepeda_1v26'),
]

full_comp = []
for r in comp_loc:
    row = {'loc': r['Localidad']}
    for label, col22, col26 in COMP_PAIRS:
        v22 = r.get(col22, 0)
        v26 = r.get(col26, 0)
        v22_pct = round(float(v22) * 100, 1) if v22 else 0
        v26_pct = round(float(v26) * 100, 1) if v26 else 0
        delta = round(v26_pct - v22_pct, 1)
        row[f'{label}_22'] = v22_pct
        row[f'{label}_26'] = v26_pct
        row[f'{label}_delta'] = delta
    full_comp.append(row)
full_comp_json = json.dumps(full_comp, ensure_ascii=False)
comp_pairs_json = json.dumps([p[0] for p in COMP_PAIRS], ensure_ascii=False)

# ─── CONSTANTES TEMPLATE ───
ESTILOS = CSS_RESET + CSS_CARD + CSS_BUTTON + CSS_INPUT + CSS_TABLE + CSS_BADGE + CSS_STAT_CARD + CSS_SECTION_NAV + CSS_ANIMATIONS

# ─── HTML ───
html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Elecciones Presidenciales 2026 - Bogota D.C.</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
{ESTILOS}
body {{ padding-bottom:48px; }}
.hero {{ background:linear-gradient(135deg, {P['primary']} 0%, #8E0000 50%, {P['primary']} 100%);
  color:white; padding:32px 24px; position:relative; overflow:hidden; }}
.hero::after {{ content:''; position:absolute; top:0; right:0; width:300px; height:100%;
  background:linear-gradient(135deg, transparent 30%, rgba(249,168,37,0.15) 100%); }}
.hero h1 {{ font-size:28px; font-weight:700; letter-spacing:-0.5px; position:relative; z-index:1; }}
.hero p {{ font-size:14px; opacity:0.8; margin-top:4px; position:relative; z-index:1; }}
.hero-meta {{ display:flex; gap:16px; margin-top:12px; flex-wrap:wrap; position:relative; z-index:1; }}
.hero-meta span {{ font-size:12px; opacity:0.7; }}
.container {{ max-width:1400px; margin:0 auto; padding:0 24px; }}

.section {{ margin-top:24px; }}
.section-title {{ font-size:18px; font-weight:600; color:{P['text']}; margin-bottom:16px; display:flex; align-items:center; gap:8px; }}

/* Stats grid */
.stats-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:24px; }}
@media (max-width:{BP['md']}) {{ .stats-grid {{ grid-template-columns:repeat(2,1fr); }} }}
@media (max-width:{BP['sm']}) {{ .stats-grid {{ grid-template-columns:1fr; }} }}

/* Chart grid */
.chart-row {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:16px; }}
.chart-row .card-body {{ padding:16px; }}
.chart-box {{ width:100%; height:400px; }}
.chart-tall {{ height:500px; }}
@media (max-width:{BP['md']}) {{ .chart-row {{ grid-template-columns:1fr; }} }}

/* Full width sections */
.full-card {{ background:white; border-radius:12px; border:1px solid {P['border-light']};
  box-shadow:0 1px 3px {P['shadow']}; padding:24px; margin-bottom:20px; }}

/* Map iframe */
.map-frame {{ width:100%; height:620px; border:none; border-radius:8px; }}
@media (max-width:{BP['sm']}) {{ .map-frame {{ height:400px; }} }}

/* Table controls */
.table-controls {{ display:flex; gap:12px; margin-bottom:16px; flex-wrap:wrap; align-items:center; }}
.table-controls .input {{ flex:1; min-width:180px; }}
.table-controls .select {{ min-width:150px; }}

/* ECharts tooltip override */
.echarts-tooltip {{ font-family:{FONT_FAMILY} !important; }}

/* Footer */
.footer {{ text-align:center; padding:24px; color:{P['text-hint']}; font-size:12px; }}

/* Tab sections */
.section {{ display:none; }}
.section.active {{ display:block; }}

/* Sticky nav */
.section-nav-wrap {{ position:sticky; top:0; z-index:100; margin-bottom:24px; }}
</style>
</head>
<body>

<div class="hero">
  <h1>Elecciones Presidenciales 2026</h1>
  <p>Primera vuelta &middot; Resultados por UPZ en Bogota D.C.</p>
  <div class="hero-meta">
    <span>Datos: Registraduria Nacional + IDECA</span>
    <span>110 UPZs &middot; 20 localidades &middot; 13 candidatos</span>
    <span>Procesado: {pd.Timestamp.now().strftime('%d %B %Y')}</span>
  </div>
</div>

<div class="container">

<div class="section-nav-wrap">
  <nav class="section-nav" id="section-nav">
    <a href="#" data-section="resumen" class="active">Resumen</a>
    <a href="#" data-section="mapa">Mapa</a>
    <a href="#" data-section="graficos">Graficos</a>
    <a href="#" data-section="detalle">Detalle UPZ</a>
    <a href="#" data-section="comparativo">Comparativo 22-26</a>
  </nav>
</div>

<!-- ═══ RESUMEN ═══ -->
<section id="resumen" class="section">
  <div class="stats-grid">
    <div class="stat-card anim-fade-up anim-delay-1">
      <div class="stat-icon primary">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20V10"/><path d="M18 20V4"/><path d="M6 20v-4"/></svg>
      </div>
      <div class="stat-num">{total_votos:,}</div>
      <div class="stat-label">Votos procesados</div>
      <div class="stat-bar"><div class="stat-bar-fill" style="width:100%;background:{P['primary']}"></div></div>
    </div>
    <div class="stat-card anim-fade-up anim-delay-2">
      <div class="stat-icon accent">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
      </div>
      <div class="stat-num">{total_upzs}</div>
      <div class="stat-label">UPZs</div>
      <div class="stat-bar"><div class="stat-bar-fill" style="width:100%;background:{P['accent']}"></div></div>
    </div>
    <div class="stat-card anim-fade-up anim-delay-3">
      <div class="stat-icon success">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/></svg>
      </div>
      <div class="stat-num">{total_localidades}</div>
      <div class="stat-label">Localidades</div>
      <div class="stat-bar"><div class="stat-bar-fill" style="width:{total_localidades/20*100}%;background:{P['success']}"></div></div>
    </div>
    <div class="stat-card anim-fade-up anim-delay-4">
      <div class="stat-icon warning">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
      </div>
      <div class="stat-num">{total_candidatos}</div>
      <div class="stat-label">Candidatos</div>
      <div class="stat-bar"><div class="stat-bar-fill" style="width:100%;background:{P['warning']}"></div></div>
    </div>
  </div>
</section>

<!-- ═══ MAPA ═══ -->
<section id="mapa" class="section">
  <div class="section-title">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{P['primary']}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/></svg>
    Mapa interactivo
    <span class="badge badge-primary">5 modos + multi-select + toggle UPZ/Localidad</span>
  </div>
  <div class="full-card" style="padding:0;overflow:hidden">
    <iframe class="map-frame" data-src="mapa_bogota.html" title="Mapa electoral interactivo"></iframe>
  </div>
</section>

<!-- ═══ GRAFICOS ═══ -->
<section id="graficos" class="section">
  <div class="section-title">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{P['primary']}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
    Graficos interactivos
  </div>

  <div class="chart-row">
    <div class="card">
      <div class="card-header"><div class="card-title">Votos totales por candidato</div><div class="card-subtitle">Distribucion del voto en Bogota D.C.</div></div>
      <div class="card-body"><div class="chart-box" id="chart-candidatos"></div></div>
    </div>
    <div class="card">
      <div class="card-header"><div class="card-title">Top 10 UPZ - Distribucion porcentual</div><div class="card-subtitle">Composicion del voto en las UPZs con mas votantes</div></div>
      <div class="card-body"><div class="chart-box" id="chart-upz-dist"></div></div>
    </div>
  </div>

  <div class="chart-row">
    <div class="card">
      <div class="card-header"><div class="card-title">Matriz candidato por localidad</div><div class="card-subtitle">Porcentaje de votacion por candidato en cada localidad</div></div>
      <div class="card-body"><div class="chart-box chart-tall" id="chart-matriz"></div></div>
    </div>
    <div class="card">
      <div class="card-header"><div class="card-title">Brecha Cepeda vs Espriella</div><div class="card-subtitle">Diferencia porcentual en las 30 UPZs mas polarizadas</div></div>
      <div class="card-body"><div class="chart-box chart-tall" id="chart-brecha"></div></div>
    </div>
  </div>

  <div class="chart-row">
    <div class="card">
      <div class="card-header"><div class="card-title">Comparativo 2022 vs 2026</div><div class="card-subtitle">Correlacion entre el voto de Petro (2022) y Cepeda (2026) por localidad</div></div>
      <div class="card-body"><div class="chart-box" id="chart-scatter"></div></div>
    </div>
    <div class="card">
      <div class="card-header"><div class="card-title">Evolucion por localidad</div><div class="card-subtitle">Petro 2022 vs Cepeda 2026 y delta en puntos porcentuales</div></div>
      <div class="card-body"><div class="chart-box" id="chart-dual"></div></div>
    </div>
  </div>
</section>

<!-- ═══ TABLA UPZ ═══ -->
<section id="detalle" class="section">
  <div class="section-title">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{P['primary']}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
    Detalle por UPZ
    <span class="badge badge-neutral" id="row-count">110 UPZs</span>
  </div>
  <div class="full-card">
    <div class="table-controls">
      <input class="input" type="text" id="search-input" placeholder="Buscar UPZ o codigo..." onkeyup="filterTable()">
      <select class="select" id="loc-filter" onchange="filterTable()">
        <option value="">Todas las localidades</option>
        {"".join(f'<option value="{l}">{l}</option>' for l in localidades)}
      </select>
      <select class="select" id="cat-filter" onchange="filterTable()">
        <option value="">Todas las categorias</option>
        <option value="Seguro">Seguro</option>
        <option value="Competido">Competido</option>
        <option value="Empate">Empate tecnico</option>
      </select>
    </div>
    <div class="table-wrap">
      <table id="upz-table">
        <thead>
          <tr>
            <th onclick="sortTable(0)">UPZ <span class="sort-arrow">&#9650;</span></th>
            <th onclick="sortTable(1)">Nombre <span class="sort-arrow">&#9650;</span></th>
            <th onclick="sortTable(2)">Localidad <span class="sort-arrow">&#9650;</span></th>
            <th onclick="sortTable(3)">Votos <span class="sort-arrow">&#9650;</span></th>
            <th onclick="sortTable(4)">Ganador <span class="sort-arrow">&#9650;</span></th>
            <th onclick="sortTable(5)">% <span class="sort-arrow">&#9650;</span></th>
            <th onclick="sortTable(6)">Segundo <span class="sort-arrow">&#9650;</span></th>
            <th onclick="sortTable(7)">Diferencia <span class="sort-arrow">&#9650;</span></th>
            <th onclick="sortTable(8)">Margen <span class="sort-arrow">&#9650;</span></th>
            <th onclick="sortTable(9)">Categoria <span class="sort-arrow">&#9650;</span></th>
          </tr>
        </thead>
        <tbody id="table-body"></tbody>
      </table>
    </div>
  </div>
</section>

<!-- ═══ COMPARATIVO ═══ -->
<section id="comparativo" class="section">
  <div class="section-title">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{P['primary']}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
    Comparativo 2022-2026
    <span class="badge badge-primary" id="comp-pair-badge">Petro 22 vs Cepeda 26</span>
  </div>

  <div class="stats-grid" style="margin-bottom:16px">
    <div class="stat-card">
      <div class="stat-icon warning">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>
      </div>
      <div class="stat-num-sm" id="comp-mejor">-</div>
      <div class="stat-label">Mejor desempeno</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon error">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/></svg>
      </div>
      <div class="stat-num-sm" id="comp-peor">-</div>
      <div class="stat-label">Peor desempeno</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon primary">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
      </div>
      <div class="stat-num-sm" id="comp-pct22">-</div>
      <div class="stat-label">% 2022 citywide</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon accent">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
      </div>
      <div class="stat-num-sm" id="comp-pct26">-</div>
      <div class="stat-label">% 2026 citywide</div>
    </div>
  </div>

  <div class="chart-row">
    <div class="card">
      <div class="card-header">
        <div class="card-title">Comparacion de pares</div>
        <div class="card-subtitle">2022 vs 2026 para cada par de candidatos comparable</div>
      </div>
      <div class="card-body"><div class="chart-box" id="chart-comp-heatmap"></div></div>
    </div>
    <div class="card">
      <div class="card-header">
        <div class="card-title">Distribucion de deltas</div>
        <div class="card-subtitle">Rango de variacion (pp) entre 2022 y 2026 para cada par</div>
      </div>
      <div class="card-body"><div class="chart-box" id="chart-comp-box"></div>
        <div style="padding:8px 16px 16px;font-size:11px;color:#9E9E9E;line-height:1.4">Cada caja muestra la distribucion del delta entre 2022 y 2026. La linea central es la mediana; los extremos son el minimo y maximo. La linea punteada marca 0 pp (sin cambio).</div></div>
    </div>
  </div>

  <div class="full-card">
    <div class="table-controls" style="justify-content:space-between">
      <div style="display:flex;gap:8px;align-items:center">
        <label style="font-size:12px;font-weight:500;color:{P['text-secondary']}">Par a comparar:</label>
        <select class="select" id="comp-pair-select" onchange="switchComparativo(this.value)" style="min-width:220px">
          {"".join(f'<option value="{i}">{p[0]}</option>' for i, p in enumerate(COMP_PAIRS))}
        </select>
      </div>
      <span class="badge badge-neutral" id="comp-count">20 localidades</span>
    </div>
    <div class="table-wrap" style="max-height:420px">
      <table id="comp-table">
        <thead>
          <tr>
            <th onclick="sortComp(0)">Localidad</th>
            <th onclick="sortComp(1)" id="comp-th22">% 2022</th>
            <th onclick="sortComp(2)" id="comp-th26">% 2026</th>
            <th onclick="sortComp(3)">Delta (pp)</th>
            <th onclick="sortComp(4)">Votos 2022</th>
            <th onclick="sortComp(5)">Votos 2026</th>
            <th onclick="sortComp(6)">Situacion</th>
          </tr>
        </thead>
        <tbody id="comp-body"></tbody>
      </table>
    </div>
  </div>
</section>

</div>

<div class="footer">
  Generado con datos de la Registraduria Nacional (2026) y geografia de IDECA. &middot; Analisis Electoral Bogota 2026
</div>

<script>
// ─── DATOS EMBEBIDOS ───
var tableData = {table_json};
var statsCand = {stats_cand_json};
var upzDist = {upz_dist_json};
var matrizData = {matriz_json};
var locList = {loc_list_json};
var candNames = {cand_names_json};
var brechaData = {brecha_json};
var compData = {comp_json};
var fullComp = {full_comp_json};
var compPairs = {comp_pairs_json};
var scatterData = {scatter_json};
var dualData = {dual_json};
var candColors = {json.dumps(dict(zip(cand_order, CAND_COLORS)), ensure_ascii=False)};

// ─── TABLA UPZ ───
var sortCol = -1;
var sortAsc = true;
function renderTable(data) {{
  var tbody = document.getElementById('table-body');
  tbody.innerHTML = data.map(function(r) {{
    var catClass = 'badge badge-' + (r.cat === 'Seguro' ? 'success' : r.cat === 'Competido' ? 'warning' : 'error');
    return '<tr>' +
      '<td style="font-family:{FONT_MONO_JS};font-size:12px;color:{P['text-secondary']}">' + r.cod + '</td>' +
      '<td><strong>' + r.nom + '</strong></td>' +
      '<td>' + r.loc + '</td>' +
      '<td style="text-align:right;font-family:{FONT_MONO_JS}">' + r.total.toLocaleString() + '</td>' +
      '<td><span style="display:inline-block;width:10px;height:10px;border-radius:2px;' +
        'background:' + (candColors[r.ganador] || '#ccc') + ';margin-right:6px"></span>' + r.ganador + '</td>' +
      '<td style="text-align:right;font-family:{FONT_MONO_JS}">' + r.pct_g + '%</td>' +
      '<td>' + r.segundo + '</td>' +
      '<td style="text-align:right;font-family:{FONT_MONO_JS}">' + r.diff.toLocaleString() + '</td>' +
      '<td style="text-align:right;font-family:{FONT_MONO_JS}">' + r.margen.toFixed(1) + '%' +
        '<div style="height:4px;border-radius:2px;background:{P['border-light']};margin-top:4px;overflow:hidden">' +
        '<div style="height:100%;width:' + Math.min(r.margen * 3, 100) + '%;background:{P['primary']};border-radius:2px"></div></div></td>' +
      '<td><span class="' + catClass + '">' + r.cat + '</span></td>' +
      '</tr>';
  }}).join('');
  document.getElementById('row-count').textContent = data.length + ' de ' + tableData.length + ' UPZs';
}}
function filterTable() {{
  var q = document.getElementById('search-input').value.toLowerCase();
  var loc = document.getElementById('loc-filter').value;
  var cat = document.getElementById('cat-filter').value;
  renderTable(tableData.filter(function(r) {{
    return (!q || r.nom.toLowerCase().indexOf(q) >= 0 || r.cod.toLowerCase().indexOf(q) >= 0) &&
           (!loc || r.loc === loc) &&
           (!cat || r.cat === cat);
  }}));
}}
function sortTable(col) {{
  sortAsc = sortCol === col ? !sortAsc : true; sortCol = col;
  var keys = ['cod', 'nom', 'loc', 'total', 'ganador', 'pct_g', 'segundo', 'diff', 'margen', 'cat'];
  var key = keys[col];
  tableData.sort(function(a, b) {{
    var va = a[key], vb = b[key];
    if (typeof va === 'number') return sortAsc ? va - vb : vb - va;
    return sortAsc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
  }});
  // Update sort arrows
  document.querySelectorAll('#upz-table th').forEach(function(th, i) {{
    th.classList.toggle('sort-asc', i === col && sortAsc);
    th.classList.toggle('sort-desc', i === col && !sortAsc);
  }});
  filterTable();
}}
renderTable(tableData);

// ─── TABLA COMPARATIVA (multi-par) ───
var compPairIdx = 0;

function getCompPrefix(idx) {{
  return compPairs[idx] + '_';
}}

function renderComp() {{
  var tbody = document.getElementById('comp-body');
  var prefix = getCompPrefix(compPairIdx);
  var pairLabel = compPairs[compPairIdx];
  document.getElementById('comp-pair-badge').textContent = pairLabel;
  document.getElementById('comp-th22').textContent = '% 2022 (' + pairLabel.split(' vs ')[0] + ')';
  document.getElementById('comp-th26').textContent = '% 2026 (' + pairLabel.split(' vs ')[1] + ')';

  var data = fullComp.map(function(r) {{
    var d = r[prefix + 'delta'] || 0;
    return {{
      loc: r.loc,
      pct22: r[prefix + '22'] || 0,
      pct26: r[prefix + '26'] || 0,
      delta: d,
      sit: d > 0 ? 'Mejora' : 'Retrocede'
    }};
  }});

  // Calculate max abs delta for bar scaling
  var maxDelta = Math.max(0.1, Math.max.apply(null, data.map(function(d) {{ return Math.abs(d.delta); }})));

  tbody.innerHTML = data.map(function(r) {{
    var barPct = Math.min(Math.abs(r.delta) / maxDelta * 100, 100);
    var barColor = r.delta > 0 ? '{P['success']}' : '{P['error']}';
    return '<tr>' +
      '<td><strong>' + r.loc + '</strong></td>' +
      '<td style="text-align:right;font-family:{FONT_MONO_JS}">' + r.pct22.toFixed(1) + '%</td>' +
      '<td style="text-align:right;font-family:{FONT_MONO_JS}">' + r.pct26.toFixed(1) + '%</td>' +
      '<td style="font-family:{FONT_MONO_JS}">' +
        '<div style="display:flex;align-items:center;gap:8px">' +
        '<span style="font-weight:600;color:' + barColor + ';min-width:45px">' + (r.delta > 0 ? '+' : '') + r.delta.toFixed(1) + ' pp</span>' +
        '<div style="flex:1;height:8px;border-radius:4px;background:{P['border-light']};overflow:hidden">' +
        '<div style="height:100%;width:' + barPct + '%;background:' + barColor + ';border-radius:4px;transition:width 0.5s"></div></div></div></td>' +
      '<td style="text-align:right;font-family:{FONT_MONO_JS}">-</td>' +
      '<td style="text-align:right;font-family:{FONT_MONO_JS}">-</td>' +
      '<td><span style="color:' + barColor + ';font-weight:500">' + r.sit + '</span></td>' +
      '</tr>';
  }}).join('');

  // Update stats
  var sorted = data.slice().sort(function(a, b) {{ return b.delta - a.delta; }});
  var mejor = sorted[0], peor = sorted[sorted.length - 1];
  document.getElementById('comp-mejor').textContent = mejor.loc + ' (' + (mejor.delta > 0 ? '+' : '') + mejor.delta.toFixed(1) + ' pp)';
  document.getElementById('comp-peor').textContent = peor.loc + ' (' + (peor.delta > 0 ? '+' : '') + peor.delta.toFixed(1) + ' pp)';
  document.getElementById('comp-pct22').textContent = (data.reduce(function(s, r) {{ return s + r.pct22; }}, 0) / data.length).toFixed(1) + '%';
  document.getElementById('comp-pct26').textContent = (data.reduce(function(s, r) {{ return s + r.pct26; }}, 0) / data.length).toFixed(1) + '%';
}}

window.switchComparativo = function(idx) {{
  compPairIdx = parseInt(idx);
  renderComp();
}};

function sortComp(col) {{
  var prefix = getCompPrefix(compPairIdx);
  var keys = ['loc', prefix + '22', prefix + '26', prefix + 'delta', 'loc', 'loc', 'sit'];
  var key = keys[col];
  fullComp.sort(function(a, b) {{
    var va = a[key] !== undefined ? a[key] : 0;
    var vb = b[key] !== undefined ? b[key] : 0;
    if (typeof va === 'number') return va - vb;
    return String(va).localeCompare(String(vb));
  }});
  renderComp();
}}
renderComp();

// Title stats for default (Petro vs Cepeda)
var title22 = (compData.reduce(function(s, r) {{ return s + (r.pct_petro_1v22 || 0); }}, 0) / compData.length * 100).toFixed(1);
var title26 = (compData.reduce(function(s, r) {{ return s + (r.pct_cepeda_1v26 || 0); }}, 0) / compData.length * 100).toFixed(1);

// ─── ECHARTS ───
var chartTheme = {{
  color: ['#E53935','#1E88E5','#43A047','#8E24AA','#FB8C00','#FDD835','#6D4C41','#D81B60','#757575','#00ACC1','#FFB300','#795548','#00897B'],
  backgroundColor: 'transparent',
  textStyle: {{ fontFamily: 'Inter, sans-serif' }},
}};
echarts.registerTheme('colombia', chartTheme);

var allCharts = [];
function initChart(id) {{
  var dom = document.getElementById(id);
  if (!dom) return {{ setOption:function(){{}}, resize:function(){{}} }};
  var chart = echarts.init(dom, 'colombia', {{ renderer: 'canvas' }});
  allCharts.push(chart);
  return chart;
}}

// Chart 1: Votos totales por candidato
(function() {{
  var chart = initChart('chart-candidatos');
  var data = statsCand.map(function(r) {{ return {{ name: r.c, value: r.v }}; }});
  chart.setOption({{
    tooltip: {{ trigger:'axis', axisPointer:{{ type:'shadow' }}, valueFormatter: function(v) {{ return Number(v).toLocaleString(); }} }},
    grid: {{ left:80, right:40, top:20, bottom:20 }},
    xAxis: {{ type:'value', axisLabel:{{ formatter: function(v) {{ return (v/1000000).toFixed(1) + 'M'; }} }}, splitLine:{{ lineStyle:{{ color:'#f0f0f0' }} }} }},
    yAxis: {{ type:'category', data: data.map(function(d) {{ return d.name; }}).reverse(), axisLabel:{{ fontSize:11, fontWeight:500 }} }},
    series: [{{
      type:'bar', data: data.map(function(d) {{ return d.value; }}).reverse(),
      itemStyle: {{ color: function(p) {{ return candColors[data[data.length-1-p.dataIndex].name] || '#ccc'; }} }},
      barMaxWidth: 24, label: {{ show:true, position:'right', formatter: function(p) {{ return Number(p.value).toLocaleString(); }}, fontSize:11, fontWeight:500 }},
      animationDuration: 800, animationEasing: 'elasticOut'
    }}]
  }});
  window.addEventListener('resize', function() {{ chart.resize(); }});
}})();

// Chart 2: Top 10 UPZ distribucion
(function() {{
  var chart = initChart('chart-upz-dist');
  var cands = {json.dumps(top_cands_short, ensure_ascii=False)};
  cands.push('Otros');
  var series = cands.map(function(c) {{
    return {{
      name: c, type: 'bar', stack: 'total',
      data: upzDist.map(function(r) {{ return r[c] || 0; }}),
      itemStyle: {{ color: candColors[c] || '#ccc' }},
      barMaxWidth: 20
    }};
  }});
  chart.setOption({{
    tooltip: {{ trigger:'axis', axisPointer:{{ type:'shadow' }}, formatter: function(ps) {{
      var html = '<strong>' + ps[0].axisValue + '</strong><br>';
      ps.forEach(function(p) {{ html += p.marker + ' ' + p.seriesName + ': ' + p.value + '%<br>'; }});
      return html;
    }} }},
    legend: {{ data: cands, type:'scroll', bottom:0, itemWidth:10, itemHeight:10, textStyle:{{ fontSize:11 }} }},
    grid: {{ left:100, right:40, top:10, bottom:40 }},
    xAxis: {{ type:'value', max:100, axisLabel:{{ formatter: '{{value}}%' }}, splitLine:{{ lineStyle:{{ color:'#f0f0f0' }} }} }},
    yAxis: {{ type:'category', data: upzDist.map(function(r) {{ return r.upz; }}), axisLabel:{{ fontSize:11, width:90, overflow:'truncate' }} }},
    series: series
  }});
  window.addEventListener('resize', function() {{ chart.resize(); }});
}})();

// Chart 3: Matriz candidato x localidad
(function() {{
  var chart = initChart('chart-matriz');
  chart.setOption({{
    tooltip: {{ position:'top', formatter: function(p) {{
      return candNames[p.data[1]] + ' en ' + locList[p.data[0]] + ': <strong>' + p.data[2] + '%</strong>';
    }} }},
    grid: {{ left:130, right:40, top:20, bottom:60 }},
    xAxis: {{ type:'category', data: locList, axisLabel:{{ rotate:45, fontSize:10, width:80, overflow:'break' }}, splitArea:{{ show:true }} }},
    yAxis: {{ type:'category', data: candNames, axisLabel:{{ fontSize:10, fontWeight:500 }} }},
    visualMap: {{ min:0, max:70, calculable:true, orient:'horizontal', left:'center', bottom:0,
      inRange: {{ color: ['#f7f7f7','#dadaeb','#9e9ac8','#6a51a3','#3f007d'] }},
      textStyle:{{ fontSize:10 }} }},
    series: [{{
      type:'heatmap', data: matrizData,
      label: {{ show: true, fontSize: 8, color: '#333', formatter: function(p) {{ return p.data[2] > 0 ? p.data[2] + '%' : ''; }} }},
      emphasis: {{ itemStyle: {{ shadowBlur:10, shadowColor:'rgba(0,0,0,0.15)' }} }}
    }}]
  }});
  window.addEventListener('resize', function() {{ chart.resize(); }});
}})();

// Chart 4: Brecha Cepeda vs Espriella
(function() {{
  var chart = initChart('chart-brecha');
  var labels = brechaData.map(function(r) {{ return r.upz; }});
  chart.setOption({{
    tooltip: {{ trigger:'axis', axisPointer:{{ type:'shadow' }}, formatter: function(ps) {{
      return '<strong>' + ps[0].axisValue + '</strong><br>' + ps.map(function(p) {{ return p.marker + ' ' + p.seriesName + ': ' + p.value + '%'; }}).join('<br>');
    }} }},
    legend: {{ data: ['Cepeda', 'Espriella'], bottom:0, itemWidth:10, itemHeight:10, textStyle:{{ fontSize:11 }} }},
    grid: {{ left:120, right:30, top:10, bottom:40 }},
    xAxis: {{ type:'value', axisLabel:{{ formatter: '{{value}}%' }}, splitLine:{{ lineStyle:{{ color:'#f0f0f0' }} }} }},
    yAxis: {{ type:'category', data: labels, axisLabel:{{ fontSize:10, width:100, overflow:'truncate' }} }},
    series: [
      {{ name:'Cepeda', type:'bar', data: brechaData.map(function(r) {{ return r.cepeda; }}),
        itemStyle:{{ color: {json.dumps(P['primary'])} }}, barMaxWidth:14, barGap:'20%' }},
      {{ name:'Espriella', type:'bar', data: brechaData.map(function(r) {{ return r.espriella; }}),
        itemStyle:{{ color: {json.dumps(P['accent'])} }}, barMaxWidth:14 }}
    ]
  }});
  window.addEventListener('resize', function() {{ chart.resize(); }});
}})();

// Chart 5: Scatter Petro 2022 vs Cepeda 2026
(function() {{
  var chart = initChart('chart-scatter');
  chart.setOption({{
    tooltip: {{ formatter: function(p) {{
      var d = p.data;
      return '<strong>' + d[3] + '</strong><br>Petro 2022: ' + d[0] + '%<br>Cepeda 2026: ' + d[1] + '%<br>Delta: ' + (d[2] > 0 ? '+' : '') + d[2] + ' pp';
    }} }},
    grid: {{ left:60, right:30, top:30, bottom:50 }},
    xAxis: {{ name:'% Petro 2022', nameLocation:'center', nameGap:30, type:'value', splitLine:{{ lineStyle:{{ color:'#f0f0f0' }} }} }},
    yAxis: {{ name:'% Cepeda 2026', nameLocation:'center', nameGap:30, type:'value', splitLine:{{ lineStyle:{{ color:'#f0f0f0' }} }} }},
    series: [{{
      type:'scatter', data: scatterData,
      symbolSize: 16,
      itemStyle: {{ color: function(p) {{
        var d = p.data[2];
        return d > -3 ? '{P['error']}' : d > -5.5 ? '{P['warning']}' : d > -7 ? '{P['success']}' : '{P['accent']}';
      }}, shadowBlur:4, shadowColor:'rgba(0,0,0,0.1)' }},
      label: {{ show:true, formatter: function(p) {{ return p.data[3]; }}, fontSize:10, color:'{P['text-secondary']}', position:'right' }},
      markLine: {{
        data: [{{ xAxis: 0, yAxis: 0, lineStyle:{{ color:'#e0e0e0', type:'dashed' }}, label:{{ formatter:'y=x', position:'end' }} }}],
        silent: true
      }},
      animationDuration: 1000
    }}]
  }});
  window.addEventListener('resize', function() {{ chart.resize(); }});
}})();

// Chart 6: Dual-axis bar + line
(function() {{
  var chart = initChart('chart-dual');
  var locs = dualData.map(function(r) {{ return r.loc; }});
  chart.setOption({{
    tooltip: {{ trigger:'axis', axisPointer:{{ type:'shadow' }}, formatter: function(ps) {{
      var html = '<strong>' + ps[0].axisValue + '</strong><br>';
      ps.forEach(function(p) {{ html += p.marker + ' ' + p.seriesName + ': ' + (p.seriesType === 'bar' ? p.value + '%' : p.value + ' pp') + '<br>'; }});
      return html;
    }} }},
    legend: {{ data: ['% Petro 2022', '% Cepeda 2026', 'Delta (pp)'], bottom:0, itemWidth:10, itemHeight:10, textStyle:{{ fontSize:11 }} }},
    grid: {{ left:60, right:60, top:15, bottom:40 }},
    xAxis: {{ type:'category', data: locs, axisLabel:{{ rotate:45, fontSize:9, width:70, overflow:'break' }} }},
    yAxis: [
      {{ type:'value', name:'%', nameTextStyle:{{ fontSize:11, color:'{P['text-secondary']}' }}, splitLine:{{ lineStyle:{{ color:'#f0f0f0' }} }} }},
      {{ type:'value', name:'Delta pp', nameTextStyle:{{ fontSize:11, color:'{P['text-secondary']}' }}, splitLine:{{ show:false }},
        axisLabel:{{ formatter: function(v) {{ return v + ' pp'; }} }} }}
    ],
    series: [
      {{ name:'% Petro 2022', type:'bar', data: dualData.map(function(r) {{ return r.petro; }}),
        itemStyle:{{ color: {json.dumps(P['primary'])} }}, barMaxWidth:12, barGap:'10%' }},
      {{ name:'% Cepeda 2026', type:'bar', data: dualData.map(function(r) {{ return r.cepeda; }}),
        itemStyle:{{ color: {json.dumps(P['accent'])} }}, barMaxWidth:12 }},
      {{ name:'Delta (pp)', type:'line', data: dualData.map(function(r) {{ return r.delta; }}),
        yAxisIndex:1, symbol:'circle', symbolSize:6,
        lineStyle:{{ color:{json.dumps(P['warning'])}, width:2 }},
        itemStyle:{{ color:{json.dumps(P['warning'])} }},
        areaStyle:{{ color: 'rgba(249,168,37,0.1)' }} }}
    ]
  }});
  window.addEventListener('resize', function() {{ chart.resize(); }});
}})();

// Chart 7: Comparativo heatmap - todos los pares 2022 vs 2026
(function() {{
  var chart = initChart('chart-comp-heatmap');
  // Build data: rows = localidades, cols = pairs, value = delta
  var pairLabels = compPairs.map(function(p) {{ return p.split(' vs ').join('\\n'); }});
  var heatData = [];
  fullComp.forEach(function(r, i) {{
    compPairs.forEach(function(p, j) {{
      var prefix = p + '_';
      var d = r[prefix + 'delta'] || 0;
      heatData.push([j, i, d]);
    }});
  }});
  var maxAbs = Math.max.apply(null, heatData.map(function(d) {{ return Math.abs(d[2]); }}));
  var locs = fullComp.map(function(r) {{ return r.loc; }});
  chart.setOption({{
    tooltip: {{ position:'top', formatter: function(p) {{
      return locs[p.data[1]] + '<br>' + compPairs[p.data[0]] + ': <strong>' + (p.data[2] > 0 ? '+' : '') + p.data[2].toFixed(1) + ' pp</strong>';
    }} }},
    grid: {{ left:90, right:30, top:10, bottom:60 }},
    xAxis: {{ type:'category', data: compPairs, axisLabel:{{ fontSize:9, interval:0, width:70, overflow:'break' }} }},
    yAxis: {{ type:'category', data: locs, axisLabel:{{ fontSize:9 }} }},
    visualMap: {{ min:-maxAbs, max:maxAbs, calculable:true, orient:'horizontal', left:'center', bottom:0,
      inRange: {{ color: ['{P['error']}', '#f7f7f7', '{P['success']}'] }},
      textStyle:{{ fontSize:10 }} }},
    series: [{{
      type:'heatmap', data: heatData,
      label: {{ show:false }},
      emphasis: {{ itemStyle: {{ shadowBlur:10, shadowColor:'rgba(0,0,0,0.15)' }} }}
    }}]
  }});
  window.addEventListener('resize', function() {{ chart.resize(); }});
}})();

// Chart 8: Box-style distribution of deltas per pair
(function() {{
  var chart = initChart('chart-comp-box');
  function calcBox(vals) {{
    var sorted = vals.slice().sort(function(a,b) {{ return a-b; }});
    var n = sorted.length;
    var min = sorted[0], max = sorted[n-1];
    var q1 = sorted[Math.round(n*0.25)];
    var med = sorted[Math.round(n*0.5)];
    var q3 = sorted[Math.round(n*0.75)];
    return [min, q1, med, q3, max];
  }}
  var series = compPairs.map(function(p) {{
    var prefix = p + '_';
    var vals = fullComp.map(function(r) {{ return r[prefix + 'delta'] || 0; }});
    return {{
      name: p.split(' vs ').join(' '),
      type: 'boxplot',
      data: [calcBox(vals)],
      itemStyle: {{ color: '{P['primary']}' }},
    }};
  }});
  // Add a reference line at 0
  series.push({{
    type: 'line',
    markLine: {{
      silent: true,
      data: [{{
        yAxis: 0,
        label: {{ formatter: 'Sin cambio (0 pp)', fontSize:10, color:'#616161' }},
        lineStyle: {{ color:'#9E9E9E', type:'dashed', width:1 }}
      }}]
    }}
  }});
  chart.setOption({{
    tooltip: {{ trigger:'item', formatter: function(p) {{
      var d = p.data;
      return '<strong>' + p.seriesName + '</strong><br>' +
        '<span style="color:#757575">Valor minimo</span>: ' + d[1].toFixed(1) + ' pp<br>' +
        '<span style="color:#757575">25% percentil</span>: ' + d[2].toFixed(1) + ' pp<br>' +
        '<span style="color:#757575">Mediana</span>: <strong>' + d[3].toFixed(1) + '</strong> pp<br>' +
        '<span style="color:#757575">75% percentil</span>: ' + d[4].toFixed(1) + ' pp<br>' +
        '<span style="color:#757575">Valor maximo</span>: ' + d[5].toFixed(1) + ' pp';
    }} }},
    grid: {{ left:60, right:30, top:30, bottom:60 }},
    xAxis: {{ type:'category', data: compPairs,
      axisLabel:{{ fontSize:9, width:70, overflow:'break' }} }},
    yAxis: {{ type:'value', name:'Delta (pp)',
      axisLabel:{{ formatter: function(v) {{ return v.toFixed(0); }} }},
      splitLine:{{ lineStyle:{{ color:'#f0f0f0' }} }} }},
    series: series
  }});
  window.addEventListener('resize', function() {{ chart.resize(); }});
}})();

// ─── SPA TAB NAV ───
var loadedIframes = {{}};
function switchSection(id) {{
  document.querySelectorAll('.section').forEach(function(s) {{ s.classList.remove('active'); }});
  var section = document.getElementById(id);
  if (section) section.classList.add('active');
  document.querySelectorAll('.section-nav a').forEach(function(a) {{ a.classList.remove('active'); }});
  var link = document.querySelector('.section-nav a[data-section="' + id + '"]');
  if (link) link.classList.add('active');
  // Lazy-load iframe if needed (Leaflet needs visible container)
  var iframe = section && section.querySelector('iframe[data-src]');
  if (iframe && !loadedIframes[id]) {{
    iframe.src = iframe.getAttribute('data-src');
    loadedIframes[id] = true;
  }}
  // Resize charts
  setTimeout(function() {{
    allCharts.forEach(function(c) {{ if (c && c.resize) try {{ c.resize(); }} catch(e) {{ }} }});
  }}, 50);
}}
document.getElementById('section-nav').addEventListener('click', function(e) {{
  var a = e.target.closest('.section-nav a');
  if (a) {{ e.preventDefault(); switchSection(a.getAttribute('data-section')); }}
}});
// Show initial section based on hash
var initialSection = window.location.hash.replace('#', '') || 'resumen';
switchSection(initialSection);
</script>
</body>
</html>"""

dashboard_path = os.path.join(OUT, 'index.html')
with open(dashboard_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'  OK  {dashboard_path}')
print(f'      - Hero + stats cards con iconos SVG')
print(f'      - 6 graficos ECharts interactivos (barra, stack, heatmap, divergente, scatter, dual-axis)')
print(f'      - Tabla UPZ con sort arrows + mini barras')
print(f'      - Tabla comparativa con barras de delta')
print(f'      - Navegacion sticky con IntersectionObserver')
