"""
Pipeline completo:
1. Carga Bogota.xlsx → agrega votos por puesto
2. Spatial join: puestos → UPZ
3. Merge y agregación por UPZ
4. Exporta resultados
"""

import pandas as pd
import geopandas as gpd
import os, sys

RAW = os.path.join("data", "raw")
PROC = os.path.join("data", "processed")
os.makedirs(PROC, exist_ok=True)

# ── 1. Cargar votos ────────────────────────────────────────────────
print("Cargando Bogota.xlsx...")
df = pd.read_excel(
    os.path.join(RAW, "Bogota.xlsx"),
    engine="openpyxl",
    dtype={"ZONA": str, "PUESTO": str, "MESA": str, "CODIGOLOCALIDAD": str}
)
print(f"  Filas: {len(df):,}")

# Filtrar solo candidatos reales (CAN 1..99, excluir especiales 996-998)
cands = df[(df["CAN"] >= 1) & (df["CAN"] <= 99)].copy()
print(f"  Filas de candidatos: {len(cands):,}")

# Agregar votos por puesto (sumar todas las mesas del mismo puesto)
# Clave de join: DEP + MUN + ZONA + PUESTO + CODIGOLOCALIDAD
agg = cands.groupby(
    ["DEP", "MUN", "ZONA", "PUESTO", "PUESNOMBRE",
     "CODIGOLOCALIDAD", "COMUNOMBRE",
     "PAR", "PARNOMBRE", "CAN", "CANCEDULA", "CANNOMBRE"],
    as_index=False
)["VOTOS"].sum()
agg.sort_values(["CODIGOLOCALIDAD", "PUESTO", "CAN"], inplace=True)
print(f"  Filas agregadas por puesto: {len(agg):,}")
agg.to_parquet(os.path.join(PROC, "votos_por_puesto.parquet"))
print("  OK  votos_por_puesto.parquet")

# ── 2. Cargar puestos GeoJSON ──────────────────────────────────────
print("Cargando puestos GeoJSON...")
puestos = gpd.read_file(os.path.join(RAW, "puestos_bogota.geojson"))
print(f"  Features: {len(puestos)}")
print(f"  CRS: {puestos.crs}")

# ── 3. Cargar UPZ GeoJSON ──────────────────────────────────────────
print("Cargando UPZ GeoJSON...")
upz = gpd.read_file(os.path.join(RAW, "upz_bogota.geojson"))
print(f"  Features: {len(upz)}")
print(f"  CRS: {upz.crs}")

# Reproject puestos a CRS de UPZ para el spatial join
if str(puestos.crs) != str(upz.crs):
    print(f"  Reprojectando puestos de {puestos.crs} a {upz.crs}...")
    puestos = puestos.to_crs(upz.crs)

# ── 4. Spatial join ────────────────────────────────────────────────
print("Spatial join...")
puestos_upz = gpd.sjoin(
    puestos, upz[["UPLCODIGO", "UPLNOMBRE", "LOCNOMBRE", "LOCCODIGO", "geometry"]],
    how="left", predicate="within"
)
# Para puntos fuera de polígonos, intentar nearest
sin_upz = puestos_upz[puestos_upz["UPLCODIGO"].isna()]
if len(sin_upz) > 0:
    print(f"  {len(sin_upz)} puntos sin UPZ (dentro de ningún polígono), usando nearest...")
    puestos_upz2 = gpd.sjoin_nearest(
        puestos[~puestos.index.isin(sin_upz.index)],
        upz[["UPLCODIGO", "UPLNOMBRE", "LOCNOMBRE", "LOCCODIGO", "geometry"]],
        how="left", max_distance=0.01
    )
    puestos_upz = pd.concat([puestos_upz2, sin_upz])

print(f"  Filas con UPZ: {puestos_upz['UPLCODIGO'].notna().sum()}/{len(puestos_upz)}")

# ── 5. Merge votos + UPZ ───────────────────────────────────────────
# Normalizar claves para el merge
agg["PUESTO_KEY"] = agg["PUESTO"].str.strip().str.upper()
agg["LOC_KEY"] = agg["CODIGOLOCALIDAD"].str.strip().str.zfill(2)
puestos_upz["PUESTO_KEY"] = puestos_upz["Número_del_puesto"].str.strip().str.upper()
puestos_upz["LOC_KEY"] = puestos_upz["Código_de_localidad"].str.strip().str.zfill(2)

merged = agg.merge(
    puestos_upz[["PUESTO_KEY", "LOC_KEY", "UPLCODIGO", "UPLNOMBRE", "LOCNOMBRE", "geometry"]],
    on=["PUESTO_KEY", "LOC_KEY"],
    how="left"
)

sin_match = merged[merged["UPLCODIGO"].isna()]
if len(sin_match) > 0:
    print(f"  {len(sin_match)} filas sin match UPZ (de {len(merged)})")
    print(f"  Ejemplos: {sin_match[['CODIGOLOCALIDAD','PUESTO','PUESNOMBRE']].drop_duplicates().head(5).to_string()}")

# ── 6. Agregar por UPZ ─────────────────────────────────────────────
print("Agregando votos por UPZ...")
upz_votos = merged.groupby(
    ["UPLCODIGO", "UPLNOMBRE", "LOCNOMBRE", "CAN", "CANNOMBRE", "PAR", "PARNOMBRE"],
    as_index=False
)["VOTOS"].sum()

# Agregar total por UPZ para calcular porcentajes
total_upz = upz_votos.groupby("UPLCODIGO")["VOTOS"].sum().rename("TOTAL_UPZ")
upz_votos = upz_votos.merge(total_upz, on="UPLCODIGO")
upz_votos["PORCENTAJE"] = (upz_votos["VOTOS"] / upz_votos["TOTAL_UPZ"] * 100).round(2)

upz_votos.sort_values(["UPLCODIGO", "CAN"], inplace=True)
print(f"  Filas: {len(upz_votos):,}")
upz_votos.to_csv(os.path.join(PROC, "votos_por_upz.csv"), index=False)
print("  OK  votos_por_upz.csv")

# ── 7. Crear GeoJSON con votos por UPZ (para mapas) ────────────────
print("Creando GeoJSON de UPZ con votos...")

# Pivot: columnas por candidato
top_cands = upz_votos.groupby("CAN").agg({"VOTOS": "sum"}).nlargest(15, "VOTOS").index
pivot = upz_votos.pivot_table(
    index="UPLCODIGO",
    columns="CANNOMBRE",
    values="VOTOS",
    aggfunc="sum"
).fillna(0).astype(int)
pivot.columns = [f"votos_{c}" for c in pivot.columns]
# Also add CAN-based column names for safety
cand_map = upz_votos[["CANNOMBRE", "CAN"]].drop_duplicates()
cand_map["COL_VOTOS"] = cand_map.apply(
    lambda r: f"votos_can{r['CAN']:02d}", axis=1
)
col_rename = dict(zip(
    [f"votos_{c}" for c in pivot.columns.str.replace("votos_", "")],
    cand_map.set_index("CANNOMBRE")["COL_VOTOS"].to_dict()
))

# Ganador por UPZ
winner = upz_votos.loc[
    upz_votos.groupby("UPLCODIGO")["VOTOS"].idxmax(),
    ["UPLCODIGO", "CANNOMBRE", "VOTOS", "PORCENTAJE"]
].rename(columns={
    "CANNOMBRE": "GANADOR",
    "VOTOS": "VOTOS_GANADOR",
    "PORCENTAJE": "PCT_GANADOR"
})

# Total votos por UPZ
totales = upz_votos.groupby("UPLCODIGO").agg(
    TOTAL_VOTOS=("VOTOS", "sum")
).reset_index()

upz_geo = upz.merge(pivot, on="UPLCODIGO", how="left")
upz_geo = upz_geo.merge(winner, on="UPLCODIGO", how="left")
upz_geo = upz_geo.merge(totales, on="UPLCODIGO", how="left")
upz_geo.fillna(0, inplace=True)

upz_geo.to_file(os.path.join(PROC, "upz_con_votos.geojson"), driver="GeoJSON")
print(f"  OK  upz_con_votos.geojson ({len(upz_geo)} features)")

print("\n*** Procesamiento completado ***")
