"""
Genera seccion de small multiples (D3.js) para el dashboard.
Crea 13 mini-mapas de UPZs, uno por candidato, con D3.js + TopoJSON.
"""
import geopandas as gpd
import pandas as pd
import numpy as np
import os, json, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _theme import P, CAND_COLORS, PURPLES
from _utils import fix_name

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(BASE, 'data', 'processed')
OUT = os.path.join(BASE, 'outputs')

votos = pd.read_csv(os.path.join(PROC, 'votos_por_upz.csv'))
votos['CANNOMBRE'] = votos['CANNOMBRE'].apply(fix_name)

cand_order = (
    votos.groupby('CANNOMBRE')['VOTOS'].sum()
    .sort_values(ascending=False).index.tolist()
)

upz_geo = gpd.read_file(os.path.join(PROC, 'upz_con_votos.geojson'))
upz_geo = upz_geo.to_crs('EPSG:4326')

# Merge PCT data
pivot_pct = votos.pivot_table(index='UPLCODIGO', columns='CANNOMBRE', values='PORCENTAJE', aggfunc='mean').fillna(0)
for cand in cand_order:
    upz_geo[f'pct_{cand}'] = upz_geo['UPLCODIGO'].map(pivot_pct[cand]).fillna(0)

# Simplify geometry for TopoJSON
upz_simple = upz_geo[['UPLCODIGO'] + [f'pct_{c}' for c in cand_order] + ['geometry']].copy()
upz_simple['geometry'] = upz_simple.simplify(0.001, preserve_topology=True)

# Convert to TopoJSON
topo_data = json.loads(upz_simple.to_json())
topo_str = json.dumps(topo_data)

# Build DATA for D3 - each candidate's pct values per UPZ
data_by_cand = {}
for cand in cand_order:
    data_by_cand[cand] = []
    for _, r in upz_simple.iterrows():
        data_by_cand[cand].append({
            'id': r['UPLCODIGO'],
            'val': round(float(r[f'pct_{cand}']), 1),
        })
data_json = json.dumps(data_by_cand, ensure_ascii=False)

cand_labels = json.dumps(cand_order, ensure_ascii=False)
cand_colors_dict = dict(zip(cand_order, CAND_COLORS[:len(cand_order)]))
colors_json = json.dumps(cand_colors_dict, ensure_ascii=False)

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Small Multiples - Candidatos 2026</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script src="https://d3js.org/topojson-client.v3.min.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Inter',sans-serif; background:{P['bg']}; padding:16px; }}
  .grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:8px; }}
  @media (max-width:900px) {{ .grid {{ grid-template-columns:repeat(2,1fr); }} }}
  @media (max-width:480px) {{ .grid {{ grid-template-columns:1fr; }} }}
  .cand-card {{ background:white; border-radius:8px; border:1px solid {P['border-light']};
    overflow:hidden; cursor:pointer; transition:all 0.2s; position:relative; }}
  .cand-card:hover {{ box-shadow:0 4px 12px rgba(0,0,0,0.1); transform:translateY(-2px); }}
  .cand-card.active {{ box-shadow:0 0 0 2px {P['primary']}; }}
  .cand-card svg {{ display:block; width:100%; height:auto; }}
  .cand-label {{ padding:6px 8px; font-size:11px; font-weight:500; display:flex; justify-content:space-between; align-items:center; }}
  .cand-label .name {{ color:{P['text']}; }}
  .cand-label .pct {{ font-family:monospace; font-size:12px; font-weight:600; color:{P['text-secondary']}; }}
  .cand-swatch {{ width:8px; height:8px; border-radius:2px; display:inline-block; margin-right:4px; }}
  .title {{ font-size:16px; font-weight:600; color:{P['text']}; margin-bottom:12px; display:flex; align-items:center; gap:8px; }}
  .hint {{ font-size:11px; color:{P['text-hint']}; margin-top:8px; text-align:center; }}
</style>
</head>
<body>
<div class="title">
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{P['primary']}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
  Todos los candidatos
  <span style="font-size:12px;font-weight:400;color:{P['text-secondary']}">Clic para ver en el mapa</span>
</div>
<div class="grid" id="grid"></div>
<div class="hint">Cada mapa coloreado por % de votacion del candidato en cada UPZ | Escala compartida (0-100%)</div>

<script>
(function() {{
  var geoJSON = {topo_str};
  var candData = {data_json};
  var candOrder = {cand_labels};
  var candColors = {colors_json};
  var purples = {json.dumps(PURPLES)};

  // Convert to TopoJSON-like structure for d3
  var features = geoJSON.features;
  var projection = d3.geoMercator().fitSize([160, 140], {{ type:'FeatureCollection', features:features }});
  var path = d3.geoPath().projection(projection);

  var grid = document.getElementById('grid');

  candOrder.forEach(function(cand, idx) {{
    var card = document.createElement('div');
    card.className = 'cand-card';
    card.setAttribute('data-cand', cand);

    // Build color map for this candidate
    var valMin = 0, valMax = 100;
    var colorMap = {{}};
    candData[cand].forEach(function(d) {{
      var normalized = (d.val - valMin) / (valMax - valMin || 1);
      var ci = Math.min(Math.floor(normalized * (purples.length - 1)), purples.length - 1);
      colorMap[d.id] = purples[Math.max(0, ci)];
    }});

    // Create SVG
    var svg = d3.select(card).append('svg')
      .attr('viewBox', '0 0 160 140')
      .attr('width', '100%');

    svg.selectAll('path')
      .data(features)
      .join('path')
      .attr('d', path)
      .attr('fill', function(d) {{ return colorMap[d.properties.UPLCODIGO] || '#f0f0f0'; }})
      .attr('stroke', '#fff')
      .attr('stroke-width', 0.3)
      .attr('opacity', function(d) {{
        var v = (candData[cand].find(function(x) {{ return x.id === d.properties.UPLCODIGO; }}) || {{}}).val || 0;
        return v > 0 ? 0.9 : 0.3;
      }});

    // Label
    var totalPct = d3.mean(candData[cand], function(d) {{ return d.val; }});
    var label = document.createElement('div');
    label.className = 'cand-label';
    label.innerHTML =
      '<span class="name"><span class="cand-swatch" style="background:' + (candColors[cand] || '#ccc') + '"></span>' + cand + '</span>' +
      '<span class="pct">' + (totalPct ? totalPct.toFixed(1) + '%' : '') + '</span>';
    card.appendChild(label);

    // Click handler
    card.addEventListener('click', function() {{
      document.querySelectorAll('.cand-card').forEach(function(c) {{ c.classList.remove('active'); }});
      card.classList.add('active');
      // Send message to parent dashboard
      window.parent.postMessage({{ type:'select-candidate', candidate: cand }}, '*');
    }});

    grid.appendChild(card);
  }});
}})();
</script>
</body>
</html>"""

out_path = os.path.join(OUT, 'small_multiples.html')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'  OK  {out_path}')
print(f'      - 13 mini-mapas D3.js con TopoJSON')
print(f'      - Grid responsivo 4 columnas')
print(f'      - Hover + clic para seleccionar candidato')
print(f'      - postMessage para comunicacion con dashboard')
