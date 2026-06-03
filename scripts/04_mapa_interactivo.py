"""
Mapa interactivo redisenado:
  - 5 modos: Ganador, Relativo, % UPZ, Diferencia, Comparativo
  - Pill buttons en vez de dropdown
  - Checkboxes custom con swatches de color
  - Tooltip/popup profesionales
  - Toggle "Ver puestos" (para Fase 3)
  - Animaciones y transiciones
"""
import pandas as pd
import geopandas as gpd
import numpy as np
import os, json, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _theme import P, CAND_COLORS, FONT_FAMILY, FONT_MONO, CSS_RESET, YLORRD, RDBU, PURPLES
from _utils import fix_name

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(BASE, 'data', 'processed')
OUT = os.path.join(BASE, 'outputs')
os.makedirs(OUT, exist_ok=True)

votos = pd.read_csv(os.path.join(PROC, 'votos_por_upz.csv'))
votos['CANNOMBRE'] = votos['CANNOMBRE'].apply(fix_name)
upz_geo = gpd.read_file(os.path.join(PROC, 'upz_con_votos.geojson'))

comp_upz = pd.read_csv(os.path.join(PROC, 'comparativo_upz.csv'))
comp_by_loc = {r['Localidad']: r for r in json.load(open(os.path.join(PROC, 'comparativo_localidad.json'), encoding='utf-8'))}

cand_order = (
    votos.groupby('CANNOMBRE')['VOTOS'].sum()
    .sort_values(ascending=False).index.tolist()
)

pivot = votos.pivot_table(index='UPLCODIGO', columns='CANNOMBRE', values='VOTOS', aggfunc='sum').fillna(0).reset_index()
upz_geo_4326 = upz_geo.to_crs('EPSG:4326')
upz_geo_4326 = upz_geo_4326.merge(pivot, on='UPLCODIGO', how='left')
for col in cand_order:
    upz_geo_4326[col] = upz_geo_4326[col].fillna(0).astype(float)

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

for cand in cand_order:
    upz_geo_4326[f'pct_{cand}'] = np.where(
        upz_geo_4326[total_col] > 0,
        (upz_geo_4326[cand] / upz_geo_4326[total_col] * 100).round(2), 0,
    )
    mean_val = upz_geo_4326[cand].mean()
    upz_geo_4326[f'diff_{cand}'] = (upz_geo_4326[cand] - mean_val).round(0)
    # Residual: pct deviation from citywide avg pct (for rendimiento relativo)
    citywide_pct = (upz_geo_4326[cand].sum() / upz_geo_4326[total_col].sum() * 100) if upz_geo_4326[total_col].sum() > 0 else 0
    upz_geo_4326[f'residual_{cand}'] = np.where(
        upz_geo_4326[total_col] > 0,
        (upz_geo_4326[f'pct_{cand}'] - citywide_pct).round(1), 0,
    )

upz_geo_4326['GANADOR_IDX'] = upz_geo_4326[cand_order].idxmax(axis=1)
upz_geo_4326['GANADOR'] = upz_geo_4326['GANADOR_IDX']

# Segundo lugar: for each row, find the 2nd highest
def get_segundo(r):
    vals = {c: r[c] for c in cand_order}
    sorted_c = sorted(vals, key=vals.get, reverse=True)
    return sorted_c[1] if len(sorted_c) > 1 else sorted_c[0]
upz_geo_4326['SEGUNDO'] = upz_geo_4326.apply(get_segundo, axis=1)

vote_cols_arr = np.array([upz_geo_4326[c].values for c in cand_order])
sorted_votes = np.sort(vote_cols_arr, axis=0)
upz_geo_4326['MARGEN_VOTOS'] = sorted_votes[-1] - sorted_votes[-2]
upz_geo_4326['MARGEN_PCT'] = np.where(
    upz_geo_4326[total_col] > 0,
    (upz_geo_4326['MARGEN_VOTOS'] / upz_geo_4326[total_col] * 100).round(1), 0,
)

cand_colors_dict = dict(zip(cand_order, CAND_COLORS[:len(cand_order)]))
upz_geo_4326['COLOR_GANADOR'] = upz_geo_4326['GANADOR'].map(cand_colors_dict)

# Mark UPZs without data (0 total votes)
sin_datos_mask = upz_geo_4326[total_col] == 0
upz_geo_4326.loc[sin_datos_mask, 'GANADOR'] = 'Sin datos'
upz_geo_4326.loc[sin_datos_mask, 'SEGUNDO'] = 'Sin datos'
upz_geo_4326.loc[sin_datos_mask, 'COLOR_GANADOR'] = '#e0e0e0'
upz_geo_4326.loc[sin_datos_mask, 'MARGEN_PCT'] = 0.0

cand_ranges = {cand: {'min': float(upz_geo_4326[cand].min()), 'max': float(upz_geo_4326[cand].max())} for cand in cand_order}
global_max_votos = float(upz_geo_4326[cand_order].values.max())

diff_max_abs = {}
citywide_pcts = {}
for cand in cand_order:
    d = max(abs(upz_geo_4326[f'diff_{cand}'].min()), abs(upz_geo_4326[f'diff_{cand}'].max()))
    diff_max_abs[cand] = d if d > 0 else 1
    citywide_pcts[cand] = round((upz_geo_4326[cand].sum() / upz_geo_4326[total_col].sum() * 100), 1) if upz_geo_4326[total_col].sum() > 0 else 0

# ─── POPUP ───
def make_popup(props, is_loc=False):
    uplnombre = props.get('UPLNOMBRE', '')
    locnombre = props.get('LOCNOMBRE', '')
    total = int(props.get(total_col, 0) or 0)

    if total == 0:
        label = ' (Localidad)' if is_loc else ''
        return (
            f'<div class="pp">'
            f'<div class="pp-header"><span class="pp-title">{uplnombre}{label}</span>'
            f'<span class="pp-subtitle">{locnombre}</span></div>'
            f'<div style="padding:24px;text-align:center;font-size:13px;color:{P["text-secondary"]}">'
            f'Sin datos electorales para esta zona</div></div>'
        )

    rows = []
    for cand in cand_order:
        v = int(props.get(cand, 0) or 0)
        p = props.get(f'pct_{cand}', 0)
        rows.append((cand, v, p))
    rows.sort(key=lambda x: x[1], reverse=True)
    max_v = rows[0][1] if rows else 1
    popup_rows = ''
    for r in rows:
        name, v, pct = r
        bar_pct = (v / max_v * 100) if max_v > 0 else 0
        color = cand_colors_dict.get(name, '#ccc')
        popup_rows += (
            f'<tr><td class="pp-name">{name}</td>'
            f'<td class="pp-num">{v:,}</td>'
            f'<td class="pp-num">{pct:.1f}%</td>'
            f'<td class="pp-bar"><div class="pp-bar-fill" style="width:{bar_pct:.0f}%;background:{color}"></div></td></tr>'
        )
    d1v = props.get('delta_petro_1v_pp', 0)
    vc26 = int(props.get('votos_cepeda_1v26', 0))
    vp22 = int(props.get('votos_petro_1v22', 0))
    d1v_pct = round(d1v * 100, 1) if d1v != 0 else 0
    comp_html = ''
    if d1v != 0:
        comp_html = f'<div class="pp-comp"><strong>Comparativo 2022-2026</strong><br>Cepeda 26: {vc26:,} votos | Petro 22: {vp22:,} votos<br><span class="pp-delta">Delta: {d1v_pct:+.1f} pp</span></div>'
    label = ' (Localidad)' if is_loc else ''
    return (
        f'<div class="pp">'
        f'<div class="pp-header"><span class="pp-title">{uplnombre}{label}</span>'
        f'<span class="pp-subtitle">{locnombre} &middot; {total:,} votos</span></div>'
        f'<table class="pp-table"><thead><tr>'
        f'<th>Candidato</th><th class="pp-num">Votos</th><th class="pp-num">%</th><th></th></tr></thead>'
        f'<tbody>{popup_rows}</tbody></table>'
        f'{comp_html}</div>'
    )

for idx in upz_geo_4326.index:
    props = upz_geo_4326.loc[idx]
    upz_geo_4326.at[idx, '_popup'] = make_popup(props)

keep_cols = (['UPLCODIGO','UPLNOMBRE','LOCNOMBRE','LOCCODIGO',total_col,
              '_popup','GANADOR','SEGUNDO','MARGEN_VOTOS','MARGEN_PCT','COLOR_GANADOR',
              'GANADOR_IDX','geometry'] + cand_order
             + [f'pct_{c}' for c in cand_order]
             + [f'diff_{c}' for c in cand_order]
             + [f'residual_{c}' for c in cand_order]
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
loc_geo = loc_geo.merge(loc_agg_sum, on='LOCNOMBRE', how='left').merge(loc_agg_first, on='LOCNOMBRE', how='left')
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
    citywide_pct_loc = (loc_geo[cand].sum() / loc_geo[total_col].sum() * 100) if loc_geo[total_col].sum() > 0 else 0
    loc_geo[f'residual_{cand}'] = np.where(
        loc_geo[total_col] > 0,
        (loc_geo[f'pct_{cand}'] - citywide_pct_loc).round(1), 0,
    )

def get_segundo_loc(r):
    vals = {c: r[c] for c in cand_order}
    sorted_c = sorted(vals, key=vals.get, reverse=True)
    return sorted_c[1] if len(sorted_c) > 1 else sorted_c[0]
loc_geo['SEGUNDO'] = loc_geo.apply(get_segundo_loc, axis=1)
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

for idx in loc_geo.index:
    props = loc_geo.loc[idx]
    loc_geo.at[idx, '_popup'] = make_popup(props, is_loc=True)

keep_loc = (['LOCNOMBRE', total_col, '_popup', 'GANADOR', 'SEGUNDO',
             'MARGEN_VOTOS', 'MARGEN_PCT', 'COLOR_GANADOR',
             'GANADOR_IDX', 'geometry'] + cand_order
            + [f'pct_{c}' for c in cand_order]
            + [f'diff_{c}' for c in cand_order]
            + [f'residual_{c}' for c in cand_order]
            + comp_fields)
drop_loc = [c for c in loc_geo.columns if c not in keep_loc]
loc_clean = loc_geo.drop(columns=drop_loc)
loc_clean['UPLNOMBRE'] = loc_clean['LOCNOMBRE']
loc_clean['UPLCODIGO'] = loc_clean['LOCNOMBRE']
loc_json_str = json.dumps(loc_clean.__geo_interface__, ensure_ascii=False)

# ─── HTML ───
html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mapa Electoral Bogota 2026</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
<style>
  {CSS_RESET}
  body {{ overflow:hidden; }}
  #map {{ width:100vw; height:100vh; background:{P['bg']}; }}

  /* ── CONTROL PANEL ── */
  .panel {{ position:absolute; top:16px; right:16px; z-index:1000;
    background:rgba(255,255,255,0.96); backdrop-filter:blur(8px);
    border-radius:12px; padding:14px; width:260px;
    box-shadow:0 4px 16px rgba(0,0,0,0.1); font-family:{FONT_FAMILY}; font-size:13px; color:{P['text']};
    transition:opacity 0.2s, transform 0.2s; max-height:calc(100vh - 32px); overflow-y:auto; }}
  .panel::-webkit-scrollbar {{ width:4px; }}
  .panel::-webkit-scrollbar-thumb {{ background:{P['border']}; border-radius:2px; }}

  /* Mode pills */
  .mode-pills {{ display:flex; flex-wrap:wrap; gap:4px; margin-bottom:10px; }}
  .mode-pill {{ padding:5px 10px; border:1px solid {P['border']}; border-radius:6px;
    font-size:11px; font-weight:500; cursor:pointer; transition:all 0.15s;
    background:white; color:{P['text-secondary']};
    font-family:{FONT_FAMILY}; line-height:1.2; }}
  .mode-pill:hover {{ border-color:{P['primary']}; color:{P['primary']}; background:{P['primary-bg']}; }}
  .mode-pill.active {{ background:{P['primary']}; color:white; border-color:{P['primary']}; }}

  /* Toggle buttons */
  .toggles {{ display:flex; gap:4px; margin-bottom:8px; }}
  .toggle-btn {{ flex:1; padding:5px 0; border:1px solid {P['border']}; border-radius:6px;
    font-size:11px; font-weight:500; cursor:pointer; transition:all 0.15s;
    background:white; color:{P['text-secondary']}; text-align:center; font-family:{FONT_FAMILY}; }}
  .toggle-btn:hover {{ border-color:{P['primary']}; }}
  .toggle-btn.active {{ background:{P['primary']}; color:white; border-color:{P['primary']}; }}

  /* Switch toggle (Ver puestos) */
  .switch-row {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:8px; padding:4px 0; }}
  .switch-label {{ font-size:11px; font-weight:500; color:{P['text-secondary']}; }}
  .switch {{ position:relative; width:36px; height:20px; flex-shrink:0; cursor:pointer; }}
  .switch input {{ opacity:0; width:0; height:0; }}
  .switch-slider {{ position:absolute; inset:0; background:{P['border']}; border-radius:10px; transition:0.2s; }}
  .switch-slider::before {{ content:''; position:absolute; width:16px; height:16px; left:2px; bottom:2px; background:white; border-radius:50%; transition:0.2s; }}
  .switch input:checked + .switch-slider {{ background:{P['primary']}; }}
  .switch input:checked + .switch-slider::before {{ transform:translateX(16px); }}

  /* Checkbox group */
  .cand-section {{ border-top:1px solid {P['border-light']}; padding-top:8px; margin-top:4px; }}
  .cand-section-title {{ font-size:11px; font-weight:600; color:{P['text-secondary']}; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.5px; }}
  .checkbox-group {{ max-height:180px; overflow-y:auto; }}
  .checkbox-group::-webkit-scrollbar {{ width:3px; }}
  .checkbox-group::-webkit-scrollbar-thumb {{ background:{P['border']}; border-radius:2px; }}
  .cand-row {{ display:flex; align-items:center; gap:6px; padding:3px 0; cursor:pointer; font-size:12px; }}
  .cand-row:hover {{ color:{P['primary']}; }}
  .cand-check {{ display:none; }}
  .cand-custom {{ width:16px; height:16px; border:2px solid {P['border']}; border-radius:4px; flex-shrink:0; transition:all 0.15s; display:flex; align-items:center; justify-content:center; }}
  .cand-check:checked + .cand-custom {{ background:{P['primary']}; border-color:{P['primary']}; }}
  .cand-check:checked + .cand-custom::after {{ content:'✓'; color:white; font-size:10px; font-weight:700; line-height:1; }}
  .cand-swatch {{ width:10px; height:10px; border-radius:2px; flex-shrink:0; }}
  .cand-name {{ flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
  .sel-count {{ font-size:10px; color:{P['text-hint']}; margin-top:4px; }}

  /* ── LEGEND ── */
  .legend {{ position:absolute; bottom:30px; right:16px; z-index:1000;
    background:rgba(255,255,255,0.96); backdrop-filter:blur(8px);
    padding:12px 16px; border-radius:10px; font-size:12px;
    box-shadow:0 2px 8px rgba(0,0,0,0.1); min-width:190px; display:none;
    font-family:{FONT_FAMILY}; }}
  .legend-title {{ font-size:11px; font-weight:600; color:{P['text']}; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.3px; }}
  .legend-bar {{ width:100%; height:12px; border-radius:4px; margin:6px 0; }}
  .legend-labels {{ display:flex; justify-content:space-between; font-size:10px; color:{P['text-secondary']}; }}
  .legend-item {{ display:flex; align-items:center; gap:6px; font-size:11px; padding:2px 0; }}
  .legend-item:hover {{ color:{P['primary']}; }}
  .legend-swatch {{ width:12px; height:12px; border-radius:3px; flex-shrink:0; }}
  .legend-count {{ color:{P['text-hint']}; font-size:10px; }}
  .legend-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:2px; }}

  /* ── TOOLTIP ── */
  .leaflet-tooltip {{ background:white !important; border:none !important; border-radius:8px !important;
    padding:8px 12px !important; box-shadow:0 2px 10px rgba(0,0,0,0.15) !important;
    font-family:{FONT_FAMILY} !important; font-size:12px !important; color:{P['text']} !important;
    line-height:1.5 !important; }}
  .leaflet-tooltip-top::before {{ border-top-color:white !important; }}
  .tt-name {{ font-weight:600; }}
  .tt-sub {{ color:{P['text-secondary']}; font-size:11px; }}
  .tt-val {{ color:{P['primary']}; font-weight:500; font-size:12px; }}
  .tt-total {{ color:{P['text-hint']}; font-size:10px; }}

  /* ── POPUP ── */
  .leaflet-popup-content-wrapper {{ border-radius:12px !important; padding:0 !important;
    box-shadow:0 4px 20px rgba(0,0,0,0.15) !important; font-family:{FONT_FAMILY} !important; }}
  .leaflet-popup-content {{ margin:0 !important; padding:0 !important; min-width:360px; }}
  .pp {{ padding:0; }}
  .pp-header {{ background:{P['primary']}; color:white; padding:12px 16px; }}
  .pp-title {{ font-size:15px; font-weight:600; display:block; }}
  .pp-subtitle {{ font-size:11px; opacity:0.85; display:block; margin-top:2px; }}
  .pp-table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  .pp-table th {{ padding:6px 10px; font-size:10px; font-weight:500; color:{P['text-secondary']}; text-transform:uppercase; letter-spacing:0.3px;
    background:{P['bg']}; border-bottom:1px solid {P['border-light']}; }}
  .pp-table td {{ padding:4px 10px; border-bottom:1px solid {P['border-light']}; }}
  .pp-table tr:last-child td {{ border-bottom:none; }}
  .pp-name {{ font-weight:500; }}
  .pp-num {{ font-family:{FONT_MONO}; font-size:12px; text-align:right; white-space:nowrap; }}
  .pp-bar {{ width:80px; }}
  .pp-bar-fill {{ height:8px; border-radius:4px; min-width:2px; transition:width 0.3s; }}
  .pp-comp {{ padding:10px 16px; background:{P['primary-bg']}; font-size:12px; color:{P['text']}; line-height:1.6; }}
  .pp-comp strong {{ font-size:11px; text-transform:uppercase; letter-spacing:0.3px; color:{P['text-secondary']}; display:block; margin-bottom:2px; }}
  .pp-delta {{ font-weight:600; color:{P['primary']}; }}

  /* ── HINT ── */
  .hint {{ position:absolute; bottom:30px; left:16px; z-index:1000;
    background:rgba(255,255,255,0.9); backdrop-filter:blur(4px);
    padding:6px 12px; border-radius:8px; font-family:{FONT_FAMILY}; font-size:11px;
    box-shadow:0 1px 4px rgba(0,0,0,0.06); color:{P['text-hint']}; }}

  /* ── RESPONSIVE ── */
  @media (max-width:768px) {{
    .panel {{ top:8px; right:8px; width:220px; padding:10px; font-size:12px; }}
    .mode-pill {{ font-size:10px; padding:4px 8px; }}
    .pp {{ min-width:280px; }}
    .hint {{ display:none; }}
  }}
  @media (max-width:480px) {{
    .panel {{ width:200px; right:4px; top:4px; padding:8px; }}
    .checkbox-group {{ max-height:120px; }}
  }}

  /* ── TRANSITIONS ── */
  .leaflet-interactive {{ transition:fill-opacity 0.2s, stroke-opacity 0.2s; }}
</style>
</head>
<body>
<div id="map"></div>

<div class="panel" id="panel">
  <!-- Mode pills -->
  <div class="mode-pills" id="mode-pills">
    <button class="mode-pill active" data-mode="winner">Ganador</button>
    <button class="mode-pill" data-mode="relative">Relativo</button>
    <button class="mode-pill" data-mode="percentage">% UPZ</button>
    <button class="mode-pill" data-mode="difference">Diferen.</button>
    <button class="mode-pill" data-mode="runnerup">2 Lugar</button>
    <button class="mode-pill" data-mode="performance">Rendim.</button>
    <button class="mode-pill" data-mode="comparative">Comp.</button>
  </div>

  <!-- View toggle -->
  <div class="toggles">
    <button class="toggle-btn active" data-view="upz">UPZ</button>
    <button class="toggle-btn" data-view="loc">Localidad</button>
  </div>

  <!-- Polling station toggle -->
  <div class="switch-row">
    <span class="switch-label">Ver puestos</span>
    <label class="switch">
      <input type="checkbox" id="toggle-puestos" onchange="togglePuestos()">
      <span class="switch-slider"></span>
    </label>
  </div>

  <!-- Candidate selection -->
  <div class="cand-section" id="cand-section">
    <div class="cand-section-title">Candidatos</div>
    <div class="checkbox-group" id="checkbox-group">
      <label class="cand-row" style="font-weight:600;font-size:11px;color:{P['text-secondary']}">
        <input type="checkbox" class="cand-check" id="check-all" checked onchange="toggleAll()">
        <span class="cand-custom"></span>
        <span class="cand-name">Todos</span>
      </label>
      {"".join(
        f'<label class="cand-row">'
        f'<input type="checkbox" class="cand-check" value="{i}" checked onchange="updateSelected(\'{cand}\')">'
        f'<span class="cand-custom"></span>'
        f'<span class="cand-swatch" style="background:{cand_colors_dict[cand]}"></span>'
        f'<span class="cand-name">{cand}</span></label>'
        for i, cand in enumerate(cand_order)
      )}
    </div>
    <div class="sel-count" id="sel-count">13 seleccionados</div>
  </div>
</div>

<div class="legend" id="legend">
  <div class="legend-title" id="legend-title">Ganador por UPZ</div>
  <div id="legend-content"></div>
  <div class="legend-bar" id="legend-bar" style="display:none"></div>
  <div class="legend-labels" id="legend-labels" style="display:none">
    <span id="legend-min">0</span>
    <span id="legend-mid">0</span>
    <span id="legend-max">0</span>
  </div>
</div>

<div class="hint">UPZ / Localidad &middot; Hover para info &middot; Click para detalle</div>

<script>
(function() {{
  var geoData = {geo_json_str};
  var locGeoData = {loc_json_str};
  var candOrder = {json.dumps(cand_order, ensure_ascii=False)};
  var candColors = {json.dumps(cand_colors_dict, ensure_ascii=False)};
  var globalMaxVotos = {global_max_votos};
  var candRanges = {json.dumps(cand_ranges)};
  var diffMaxAbs = {json.dumps(diff_max_abs)};
  var citywidePcts = {json.dumps(citywide_pcts)};
  var ylorrd = {json.dumps(YLORRD)};
  var rdbu = {json.dumps(RDBU)};
  var purples = {json.dumps(PURPLES)};

  var currentMode = 'winner';
  var currentView = 'upz';
  var selectedCands = candOrder.map(function(_,i) {{ return i; }});
  var puestosLayer = null;

  function getSelectedIndices() {{
    var checks = document.querySelectorAll('.cand-check:checked:not(#check-all)');
    return Array.from(checks).map(function(c) {{ return parseInt(c.value); }});
  }}

  function getActiveData() {{
    return currentView === 'loc' ? locGeoData : geoData;
  }}

  window.updateSelected = function() {{
    selectedCands = getSelectedIndices();
    document.getElementById('sel-count').textContent = selectedCands.length + ' seleccionado' + (selectedCands.length !== 1 ? 's' : '');
    var allCheck = document.getElementById('check-all');
    var total = document.querySelectorAll('.cand-check:not(#check-all)').length;
    var checked = selectedCands.length;
    allCheck.checked = checked === total;
    updateMap();
  }};

  window.toggleAll = function() {{
    var checked = document.getElementById('check-all').checked;
    document.querySelectorAll('.cand-check:not(#check-all)').forEach(function(c) {{ c.checked = checked; }});
    updateSelected();
  }};

  // ─── MAP ───
  var map = L.map('map', {{ center:[4.65,-74.1], zoom:11, zoomControl:true,
    zoomSnap:0.5, zoomDelta:0.5, wheelPxPerZoomLevel:120 }});
  L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
    attribution:'&copy; <a href="https://carto.com">CARTO</a>', subdomains:'abcd', maxZoom:19
  }}).addTo(map);

  // ─── PUESTOS LAYER (placeholder, loaded from external GeoJSON) ───
  window.togglePuestos = function() {{
    var checked = document.getElementById('toggle-puestos').checked;
    if (checked) {{
      if (!puestosLayer) {{
        // Load puestos data - will be populated in Fase 3
        fetch('puestos_con_votos.geojson')
          .then(function(r) {{ return r.json(); }})
          .then(function(data) {{
            puestosLayer = buildPuestosLayer(data);
            map.addLayer(puestosLayer);
          }})
          .catch(function() {{
            // Fallback: no puestos data yet
            document.getElementById('toggle-puestos').checked = false;
          }});
      }} else {{
        map.addLayer(puestosLayer);
      }}
    }} else {{
      if (puestosLayer) map.removeLayer(puestosLayer);
    }}
  }};

  function buildPuestosLayer(data) {{
    var cluster = L.markerClusterGroup({{
      maxClusterRadius: 50,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      zoomToBoundsOnClick: true,
      iconCreateFunction: function(cluster) {{
        var childCount = cluster.getChildCount();
        return L.divIcon({{ html: '<div style="background:'+'{P['primary']}'+';color:white;border-radius:50%;width:36px;height:36px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;box-shadow:0 2px 6px rgba(0,0,0,0.2)">'+childCount+'</div>', className:'', iconSize:L.point(36,36) }});
      }}
    }});
    L.geoJSON(data, {{
      pointToLayer: function(feature, latlng) {{
        var p = feature.properties;
        var r = Math.max(3, Math.sqrt(p.TOTAL_VOTOS || 100) / 10);
        return L.circleMarker(latlng, {{
          radius: r, fillColor: candColors[p.GANADOR] || '#ccc',
          color: 'white', weight: 1, fillOpacity: 0.8
        }});
      }},
      onEachFeature: function(feature, layer) {{
        var p = feature.properties;
        var nom = p.NOMBRE || 'Puesto';
        var gan = p.GANADOR || 'N/A';
        var total = Number(p.TOTAL_VOTOS || 0);
        var vg = Number(p.VOTOS_GANADOR || 0);
        var pct = Number(p.PCT_GANADOR || 0);
        var dir = p.DIRECCION || '';
        var loc = p.LOCALIDAD || '';
        var color = candColors[gan] || '#ccc';
        layer.bindTooltip('<div class="tt-name">' + nom + '</div>' +
          '<div class="tt-sub">' + loc + '</div>' +
          '<div class="tt-val">' + gan + '</div>' +
          '<div class="tt-total">' + total.toLocaleString() + ' votos &middot; ' + pct.toFixed(1) + '%</div>', {{
          sticky: true, direction:'top', offset:L.point(0,-8)
        }});
        var popupContent = '<div class="pp"><div class="pp-header"><span class="pp-title">' + nom +
          '</span><span class="pp-subtitle">' + dir + '</span></div>' +
          '<div style="padding:12px 16px">' +
          '<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #F0F0F0;font-size:12px"><span style="color:#757575">Localidad</span><span style="font-weight:600;color:#333">' + loc + '</span></div>' +
          '<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #F0F0F0;font-size:12px"><span style="color:#757575">Ganador</span><span style="font-weight:600;color:' + color + '">' + gan + '</span></div>' +
          '<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #F0F0F0;font-size:12px"><span style="color:#757575">Total votos</span><span style="font-weight:600;font-family:JetBrains Mono,monospace;color:#333">' + total.toLocaleString() + '</span></div>' +
          '<div style="display:flex;justify-content:space-between;padding:5px 0;font-size:12px"><span style="color:#757575">Votos ganador</span><span style="font-weight:600;font-family:JetBrains Mono,monospace;color:#333">' + vg.toLocaleString() + ' (' + pct.toFixed(1) + '%)</span></div>' +
          '</div></div>';
        layer.bindPopup(popupContent, {{ maxWidth:340, className:'' }});
      }}
    }}).eachLayer(function(l) {{ cluster.addLayer(l); }});
    return cluster;
  }}

  // ─── STYLE FUNCTIONS ───
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

  function buildTooltip(p) {{
    if (!p.TOTAL_VOTOS) {{
      return '<div class="tt-name">' + (p.UPLNOMBRE || p.LOCNOMBRE || '') + '</div>' +
        (currentView === 'upz' && p.LOCNOMBRE ? '<div class="tt-sub">'+p.LOCNOMBRE+'</div>' : '') +
        '<div class="tt-val" style="color:#9E9E9E">Sin datos electorales</div>';
    }}
    var sel = selectedCands;
    var mode = currentMode;
    var name = p.UPLNOMBRE || p.LOCNOMBRE || '';
    var loc = (currentView === 'upz' && p.LOCNOMBRE) ? '<div class="tt-sub">'+p.LOCNOMBRE+'</div>' : '';
    var extra = '', val;
    if (mode === 'winner') {{
      extra = '<div class="tt-val">Ganador: ' + (p.GANADOR || '') + '</div>' +
        '<div class="tt-total">Margen: ' + (p.MARGEN_PCT || 0).toFixed(1) + '%</div>';
    }} else if (mode === 'runnerup') {{
      extra = '<div class="tt-val">2 Lugar: ' + (p.SEGUNDO || '') + '</div>' +
        '<div class="tt-total">Ganador: ' + (p.GANADOR || '') + ' | Margen: ' + (p.MARGEN_PCT || 0).toFixed(1) + '%</div>';
    }} else if (mode === 'performance') {{
      if (sel.length === 1) {{
        var cand = candOrder[sel[0]];
        var resid = parseFloat(p['residual_'+cand]) || 0;
        extra = '<div class="tt-val">Rendimiento: ' + (resid > 0 ? '+' : '') + resid.toFixed(1) + ' pp</div>' +
          '<div class="tt-total">' + cand + ' vs promedio citywide (' + citywidePcts[cand] + '%)</div>';
      }}
    }} else if (mode === 'comparative') {{
      var d = p.delta_petro_1v_pp || 0;
      extra = '<div class="tt-val">Delta: ' + (d > 0 ? '+' : '') + (d*100).toFixed(1) + ' pp</div>' +
        '<div class="tt-total">Cepeda 26 vs Petro 22</div>';
    }} else if (sel.length === 1) {{
      var cand = candOrder[sel[0]];
      if (mode === 'percentage') {{
        val = (p['pct_'+cand] || 0).toFixed(1) + '%';
      }} else if (mode === 'difference') {{
        var dv = p['diff_'+cand] || 0;
        val = (dv > 0 ? '+' : '') + Number(dv).toLocaleString() + ' vs promedio';
      }} else {{
        val = Number(p[cand] || 0).toLocaleString() + ' votos';
      }}
      extra = '<div class="tt-val">' + val + '</div><div class="tt-total">' + cand + '</div>';
    }} else if (sel.length === 2) {{
      var c1 = candOrder[sel[0]], c2 = candOrder[sel[1]];
      extra = '<div class="tt-val">' + c1 + ': ' + Number(p[c1] || 0).toLocaleString() + '</div>' +
        '<div class="tt-val">' + c2 + ': ' + Number(p[c2] || 0).toLocaleString() + '</div>';
    }} else {{
      extra = '<div class="tt-val">Ganador: ' + (p.GANADOR || '') + '</div>';
    }}
    var total = (p.TOTAL_VOTOS && mode !== 'comparative') ? '<div class="tt-total">Total: ' + Number(p.TOTAL_VOTOS).toLocaleString() + ' votos</div>' : '';
    return '<div class="tt-name">' + name + '</div>' + loc + extra + total;
  }}

  function onEachFeature(feature, layer) {{
    var p = feature.properties;
    if (p._popup) layer.bindPopup(p._popup, {{ maxWidth:420, className:'' }});
    layer.bindTooltip(buildTooltip(p), {{ sticky:false, direction:'top', offset:L.point(0,-6) }});
  }}

  function makeLayer(data) {{
    return L.geoJson(data, {{
      style: function() {{ return {{ fillColor:'#e0e0e0', fillOpacity:0.3, color:'#bbb', weight:0.5 }}; }},
      onEachFeature: onEachFeature,
    }});
  }}

  var upzLayer = makeLayer(geoData);
  var locLayer = makeLayer(locGeoData);
  upzLayer.addTo(map);
  map.fitBounds(upzLayer.getBounds().pad(0.05));

  // Layer hover effects
  function addHover(layer) {{
    layer.eachLayer(function(l) {{
      l.on('mouseover', function(e) {{
        e.target.setStyle({{ weight:1.5, color:'#333', fillOpacity:0.6 }});
        if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) e.target.bringToFront();
      }});
      l.on('mouseout', function(e) {{ applyStyle(e.target); }});
    }});
  }}
  addHover(upzLayer);
  addHover(locLayer);

  // ─── APPLY STYLE ───
  function applyStyle(layer) {{
    var p = layer.feature.properties;
    var sel = selectedCands;
    var mode = currentMode;
    var style = {{ color:'#bbb', weight:0.5, fillOpacity:0.85 }};

    if (mode === 'comparative') {{
      var d = parseFloat(p.delta_petro_1v_pp) || 0;
      var compR = getCompRange();
      var minD = compR.min, maxD = compR.max;
      var idx;
      if (minD === maxD) idx = 4;
      else if (d >= 0) {{ idx = Math.min(4 + Math.floor((d / (maxD||1)) * 4), 8); }}
      else {{ idx = Math.max(0, 4 - Math.floor((d - minD) / (-(minD||1)) * 4)); }}
      style.fillColor = rdbu[Math.max(0, Math.min(Math.round(idx), 8))];
      layer.setStyle(style);
      return;
    }}

    if (!p.TOTAL_VOTOS) {{
      style.fillColor = '#e0e0e0'; style.fillOpacity = 0.15;
      layer.setStyle(style);
      return;
    }}

    if (mode === 'winner') {{
      style.fillColor = p.COLOR_GANADOR || '#e0e0e0';
      style.fillOpacity = 0.3 + (p.MARGEN_PCT || 0) / 100 * 0.6;
      layer.setStyle(style);
      return;
    }}

    if (mode === 'runnerup') {{
      // Segundo lugar: color del segundo lugar, opacidad = 1 - margen (menos margen = mas cerca = mas opaco)
      var segundo = p.SEGUNDO || '';
      style.fillColor = candColors[segundo] || '#e0e0e0';
      style.fillOpacity = 0.8 - (p.MARGEN_PCT || 0) / 100 * 0.5;
      layer.setStyle(style);
      return;
    }}

    if (mode === 'performance') {{
      if (sel.length === 1) {{
        var cand = candOrder[sel[0]];
        var residual = parseFloat(p['residual_'+cand]) || 0;
        var maxRes = Math.max(1, Math.abs(citywidePcts[cand]) || 10);
        var idx = Math.floor((residual / maxRes + 1) / 2 * (rdbu.length - 1));
        idx = Math.min(Math.max(0, Math.round(idx)), rdbu.length - 1);
        style.fillColor = rdbu[idx];
        layer.setStyle(style);
        return;
      }}
      // Fallback to winner if no candidate selected
      style.fillColor = p.COLOR_GANADOR || '#e0e0e0';
      style.fillOpacity = 0.3;
      layer.setStyle(style);
      return;
    }}

    if (sel.length === 0) {{
      style.fillColor = '#e0e0e0'; style.fillOpacity = 0.3;
      layer.setStyle(style);
      return;
    }}

    if (sel.length === 1) {{
      var cand = candOrder[sel[0]];
      var val = (mode === 'percentage') ? p['pct_'+cand] || 0 : p[cand] || 0;
      if (mode === 'difference') val = p['diff_'+cand] || 0;
      style.fillColor = getColor(val, mode, sel[0]);
      layer.setStyle(style);
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
      style.fillColor = rdbu[idx];
      layer.setStyle(style);
      return;
    }}

    style.fillColor = p.COLOR_GANADOR || '#e0e0e0';
    style.fillOpacity = 0.3 + (p.MARGEN_PCT || 0) / 100 * 0.6;
    layer.setStyle(style);
  }}

  function getColor(value, mode, candIdx) {{
    var cand = candOrder[candIdx];
    var min, max, palette;
    if (mode === 'relative') {{ min = candRanges[cand].min; max = candRanges[cand].max; palette = ylorrd; }}
    else if (mode === 'percentage') {{ min = 0; max = 100; palette = purples; }}
    else if (mode === 'difference') {{ var d = diffMaxAbs[cand]; min = -d; max = d; }}
    if (mode === 'difference') {{
      var mid = (max+min)/2;
      if (max===min) return rdbu[4];
      var idx;
      if (value <= mid) {{ idx = Math.floor(((value-min)/(mid-min))*3); idx = Math.min(idx,3); }}
      else {{ idx = 4+Math.floor(((value-mid)/(max-mid))*4); idx = Math.min(idx,8); }}
      return rdbu[Math.max(0,idx)];
    }}
    if (max===min) return palette[0];
    var idx = Math.floor(((value-min)/(max-min))*(palette.length-1));
    idx = Math.min(idx, palette.length-1);
    return palette[Math.max(0,idx)];
  }}

  function refreshTooltips() {{
    var activeLayer = currentView === 'loc' ? locLayer : upzLayer;
    activeLayer.eachLayer(function(layer) {{
      layer.unbindTooltip();
      layer.bindTooltip(buildTooltip(layer.feature.properties), {{ sticky:false, direction:'top', offset:L.point(0,-6) }});
    }});
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
      title.textContent = 'Delta Cepeda 26 vs Petro 22 (pp)';
      var compR = getCompRange();
      bar.style.background = 'linear-gradient(to right, '+rdbu.join(', ')+')';
      bar.style.display = 'block';
      labels.style.display = 'flex';
      document.getElementById('legend-min').textContent = (compR.min*100).toFixed(1) + ' pp';
      document.getElementById('legend-mid').textContent = '0';
      document.getElementById('legend-max').textContent = (compR.max*100).toFixed(1) + ' pp';
      el.innerHTML = '<div style="font-size:10px;color:{P['text-hint']};margin-top:4px">Rojo = Cepeda pierde | Azul = Cepeda gana</div>';
      document.getElementById('legend').style.display = 'block';
      return;
    }}

    if (currentMode === 'winner' || currentMode === 'runnerup') {{
      var label = currentMode === 'winner' ? 'Ganador' : 'Segundo lugar';
      title.textContent = label + ' por ' + viewLabel;
      var key = currentMode === 'winner' ? 'GANADOR' : 'SEGUNDO';
      var counts = {{}};
      activeData.features.forEach(function(f) {{
        var g = f.properties[key] || 'Sin datos';
        counts[g] = (counts[g] || 0) + 1;
      }});
      var html = '<div class="legend-grid">';
      candOrder.forEach(function(c) {{
        if (counts[c]) {{
          html += '<div class="legend-item"><span class="legend-swatch" style="background:'+(candColors[c]||'#ccc')+'"></span> '+
            c.split(' ').slice(0,2).join(' ') + ' <span class="legend-count">'+counts[c]+'</span></div>';
        }}
      }});
      if (counts['Sin datos']) {{
        html += '<div class="legend-item"><span class="legend-swatch" style="background:#e0e0e0"></span> Sin datos <span class="legend-count">'+counts['Sin datos']+'</span></div>';
      }}
      html += '</div>';
      el.innerHTML = html;
      bar.style.display = 'none'; labels.style.display = 'none';
      document.getElementById('legend').style.display = 'block';
      return;
    }}

    if (currentMode === 'performance') {{
      if (selectedCands.length === 1) {{
        var cand = candOrder[selectedCands[0]];
        title.textContent = 'Rendimiento - ' + cand.split(' ').slice(0,2).join(' ');
        var maxRes = Math.max(5, Math.abs(citywidePcts[cand]) || 10);
        bar.style.background = 'linear-gradient(to right, '+rdbu.join(', ')+')';
        bar.style.display = 'block'; labels.style.display = 'flex';
        document.getElementById('legend-min').textContent = '-' + maxRes.toFixed(0) + ' pp';
        document.getElementById('legend-mid').textContent = '0 (promedio)';
        document.getElementById('legend-max').textContent = '+' + maxRes.toFixed(0) + ' pp';
        el.innerHTML = '<div style="font-size:10px;color:{P['text-hint']};margin-top:4px">Rojo = sobre-rendimiento | Azul = sub-rendimiento</div>';
        document.getElementById('legend').style.display = 'block';
      }} else {{
        document.getElementById('legend').style.display = 'none';
      }}
      return;
    }}

    bar.style.display = 'block';
    labels.style.display = 'flex';

    if (selectedCands.length === 1) {{
      var cand = candOrder[selectedCands[0]];
      var activePill = document.querySelector('.mode-pill.active');
      title.textContent = (activePill ? activePill.textContent : '') + ' - ' + cand.split(' ').slice(0,2).join(' ');
      var legendPalette = currentMode === 'percentage' ? purples : (currentMode === 'difference' ? rdbu : ylorrd);
      bar.style.background = 'linear-gradient(to right, '+legendPalette.join(', ')+')';
      if (currentMode === 'percentage') {{
        document.getElementById('legend-min').textContent = '0%';
        document.getElementById('legend-mid').textContent = '50%';
        document.getElementById('legend-max').textContent = '100%';
      }} else if (currentMode === 'difference') {{
        var d = diffMaxAbs[cand];
        document.getElementById('legend-min').textContent = '-' + Math.round(d).toLocaleString();
        document.getElementById('legend-mid').textContent = '0';
        document.getElementById('legend-max').textContent = '+' + Math.round(d).toLocaleString();
      }} else {{
        var r = candRanges[cand];
        document.getElementById('legend-min').textContent = Math.round(r.min).toLocaleString();
        document.getElementById('legend-mid').textContent = Math.round((r.min+r.max)/2).toLocaleString();
        document.getElementById('legend-max').textContent = Math.round(r.max).toLocaleString();
      }}
      el.innerHTML = '';
      document.getElementById('legend').style.display = 'block';
    }} else if (selectedCands.length === 2) {{
      var c1 = candOrder[selectedCands[0]], c2 = candOrder[selectedCands[1]];
      title.textContent = c1.split(' ').slice(0,2).join(' ') + ' vs ' + c2.split(' ').slice(0,2).join(' ');
      bar.style.background = 'linear-gradient(to right, '+rdbu.join(', ')+')';
      document.getElementById('legend-min').textContent = 'Mas ' + c2.split(' ')[0];
      document.getElementById('legend-mid').textContent = 'Empate';
      document.getElementById('legend-max').textContent = 'Mas ' + c1.split(' ')[0];
      el.innerHTML = '';
      document.getElementById('legend').style.display = 'block';
    }} else {{
      document.getElementById('legend').style.display = 'none';
    }}
  }}

  // ─── EVENTS ───
  // Mode pills
  document.querySelectorAll('.mode-pill').forEach(function(btn) {{
    btn.addEventListener('click', function() {{
      document.querySelectorAll('.mode-pill').forEach(function(b) {{ b.classList.remove('active'); }});
      this.classList.add('active');
      currentMode = this.dataset.mode;
      document.getElementById('cand-section').style.display = (currentMode === 'winner' || currentMode === 'comparative' || currentMode === 'runnerup') ? 'none' : 'block';
      updateMap();
    }});
  }});

  // View toggle
  document.querySelectorAll('.toggle-btn').forEach(function(btn) {{
    btn.addEventListener('click', function() {{
      if (this.classList.contains('active')) return;
      document.querySelectorAll('.toggle-btn').forEach(function(b) {{ b.classList.remove('active'); }});
      this.classList.add('active');
      currentView = this.dataset.view;
      if (currentView === 'loc') {{ map.removeLayer(upzLayer); map.addLayer(locLayer); }}
      else {{ map.removeLayer(locLayer); map.addLayer(upzLayer); }}
      updateMap();
    }});
  }});

  // Update puestos layer style when mode changes (if active)
  document.getElementById('toggle-puestos').addEventListener('change', function() {{
    if (this.checked && puestosLayer) {{
      map.addLayer(puestosLayer);
    }}
  }});

  // Initially hide cand section (winner mode)
  document.getElementById('cand-section').style.display = 'none';

  updateMap();
}})();
</script>
</body>
</html>"""

map_path = os.path.join(OUT, 'mapa_bogota.html')
with open(map_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'  OK  {map_path}')
print(f'      - Pill buttons (ganador, relativo, %, diferencia, comparativo)')
print(f'      - Toggle UPZ/Localidad con botones')
print(f'      - Switch Ver puestos (carga asincrona)')
print(f'      - Checkboxes custom con swatches + hover')
print(f'      - Tooltip/popup redisenados con tema')
print(f'      - Leyenda profesional con grid y gradientes')
