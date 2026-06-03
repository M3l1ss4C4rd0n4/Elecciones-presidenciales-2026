"""
Dashboard completo:
  - Header con stats
  - Mapa interactivo (iframe)
  - 4 graficos PNG
  - Tabla 110 UPZs con buscador + ordenamiento
"""

import pandas as pd
import numpy as np
import os, json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(BASE, 'data', 'processed')
OUT = os.path.join(BASE, 'outputs')
os.makedirs(OUT, exist_ok=True)

# ─── FIX MOJIBAKE ───
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

# Totals
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

# Stats por candidato
stats_cand = []
for c in cand_order:
    sv = int(votos[votos['CANNOMBRE'] == c]['VOTOS'].sum())
    sp = round(sv / total_votos * 100, 1)
    stats_cand.append({'c': c, 'v': sv, 'p': sp})

stats_json = json.dumps(stats_cand, ensure_ascii=False)

# ─── HTML ───
html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Análisis Electoral Bogotá 2026</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; font-family:system-ui,-apple-system,sans-serif; }}
  body {{ background:#f0f2f5; color:#333; }}
  .header {{ background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%); color:white; padding:24px 20px; text-align:center; }}
  .header h1 {{ font-size:26px; letter-spacing:-0.5px; }}
  .header p {{ font-size:14px; opacity:0.75; margin-top:4px; }}
  .container {{ max-width:1400px; margin:0 auto; padding:20px; }}
  .stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:20px; }}
  .stat-card {{ background:white; border-radius:10px; padding:16px 20px; box-shadow:0 1px 4px rgba(0,0,0,0.08); text-align:center; }}
  .stat-card .num {{ font-size:28px; font-weight:700; color:#1a1a2e; }}
  .stat-card .label {{ font-size:12px; color:#666; margin-top:4px; }}
  .section {{ background:white; border-radius:10px; padding:20px; margin-bottom:20px; box-shadow:0 1px 4px rgba(0,0,0,0.08); }}
  .section-title {{ font-size:17px; font-weight:600; margin-bottom:16px; color:#1a1a2e; }}
  .map-frame {{ width:100%; height:620px; border:none; border-radius:6px; }}
  .chart-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
  .chart-grid img {{ width:100%; height:auto; border-radius:6px; border:1px solid #eee; }}
  .chart-full img {{ width:100%; height:auto; border-radius:6px; border:1px solid #eee; }}
  .table-controls {{ display:flex; gap:12px; margin-bottom:12px; flex-wrap:wrap; }}
  .table-controls input, .table-controls select {{ padding:8px 12px; border:1px solid #ccc; border-radius:6px; font-size:13px; flex:1; min-width:150px; }}
  .table-controls input:focus, .table-controls select:focus {{ outline:none; border-color:#1a1a2e; }}
  .table-wrap {{ overflow-x:auto; max-height:520px; overflow-y:auto; border-radius:6px; border:1px solid #eee; }}
  table {{ width:100%; border-collapse:collapse; font-size:12px; }}
  th {{ background:#1a1a2e; color:white; padding:7px 8px; text-align:left; white-space:nowrap; cursor:pointer; position:sticky; top:0; z-index:1; }}
  th:hover {{ background:#2a2a4e; }}
  td {{ padding:5px 8px; border-bottom:1px solid #eee; }}
  tr:hover {{ background:#f0f4ff; }}
  .cat-Seguro {{ color:#2d7d2d; font-weight:600; }}
  .cat-Competido {{ color:#cc7a00; font-weight:600; }}
  .cat-Empate {{ color:#c00; font-weight:600; }}
  .winner-cell {{ font-weight:600; color:#1a1a2e; }}
  .bar-cell {{ display:inline-block; height:14px; border-radius:3px; background:#1a1a2e; }}
  .badge {{ background:#1a1a2e; color:white; font-size:11px; padding:2px 8px; border-radius:10px; }}
  .count {{ font-size:13px; color:#666; margin-bottom:8px; }}
  @media (max-width:900px) {{ .stats {{ grid-template-columns:1fr 1fr; }} .chart-grid {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="header">
  <h1>Elecciones Presidenciales Colombia 2026 &mdash; Primera Vuelta</h1>
  <p>Resultados por UPZ en Bogot&aacute; D.C. &middot; Datos: Registradur&iacute;a Nacional + IDECA</p>
</div>
<div class="container">

<div class="stats">
  <div class="stat-card"><div class="num">{total_votos:,}</div><div class="label">Votos procesados</div></div>
  <div class="stat-card"><div class="num">{total_upzs}</div><div class="label">UPZs</div></div>
  <div class="stat-card"><div class="num">{total_localidades}</div><div class="label">Localidades</div></div>
  <div class="stat-card"><div class="num">{total_candidatos}</div><div class="label">Candidatos</div></div>
</div>

<div class="section">
  <div class="section-title">Mapa interactivo <span class="badge">4 modos: ganador / relativo / % / diferencia + multi-select</span></div>
  <iframe class="map-frame" src="mapa_bogota.html"></iframe>
</div>

<div class="chart-grid">
  <div class="section">
    <div class="section-title">Votos totales por candidato</div>
    <img src="top_candidatos.png" alt="Top candidatos" loading="lazy">
  </div>
  <div class="section">
    <div class="section-title">Top 10 UPZ - Distribución %</div>
    <img src="votos_upz_top10.png" alt="Votos por UPZ" loading="lazy">
  </div>
</div>

<div class="chart-grid">
  <div class="section">
    <div class="section-title">Matriz candidato × localidad</div>
    <img src="matriz_candidato_localidad.png" alt="Matriz" loading="lazy">
  </div>
  <div class="section">
    <div class="section-title">Brecha Cepeda vs De La Espriella</div>
    <img src="brecha_geografica.png" alt="Brecha" loading="lazy">
  </div>
</div>

<div class="section">
  <div class="section-title">Resumen completo por UPZ</div>
  <div class="table-controls">
    <input type="text" id="search-input" placeholder="Buscar UPZ o localidad..." onkeyup="filterTable()">
    <select id="cat-filter" onchange="filterTable()">
      <option value="">Todas las categorías</option>
      <option value="Seguro">Seguro</option>
      <option value="Competido">Competido</option>
      <option value="Empate">Empate técnico</option>
    </select>
    <span class="count" id="row-count">Mostrando {len(resumen)} de {len(resumen)} UPZs</span>
  </div>
  <div class="table-wrap">
    <table id="upz-table">
      <thead>
        <tr>
          <th onclick="sortTable(0)">UPZ</th>
          <th onclick="sortTable(1)">Nombre</th>
          <th onclick="sortTable(2)">Localidad</th>
          <th onclick="sortTable(3)">Votos</th>
          <th onclick="sortTable(4)">Ganador</th>
          <th onclick="sortTable(5)">%</th>
          <th onclick="sortTable(6)">Segundo</th>
          <th onclick="sortTable(7)">Diferencia</th>
          <th onclick="sortTable(8)">Margen</th>
          <th onclick="sortTable(9)">Categoría</th>
        </tr>
      </thead>
      <tbody id="table-body">
      </tbody>
    </table>
  </div>
</div>

<div style="text-align:center;padding:16px;color:#999;font-size:12px">
  Generado con datos de la Registradur&iacute;a Nacional (2026) y geograf&iacute;a de IDECA.
</div>
</div>

<script>
var tableData = {table_json};
var sortCol = -1;
var sortAsc = true;

function renderTable(data) {{
  var tbody = document.getElementById('table-body');
  tbody.innerHTML = data.map(function(r) {{
    var barW = Math.min(r.margen * 3, 100);
    return '<tr>' +
      '<td>' + r.cod + '</td>' +
      '<td><strong>' + r.nom + '</strong></td>' +
      '<td>' + r.loc + '</td>' +
      '<td style="text-align:right">' + r.total.toLocaleString() + '</td>' +
      '<td class="winner-cell">' + r.ganador + '</td>' +
      '<td style="text-align:right">' + r.pct_g + '%</td>' +
      '<td>' + r.segundo + '</td>' +
      '<td style="text-align:right">' + r.diff.toLocaleString() + '</td>' +
      '<td style="text-align:right">' + r.margen.toFixed(1) + '%</td>' +
      '<td class="cat-' + r.cat + '">' + r.cat + '</td>' +
      '</tr>';
  }}).join('');
  document.getElementById('row-count').textContent = 'Mostrando ' + data.length + ' de ' + tableData.length + ' UPZs';
}}

function filterTable() {{
  var q = document.getElementById('search-input').value.toLowerCase();
  var cat = document.getElementById('cat-filter').value;
  var filtered = tableData.filter(function(r) {{
    var matchName = r.nom.toLowerCase().indexOf(q) >= 0 || r.cod.toLowerCase().indexOf(q) >= 0 || r.loc.toLowerCase().indexOf(q) >= 0;
    var matchCat = !cat || r.cat === cat;
    return matchName && matchCat;
  }});
  renderTable(filtered);
}}

function sortTable(col) {{
  if (sortCol === col) {{ sortAsc = !sortAsc; }} else {{ sortCol = col; sortAsc = true; }}
  var keys = ['cod', 'nom', 'loc', 'total', 'ganador', 'pct_g', 'segundo', 'diff', 'margen', 'cat'];
  var key = keys[col];
  tableData.sort(function(a, b) {{
    var va = a[key], vb = b[key];
    if (typeof va === 'number') {{ return sortAsc ? va - vb : vb - va; }}
    return sortAsc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
  }});
  filterTable();
}}

// Initial render
renderTable(tableData);
</script>
</body>
</html>"""

dashboard_path = os.path.join(OUT, 'index.html')
with open(dashboard_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'  OK  {dashboard_path} (se sirve como index.html en la raiz)')
print(f'      - Mapa interactivo (4 modos: ganador, relativo, %, diferencia)')
print(f'      - 4 graficos PNG')
print(f'      - Tabla completa con busqueda + ordenamiento')
