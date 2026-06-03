"""
Procesa el Excel comparativo 2022-2026 y genera:
  - data/processed/comparativo_localidad.json  (datos por localidad)
  - data/processed/comparativo_upz.csv         (datos asignados a cada UPZ)
"""

import pandas as pd
import numpy as np
import os, json, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _utils import fix_name

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, 'data', 'raw')
PROC = os.path.join(BASE, 'data', 'processed')
OUT = os.path.join(BASE, 'outputs')
# Buscar el Excel en RAW o Downloads
XLSX = os.path.join(RAW, 'bogota_electoral_2022_2026.xlsx')
if not os.path.exists(XLSX):
    XLSX = os.path.join(os.path.expanduser('~'), 'Downloads', 'bogota_electoral_2022_2026 4.xlsx')

# ─── LEER SHEET 1: Resumen por Localidad ───
# El Excel tiene headers multi-fila. Leemos sin header y parseamos manual.
raw = pd.read_excel(XLSX, sheet_name='Resumen por Localidad', header=None)

# Fila 0: headers generales (col names reemplazadas)
# Fila 4: header real con nombres de columna
# Fila 5+: datos
# Locate row with "Localidad" in col 0
header_row = None
for i in range(raw.shape[0]):
    if str(raw.iloc[i, 0]).strip() == 'Localidad':
        header_row = i
        break

if header_row is None:
    raise ValueError("No se encontro fila 'Localidad'")

cols = [str(c).strip() for c in raw.iloc[header_row].tolist()]
data = raw.iloc[header_row + 1:].copy()
data.columns = cols
data = data.reset_index(drop=True)

# Filtrar filas vacias o que no sean localidades reales
data = data[data['Localidad'].notna()].copy()
data = data[data['Localidad'].str.strip() != ''].copy()
# Eliminar fila "Bogotá D.C." total si existe
data = data[~data['Localidad'].str.contains('BOGOT', na=False)].copy()

# Renombrar columnas para facil acceso
data.rename(columns={
    'Δ vs Petro 1v': 'delta_petro_1v_pp',
    'Δ vs Petro 2v': 'delta_petro_2v_pp',
    'Sit. vs 1v22': 'sit_vs_1v22',
    'Sit. vs 2v22': 'sit_vs_2v22',
    'Votos Petro 1v22': 'votos_petro_1v22',
    'Votos Cepeda 1v26': 'votos_cepeda_1v26',
    '% Petro 1v': 'pct_petro_1v22',
    '% Cepeda 26': 'pct_cepeda_1v26',
}, inplace=True)

# Columnas de porcentaje a numeric
pct_cols = ['pct_petro_1v22', 'pct_cepeda_1v26', 'delta_petro_1v_pp', 'delta_petro_2v_pp']
for c in pct_cols:
    data[c] = pd.to_numeric(data[c], errors='coerce')

vote_cols = ['votos_petro_1v22', 'votos_cepeda_1v26']
for c in vote_cols:
    data[c] = pd.to_numeric(data[c], errors='coerce').fillna(0).astype(int)

# Limpiar nombres de localidad
data['Localidad'] = data['Localidad'].str.strip().str.upper()

# Guardar como JSON
comparativo = data.to_dict(orient='records')
json_path = os.path.join(PROC, 'comparativo_localidad.json')
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(comparativo, f, ensure_ascii=False, indent=2)

print(f'  OK  {json_path}')
print(f'      - {len(comparativo)} localidades con datos comparativos')

# ─── ASIGNAR A UPZ ───
# Cargar votos por UPZ para mapear localidad -> UPZ
votos = pd.read_csv(os.path.join(PROC, 'votos_por_upz.csv'))

votos['CANNOMBRE'] = votos['CANNOMBRE'].apply(fix_name)
votos['LOCNOMBRE'] = votos['LOCNOMBRE'].str.strip().str.upper()

# Pivot para tener votos de Cepeda
pivot = votos.pivot_table(index='UPLCODIGO', columns='CANNOMBRE', values='VOTOS', aggfunc='sum').fillna(0)
pivot['TOTAL_UPZ'] = pivot.sum(axis=1)

# Crear mapping localidad -> UPZ
upz_loc = votos[['UPLCODIGO', 'LOCNOMBRE', 'UPLNOMBRE']].drop_duplicates().copy()
upz_loc['LOCNOMBRE'] = upz_loc['LOCNOMBRE'].str.strip().str.upper()

# Merge comparativo data into UPZ
upz_loc = upz_loc.merge(data[['Localidad', 'delta_petro_1v_pp', 'delta_petro_2v_pp',
                               'sit_vs_1v22', 'sit_vs_2v22',
                               'votos_petro_1v22', 'votos_cepeda_1v26']],
                         left_on='LOCNOMBRE', right_on='Localidad', how='left')

# Guardar CSV
upz_csv_path = os.path.join(PROC, 'comparativo_upz.csv')
upz_loc.to_csv(upz_csv_path, index=False, encoding='utf-8')
print(f'  OK  {upz_csv_path}')
print(f'      - {len(upz_loc)} UPZs con datos comparativos asignados')

print('\nEjemplo:')
print(upz_loc[['UPLCODIGO', 'UPLNOMBRE', 'LOCNOMBRE', 'delta_petro_1v_pp',
               'sit_vs_1v22', 'votos_petro_1v22', 'votos_cepeda_1v26']].head(5).to_string())
