"""
Diagnostico de cada modo del mapa.
Genera datos concretos para analizar.
"""

import pandas as pd, numpy as np, os

BASE = 'C:/Users/RYZEN/analisis-electoral-bogota'
v = pd.read_csv(os.path.join(BASE, 'data/processed/votos_por_upz.csv'))

fixes = {
    b'IV\xc3\x83\xc2\x81N CEPEDA CASTRO': 'IV\u00c1N CEPEDA CASTRO',
    b'CLAUDIA L\xc3\x83\xe2\x80\x9cPEZ': 'CLAUDIA L\u00d3PEZ',
    b'RA\xc3\x83\xc5\xa1L SANTIAGO BOTERO JARAMILLO': 'RA\u00daL SANTIAGO BOTERO JARAMILLO',
    b'\xc3\x83\xe2\x80\x9cSCAR MAURICIO LIZCANO ARANGO': '\u00d3SCAR MAURICIO LIZCANO ARANGO',
    b'MIGUEL URIBE LONDO\xc3\x83\xe2\x80\x98O': 'MIGUEL URIBE LONDO\u00d1O',
}
def fix_name(n):
    return fixes.get(n.encode('utf-8'), n)
v['CANNOMBRE'] = v['CANNOMBRE'].apply(fix_name)

cand_order = v.groupby('CANNOMBRE')['VOTOS'].sum().sort_values(ascending=False).index.tolist()

OUT = os.path.join(BASE, 'outputs')
os.makedirs(OUT, exist_ok=True)

with open(os.path.join(OUT, 'summary.txt'), 'w', encoding='utf-8') as f:
    f.write('='*90 + '\n')
    f.write('DIAGNOSTICO DE MODOS DEL MAPA\n')
    f.write('='*90 + '\n\n')

    # 1. Winner mode
    f.write('--- MODO 1: GANADOR ---\n')
    f.write('Cada UPZ se pinta del color del candidato que la gano.\n')
    f.write('Intensidad = margen de victoria (% del total de la UPZ).\n')
    f.write('Muestra distribucion geografica del poder politico.\n')
    for upz in v['UPLCODIGO'].unique():
        sub = v[v['UPLCODIGO'] == upz]
        g = sub.sort_values('VOTOS', ascending=False).iloc[0]
        s = sub.sort_values('VOTOS', ascending=False).iloc[1]
        margen = (g['VOTOS'] - s['VOTOS']) / sub['TOTAL_UPZ'].iloc[0] * 100
        f.write(f'  {upz}: GANA {g["CANNOMBRE"]:40s} con {g["VOTOS"]:>6,} votos ({g["PORCENTAJE"]:.1f}%) | margen={margen:.1f}%\n')
    f.write('\n')

    # 2. Relativo vs Absoluto
    f.write('--- MODO 2 y 3: RELATIVO vs ABSOLUTO ---\n')
    f.write('Para Cepeda vs Matamoros (extremos):\n')
    for c in [cand_order[0], cand_order[-1]]:
        sub = v[v['CANNOMBRE'] == c]
        f.write(f'  {c}:\n')
        f.write(f'    Relativo escala: {sub["VOTOS"].min():,.0f} a {sub["VOTOS"].max():,}\n')
        f.write(f'    Absoluto escala: 0 a {v["VOTOS"].max():,}\n')
        f.write(f'    Porcentaje escala: 0 a 100%\n')
        top5 = sub.nlargest(5, 'VOTOS')
        f.write(f'    Top 5 UPZ:\n')
        for _, r in top5.iterrows():
            f.write(f'      {r["UPLNOMBRE"]:30s} | Realtivo: {r["VOTOS"]:>6,} | % UPZ: {r["PORCENTAJE"]:.1f}% | Absoluto: {r["VOTOS"]:>6,}\n')
        f.write('\n')

    # 3. Diferencia vs promedio
    f.write('--- MODO 5: DIFERENCIA VS PROMEDIO ---\n')
    for c in cand_order[:3]:
        sub = v[v['CANNOMBRE'] == c]
        mean_v = sub['VOTOS'].mean()
        sub['DIFF'] = sub['VOTOS'] - mean_v
        best = sub.nlargest(3, 'DIFF')
        worst = sub.nsmallest(3, 'DIFF')
        f.write(f'  {c}: media={mean_v:.0f}\n')
        f.write(f'    Mejor que promedio:\n')
        for _, r in best.iterrows():
            f.write(f'      {r["UPLNOMBRE"]:30s} | votos={r["VOTOS"]:>6,} | diff={r["DIFF"]:>+6,.0f}\n')
        f.write(f'    Peor que promedio:\n')
        for _, r in worst.iterrows():
            f.write(f'      {r["UPLNOMBRE"]:30s} | votos={r["VOTOS"]:>6,} | diff={r["DIFF"]:>+6,.0f}\n')
        f.write('\n')

    # 4. 2-candidate comparison
    f.write('--- 2 CANDIDATOS SELECCIONADOS: Cepeda vs Espriella ---\n')
    c1 = v[v['CANNOMBRE'] == cand_order[0]].set_index('UPLCODIGO')
    c2 = v[v['CANNOMBRE'] == cand_order[1]].set_index('UPLCODIGO')
    diff_df = c1[['UPLNOMBRE', 'VOTOS']].copy()
    diff_df['VOTOS_C2'] = c2['VOTOS']
    diff_df['DIF'] = diff_df['VOTOS'] - diff_df['VOTOS_C2']
    max_abs_diff = diff_df['DIF'].abs().max()
    f.write(f'  Max diferencia absoluta entre estos 2: {max_abs_diff:,.0f} votos\n')
    f.write(f'  Global max votos (usado en codigo): {v["VOTOS"].max():,.0f}\n')
    f.write(f'  >> PROBLEMA: la escala usa {v["VOTOS"].max()}:,0 en lugar de {max_abs_diff:,.0f}\n')
    f.write(f'     Para candidatos chicos, diff/maxGlobal ~ 0 -> todo blanco\n\n')

    f.write('='*90 + '\n')
    f.write('CONCLUSIONES:\n')
    f.write('='*90 + '\n')
    f.write('1. GANADOR: funciona bien, visualmente distinto\n')
    f.write('2. RELATIVO vs ABSOLUTO: casi identicos para el candidato lider\n')
    f.write('3. % UPZ: distinto para UPZs chicas con alta concentracion\n')
    f.write('4. DIFERENCIA: visualmente distinto (RdBu), muestra desviacion\n')
    f.write('5. 2-CAND COMPARISON: ESCALA ROTA - usa max global en vez de rango real\n')
    f.write('6. Todos los modos se ven igual para candidatos chicos (0-50 votos)\n')

print('Diagnostico guardado en outputs/summary.txt')
