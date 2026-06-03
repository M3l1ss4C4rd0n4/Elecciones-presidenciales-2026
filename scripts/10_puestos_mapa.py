"""
Procesa datos de puestos de votacion para mapa dot-density.
Genera puestos_con_votos.geojson con ganador, votos y ubicacion por puesto.
"""
import pandas as pd
import geopandas as gpd
import numpy as np
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _utils import fix_name

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, 'data', 'raw')
PROC = os.path.join(BASE, 'data', 'processed')
OUT = os.path.join(BASE, 'outputs')

print("Cargando votos por puesto...")
votos = pd.read_parquet(os.path.join(PROC, 'votos_por_puesto.parquet'))
votos['CANNOMBRE'] = votos['CANNOMBRE'].apply(fix_name)

print(f"  {len(votos):,} filas, {votos['PUESTO'].nunique()} puestos, {votos['CANNOMBRE'].nunique()} candidatos")

print("Pivotando por puesto...")
pivot = votos.pivot_table(
    index=['DEP', 'MUN', 'ZONA', 'PUESTO', 'CODIGOLOCALIDAD'],
    columns='CANNOMBRE',
    values='VOTOS',
    aggfunc='sum'
).fillna(0).reset_index()

cand_order = (
    votos.groupby('CANNOMBRE')['VOTOS'].sum()
    .sort_values(ascending=False).index.tolist()
)

# Determinar ganador por puesto
vote_cols = [c for c in cand_order if c in pivot.columns]
pivot['TOTAL_VOTOS'] = pivot[vote_cols].sum(axis=1)
pivot['GANADOR'] = pivot[vote_cols].idxmax(axis=1)
pivot['VOTOS_GANADOR'] = pivot.apply(lambda r: r[r['GANADOR']], axis=1)
pivot['PCT_GANADOR'] = np.where(
    pivot['TOTAL_VOTOS'] > 0,
    (pivot['VOTOS_GANADOR'] / pivot['TOTAL_VOTOS'] * 100).round(1), 0
)

print(f"  {len(pivot)} puestos con datos")

print("Cargando GeoJSON de puestos...")
puestos = gpd.read_file(os.path.join(RAW, 'puestos_bogota.geojson'))
print(f"  {len(puestos)} features en GeoJSON")

# Merge keys - Numero del puesto (columnas con encoding problems)
# Buscar columna que contenga 'numero' o 'nro' (ignorando encoding)
import unicodedata
def clean_col_name(name):
    return unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower()

key_col = None
for c in puestos.columns:
    cleaned = clean_col_name(c)
    if 'numero' in cleaned or 'nro' in cleaned:
        key_col = c
        break
if not key_col:
    # fallback: buscar columna que no sea nombre ni codigo y tenga digitos
    for c in puestos.columns:
        if 'puesto' in clean_col_name(c) and 'nombre' not in clean_col_name(c) and 'codigo' not in clean_col_name(c):
            key_col = c
            break
if not key_col:
    key_col = puestos.columns[3]  # ultimo recurso
print(f"  Columna de merge numero: '{key_col}' (clean: '{clean_col_name(key_col)}')")

# Also find locality code column
loc_col = None
for c in puestos.columns:
    cleaned = clean_col_name(c)
    if 'codigo_de_localidad' in cleaned or 'codigo_localidad' in cleaned:
        loc_col = c
        break
print(f"  Columna de localidad: '{loc_col}' (clean: '{clean_col_name(loc_col)}')")

pivot['PUESTO_KEY'] = pivot['PUESTO'].astype(str).str.strip().str.upper()
puestos['PUESTO_KEY'] = puestos[key_col].astype(str).str.strip().str.upper()
puestos['LOC_KEY'] = puestos[loc_col].astype(str).str.strip().str.zfill(2) if loc_col else ''
pivot['LOC_KEY'] = pivot['CODIGOLOCALIDAD'].astype(str).str.strip().str.zfill(2)

print("Mergeando (por numero + localidad)...")
if loc_col:
    merged = puestos.merge(pivot, on=['PUESTO_KEY', 'LOC_KEY'], how='inner')
else:
    merged = puestos.merge(pivot, on='PUESTO_KEY', how='inner')
print(f"  {len(merged)} puestos con match exitoso")

# Seleccionar y renombrar columnas para el GeoJSON final
# Buscar columnas reales (con encoding problems)
col_map = {}
for c in merged.columns:
    cleaned = clean_col_name(c)
    if 'nombre_del_puesto' in cleaned or 'nombre_del_sitio' in cleaned:
        col_map[c] = {'nombre_del_puesto': 'NOMBRE', 'nombre_del_sitio': 'SITIO'}[cleaned]
    elif cleaned == 'direccion' or 'direcci' in cleaned:
        col_map[c] = 'DIRECCION'
    elif 'nombre_de_localidad' in cleaned:
        col_map[c] = 'LOCALIDAD'
    elif c in ['GANADOR', 'TOTAL_VOTOS', 'VOTOS_GANADOR', 'PCT_GANADOR', 'geometry']:
        col_map[c] = c
    elif c in vote_cols:
        col_map[c] = c

out = merged[list(col_map.keys())].rename(columns=col_map)

# Guardar
out_path = os.path.join(PROC, 'puestos_con_votos.geojson')
out.to_file(out_path, driver='GeoJSON')
print(f"  OK  {out_path} ({len(out)} features)")

out_light = out[['NOMBRE', 'SITIO', 'DIRECCION', 'LOCALIDAD', 'GANADOR', 'TOTAL_VOTOS', 'VOTOS_GANADOR', 'PCT_GANADOR', 'geometry']]
out_light_path = os.path.join(PROC, 'puestos_con_votos_light.geojson')
out_light.to_file(out_light_path, driver='GeoJSON')
print(f"  OK  {out_light_path} (version ligera, {len(out_light)} features)")

# Also copy to outputs for map loading
out_light.to_file(os.path.join(OUT, 'puestos_con_votos.geojson'), driver='GeoJSON')
print(f"  OK  outputs/puestos_con_votos.geojson")
