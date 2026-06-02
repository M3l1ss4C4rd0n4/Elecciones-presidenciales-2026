import requests
import os

RAW_DIR = os.path.join("data", "raw")

UPZ_URL = (
    "https://mapas.gobiernobogota.gov.co/waserver/rest/services/"
    "Mapa_Base/MapServer/8/query?where=1%3D1&outFields=*&f=geojson"
)

PUESTOS_URL = (
    "https://datosabiertos.bogota.gov.co/dataset/"
    "d03ad429-75f7-4307-9521-da7442154289/resource/"
    "acc0e326-b82c-46f7-8af6-9a46f2ff79de/download/"
    "puesto_de_votacion.geojson"
)

os.makedirs(RAW_DIR, exist_ok=True)

for name, url in [("upz_bogota.geojson", UPZ_URL), ("puestos_bogota.geojson", PUESTOS_URL)]:
    path = os.path.join(RAW_DIR, name)
    print(f"Descargando {name}...")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    with open(path, "wb") as f:
        f.write(resp.content)
    print(f"  OK  {len(resp.content):,} bytes -> {path}")

print("Listo.")
