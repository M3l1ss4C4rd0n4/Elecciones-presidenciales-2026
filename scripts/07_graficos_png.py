"""
Graficos PNG:
  1. top_candidatos.png — barras horizontales, 13 candidatos, color por espectro
  2. votos_upz_top10.png — 100% stacked, top UPZ por candidatos principales
  3. matriz_candidato_localidad.png — heatmap candidato x localidad
  4. brecha_geografica.png — Cepeda vs Espriella por UPZ
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import os

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

cand_order = (
    votos.groupby('CANNOMBRE')['VOTOS'].sum()
    .sort_values(ascending=False).index.tolist()
)

# Colores por candidato (espectro politico aproximado)
CAND_COLORS = {
    'IV\u00c1N CEPEDA CASTRO': '#E41A1C',       # Rojo - izquierda
    'ABELARDO DE LA ESPRIELLA': '#377EB8',       # Azul - derecha
    'PALOMA VALENCIA LASERNA': '#984EA3',        # Morado - derecha
    'SERGIO FAJARDO VALDERRAMA': '#4DAF4A',      # Verde - centro
    'CLAUDIA L\u00d3PEZ': '#FF7F00',             # Naranja - izquierda
    'RA\u00daL SANTIAGO BOTERO JARAMILLO': '#A65628',  # Marron - izquierda
    '\u00d3SCAR MAURICIO LIZCANO ARANGO': '#F781BF',  # Rosa
    'MIGUEL URIBE LONDO\u00d1O': '#1B9E77',      # Teal
    'SONDRA MACOLLINS GARVIN PINTO': '#D95F02',
    'LUIS GILBERTO MURILLO URRUTIA': '#7570B3',
    'ROY LEONARDO BARRERAS MONTEALEGRE': '#E7298A',
    'CARLOS EDUARDO CAICEDO OMAR': '#66A61E',
    'GUSTAVO MATAMOROS CAMACHO': '#E6AB02',
}
colors_list = [CAND_COLORS.get(c, '#999999') for c in cand_order]

plt.rcParams.update({'font.family': 'sans-serif', 'font.size': 11})
# Intentar usar una fuente con acentos
for f in ['Segoe UI', 'DejaVu Sans', 'Arial', 'Tahoma']:
    try:
        plt.rcParams['font.family'] = f
        break
    except:
        pass

# ═══════════════════════════════════════════════════
# 1. TOP CANDIDATOS (todos los 13)
# ═══════════════════════════════════════════════════
print('1. top_candidatos.png...')
totales = votos.groupby('CANNOMBRE')['VOTOS'].sum().sort_values(ascending=True)
fig, ax = plt.subplots(figsize=(10, 7))

bars = ax.barh(range(len(totales)), totales.values, color=[CAND_COLORS.get(c, '#999') for c in totales.index], edgecolor='white', height=0.7)

for bar, v in zip(bars, totales.values):
    ax.text(bar.get_width() + 8000, bar.get_y() + bar.get_height()/2,
            f'{v/1e6:.2f}M', va='center', fontsize=10, fontweight='bold', color='#333')

ax.set_yticks(range(len(totales)))
ax.set_yticklabels(totales.index, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel('Votos', fontsize=11)
ax.set_title('Elecciones Presidenciales 2026 - Bogotá\nVotos totales por candidato', fontsize=13, fontweight='bold', color='#1a1a2e')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.tick_params(axis='x', labelsize=9)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x/1e6:.1f}M'))
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'top_candidatos.png'), dpi=150, bbox_inches='tight')
plt.close(fig)
print('  OK')

# ═══════════════════════════════════════════════════
# 2. TOP UPZ - 100% STACKED
# ═══════════════════════════════════════════════════
print('2. votos_upz_top10.png...')
top_upz = votos.groupby(['UPLCODIGO', 'UPLNOMBRE', 'LOCNOMBRE'])['VOTOS'].sum().nlargest(10).reset_index()
top_upz_codes = top_upz['UPLCODIGO'].tolist()

# Top 5 candidatos para el stacked
top5_cands = cand_order[:5]
upz_sub = votos[votos['UPLCODIGO'].isin(top_upz_codes)]
# 100% stacked: calcular %
pivot = upz_sub.pivot_table(index='UPLCODIGO', columns='CANNOMBRE', values='VOTOS', aggfunc='sum').fillna(0)
# Add others
pivot['OTROS'] = pivot.sum(axis=1) - pivot[top5_cands].sum(axis=1)
pivot = pivot[top5_cands + ['OTROS']]
pivot_pct = pivot.div(pivot.sum(axis=1), axis=0) * 100
pivot_pct = pivot_pct.loc[[c for c in top_upz_codes if c in pivot_pct.index]]

fig, ax = plt.subplots(figsize=(12, 6))

colors_stacked = [CAND_COLORS.get(c, '#999') for c in top5_cands] + ['#CCCCCC']
pivot_pct.plot(kind='barh', stacked=True, ax=ax, color=colors_stacked, width=0.7)

ax.set_xlabel('% del total de la UPZ', fontsize=11)
ax.set_title('Top 10 UPZ - Distribucion porcentual de votos', fontsize=13, fontweight='bold', color='#1a1a2e')
ax.invert_yaxis()
ax.legend(loc='lower right', fontsize=8, framealpha=0.9)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.tick_params(labelsize=9)
# UPZ labels
upz_labels = []
for c in top_upz_codes:
    if c in pivot_pct.index:
        row = top_upz[top_upz['UPLCODIGO'] == c].iloc[0]
        upz_labels.append(f"{row['UPLNOMBRE']} ({row['LOCNOMBRE']})")
ax.set_yticklabels(upz_labels, fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'votos_upz_top10.png'), dpi=150, bbox_inches='tight')
plt.close(fig)
print('  OK')

# ═══════════════════════════════════════════════════
# 3. MATRIZ CANDIDATO x LOCALIDAD (heatmap)
# ═══════════════════════════════════════════════════
print('3. matriz_candidato_localidad.png...')
pivot_loc = votos.pivot_table(
    index='LOCNOMBRE',
    columns='CANNOMBRE',
    values='VOTOS',
    aggfunc='sum',
).fillna(0)
# Order by total per locality
loc_order = votos.groupby('LOCNOMBRE')['VOTOS'].sum().sort_values(ascending=False).index.tolist()
pivot_loc = pivot_loc.loc[loc_order, cand_order]
# Convert to %
pivot_loc_pct = pivot_loc.div(pivot_loc.sum(axis=1), axis=0) * 100

fig, ax = plt.subplots(figsize=(14, 8))
im = ax.imshow(pivot_loc_pct.values, aspect='auto', cmap='YlOrRd', vmin=0, vmax=60)

ax.set_xticks(range(len(pivot_loc_pct.columns)))
ax.set_xticklabels(pivot_loc_pct.columns, fontsize=8, rotation=45, ha='right')
ax.set_yticks(range(len(pivot_loc_pct.index)))
ax.set_yticklabels([n[:25] + '...' if len(n) > 25 else n for n in pivot_loc_pct.index], fontsize=7)

# Annotate cells
for i in range(len(pivot_loc_pct.index)):
    for j in range(len(pivot_loc_pct.columns)):
        val = pivot_loc_pct.values[i, j]
        if val > 10:
            ax.text(j, i, f'{val:.0f}%', ha='center', va='center', fontsize=6, fontweight='bold', color='white' if val > 30 else '#333')

ax.set_title('Votos por candidato y localidad\n(% del total de votos de cada localidad)', fontsize=13, fontweight='bold', color='#1a1a2e')
ax.spines[:].set_visible(False)
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'matriz_candidato_localidad.png'), dpi=150, bbox_inches='tight')
plt.close(fig)
print('  OK')

# ═══════════════════════════════════════════════════
# 4. BRECHA CEPEDA vs ESPRIELLA por UPZ
# ═══════════════════════════════════════════════════
print('4. brecha_geografica.png...')
cepeda = votos[votos['CANNOMBRE'] == cand_order[0]][['UPLCODIGO', 'UPLNOMBRE', 'VOTOS', 'TOTAL_UPZ']].copy()
espriella = votos[votos['CANNOMBRE'] == cand_order[1]][['UPLCODIGO', 'VOTOS']].copy()
brecha = cepeda.merge(espriella, on='UPLCODIGO', suffixes=('_CEPVDA', '_ESPRIELLA'))
brecha['DIFERENCIA'] = brecha['VOTOS_CEPVDA'] - brecha['VOTOS_ESPRIELLA']
brecha['PCT_CEPVDA'] = (brecha['VOTOS_CEPVDA'] / brecha['TOTAL_UPZ'] * 100).round(1)
brecha['PCT_ESPRIELLA'] = (brecha['VOTOS_ESPRIELLA'] / brecha['TOTAL_UPZ'] * 100).round(1)
brecha = brecha.sort_values('DIFERENCIA', ascending=False).head(20)
brecha_bottom = brecha.tail(20)
brecha = pd.concat([brecha, brecha_bottom])

fig, ax = plt.subplots(figsize=(12, 10))
y_pos = range(len(brecha))
colors_brecha = ['#E41A1C' if d > 0 else '#377EB8' for d in brecha['DIFERENCIA']]
bars = ax.barh(y_pos, brecha['DIFERENCIA'], color=colors_brecha, height=0.7, edgecolor='white')

for bar, d in zip(bars, brecha['DIFERENCIA']):
    if abs(d) > 1000:
        ax.text(d + (500 if d > 0 else -500), bar.get_y() + bar.get_height()/2,
                f'{d:+,}', va='center', fontsize=8, ha='left' if d > 0 else 'right')

ax.axvline(0, color='#333', linewidth=0.5)
ax.set_yticks(list(y_pos))
ax.set_yticklabels(brecha['UPLNOMBRE'], fontsize=8)
ax.set_xlabel('Diferencia de votos (Cepeda - Espriella)', fontsize=11)
ax.set_title('Brecha Cepeda vs De La Espriella por UPZ\n(arriba: mas Cepeda | abajo: mas Espriella)', fontsize=13, fontweight='bold', color='#1a1a2e')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.tick_params(labelsize=9)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:+,}'))
fig.tight_layout()
fig.savefig(os.path.join(OUT, 'brecha_geografica.png'), dpi=150, bbox_inches='tight')
plt.close(fig)
print('  OK')

print()
print('*** Graficos generados ***')
