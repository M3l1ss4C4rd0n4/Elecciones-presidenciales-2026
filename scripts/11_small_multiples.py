"""
Genera seccion de small multiples con SVG inline (sin D3.js).
Crea 13 mini-mapas de UPZs, uno por candidato, con SVG pre-renderizado.
"""
import geopandas as gpd
import pandas as pd
import numpy as np
import os, json, sys, math
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

pivot_pct = votos.pivot_table(index='UPLCODIGO', columns='CANNOMBRE', values='PORCENTAJE', aggfunc='mean').fillna(0)
for cand in cand_order:
    upz_geo[f'pct_{cand}'] = upz_geo['UPLCODIGO'].map(pivot_pct[cand]).fillna(0)

# Simplify geometry
upz_simple = upz_geo[['UPLCODIGO'] + [f'pct_{c}' for c in cand_order] + ['geometry']].copy()
upz_simple['geometry'] = upz_simple.simplify(0.001, preserve_topology=True)

# Convert all to lon/lat lists for Mercator projection
def mercator_x(lon):
    return (lon + 180) / 360 * 160

def mercator_y(lat):
    lat_rad = math.radians(lat)
    merc = math.log(math.tan(math.pi / 4 + lat_rad / 2))
    return (1 - merc / math.pi) / 2 * 140

# Collect all coordinates to compute bounding box
all_coords = []
for _, row in upz_simple.iterrows():
    geom = row.geometry
    if geom and not geom.is_empty:
        if geom.geom_type == 'Polygon':
            coords = list(geom.exterior.coords)
            all_coords.extend(coords)
        elif geom.geom_type == 'MultiPolygon':
            for poly in geom.geoms:
                all_coords.extend(list(poly.exterior.coords))

if all_coords:
    xs = [c[0] for c in all_coords]
    ys = [c[1] for c in all_coords]
    min_lon, max_lon = min(xs), max(xs)
    min_lat, max_lat = min(ys), max(ys)
    # Add padding
    lon_pad = (max_lon - min_lon) * 0.05
    lat_pad = (max_lat - min_lat) * 0.05
    min_lon -= lon_pad
    max_lon += lon_pad
    min_lat -= lat_pad
    max_lat += lat_pad

    # Scale to fit 160x140 viewBox
    def scale_x(lon):
        return (lon - min_lon) / (max_lon - min_lon) * 154 + 3

    def scale_y(lat):
        return (lat - min_lat) / (max_lat - min_lat) * 134 + 3
else:
    scale_x = lambda lon: (lon + 180) / 360 * 160
    scale_y = lambda lat: (90 - lat) / 180 * 140

def geom_to_svg_path(geom):
    """Convert a shapely geometry to an SVG path string."""
    if geom is None or geom.is_empty:
        return ''
    if geom.geom_type == 'Polygon':
        return polygon_to_path(geom)
    elif geom.geom_type == 'MultiPolygon':
        return ' '.join(polygon_to_path(p) for p in geom.geoms)
    return ''

def polygon_to_path(poly):
    parts = []
    ext = list(poly.exterior.coords)
    if ext:
        d = f'M {scale_x(ext[0][0])} {scale_y(ext[0][1])}'
        for x, y in ext[1:]:
            d += f' L {scale_x(x)} {scale_y(y)}'
        d += ' Z'
        parts.append(d)
    for ring in poly.interiors:
        r = list(ring.coords)
        if r:
            d = f'M {scale_x(r[0][0])} {scale_y(r[0][1])}'
            for x, y in r[1:]:
                d += f' L {scale_x(x)} {scale_y(y)}'
            d += ' Z'
            parts.append(d)
    return ' '.join(parts)

# Precompute all SVG paths and data
upz_paths = []
upz_ids = []
for _, row in upz_simple.iterrows():
    path_d = geom_to_svg_path(row.geometry)
    if path_d:
        upz_paths.append(path_d)
        upz_ids.append(row['UPLCODIGO'])

# Candidate data
cand_data_json = {}
for cand in cand_order:
    cand_data_json[cand] = []
    for _, row in upz_simple.iterrows():
        cand_data_json[cand].append({
            'id': row['UPLCODIGO'],
            'val': round(float(row[f'pct_{cand}']), 1),
        })

# Build HTML
purples_js = json.dumps(PURPLES)
cand_colors_js = json.dumps(dict(zip(cand_order, CAND_COLORS[:len(cand_order)])))
upz_paths_js = json.dumps(upz_paths)
upz_ids_js = json.dumps(upz_ids)
cand_data_js = json.dumps(cand_data_json, ensure_ascii=False)
cand_order_js = json.dumps(cand_order, ensure_ascii=False)

cards_html = ''
for idx, cand in enumerate(cand_order):
    pct_vals = [d['val'] for d in cand_data_json[cand]]
    avg_pct = sum(pct_vals) / len(pct_vals) if pct_vals else 0
    color = CAND_COLORS[idx % len(CAND_COLORS)]
    
    # Build colored paths
    paths_html = ''
    for pi, pid in enumerate(upz_ids):
        val = next((d['val'] for d in cand_data_json[cand] if d['id'] == pid), 0)
        normalized = val / 100.0
        ci = min(int(normalized * (len(PURPLES) - 1)), len(PURPLES) - 1)
        fill = PURPLES[max(0, ci)]
        opacity = 0.9 if val > 0 else 0.3
        paths_html += f'<path d="{upz_paths[pi]}" fill="{fill}" stroke="#fff" stroke-width="0.3" opacity="{opacity}"/>'
    
    cards_html += f'''<div class="cand-card" data-cand-idx="{idx}" data-cand="{cand.replace('"', '&quot;')}">
    <svg viewBox="0 0 160 140" width="100%">{paths_html}</svg>
    <div class="cand-label">
      <span class="name"><span class="cand-swatch" style="background:{color}"></span>{cand}</span>
      <span class="pct">{avg_pct:.1f}%</span>
    </div>
  </div>'''

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Small Multiples - Candidatos 2026</title>
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
<div class="grid" id="grid">
{cards_html}
</div>
<div class="hint">Cada mapa coloreado por % de votacion del candidato en cada UPZ | Escala compartida (0-100%) | Clic para seleccionar</div>

<script>
// Click handler for candidate selection
document.getElementById('grid').addEventListener('click', function(e) {{
  var card = e.target.closest('.cand-card');
  if (!card) return;
  document.querySelectorAll('.cand-card').forEach(function(c) {{ c.classList.remove('active'); }});
  card.classList.add('active');
  var cand = card.getAttribute('data-cand');
  try {{ window.parent.postMessage({{ type:'select-candidate', candidate: cand }}, '*'); }} catch(e) {{}}
}});
</script>
</body>
</html>"""

out_path = os.path.join(OUT, 'small_multiples.html')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'  OK  {out_path}')
print(f'      - {len(cand_order)} mini-mapas con SVG inline')
print(f'      - {len(upz_paths)} UPZs renderizadas')
print(f'      - Sin dependencia de D3.js')
print(f'      - Grid responsivo 4 columnas')
print(f'      - Clic para seleccionar candidato')
