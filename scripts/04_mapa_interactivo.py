"""
Mapa interactivo:
  - Modo GANADOR (default): cada UPZ del color del candidato que la gano
  - Modos: relativo / absoluto / % UPZ / diferencia
  - Multi-select de candidatos (checkboxes)
  - Tooltip + popup completo
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import os, json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(BASE, 'data', 'processed')
OUT = os.path.join(BASE, 'outputs')
os.makedirs(OUT, exist_ok=True)

def fix_name(n):
    raw = n.encode('utf-8')
    fixes = {
        b'IV\xc3\x83\xc2\x81N CEPEDA CASTRO': 'IV\u00c1N CEPEDA CASTRO',
        b'CLAUDIA L\xc3\x83\xe2\x80\x9cPEZ': 'CLAUDIA L\u00d3PEZ',
        b'RA\xc3\x83\xc5\xa1L SANTIAGO BOTERO JARAMILLO': 'RA\u00daL SANTIAGO BOTERO JARAMILLO',
        b'\xc3\x83\xe2\x80\x9cSCAR MAURICIO LIZCANO ARANGO': '\u00d3SCAR MAURICIO LIZCANO ARANGO',
        b'MIGUEL URIBE LONDO\xc3\x83\xe2\x80\x98O': 'MIGUEL URIBE LONDO\u00d1O',
    }
    return fixes.get(raw, n)

# ─── DATOS ───
votos = pd.read_csv(os.path.join(PROC, 'votos_por_upz.csv'))
votos['CANNOMBRE'] = votos['CANNOMBRE'].apply(fix_name)
upz_geo = gpd.read_file(os.path.join(PROC, 'upz_con_votos.geojson'))

# ─── COMPARATIVO 2022-2026 ───
comp_upz = pd.read_csv(os.path.join(PROC, 'comparativo_upz.csv'))
comp_by_loc = {r['Localidad']: r for r in json.load(open(os.path.join(PROC, 'comparativo_localidad.json'), encoding='utf-8'))}

cand_order = (
    votos.groupby('CANNOMBRE')['VOTOS'].sum()
    .sort_values(ascending=False).index.tolist()
)

# ─── PIVOT ───
pivot = votos.pivot_table(index='UPLCODIGO', columns='CANNOMBRE', values='VOTOS', aggfunc='sum').fillna(0).reset_index()
upz_geo_4326 = upz_geo.to_crs('EPSG:4326')
upz_geo_4326 = upz_geo_4326.merge(pivot, on='UPLCODIGO', how='left')
for col in cand_order:
    upz_geo_4326[col] = upz_geo_4326[col].fillna(0).astype(float)

# Merge comparativo
comp_fields = ['delta_petro_1v_pp','delta_petro_2v_pp','sit_vs_1v22','sit_vs_2v22',
               'votos_petro_1v22','votos_cepeda_1v26']
for col in comp_fields:
    if col not in comp_upz.columns:
        comp_upz[col] = 0
upz_geo_4326 = upz_geo_4326.merge(comp_upz[['UPLCODIGO'] + comp_fields], on='UPLCODIGO', how='left')
for col in comp_fields:
    upz_geo_4326[col] = upz_geo_4326[col].fillna(0)
    if col.startswith('votos_'):
        upz_geo_4326[col] = upz_geo_4326[col].astype(float)

total_col = 'TOTAL_VOTOS'
if total_col not in upz_geo_4326.columns:
    upz_geo_4326[total_col] = upz_geo_4326[cand_order].sum(axis=1)

# ─── PCT + DIFF ───
for cand in cand_order:
    upz_geo_4326[f'pct_{cand}'] = np.where(
        upz_geo_4326[total_col] > 0,
        (upz_geo_4326[cand] / upz_geo_4326[total_col] * 100).round(2), 0,
    )
    mean_val = upz_geo_4326[cand].mean()
    upz_geo_4326[f'diff_{cand}'] = (upz_geo_4326[cand] - mean_val).round(0)

# ─── GANADOR por UPZ ───
upz_geo_4326['GANADOR_IDX'] = upz_geo_4326[cand_order].idxmax(axis=1)
upz_geo_4326['GANADOR'] = upz_geo_4326['GANADOR_IDX']
vote_cols_arr = np.array([upz_geo_4326[c].values for c in cand_order])
sorted_votes = np.sort(vote_cols_arr, axis=0)
upz_geo_4326['MARGEN_VOTOS'] = sorted_votes[-1] - sorted_votes[-2]
upz_geo_4326['MARGEN_PCT'] = np.where(
    upz_geo_4326[total_col] > 0,
    (upz_geo_4326['MARGEN_VOTOS'] / upz_geo_4326[total_col] * 100).round(1), 0,
)

# ─── COLORES por candidato ───
# 13 colores categoricos (ColorBrewer Paired + extras)
CAND_COLORS = [
    '#E41A1C','#377EB8','#4DAF4A','#984EA3','#FF7F00',
    '#FFFF33','#A65628','#F781BF','#999999','#66A61E',
    '#E6AB02','#A6761D','#1B9E77',
]
cand_colors_dict = dict(zip(cand_order, CAND_COLORS[:len(cand_order)]))
upz_geo_4326['COLOR_GANADOR'] = upz_geo_4326['GANADOR'].map(cand_colors_dict)

# ─── RANGOS ───
cand_ranges = {cand: {'min': float(upz_geo_4326[cand].min()), 'max': float(upz_geo_4326[cand].max())} for cand in cand_order}
global_max_votos = float(upz_geo_4326[cand_order].values.max())

diff_max_abs = {}
for cand in cand_order:
    d = max(abs(upz_geo_4326[f'diff_{cand}'].min()), abs(upz_geo_4326[f'diff_{cand}'].max()))
    diff_max_abs[cand] = d if d > 0 else 1

# ─── POPUP ───
for idx in upz_geo_4326.index:
    props = upz_geo_4326.loc[idx]
    uplnombre = props.get('UPLNOMBRE', '')
    locnombre = props.get('LOCNOMBRE', '')
    total = int(props.get(total_col, 0) or 0)
    rows = []
    for cand in cand_order:
        v = int(props.get(cand, 0) or 0)
        p = props.get(f'pct_{cand}', 0)
        rows.append((cand, v, p))
    rows.sort(key=lambda x: x[1], reverse=True)
    max_v = rows[0][1] if rows else 1
    popup_rows = ''
    for r in rows:
        name, v, p = r
        bar_pct = (v / max_v * 100) if max_v > 0 else 0
        popup_rows += (
            f'<tr><td style="padding:3px 6px">{name}</td>'
            f'<td style="padding:3px 6px;text-align:right">{v:,}</td>'
            f'<td style="padding:3px 6px;text-align:right">{p:.1f}%</td>'
            f'<td style="padding:3px 6px;width:100px"><div style="background:#1a1a2e;height:10px;width:{bar_pct:.0f}%;border-radius:3px;min-width:2px"></div></td></tr>'
        )
    d1v_upz = props.get('delta_petro_1v_pp', 0)
    vc26_upz = int(props.get('votos_cepeda_1v26', 0))
    vp22_upz = int(props.get('votos_petro_1v22', 0))
    comp_row_upz = f'<p style="margin:8px 0 0;font-size:12px;color:#1a1a2e;border-top:1px solid #eee;padding-top:6px">'
    comp_row_upz += f'<strong>Comparativo 2022-2026:</strong><br>'
    comp_row_upz += f'Cepeda 26: {vc26_upz:,} votos | Petro 22: {vp22_upz:,} votos<br>'
    comp_row_upz += f'Delta: {d1v_upz:+.1f} pp</p>' if d1v_upz != 0 else ''
    upz_geo_4326.at[idx, '_popup'] = (
        f'<div style="min-width:320px;font-family:system-ui">'
        f'<h4 style="margin:0 0 4px">{uplnombre}</h4>'
        f'<p style="margin:0 0 8px;color:#666;font-size:13px">{locnombre} | Total: {total:,} votos</p>'
        f'<table style="width:100%;border-collapse:collapse;font-size:13px">'
        f'<thead><tr style="background:#1a1a2e;color:white">'
        f'<th style="padding:4px 6px;text-align:left">Candidato</th>'
        f'<th style="padding:4px 6px;text-align:right">Votos</th>'
        f'<th style="padding:4px 6px;text-align:right">%</th>'
        f'<th style="padding:4px 6px;width:100px"></th></tr></thead>'
        f'<tbody>{popup_rows}</tbody></table>'
        f'{comp_row_upz}</div>'
    )

# ─── GEOJSON UPZ ───
keep_cols = (['UPLCODIGO','UPLNOMBRE','LOCNOMBRE','LOCCODIGO',total_col,
              '_popup','GANADOR','MARGEN_VOTOS','MARGEN_PCT','COLOR_GANADOR',
              'GANADOR_IDX','geometry'] + cand_order
             + [f'pct_{c}' for c in cand_order]
             + [f'diff_{c}' for c in cand_order]
             + comp_fields)
drop_cols = [c for c in upz_geo_4326.columns if c not in keep_cols]
upz_clean = upz_geo_4326.drop(columns=drop_cols)
geo_json_str = json.dumps(upz_clean.__geo_interface__, ensure_ascii=False)

# ─── LOCALIDAD LEVEL ───
loc_agg = upz_geo_4326[[total_col] + cand_order + comp_fields + ['LOCNOMBRE']].copy()
vote_sum_cols = [total_col] + cand_order + ['votos_petro_1v22','votos_cepeda_1v26']
first_cols = ['delta_petro_1v_pp','delta_petro_2v_pp','sit_vs_1v22','sit_vs_2v22']
loc_agg_sum = loc_agg[vote_sum_cols + ['LOCNOMBRE']].groupby('LOCNOMBRE').sum(numeric_only=True).reset_index()
loc_agg_first = loc_agg[first_cols + ['LOCNOMBRE']].groupby('LOCNOMBRE').first().reset_index()
loc_geo = upz_geo_4326[['LOCNOMBRE','geometry']].dissolve(by='LOCNOMBRE', aggfunc='first').reset_index()
loc_geo = loc_geo.merge(loc_agg_sum, on='LOCNOMBRE', how='left')
loc_geo = loc_geo.merge(loc_agg_first, on='LOCNOMBRE', how='left')

for cand in cand_order:
    loc_geo[cand] = loc_geo[cand].fillna(0).astype(float)
loc_geo[total_col] = loc_geo[cand_order].sum(axis=1)

for cand in cand_order:
    loc_geo[f'pct_{cand}'] = np.where(
        loc_geo[total_col] > 0,
        (loc_geo[cand] / loc_geo[total_col] * 100).round(2), 0,
    )
    mean_val = loc_geo[cand].mean()
    loc_geo[f'diff_{cand}'] = (loc_geo[cand] - mean_val).round(0)

loc_geo['GANADOR_IDX'] = loc_geo[cand_order].idxmax(axis=1)
loc_geo['GANADOR'] = loc_geo['GANADOR_IDX']
vote_cols_arr_loc = np.array([loc_geo[c].values for c in cand_order])
sorted_votes_loc = np.sort(vote_cols_arr_loc, axis=0)
loc_geo['MARGEN_VOTOS'] = sorted_votes_loc[-1] - sorted_votes_loc[-2]
loc_geo['MARGEN_PCT'] = np.where(
    loc_geo[total_col] > 0,
    (loc_geo['MARGEN_VOTOS'] / loc_geo[total_col] * 100).round(1), 0,
)
loc_geo['COLOR_GANADOR'] = loc_geo['GANADOR'].map(cand_colors_dict)

# ─── POPUP LOCALIDAD ───
for idx in loc_geo.index:
    props = loc_geo.loc[idx]
    locnombre = props.get('LOCNOMBRE', '')
    total = int(props.get(total_col, 0) or 0)
    rows = []
    for cand in cand_order:
        v = int(props.get(cand, 0) or 0)
        p = props.get(f'pct_{cand}', 0)
        rows.append((cand, v, p))
    rows.sort(key=lambda x: x[1], reverse=True)
    max_v = rows[0][1] if rows else 1
    popup_rows = ''
    for r in rows:
        name, v, p = r
        bar_pct = (v / max_v * 100) if max_v > 0 else 0
        popup_rows += (
            f'<tr><td style="padding:3px 6px">{name}</td>'
            f'<td style="padding:3px 6px;text-align:right">{v:,}</td>'
            f'<td style="padding:3px 6px;text-align:right">{p:.1f}%</td>'
            f'<td style="padding:3px 6px;width:100px"><div style="background:#1a1a2e;height:10px;width:{bar_pct:.0f}%;border-radius:3px;min-width:2px"></div></td></tr>'
        )
    d1v = props.get('delta_petro_1v_pp', 0)
    vc26 = int(props.get('votos_cepeda_1v26', 0))
    vp22 = int(props.get('votos_petro_1v22', 0))
    comp_row = f'<p style="margin:8px 0 0;font-size:12px;color:#1a1a2e;border-top:1px solid #eee;padding-top:6px">'
    comp_row += f'<strong>Comparativo 2022-2026:</strong><br>'
    comp_row += f'Cepeda 26: {vc26:,} votos | Petro 22: {vp22:,} votos<br>'
    comp_row += f'Delta: {d1v:+.1f} pp</p>' if d1v != 0 else ''
    loc_geo.at[idx, '_popup'] = (
        f'<div style="min-width:320px;font-family:system-ui">'
        f'<h4 style="margin:0 0 4px">{locnombre} (Localidad)</h4>'
        f'<p style="margin:0 0 8px;color:#666;font-size:13px">Total: {total:,} votos</p>'
        f'<table style="width:100%;border-collapse:collapse;font-size:13px">'
        f'<thead><tr style="background:#1a1a2e;color:white">'
        f'<th style="padding:4px 6px;text-align:left">Candidato</th>'
        f'<th style="padding:4px 6px;text-align:right">Votos</th>'
        f'<th style="padding:4px 6px;text-align:right">%</th>'
        f'<th style="padding:4px 6px;width:100px"></th></tr></thead>'
        f'<tbody>{popup_rows}</tbody></table>'
        f'{comp_row}</div>'
    )

# ─── GEOJSON LOCALIDAD ───
keep_loc = (['LOCNOMBRE', total_col, '_popup', 'GANADOR',
             'MARGEN_VOTOS', 'MARGEN_PCT', 'COLOR_GANADOR',
             'GANADOR_IDX', 'geometry'] + cand_order
            + [f'pct_{c}' for c in cand_order]
            + [f'diff_{c}' for c in cand_order]
            + comp_fields)
drop_loc = [c for c in loc_geo.columns if c not in keep_loc]
loc_clean = loc_geo.drop(columns=drop_loc)
loc_clean['UPLNOMBRE'] = loc_clean['LOCNOMBRE']
loc_clean['UPLCODIGO'] = loc_clean['LOCNOMBRE']
loc_json_str = json.dumps(loc_clean.__geo_interface__, ensure_ascii=False)

# ─── PALETAS ───
ylorrd = ['#ffffcc','#ffeda0','#fed976','#feb24c','#fd8d3c','#fc4e2a','#e31a1c','#bd0026','#800026']
rdbu = ['#2166ac','#4393c3','#92c5de','#d1e5f0','#f7f7f7','#fddbc7','#f4a582','#d6604d','#b2182b']
purples = ['#f2f0f7','#dadaeb','#bcbddc','#9e9ac8','#807dba','#6a51a3','#54278f','#3f007d','#2c0055']

# ─── HTML ───
html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mapa Electoral Bogotá 2026</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; font-family:system-ui,sans-serif; }}
  body {{ background:#f0f2f5; }}
  #map {{ width:100vw; height:100vh; }}
  .panel {{
    position:absolute; top:12px; right:12px; z-index:1000;
    background:white; border-radius:8px; padding:10px 14px;
    box-shadow:0 2px 8px rgba(0,0,0,0.15);
    font-size:13px; max-width:270px;
  }}
  .panel select, .panel label {{ display:block; width:100%; margin-bottom:4px; }}
  .panel select {{
    padding:6px 8px; border:1px solid #ccc; border-radius:5px;
    font-size:13px; cursor:pointer; font-family:system-ui;
  }}
  .panel select:focus {{ outline:none; border-color:#1a1a2e; }}
  .legend {{
    position:absolute; bottom:30px; right:12px; z-index:1000;
    background:white; padding:10px 14px; border-radius:8px;
    font-size:12px; box-shadow:0 2px 8px rgba(0,0,0,0.15);
    line-height:1.5; min-width:180px; display:none;
  }}
  .legend .bar {{ width:100%; height:14px; border-radius:3px; margin:4px 0; }}
  .legend .labels {{ display:flex; justify-content:space-between; font-size:10px; color:#666; }}
  .legend-item {{ display:flex; align-items:center; gap:6px; font-size:11px; padding:2px 0; }}
  .legend-swatch {{ width:14px; height:14px; border-radius:3px; flex-shrink:0; }}
  .hint {{ position:absolute; bottom:30px; left:12px; z-index:1000;
    background:white; padding:6px 10px; border-radius:6px; font-size:11px;
    box-shadow:0 2px 6px rgba(0,0,0,0.1); color:#666; }}
  .checkbox-group {{ max-height:260px; overflow-y:auto; margin-top:6px; }}
  .checkbox-group label {{ display:flex; align-items:center; gap:6px; padding:2px 0; font-size:12px; cursor:pointer; }}
  .checkbox-group input {{ margin:0; }}
  .sel-count {{ font-size:11px; color:#888; margin-top:4px; }}
  .view-btn.active {{ background:#1a1a2e !important; color:white !important; border-color:#1a1a2e !important; }}
</style>
</head>
<body>
<div id="map"></div>

<div class="panel">
  <select id="mode-selector">
    <option value="winner">Ganador (todos los candidatos)</option>
    <option value="relative">Relativo (min-max por candidato)</option>
    <option value="percentage">% del UPZ (0% a 100%)</option>
    <option value="difference">Diferencia vs promedio</option>
    <option value="comparative">Comparativo Cepeda 26 vs Petro 22</option>
  </select>

  <div style="display:flex;gap:4px;margin-bottom:6px">
    <button class="view-btn active" data-view="upz" onclick="switchView('upz')" style="flex:1;padding:4px 0;border:1px solid #ccc;border-radius:4px;background:#1a1a2e;color:white;font-size:12px;cursor:pointer;font-family:system-ui">UPZ</button>
    <button class="view-btn" data-view="loc" onclick="switchView('loc')" style="flex:1;padding:4px 0;border:1px solid #ccc;border-radius:4px;background:white;color:#333;font-size:12px;cursor:pointer;font-family:system-ui">Localidad</button>
  </div>

  <div id="cand-selector">
    <div style="font-weight:500;margin:6px 0 2px;font-size:12px">Candidatos:</div>
    <div class="checkbox-group" id="checkbox-group">
      <label><input type="checkbox" id="check-all" checked onchange="toggleAll()"> <strong>Todos</strong></label>
      {"".join(
        f'<label><input type="checkbox" class="cand-check" value="{i}" checked onchange="updateSelected()"> '
        f'<span style="display:inline-block;width:12px;height:12px;border-radius:2px;background:{cand_colors_dict[cand]}"></span> '
        f'{cand}</label>'
        for i, cand in enumerate(cand_order)
      )}
    </div>
    <div class="sel-count" id="sel-count">13 seleccionados</div>
  </div>
</div>

<div class="legend" id="legend">
  <div style="font-weight:600;margin-bottom:4px"><span id="legend-title">Ganador por UPZ</span></div>
  <div id="legend-content"></div>
  <div class="bar" id="legend-bar" style="display:none"></div>
  <div class="labels" id="legend-labels" style="display:none">
    <span id="legend-min">0</span>
    <span id="legend-mid">0</span>
    <span id="legend-max">0</span>
  </div>
</div>

<div class="hint">UPZ / Localidad | Hover: info | Click: tabla completa</div>

<script>
(function() {{
  var geoData = {geo_json_str};
  var locGeoData = {loc_json_str};
  var candOrder = {json.dumps(cand_order, ensure_ascii=False)};
  var candColors = {json.dumps(cand_colors_dict, ensure_ascii=False)};
  var globalMaxVotos = {global_max_votos};
  var candRanges = {json.dumps(cand_ranges)};
  var diffMaxAbs = {json.dumps(diff_max_abs)};
  var ylorrd = {json.dumps(ylorrd)};
  var rdbu = {json.dumps(rdbu)};
  var purples = {json.dumps(purples)};

  // Estado
  var currentMode = 'winner';
  var currentView = 'upz'; // 'upz' | 'loc'
  var selectedCands = candOrder.map(function(_,i) {{ return i; }});

  function getSelectedIndices() {{
    var checks = document.querySelectorAll('.cand-check:checked');
    return Array.from(checks).map(function(c) {{ return parseInt(c.value); }});
  }}

  function getActiveData() {{
    return currentView === 'loc' ? locGeoData : geoData;
  }}

  window.updateSelected = function() {{
    selectedCands = getSelectedIndices();
    document.getElementById('sel-count').textContent = selectedCands.length + ' seleccionado' + (selectedCands.length !== 1 ? 's' : '');
    var allCheck = document.getElementById('check-all');
    var total = document.querySelectorAll('.cand-check').length;
    var checked = selectedCands.length;
    allCheck.checked = checked === total;
    allCheck.indeterminate = checked > 0 && checked < total;
    updateMap();
  }};

  window.toggleAll = function() {{
    var checked = document.getElementById('check-all').checked;
    document.querySelectorAll('.cand-check').forEach(function(c) {{ c.checked = checked; }});
    updateSelected();
  }};

  window.switchView = function(view) {{
    currentView = view;
    document.querySelectorAll('.view-btn').forEach(function(b) {{
      b.classList.toggle('active', b.dataset.view === view);
    }});
    // Swap layers
    if (view === 'loc') {{
      map.removeLayer(upzLayer);
      map.addLayer(locLayer);
    }} else {{
      map.removeLayer(locLayer);
      map.addLayer(upzLayer);
    }}
    updateMap();
  }};

  // ─── MAPA ───
  var map = L.map('map', {{ center:[4.65,-74.1], zoom:11, zoomControl:true }});
  L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
    attribution:'&copy; <a href="https://carto.com">CARTO</a>', subdomains:'abcd', maxZoom:19
  }}).addTo(map);

  function buildTooltip(p) {{
    var sel = selectedCands;
    var mode = currentMode;
    var extra = '';
    if (mode === 'winner') {{
      extra = 'Ganador: ' + (p.GANADOR || '');
    }} else if (mode === 'comparative') {{
      var d = p.delta_petro_1v_pp || 0;
      var vc = p.votos_cepeda_1v26 || 0;
      var vp = p.votos_petro_1v22 || 0;
      var sit = p.sit_vs_1v22 || '';
      extra = 'Cepeda 26: ' + Number(vc).toLocaleString() + ' votos | Petro 22: ' + Number(vp).toLocaleString() + ' votos';
      extra += '<br>Delta: ' + (d > 0 ? '+' : '') + d.toFixed(1) + ' pp ' + sit;
    }} else if (sel.length === 1) {{
      var cand = candOrder[sel[0]];
      if (mode === 'percentage') {{
        extra = (p['pct_'+cand] || 0).toFixed(1) + '% para ' + cand;
      }} else if (mode === 'difference') {{
        var dv = p['diff_'+cand] || 0;
        extra = (dv > 0 ? '+' : '') + Number(dv).toLocaleString() + ' vs promedio de ' + cand;
      }} else {{
        extra = Number(p[cand] || 0).toLocaleString() + ' votos para ' + cand;
      }}
    }} else if (sel.length === 2) {{
      var c1 = candOrder[sel[0]], c2 = candOrder[sel[1]];
      var v1 = p[c1] || 0, v2 = p[c2] || 0;
      extra = c1 + ': ' + Number(v1).toLocaleString() + ' | ' + c2 + ': ' + Number(v2).toLocaleString();
    }} else {{
      extra = 'Ganador: ' + (p.GANADOR || '');
    }}
    var name = p.UPLNOMBRE || p.LOCNOMBRE || '';
    var tt = '<strong>' + name + '</strong>';
    if (currentView === 'upz' && p.LOCNOMBRE) tt += '<br><span style="color:#666;font-size:12px">'+p.LOCNOMBRE+'</span>';
    if (extra) tt += '<br><span style="color:#1a1a2e;font-size:12px;font-weight:500">'+extra+'</span>';
    if (p.TOTAL_VOTOS && mode !== 'comparative') tt += '<br><span style="color:#999;font-size:11px">Total: '+Number(p.TOTAL_VOTOS).toLocaleString()+' votos</span>';
    return tt;
  }}

  function onEachFeature(feature, layer) {{
    var p = feature.properties;
    if (p._popup) layer.bindPopup(p._popup, {{ maxWidth:450 }});
    layer.bindTooltip(buildTooltip(p), {{ sticky:false, direction:'top' }});
  }}

  function makeLayer(data) {{
    var l = L.geoJson(data, {{
      style: function() {{ return {{ fillColor:'#e0e0e0', fillOpacity:0.3, color:'#888', weight:1 }}; }},
      onEachFeature: onEachFeature,
    }});
    l.eachLayer(function(layer) {{
      layer.on({{
        mouseover: function(e) {{
          e.target.setStyle({{ weight:2, color:'#000', fillOpacity:0.5 }});
          if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) e.target.bringToFront();
        }},
        mouseout: function(e) {{ applyStyle(e.target); }}
      }});
    }});
    return l;
  }}

  var upzLayer = makeLayer(geoData);
  var locLayer = makeLayer(locGeoData);
  upzLayer.addTo(map);
  map.fitBounds(upzLayer.getBounds().pad(0.05));

  // ─── LOGICA DE VISUALIZACION ───
  function getCompRange() {{
    var activeData = getActiveData();
    var minV = 0, maxV = 0;
    activeData.features.forEach(function(f) {{
      var d = parseFloat(f.properties.delta_petro_1v_pp) || 0;
      if (d < minV) minV = d;
      if (d > maxV) maxV = d;
    }});
    return {{min: minV, max: maxV}};
  }}

  function applyStyle(layer) {{
    var p = layer.feature.properties;
    var sel = selectedCands;
    var mode = currentMode;

    if (mode === 'comparative') {{
      var d = parseFloat(p.delta_petro_1v_pp) || 0;
      var compR = getCompRange();
      var minD = compR.min, maxD = compR.max;
      var idx;
      if (minD === maxD) {{
        idx = 4;
      }} else if (d >= 0) {{
        // Positive: use blue side
        idx = 4 + Math.floor((d / maxD) * 4);
        idx = Math.min(idx, 8);
      }} else {{
        // Negative: use red side
        idx = Math.floor((d - minD) / (-minD) * 4);
        idx = Math.min(idx, 4);
        idx = 4 - idx;
      }}
      idx = Math.max(0, Math.min(Math.round(idx), 8));
      layer.setStyle({{ fillColor:rdbu[idx], fillOpacity:0.85, color:'#555', weight:1 }});
      return;
    }}

    if (mode === 'winner') {{
      var color = p.COLOR_GANADOR || '#e0e0e0';
      var alpha = 0.3 + (p.MARGEN_PCT || 0) / 100 * 0.6;
      layer.setStyle({{ fillColor:color, fillOpacity:Math.min(alpha,0.9), color:'#555', weight:1 }});
      return;
    }}

    if (sel.length === 0) {{
      layer.setStyle({{ fillColor:'#e0e0e0', fillOpacity:0.3, color:'#888', weight:1 }});
      return;
    }}

    if (sel.length === 1) {{
      var cand = candOrder[sel[0]];
      var val = (mode === 'percentage') ? p['pct_'+cand] || 0 : p[cand] || 0;
      if (mode === 'difference') val = p['diff_'+cand] || 0;
      layer.setStyle({{ fillColor:getColor(val, mode, sel[0]), fillOpacity:0.85, color:'#555', weight:1 }});
      return;
    }}

    if (sel.length === 2) {{
      var c1 = candOrder[sel[0]], c2 = candOrder[sel[1]];
      var v1 = p[c1] || 0, v2 = p[c2] || 0;
      var diff = v1 - v2;
      var activeData = getActiveData();
      var maxAbs = 0;
      activeData.features.forEach(function(f) {{
        var d = Math.abs((f.properties[c1] || 0) - (f.properties[c2] || 0));
        if (d > maxAbs) maxAbs = d;
      }});
      if (maxAbs === 0) maxAbs = 1;
      var idx = Math.floor((diff / maxAbs + 1) / 2 * (rdbu.length - 1));
      idx = Math.min(Math.max(0, Math.round(idx)), rdbu.length - 1);
      layer.setStyle({{ fillColor:rdbu[idx], fillOpacity:0.85, color:'#555', weight:1 }});
      return;
    }}

    var color = p.COLOR_GANADOR || '#e0e0e0';
    var alpha = 0.3 + (p.MARGEN_PCT || 0) / 100 * 0.6;
    layer.setStyle({{ fillColor:color, fillOpacity:Math.min(alpha,0.9), color:'#555', weight:1 }});
  }}

  function refreshTooltips() {{
    var activeLayer = currentView === 'loc' ? locLayer : upzLayer;
    activeLayer.eachLayer(function(layer) {{
      layer.unbindTooltip();
      layer.bindTooltip(buildTooltip(layer.feature.properties), {{ sticky:false, direction:'top' }});
    }});
  }}

  function getColor(value, mode, candIdx) {{
    var cand = candOrder[candIdx];
    var min, max, palette;
    if (mode === 'relative') {{
      min = candRanges[cand].min; max = candRanges[cand].max; palette = ylorrd;
    }} else if (mode === 'percentage') {{
      min = 0; max = 100; palette = purples;
    }} else if (mode === 'difference') {{
      var d = diffMaxAbs[cand];
      min = -d; max = d;
    }}
    if (mode === 'difference') {{
      var mid = (max+min)/2;
      if (max===min) return rdbu[4];
      var idx;
      if (value <= mid) {{
        idx = Math.floor(((value-min)/(mid-min))*3); idx = Math.min(idx,3);
      }} else {{
        idx = 4+Math.floor(((value-mid)/(max-mid))*4); idx = Math.min(idx,8);
      }}
      return rdbu[Math.max(0,idx)];
    }}
    if (max===min) return palette[0];
    var idx = Math.floor(((value-min)/(max-min))*(palette.length-1));
    idx = Math.min(idx, palette.length-1);
    return palette[Math.max(0,idx)];
  }}

  function updateMap() {{
    var activeLayer = currentView === 'loc' ? locLayer : upzLayer;
    activeLayer.eachLayer(function(layer) {{ applyStyle(layer); }});
    refreshTooltips();
    updateLegend();
  }}

  function updateLegend() {{
    var el = document.getElementById('legend-content');
    var bar = document.getElementById('legend-bar');
    var labels = document.getElementById('legend-labels');
    var title = document.getElementById('legend-title');
    var viewLabel = currentView === 'loc' ? 'Localidad' : 'UPZ';
    var activeData = getActiveData();

    if (currentMode === 'comparative') {{
      title.textContent = 'Comparativo Cepeda 2026 vs Petro 2022 (delta pp)';
      var compR = getCompRange();
      bar.style.background = 'linear-gradient(to right, '+rdbu.join(', ')+')';
      bar.style.display = 'block';
      labels.style.display = 'flex';
      document.getElementById('legend-min').textContent = compR.min.toFixed(1) + ' pp';
      document.getElementById('legend-mid').textContent = '0';
      document.getElementById('legend-max').textContent = compR.max.toFixed(1) + ' pp';
      el.innerHTML = '<div style="font-size:11px;color:#666;margin-top:4px">Rojo = Cepeda pierde terreno<br>Azul = Cepeda mantiene/gana</div>';
      document.getElementById('legend').style.display = 'block';
      return;
    }}

    if (currentMode === 'winner') {{
      title.textContent = 'Ganador por ' + viewLabel + ' (intensidad = margen)';
      var counts = {{}};
      activeData.features.forEach(function(f) {{
        var g = f.properties.GANADOR || 'Sin datos';
        counts[g] = (counts[g] || 0) + 1;
      }});
      var html = '';
      var sorted = candOrder.filter(function(c) {{ return counts[c]; }});
      sorted.forEach(function(c) {{
        html += '<div class="legend-item"><span class="legend-swatch" style="background:'+(candColors[c]||'#ccc')+'"></span> '+
                c+' <span style="color:#888;font-size:10px">('+counts[c]+' '+viewLabel.toLowerCase()+(counts[c]!==1?'s':'')+')</span></div>';
      }});
      el.innerHTML = html;
      bar.style.display = 'none';
      labels.style.display = 'none';
      document.getElementById('legend').style.display = 'block';
      return;
    }}

    bar.style.display = 'block';
    labels.style.display = 'flex';

    if (selectedCands.length === 1) {{
      var cand = candOrder[selectedCands[0]];
      title.textContent = document.getElementById('mode-selector').options[document.getElementById('mode-selector').selectedIndex].text + ' — ' + cand;
      var legendPalette = (currentMode === 'percentage') ? purples : (currentMode === 'difference' ? rdbu : ylorrd);
      bar.style.background = 'linear-gradient(to right, '+legendPalette.join(', ')+')';
      var range;
      if (currentMode === 'relative') range = candRanges[cand];
      else if (currentMode === 'percentage') range = {{min:0, max:100}};
      else range = {{min:-diffMaxAbs[cand], max:diffMaxAbs[cand]}};
      if (currentMode === 'percentage') {{
        document.getElementById('legend-min').textContent = '0%';
        document.getElementById('legend-mid').textContent = '50%';
        document.getElementById('legend-max').textContent = '100%';
      }} else {{
        var mid = Math.round((range.min+range.max)/2).toLocaleString();
        document.getElementById('legend-min').textContent = Math.round(range.min).toLocaleString();
        document.getElementById('legend-mid').textContent = mid;
        document.getElementById('legend-max').textContent = Math.round(range.max).toLocaleString();
      }}
      el.innerHTML = '';
      document.getElementById('legend').style.display = 'block';
    }} else if (selectedCands.length === 2) {{
      var c1 = candOrder[selectedCands[0]], c2 = candOrder[selectedCands[1]];
      title.textContent = 'Diferencia: '+c1+' vs '+c2;
      bar.style.background = 'linear-gradient(to right, '+rdbu.join(', ')+')';
      document.getElementById('legend-min').textContent = 'M\u00e1s '+c2;
      document.getElementById('legend-mid').textContent = 'Empate';
      document.getElementById('legend-max').textContent = 'M\u00e1s '+c1;
      el.innerHTML = '';
      document.getElementById('legend').style.display = 'block';
    }} else {{
      document.getElementById('legend').style.display = 'none';
    }}
  }}

  // ─── EVENTOS ───
  document.getElementById('mode-selector').addEventListener('change', function() {{
    currentMode = this.value;
    document.getElementById('cand-selector').style.display = (currentMode === 'winner' || currentMode === 'comparative') ? 'none' : 'block';
    updateMap();
  }});

  document.getElementById('cand-selector').style.display = 'none';

  // Pass comparativo range to window so legend can use it
  window.getCompRange = getCompRange;

  updateMap();
}})();
</script>
</body>
</html>"""

map_path = os.path.join(OUT, 'mapa_bogota.html')
with open(map_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'  OK  {map_path}')
print(f'      - Modo GANADOR: todos los candidatos visibles a la vez')
print(f'      - Checkboxes multi-select para candidatos')
print(f'      - 1 selec: choropleth (relative / % / difference) | 2 selec: diferencia | 3+: ganador')
print(f'      - Modo comparativo 2022-2026: delta Cepeda vs Petro (RdBu)')
print(f'      - Paletas: YlOrRd (relative), Purples (%), RdBu (diferencia/comparativo)')
