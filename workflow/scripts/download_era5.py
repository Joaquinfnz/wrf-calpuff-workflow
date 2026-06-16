#!/usr/bin/env python3
"""
download_era5.py — Descarga datos ERA5 desde CDS API
Soporta descarga por mes con retries automáticos.
CDS API key desde variable de entorno CDSAPI_KEY o .env
"""

import os
import sys
import yaml
import time
import subprocess
from pathlib import Path


def download_era5(config_path):
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    anio = cfg["periodo"]["anio"]
    meses = cfg["periodo"]["meses"]
    era5 = cfg["era5"]
    raw_dir = Path("data/raw")

    # ── Obtener credenciales CDS ────────────────────────────────────────────
    cds_key = os.environ.get("CDSAPI_KEY", era5.get("cds_api_key", ""))
    cds_url = era5.get("cds_api_url", "https://cds.climate.copernicus.eu/api/v2")

    if not cds_key:
        print("[ERROR] CDSAPI_KEY no configurada.")
        print("  export CDSAPI_KEY='uid:api-key'")
        print("  Obten tu key en: https://cds.climate.copernicus.eu/user")
        sys.exit(1)

    uid, api_key = cds_key.split(":", 1)
    cds_config = f"{cds_url}\n{uid}:{api_key}"
    cdsrc = Path.home() / ".cdsapirc"
    cdsrc.write_text(cds_config)
    cdsrc.chmod(0o600)

    # ── Meses en español → número ──────────────────────────────────────────
    meses_nombre = {
        1: "january", 2: "february", 3: "march",
        4: "april", 5: "may", 6: "june",
        7: "july", 8: "august", 9: "september",
        10: "october", 11: "november", 12: "december"
    }

    # ── Bajar datos por mes ─────────────────────────────────────────────────
    for mes in meses:
        outfile = raw_dir / f"ERA5_{anio}_{mes}.grib"
        if outfile.exists():
            print(f"[SKIP] {outfile} ya existe")
            continue

        print(f"[DOWNLOAD] ERA5 {anio}-{mes:02d}")

        # Calcular días del mes
        import calendar
        ndias = calendar.monthrange(anio, mes)[1]

        script = f"""
import cdsapi
c = cdsapi.Client()

c.retrieve('reanalysis-era5-complete', {{
    'class': 'ea',
    'date': '{anio}-{mes:02d}-01/to/{anio}-{mes:02d}-{ndias}',
    'expver': '1',
    'levtype': 'ml',
    'levelist': '{era5["pressure_levels"]}',
    'param': '60/129/130/131/132/133/157',
    'stream': 'oper',
    'time': '00/to/23/by/6',
    'type': 'an',
    'area': {'/'.join(str(x) for x in era5['area'])},
    'grid': {'/'.join(str(x) for x in era5['grid'])},
    'format': 'grib',
}}, '{outfile}')

print(f'[OK] Descargado {{outfile}}')
"""

        max_retries = 5
        for attempt in range(max_retries):
            try:
                result = subprocess.run(
                    ["python3", "-c", script],
                    capture_output=True, text=True, timeout=3600
                )
                if result.returncode == 0:
                    print(f"  [OK] {outfile}")
                    break
                else:
                    print(f"  [RETRY {attempt+1}/{max_retries}] {result.stderr.strip()}")
                    time.sleep(30 * (attempt + 1))
            except subprocess.TimeoutExpired:
                print(f"  [TIMEOUT] Reintentando... ({attempt+1}/{max_retries})")
                time.sleep(60 * (attempt + 1))
        else:
            print(f"  [FAIL] Fallo descarga de ERA5 {anio}-{mes:02d}")
            sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 download_era5.py config.yaml")
        sys.exit(1)
    download_era5(sys.argv[1])
