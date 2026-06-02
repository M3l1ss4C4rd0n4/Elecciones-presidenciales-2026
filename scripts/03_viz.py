"""
Visualizaciones:
1. Mapa coropletico UPZ con votos por candidato (folium)
2. Grafico de barras top candidatos por UPZ (matplotlib)
3. Tabla resumen por UPZ (CSV)
4. Dashboard HTML interactivo
"""

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import os, json

PROC = os.path.join("data", "processed")
OUT = os.path.join("outputs")
os.makedirs(OUT, exist_ok=True)

# ── Cargar datos ───────────────────────────────────────────────────
upz_geo = gpd.read_file(os.path.join(PROC, "upz_con_votos.geojson"))
votos = pd.read_csv(os.path.join(PROC, "votos_por_upz.csv"))

# ── 1. Mapa coropletico con folium ─────────────────────────────────
print("Generando mapa coropletico...")

import folium
from folium import features

# Centro de Bogota
m = folium.Map(location=[4.65, -74.1], zoom_start=11, tiles="CartoDB positron")

# Top 4 candidatos para el mapa
top_cands = votos.groupby("CANNOMBRE")["VOTOS"].sum().nlargest(4).index.tolist()

colors = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3"]
colormap = dict(zip(top_cands, colors))

# Para cada candidato top, mostrar capa
upz_geo_4326 = upz_geo.to_crs("EPSG:4326")

for i, cand in enumerate(top_cands):
    col = f"votos_{cand}"
    if col not in upz_geo_4326.columns:
        continue

    choropleth = folium.Choropleth(
        geo_data=upz_geo_4326.__geo_interface__,
        name=cand,
        data=upz_geo_4326,
        columns=["UPLCODIGO", col],
        key_on="properties.UPLCODIGO",
        fill_color="YlOrRd",
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name=f"Votos {cand}",
        highlight=True,
        nan_fill_color="white",
        nan_fill_opacity=0.4,
        smooth_factor=0,
        show=(i == 0)
    ).add_to(m)

# Tooltip layer (always visible)
tooltip_style = lambda x: {"fillColor": "#ffffff", "color": "#000000", "fillOpacity": 0.0, "weight": 0.5}
tooltip_highlight = lambda x: {"weight": 2, "color": "#666666", "fillOpacity": 0.3}
tooltip_fields = ["UPLNOMBRE"] + [f"votos_{c}" for c in top_cands] + ["GANADOR", "PCT_GANADOR"]
tooltip_aliases = ["UPZ"] + [c for c in top_cands] + ["Ganador", "% Ganador"]

folium.GeoJson(
    upz_geo_4326.__geo_interface__,
    style_function=tooltip_style,
    highlight_function=tooltip_highlight,
    tooltip=folium.GeoJsonTooltip(
        fields=tooltip_fields,
        aliases=tooltip_aliases,
        localize=True,
        sticky=False,
        labels=True,
        max_width=250,
    )
).add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

map_path = os.path.join(OUT, "mapa_bogota.html")
m.save(map_path)
print(f"  OK  {map_path}")

# ── 2. Graficos de barras ──────────────────────────────────────────
print("Generando graficos...")

# 2a. Top candidatos en Bogota
top10 = votos.groupby("CANNOMBRE")["VOTOS"].sum().nlargest(10).reset_index()
fig, ax = plt.subplots(figsize=(12, 6))
bars = ax.barh(range(len(top10)), top10["VOTOS"], color="steelblue")
ax.set_yticks(range(len(top10)))
ax.set_yticklabels(top10["CANNOMBRE"], fontsize=9)
ax.set_xlabel("Votos")
ax.invert_yaxis()
for bar, v in zip(bars, top10["VOTOS"]):
    ax.text(bar.get_width() + 5000, bar.get_y() + bar.get_height()/2,
            f"{v/1e6:.2f}M", va="center", fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "top_candidatos.png"), dpi=150)
plt.close(fig)
print(f"  OK  top_candidatos.png")

# 2b. Grafico por UPZ (top 10 UPZs por votos totales)
top_upz = votos.groupby("UPLNOMBRE")["VOTOS"].sum().nlargest(10).reset_index()
fig, ax = plt.subplots(figsize=(14, 6))
upz_sub = votos[votos["UPLNOMBRE"].isin(top_upz["UPLNOMBRE"])]
pivot = upz_sub.pivot_table(index="UPLNOMBRE", columns="CANNOMBRE",
                            values="VOTOS", aggfunc="sum").fillna(0)
pivot = pivot.loc[top_upz["UPLNOMBRE"]]
pivot.plot(kind="barh", stacked=True, ax=ax, colormap="tab10", width=0.8)
ax.set_xlabel("Votos")
ax.invert_yaxis()
ax.legend(loc="lower right", fontsize=7)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "votos_upz_top10.png"), dpi=150)
plt.close(fig)
print(f"  OK  votos_upz_top10.png")

# ── 3. Tabla resumen por UPZ ──────────────────────────────────────
print("Generando tabla resumen...")

# Ganador por UPZ
winner = votos.loc[
    votos.groupby("UPLCODIGO")["VOTOS"].idxmax(),
    ["UPLCODIGO", "UPLNOMBRE", "LOCNOMBRE", "CANNOMBRE", "VOTOS", "PORCENTAJE", "TOTAL_UPZ"]
].rename(columns={
    "CANNOMBRE": "GANADOR",
    "VOTOS": "VOTOS_GANADOR",
    "PORCENTAJE": "PCT_GANADOR"
})

# Segundo lugar
votos_sorted = votos.sort_values(["UPLCODIGO", "VOTOS"], ascending=[True, False])
second = (votos_sorted.groupby("UPLCODIGO", as_index=False).nth(1)[["UPLCODIGO", "CANNOMBRE", "VOTOS"]]
          .rename(columns={"CANNOMBRE": "SEGUNDO", "VOTOS": "VOTOS_SEGUNDO"}))

tabla = winner.merge(second, on="UPLCODIGO", how="left")
tabla["DIFERENCIA"] = tabla["VOTOS_GANADOR"] - tabla["VOTOS_SEGUNDO"]
tabla = tabla.sort_values("TOTAL_UPZ", ascending=False)

tabla_path = os.path.join(OUT, "resumen_por_upz.csv")
tabla.to_csv(tabla_path, index=False, encoding="utf-8")
print(f"  OK  {tabla_path}")

# ── 4. Dashboard HTML ─────────────────────────────────────────────
print("Generando dashboard HTML...")

# Pivot amplio para la tabla
pivot_table = votos.pivot_table(
    index=["UPLCODIGO", "UPLNOMBRE", "LOCNOMBRE"],
    columns="CANNOMBRE",
    values=["VOTOS", "PORCENTAJE"],
    aggfunc="sum"
).fillna(0)

# Tabla HTML
html_rows = ""
for _, row in tabla.head(30).iterrows():
    html_rows += f"""<tr>
        <td>{row['UPLCODIGO']}</td>
        <td>{row['UPLNOMBRE']}</td>
        <td>{row['LOCNOMBRE']}</td>
        <td>{row['TOTAL_UPZ']:,}</td>
        <td><strong>{row['GANADOR']}</strong></td>
        <td>{row['PCT_GANADOR']:.1f}%</td>
        <td>{row['SEGUNDO']}</td>
        <td>{row['DIFERENCIA']:,}</td>
    </tr>"""

# Mapa embebido como iframe
with open(map_path, "r", encoding="utf-8") as f:
    map_html = f.read()

dashboard = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Analisis Electoral Bogota 2026 - Resultados por UPZ</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: system-ui, sans-serif; }}
  body {{ background: #f5f5f5; color: #333; }}
  .header {{ background: #1a1a2e; color: white; padding: 20px; text-align: center; }}
  .header h1 {{ font-size: 24px; margin-bottom: 5px; }}
  .header p {{ font-size: 14px; opacity: 0.8; }}
  .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
  .section {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .section h2 {{ font-size: 18px; margin-bottom: 15px; color: #1a1a2e; }}
  .map-container {{ width: 100%; height: 600px; border: none; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ background: #1a1a2e; color: white; padding: 8px 10px; text-align: left; white-space: nowrap; }}
  td {{ padding: 6px 10px; border-bottom: 1px solid #eee; }}
  tr:hover {{ background: #f0f0f0; }}
  .winner {{ font-weight: 600; color: #1a1a2e; }}
  img {{ width: 100%; height: auto; border-radius: 4px; }}
  @media (max-width: 768px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="header">
  <h1>Elecciones Presidenciales Colombia 2026 - Primera Vuelta</h1>
  <p>Resultados por UPZ en Bogota D.C. | Datos: Registraduria Nacional + IDECA</p>
</div>
<div class="container">
  <div class="section">
    <h2>Mapa por UPZ</h2>
    <iframe class="map-container" srcdoc='{map_html.replace("'", "&apos;")}'></iframe>
  </div>
  <div class="grid">
    <div class="section">
      <h2>Top Candidatos</h2>
      <img src="top_candidatos.png" alt="Top candidatos">
    </div>
    <div class="section">
      <h2>Top 10 UPZ - Distribucion de Votos</h2>
      <img src="votos_upz_top10.png" alt="Votos por UPZ">
    </div>
  </div>
  <div class="section">
    <h2>Resumen por UPZ (Top 30)</h2>
    <div style="overflow-x:auto">
    <table>
      <thead>
        <tr>
          <th>UPZ</th><th>Nombre</th><th>Localidad</th>
          <th>Total Votos</th><th>Ganador</th><th>%</th>
          <th>Segundo</th><th>Diferencia</th>
        </tr>
      </thead>
      <tbody>
        {html_rows}
      </tbody>
    </table>
    </div>
  </div>
</div>
</body>
</html>"""

dashboard_path = os.path.join(OUT, "dashboard.html")
with open(dashboard_path, "w", encoding="utf-8") as f:
    f.write(dashboard)
print(f"  OK  {dashboard_path}")

print("\n*** Visualizaciones generadas ***")
print(f"Archivos en: {os.path.abspath(OUT)}")
