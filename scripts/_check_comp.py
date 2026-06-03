import json, os
with open('data/processed/comparativo_localidad.json', encoding='utf-8') as f:
    d = json.load(f)
for loc in d:
    dp = loc.get('delta_petro_1v_pp', '?')
    sit = loc.get('sit_vs_1v22', '?')[:30].replace('\U0001f338','GANA ').replace('\U0001f534','PIERDE ').replace('\U0001f535','PIERDE ')
    vc = loc.get('votos_cepeda_1v26', 0)
    vp = loc.get('votos_petro_1v22', 0)
    print(f'{loc["Localidad"]:25s} delta={dp:>6}  sit={sit:30s}  cepeda26={vc:>7,}  petro22={vp:>7,}')
