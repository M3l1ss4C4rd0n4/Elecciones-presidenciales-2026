"""
Script maestro: corrige encoding, precalcula columnas, genera Excel mejorado y CSV.
"""

import pandas as pd
import numpy as np
import os

BASE = 'C:/Users/RYZEN/analisis-electoral-bogota'
PROC = os.path.join(BASE, 'data', 'processed')
OUT = os.path.join(BASE, 'outputs')
os.makedirs(OUT, exist_ok=True)

# ═══════════════════════════════════════════════════
# 1. CORREGIR MOJIBAKE en nombres de candidatos
# ═══════════════════════════════════════════════════

# Mojibake fix: match on UTF-8 bytes
def fix_name(n):
    raw = n.encode('utf-8')
    # Ordered by specificity (longer match first)
    fixes = {
        b'IV\xc3\x83\xc2\x81N CEPEDA CASTRO': 'IVÁN CEPEDA CASTRO',
        b'CLAUDIA L\xc3\x83\xe2\x80\x9cPEZ': 'CLAUDIA LÓPEZ',
        b'RA\xc3\x83\xc5\xa1L SANTIAGO BOTERO JARAMILLO': 'RAÚL SANTIAGO BOTERO JARAMILLO',
        b'\xc3\x83\xe2\x80\x9cSCAR MAURICIO LIZCANO ARANGO': 'ÓSCAR MAURICIO LIZCANO ARANGO',
        b'MIGUEL URIBE LONDO\xc3\x83\xe2\x80\x98O': 'MIGUEL URIBE LONDOÑO',
    }
    return fixes.get(raw, n)

# ═══════════════════════════════════════════════════
# 2. CARGAR Y LIMPIAR DATOS
# ═══════════════════════════════════════════════════

votos = pd.read_csv(os.path.join(PROC, 'votos_por_upz.csv'))
votos['CANNOMBRE'] = votos['CANNOMBRE'].apply(fix_name)

# upz_geo not needed for Excel generation

# ═══════════════════════════════════════════════════
# 3. ORDEN DE CANDIDATOS (por votos totales descendente)
# ═══════════════════════════════════════════════════

cand_order = (
    votos.groupby('CANNOMBRE')['VOTOS'].sum()
    .sort_values(ascending=False)
    .index.tolist()
)

# ═══════════════════════════════════════════════════
# 4. PIVOT: votos por UPZ (ancho)
# ═══════════════════════════════════════════════════

pivot_votos = votos.pivot_table(
    index=['UPLCODIGO', 'UPLNOMBRE', 'LOCNOMBRE', 'TOTAL_UPZ'],
    columns='CANNOMBRE',
    values='VOTOS',
    aggfunc='sum',
).fillna(0).reset_index()

# Renombrar columnas: prefijo VOTO_
pivot_votos.columns = [
    f'VOTO_{col}' if col in cand_order else col
    for col in pivot_votos.columns
]

# ═══════════════════════════════════════════════════
# 5. PIVOT: porcentajes
# ═══════════════════════════════════════════════════

pivot_pct = pivot_votos.copy()
for cand in cand_order:
    col = f'VOTO_{cand}'
    pct_col = f'PCT_{cand}'
    pivot_pct[pct_col] = np.where(
        pivot_pct['TOTAL_UPZ'] > 0,
        (pivot_pct[col] / pivot_pct['TOTAL_UPZ'] * 100).round(2),
        0
    )

# ═══════════════════════════════════════════════════
# 6. DIFERENCIA vs PROMEDIO (para mapa modo 4)
# ═══════════════════════════════════════════════════

cand_means = {cand: pivot_pct[f'VOTO_{cand}'].mean() for cand in cand_order}
for cand in cand_order:
    col = f'VOTO_{cand}'
    diff_col = f'DIFF_{cand}'
    pivot_pct[diff_col] = (pivot_pct[col] - cand_means[cand]).round(0)

# ═══════════════════════════════════════════════════
# 7. GANADOR, SEGUNDO, MARGEN por UPZ
# ═══════════════════════════════════════════════════

resumen = []
for _, row in pivot_pct.iterrows():
    upz = row['UPLCODIGO']
    results = []
    for cand in cand_order:
        results.append({
            'candidato': cand,
            'votos': int(row[f'VOTO_{cand}']),
            'pct': row[f'PCT_{cand}'],
        })
    results.sort(key=lambda x: x['votos'], reverse=True)

    total = int(row['TOTAL_UPZ'])
    ganador = results[0]
    segundo = results[1]
    diff_votos = ganador['votos'] - segundo['votos']
    margen_ajustado = round(diff_votos / total * 100, 2) if total > 0 else 0

    if margen_ajustado >= 20:
        categoria = 'Seguro'
    elif margen_ajustado >= 5:
        categoria = 'Competido'
    else:
        categoria = 'Empate técnico'

    resumen.append({
        'UPLCODIGO': upz,
        'UPLNOMBRE': row['UPLNOMBRE'],
        'LOCNOMBRE': row['LOCNOMBRE'],
        'TOTAL_VOTOS': total,
        'GANADOR': ganador['candidato'],
        'VOTOS_GANADOR': ganador['votos'],
        'PCT_GANADOR': ganador['pct'],
        'SEGUNDO': segundo['candidato'],
        'VOTOS_SEGUNDO': segundo['votos'],
        'PCT_SEGUNDO': segundo['pct'],
        'DIFERENCIA_VOTOS': diff_votos,
        'MARGEN_AJUSTADO': margen_ajustado,
        'CATEGORIA': categoria,
    })

df_resumen = pd.DataFrame(resumen)
df_resumen = df_resumen.sort_values('TOTAL_VOTOS', ascending=False).reset_index(drop=True)

# ═══════════════════════════════════════════════════
# 8. MATRIZ CANDIDATO x LOCALIDAD
# ═══════════════════════════════════════════════════

pivot_localidad = votos.pivot_table(
    index='CANNOMBRE',
    columns='LOCNOMBRE',
    values='VOTOS',
    aggfunc='sum',
).fillna(0)

pivot_localidad_pct = pivot_localidad.div(pivot_localidad.sum(axis=1), axis=0) * 100

# Sheet 3 combinada: votos + % intercalados
loc_order = sorted(votos.groupby('LOCNOMBRE')['VOTOS'].sum()
                   .sort_values(ascending=False).index.tolist())
matriz_data = []
for cand in cand_order:
    row = {'CANDIDATO': cand}
    for loc in loc_order:
        row[f'{loc}_VOTOS'] = int(pivot_localidad.loc[cand, loc]) if loc in pivot_localidad.columns else 0
        row[f'{loc}_PCT'] = round(pivot_localidad_pct.loc[cand, loc], 2) if loc in pivot_localidad_pct.columns else 0
    matriz_data.append(row)

df_matriz = pd.DataFrame(matriz_data)

# ═══════════════════════════════════════════════════
# 9. RANKING POR CANDIDATO (top 10 UPZs)
# ═══════════════════════════════════════════════════

ranking_data = []
for cand in cand_order:
    subset = votos[votos['CANNOMBRE'] == cand].copy()
    subset['PCT'] = (subset['VOTOS'] / subset['TOTAL_UPZ'] * 100).round(2)
    top_votos = subset.nlargest(10, 'VOTOS')[['UPLCODIGO', 'UPLNOMBRE', 'LOCNOMBRE', 'VOTOS', 'PCT']]
    top_votos['CANDIDATO'] = cand
    top_votos['TIPO'] = 'Votos'
    top_pct = subset.nlargest(10, 'PCT')[['UPLCODIGO', 'UPLNOMBRE', 'LOCNOMBRE', 'VOTOS', 'PCT']]
    top_pct['CANDIDATO'] = cand
    top_pct['TIPO'] = 'Porcentaje'
    ranking_data.append(top_votos)
    ranking_data.append(top_pct)

df_ranking = pd.concat(ranking_data, ignore_index=True)

# ═══════════════════════════════════════════════════
# 10. BRECHA CEPEDA vs ESPRIELLA
# ═══════════════════════════════════════════════════

cepeda = votos[votos['CANNOMBRE'] == cand_order[0]].copy()
espriella = votos[votos['CANNOMBRE'] == cand_order[1]].copy()
brecha = cepeda.merge(
    espriella[['UPLCODIGO', 'VOTOS']],
    on='UPLCODIGO',
    suffixes=('_CEPVDA', '_ESPRIELLA')
)
brecha['DIFERENCIA'] = brecha['VOTOS_CEPVDA'] - brecha['VOTOS_ESPRIELLA']
brecha['PCT_CEPVDA'] = (brecha['VOTOS_CEPVDA'] / brecha['TOTAL_UPZ'] * 100).round(2)
brecha['PCT_ESPRIELLA'] = (brecha['VOTOS_ESPRIELLA'] / brecha['TOTAL_UPZ'] * 100).round(2)
brecha['GANADOR'] = np.where(brecha['DIFERENCIA'] > 0, cand_order[0], cand_order[1])
brecha['MARGEN'] = brecha['DIFERENCIA'].abs()
brecha = brecha.sort_values('DIFERENCIA', ascending=False).reset_index(drop=True)
df_brecha = brecha[[
    'UPLCODIGO', 'UPLNOMBRE', 'LOCNOMBRE', 'TOTAL_UPZ',
    'VOTOS_CEPVDA', 'PCT_CEPVDA', 'VOTOS_ESPRIELLA', 'PCT_ESPRIELLA',
    'DIFERENCIA', 'GANADOR', 'MARGEN'
]]

# ═══════════════════════════════════════════════════
# 11. METADATOS
# ═══════════════════════════════════════════════════

total_votos = int(votos['VOTOS'].sum())
total_upzs = votos['UPLCODIGO'].nunique()
total_localidades = votos['LOCNOMBRE'].nunique()
ganador_global = votos.groupby('CANNOMBRE')['VOTOS'].sum().idxmax()

metadata = [
    ['Métrica', 'Valor'],
    ['Fuente datos', 'Registraduría Nacional - Bogota.xlsx'],
    ['Fuente geografía', 'IDECA - UPZ Bogotá'],
    ['Elección', 'Presidencial Colombia 2026 - Primera Vuelta'],
    ['Cobertura', 'Bogotá D.C.'],
    ['Total votos procesados', f'{total_votos:,}'],
    ['UPZs cubiertas', total_upzs],
    ['Localidades cubiertas', total_localidades],
    ['Candidatos', len(cand_order)],
    ['Ganador global Bogotá', ganador_global],
    ['Fecha de generación', pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')],
    ['', ''],
    ['Notas', ''],
    ['UPZs sin datos', '6 UPZs rurales (sin puestos de votación) no tienen cobertura'],
    ['Encoding', 'UTF-8. Nombres corregidos de mojibake en fuente original.'],
    ['Candidatos especiales', 'Votos en blanco, nulos y no marcados NO incluidos en este análisis'],
]
df_metadata = pd.DataFrame(metadata[1:], columns=metadata[0])

# ═══════════════════════════════════════════════════
# 12. GUARDAR CSV MEJORADO
# ═══════════════════════════════════════════════════

csv_path = os.path.join(OUT, 'resumen_por_upz.csv')
df_resumen.to_csv(csv_path, index=False, encoding='utf-8')
print(f'  OK  {csv_path} ({len(df_resumen)} UPZs, {len(df_resumen.columns)} cols)')

# ═══════════════════════════════════════════════════
# 13. GUARDAR EXCEL MEJORADO
# ═══════════════════════════════════════════════════

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import DataBarRule

xlsx_path = os.path.join(OUT, 'resultados_electorales_bogota.xlsx')
wb = Workbook()

# ─── Estilos ───
header_font = Font(name='Calibri', bold=True, color='FFFFFF', size=11)
header_fill = PatternFill(start_color='1A1A2E', end_color='1A1A2E', fill_type='solid')
header_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
cell_align = Alignment(vertical='center')
num_align = Alignment(horizontal='right', vertical='center')
thin_border = Border(
    left=Side(style='thin', color='D9D9D9'),
    right=Side(style='thin', color='D9D9D9'),
    top=Side(style='thin', color='D9D9D9'),
    bottom=Side(style='thin', color='D9D9D9'),
)
stripe_fill = PatternFill(start_color='F5F5F5', end_color='F5F5F5', fill_type='solid')
safe_fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
empate_fill = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')
danger_fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')

def style_header(ws, row=1, max_col=None):
    if max_col is None:
        max_col = ws.max_column
    for col in range(1, max_col + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

def style_data_rows(ws, start_row=2, end_row=None, num_cols=None):
    if end_row is None:
        end_row = ws.max_row
    for row in range(start_row, end_row + 1):
        for col in range(1, ws.max_column + 1):
            cell = ws.cell(row=row, column=col)
            cell.border = thin_border
            cell.alignment = cell_align
        if (row - start_row) % 2 == 1:
            for col in range(1, ws.max_column + 1):
                ws.cell(row=row, column=col).fill = stripe_fill

def auto_width(ws):
    for col in range(1, ws.max_column + 1):
        max_len = 0
        for row in range(1, ws.max_row + 1):
            val = ws.cell(row=row, column=col).value
            if val is not None:
                # Aprox ancho
                max_len = max(max_len, len(str(val)))
        ws.column_dimensions[get_column_letter(col)].width = min(max_len + 3, 30)

# ─── SHEET 1: Votos por UPZ ───
ws1 = wb.active
ws1.title = 'Votos por UPZ'

# Columnas base
cols1 = ['UPLCODIGO', 'UPLNOMBRE', 'LOCNOMBRE', 'TOTAL_VOTOS']
for cand in cand_order:
    cols1.append(f'VOTO_{cand}')
    cols1.append(f'PCT_{cand}')

for c, col_name in enumerate(cols1, 1):
    ws1.cell(row=1, column=c, value=col_name)

for r, (_, row) in enumerate(pivot_pct.iterrows(), 2):
    ws1.cell(row=r, column=1, value=row['UPLCODIGO'])
    ws1.cell(row=r, column=2, value=row['UPLNOMBRE'])
    ws1.cell(row=r, column=3, value=row['LOCNOMBRE'])
    ws1.cell(row=r, column=4, value=int(row['TOTAL_UPZ']))
    c = 5
    for cand in cand_order:
        ws1.cell(row=r, column=c, value=int(row[f'VOTO_{cand}']))
        ws1.cell(row=r, column=c+1, value=row[f'PCT_{cand}'])
        c += 2

# Formato: miles en votos, 1 decimal en %
for r in range(2, ws1.max_row + 1):
    ws1.cell(row=r, column=4).number_format = '#,##0'
    c = 5
    for _ in cand_order:
        ws1.cell(row=r, column=c).number_format = '#,##0'
        ws1.cell(row=r, column=c+1).number_format = '0.0'
        c += 2
    if (r - 2) % 2 == 1:
        for col in range(1, len(cols1) + 1):
            ws1.cell(row=r, column=col).fill = stripe_fill

style_header(ws1, max_col=len(cols1))
for col in range(1, len(cols1) + 1):
    ws1.cell(row=1, column=col).alignment = header_align

# Congelar
ws1.freeze_panes = 'A2'

# ─── SHEET 2: Resumen por UPZ ───
ws2 = wb.create_sheet('Resumen por UPZ')
cols2 = list(df_resumen.columns)
for c, col_name in enumerate(cols2, 1):
    ws2.cell(row=1, column=c, value=col_name)

for r, (_, row) in enumerate(df_resumen.iterrows(), 2):
    for c, col_name in enumerate(cols2, 1):
        val = row[col_name]
        if isinstance(val, (np.integer,)):
            val = int(val)
        elif isinstance(val, (np.floating,)):
            val = float(val)
        ws2.cell(row=r, column=c, value=val)

# Formato
num_cols_2 = ['TOTAL_VOTOS', 'VOTOS_GANADOR', 'VOTOS_SEGUNDO', 'DIFERENCIA_VOTOS']
pct_cols_2 = ['PCT_GANADOR', 'PCT_SEGUNDO', 'MARGEN_AJUSTADO']
for r in range(2, ws2.max_row + 1):
    for col_name in num_cols_2:
        c = cols2.index(col_name) + 1
        ws2.cell(row=r, column=c).number_format = '#,##0'
    for col_name in pct_cols_2:
        c = cols2.index(col_name) + 1
        ws2.cell(row=r, column=c).number_format = '0.00'
    if (r - 2) % 2 == 1:
        for col in range(1, len(cols2) + 1):
            ws2.cell(row=r, column=col).fill = stripe_fill

# Formato condicional: categoría
cat_col = cols2.index('CATEGORIA') + 1
for r in range(2, ws2.max_row + 1):
    cat = ws2.cell(row=r, column=cat_col).value
    if cat == 'Seguro':
        ws2.cell(row=r, column=cat_col).fill = safe_fill
    elif cat == 'Empate técnico':
        ws2.cell(row=r, column=cat_col).fill = empate_fill

# Data bar en DIFERENCIA_VOTOS
diff_col = cols2.index('DIFERENCIA_VOTOS') + 1
ws2.conditional_formatting.add(
    f'{get_column_letter(diff_col)}2:{get_column_letter(diff_col)}{ws2.max_row}',
    DataBarRule(start_type='min', end_type='max', color='1A1A2E', showValue=True)
)

style_header(ws2, max_col=len(cols2))
ws2.freeze_panes = 'A2'
auto_width(ws2)
ws2.column_dimensions['B'].width = 30  # UPLNOMBRE

# ─── SHEET 3: Matriz Candidato x Localidad ───
ws3 = wb.create_sheet('Matriz Candidato x Localidad')
for c, col_name in enumerate(df_matriz.columns, 1):
    ws3.cell(row=1, column=c, value=col_name)
for r, (_, row) in enumerate(df_matriz.iterrows(), 2):
    for c, col_name in enumerate(df_matriz.columns, 1):
        val = row[col_name]
        if isinstance(val, (np.integer,)):
            val = int(val)
        elif isinstance(val, (np.floating,)):
            val = float(val)
        ws3.cell(row=r, column=c, value=val)
# Formato
for r in range(2, ws3.max_row + 1):
    for c in range(2, ws3.max_column + 1):
        cell = ws3.cell(row=r, column=c)
        col_name = df_matriz.columns[c-1]
        if '_PCT' in col_name:
            cell.number_format = '0.00'
            cell.alignment = num_align
        elif '_VOTOS' in col_name:
            cell.number_format = '#,##0'
            cell.alignment = num_align
    if (r - 2) % 2 == 1:
        for c in range(1, ws3.max_column + 1):
            ws3.cell(row=r, column=c).fill = stripe_fill
# Totales al final
# ... (optional, skip for brevity)
style_header(ws3, max_col=len(df_matriz.columns))
ws3.freeze_panes = 'B2'
# Colores por localidad en headers
for c in range(2, ws3.max_column + 1):
    ws3.cell(row=1, column=c).alignment = Alignment(horizontal='center', vertical='center', wrap_text=True, text_rotation=90)
ws3.column_dimensions['A'].width = 35

# ─── SHEET 4: Ranking por candidato ───
ws4 = wb.create_sheet('Ranking por candidato')
cols4 = ['CANDIDATO', 'TIPO', 'UPLCODIGO', 'UPLNOMBRE', 'LOCNOMBRE', 'VOTOS', 'PCT']
for c, col_name in enumerate(cols4, 1):
    ws4.cell(row=1, column=c, value=col_name)
r = 2
for cand in cand_order:
    for tipo in ['Votos', 'Porcentaje']:
        subset = df_ranking[(df_ranking['CANDIDATO'] == cand) & (df_ranking['TIPO'] == tipo)]
        for _, row in subset.iterrows():
            ws4.cell(row=r, column=1, value=cand)
            ws4.cell(row=r, column=2, value=tipo)
            ws4.cell(row=r, column=3, value=row['UPLCODIGO'])
            ws4.cell(row=r, column=4, value=row['UPLNOMBRE'])
            ws4.cell(row=r, column=5, value=row['LOCNOMBRE'])
            ws4.cell(row=r, column=6, value=int(row['VOTOS']))
            ws4.cell(row=r, column=7, value=row['PCT'])
            r += 1
for row in range(2, ws4.max_row + 1):
    ws4.cell(row=row, column=6).number_format = '#,##0'
    ws4.cell(row=row, column=7).number_format = '0.00'
    if (row - 2) % 2 == 1:
        for c in range(1, 8):
            ws4.cell(row=row, column=c).fill = stripe_fill
style_header(ws4, max_col=7)
ws4.freeze_panes = 'A2'
auto_width(ws4)

# ─── SHEET 5: Brecha Cepeda vs Espriella ───
ws5 = wb.create_sheet('Brecha Cepeda vs Espriella')
cols5 = list(df_brecha.columns)
for c, col_name in enumerate(cols5, 1):
    ws5.cell(row=1, column=c, value=col_name)
for r, (_, row) in enumerate(df_brecha.iterrows(), 2):
    for c, col_name in enumerate(cols5, 1):
        val = row[col_name]
        if isinstance(val, (np.integer,)):
            val = int(val)
        elif isinstance(val, (np.floating,)):
            val = float(val)
        ws5.cell(row=r, column=c, value=val)
# Data bar en DIFERENCIA
dif_col = cols5.index('DIFERENCIA') + 1
ws5.conditional_formatting.add(
    f'{get_column_letter(dif_col)}2:{get_column_letter(dif_col)}{ws5.max_row}',
    DataBarRule(start_type='min', end_type='max', color='1A1A2E', showValue=True)
)
# Formato
for r in range(2, ws5.max_row + 1):
    for col_name in ['VOTOS_CEPVDA', 'VOTOS_ESPRIELLA', 'TOTAL_UPZ', 'MARGEN']:
        if col_name in cols5:
            c = cols5.index(col_name) + 1
            ws5.cell(row=r, column=c).number_format = '#,##0'
    for col_name in ['PCT_CEPVDA', 'PCT_ESPRIELLA']:
        if col_name in cols5:
            c = cols5.index(col_name) + 1
            ws5.cell(row=r, column=c).number_format = '0.00'
    if (r - 2) % 2 == 1:
        for c in range(1, len(cols5) + 1):
            ws5.cell(row=r, column=c).fill = stripe_fill
# Color ganador
gan_col = cols5.index('GANADOR') + 1
for r in range(2, ws5.max_row + 1):
    gan = ws5.cell(row=r, column=gan_col).value
    if gan == cand_order[0]:
        ws5.cell(row=r, column=gan_col).fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
    else:
        ws5.cell(row=r, column=gan_col).fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
style_header(ws5, max_col=len(cols5))
ws5.freeze_panes = 'A2'
auto_width(ws5)

# ─── SHEET 6: Metadatos ───
ws6 = wb.create_sheet('Metadatos')
for c, col_name in enumerate(df_metadata.columns, 1):
    ws6.cell(row=1, column=c, value=col_name)
for r, (_, row) in enumerate(df_metadata.iterrows(), 2):
    ws6.cell(row=r, column=1, value=row[df_metadata.columns[0]])
    ws6.cell(row=r, column=2, value=row[df_metadata.columns[1]])
style_header(ws6, max_col=2)
ws6.column_dimensions['A'].width = 30
ws6.column_dimensions['B'].width = 60

# ─── Guardar ───
wb.save(xlsx_path)
print(f'  OK  {xlsx_path}')
print(f'      Hojas: {[ws.title for ws in wb.worksheets]}')
print(f'      Cand_order: {cand_order}')
