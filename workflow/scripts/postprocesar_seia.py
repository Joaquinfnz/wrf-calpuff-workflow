#!/usr/bin/env python3
"""
postprocesar_seia.py — Post-procesamiento para evaluacion SEIA
Genera:
  - 5 grillas de receptores anidadas (SEA)
  - Tablas de concentraciones vs normas (DS 38/2011, DS 104/2018)
  - Mapas de isoconcentracion
  - Memoria de calculo auto-generada
"""

import sys
import yaml
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def generar_grillas_receptores(cfg):
    """Genera 5 grillas SEA anidadas de receptores"""
    calmet = cfg["calmet"]
    x0 = calmet.get("xorig", 0)
    y0 = calmet.get("yorig", 0)
    dx = calmet.get("dgridkm", 1.0)
    nx = calmet.get("nx", 60)
    ny = calmet.get("ny", 60)

    grillas = cfg["receptores"]["grillas_sea"]

    receptores = []
    for grilla in grillas:
        esp = grilla["espaciado_m"] / 1000.0  # m → km
        cov = grilla["cobertura_km"]
        n_pts = int(cov / esp) + 1

        for i in range(n_pts):
            xi = x0 + cov / 2 + i * esp
            for j in range(n_pts):
                yj = y0 + cov / 2 + j * esp
                receptores.append({
                    "nombre": f"G{int(esp*1000)}m_{i}_{j}",
                    "x_km": xi,
                    "y_km": yj,
                    "grilla": f"{esp*1000:.0f}m"
                })

    return pd.DataFrame(receptores)


DECRETOS = {
    "SO2": "DS 38/2011",
    "NO2": "DS 38/2011",
    "NOX": "DS 38/2011",
    "CO": "DS 115/2002",
    "MP10": "DS 38/2011",
    "MP2_5": "DS 104/2018",
    "PM10": "DS 38/2011",
    "PM2_5": "DS 104/2018",
    "O3": "DS 112/2002",
}


def comparar_normas(conc_dat_path, cfg):
    """Compara concentraciones modeladas contra normas chilenas.

    Lee conc.dat (CALPUFF output) si existe. Si no, error.
    """
    normas = cfg["normas"]

    # ponytail: placeholder until calpost integration — read conc.dat
    # if available, else raise. Never fabricate random values for SEIA.
    if conc_dat_path is None or not Path(conc_dat_path).exists():
        raise FileNotFoundError(
            f"conc.dat no encontrado en {conc_dat_path}. "
            "No se puede comparar contra normas sin resultados del modelo. "
            "Ejecute CALPUFF primero."
        )

    # TODO: parse conc.dat binary format (CALPOST output) and extract
    # receptor time series. For now, return empty DataFrame with correct schema.
    resultados = []
    for contaminante, valores in normas.items():
        decreto = DECRETOS.get(contaminante, "—")
        for periodo, limite in valores.items():
            if periodo in ("anual", "diaria", "8hr", "1hr"):
                resultados.append({
                    "Contaminante": contaminante,
                    "Periodo": periodo,
                    "Norma (ug/m3)": limite,
                    "Modelado (ug/m3)": "pendiente",
                    "Cumple": "pendiente",
                    "Norma de referencia": decreto,
                })

    return pd.DataFrame(resultados)


def generar_mapa_isoconcentracion(out_dir, cfg):
    """Genera mapa de isoconcentracion.

    TODO: Replace with real CALPOST conc.dat parsing.
    Currently generates a PLACEHOLDER — do NOT submit to SEA.
    """
    proyecto = cfg["proyecto"]["nombre"]
    anio = cfg["periodo"]["anio"]

    fig, ax = plt.subplots(figsize=(10, 10))

    # PLACEHOLDER — no real data yet
    nx, ny = 60, 60
    x = np.linspace(0, 10, nx)
    y = np.linspace(0, 10, ny)
    X, Y = np.meshgrid(x, y)

    ax.text(5, 5, "PLACEHOLDER\nNo usar para SEIA\nRequiere integracion CALPOST",
            ha="center", va="center", fontsize=16, color="red", fontweight="bold",
            transform=ax.transData)
    ax.set_xlabel("X (km)")
    ax.set_ylabel("Y (km)")
    ax.set_title(f"Isoconcentracion MP10 24h — {proyecto} {anio} [PLACEHOLDER]")
    ax.set_aspect("equal")
    fig.tight_layout()

    map_file = out_dir / "mapas" / "isoconcentracion_mp10_24h.png"
    map_file.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(map_file, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[WARN] Mapa placeholder guardado: {map_file} — NO usar para SEIA")


def generar_memoria_calculo(cfg, df_normas, out_dir):
    """Genera memoria de calculo en Markdown"""
    proyecto = cfg["proyecto"]
    wrf = cfg["wrf"]
    periodo = cfg["periodo"]
    normas = cfg["normas"]

    # Conteo de fuentes
    em_path = Path(cfg["emisiones"]["archivo"])
    if em_path.exists():
        df_em = pd.read_csv(em_path, comment="#")
        n_fuentes = len(df_em["fuente"].unique())
        contaminantes = ", ".join(df_em["contaminante"].unique())
    else:
        n_fuentes = 0
        contaminantes = ""

    md = f"""# Memoria de Calculo — Modelacion de Calidad del Aire

## Informacion General

| Campo | Valor |
|-------|-------|
| Proyecto | {proyecto['nombre']} |
| Consultora | {proyecto.get('consultora', '—')} |
| Fecha de generacion | {datetime.now().strftime('%d/%m/%Y')} |
| Guia de referencia | SEA 2023 "Guia para el uso de modelos de calidad del aire en el SEIA" v4 |

## Modelo Meteorologico (WRF)

| Parametro | Valor |
|-----------|-------|
| Version | WRF-ARW 4.6.0 |
| Dominios | {wrf['max_dom']} anidados (two-way) |
| Resolucion d01 | {wrf['dominios']['d01']['resolution_km']} km |
| Resolucion d02 | {wrf['dominios']['d02']['resolution_km']} km |
| Resolucion d03 | {wrf['dominios']['d03']['resolution_km']} km |
| Proyeccion | Lambert conformal conic |
| Centro dominio | {wrf['ref_lat']}°S, {wrf['ref_lon']}°W |
| Niveles verticales | {wrf['e_vert']} |
| Microphysics | WSM6 (6) |
| Cumulus | Kain-Fritsch (1) d01/d02, off d03 |
| PBL | YSU (1) |
| Superficie | Noah LSM (2) |
| Radiacion SW | Dudhia (1) |
| Radiacion LW | RRTM (1) |
| Forzantes | ERA5 (ECMWF), 0.25°, cada 6h |

## Periodo Modelado

- Inicio: {periodo['inicio']}
- Fin: {periodo['fin']}
- Duracion: 1 año completo
- Segmentacion: mensual con spin-up de 24h

## Modelo de Dispersion (CALPUFF)

| Parametro | Valor |
|-----------|-------|
| Version | CALPUFF 7.x / CALMET 6.5 |
| Resolucion | {cfg['calmet']['dgridkm']} km |
| Niveles verticales | {cfg['calmet']['nz']} |
| Especies modeladas | {contaminantes} |

## Inventario de Emisiones

- Numero de fuentes: {n_fuentes}
- Contaminantes: {contaminantes}
- Formato: tasas horarias reales (SEA, 2023)
"""

    # ── Tabla de normas ────────────────────────────────────────────────────
    md += f"""
## Comparacion con Normas de Calidad del Aire

{df_normas.to_markdown(index=False)}
"""

    # ── Archivos entregados ────────────────────────────────────────────────
    md += """
## Archivos Entregados

### Modelo Meteorologico
- `namelist.wps` — Configuracion WPS
- `namelist.input` — Configuracion WRF (parametrizaciones fisicas)

### Modelo de Dispersion
- `calmet.inp` — Configuracion CALMET
- `calpuff.inp` — Configuracion CALPUFF
- `calmet.dat` — Campos meteorologicos diagnosticos
- `conc.dat` — Concentraciones modeladas
- `calpost.lst` — Estadisticas de post-procesamiento

### Resultados
- Tablas de concentracion vs normas (XLSX/CSV)
- Mapas de isoconcentracion (PNG/GeoTIFF)
- Metricas de validacion meteorologica

## Validacion Meteorologica

Validacion WRF vs observaciones meteorologicas de superficie.
Metricas: RMSE, MAE, Sesgo (MB), Indice de Acuerdo (IOA), R².
Ver archivo `validacion/metricas_validacion.csv`.

---

*Documento generado automaticamente por WRF-CALPUFF Workflow v1.0*
"""

    mem_file = out_dir / "memoria_calculo.md"
    mem_file.write_text(md)
    print(f"[OK] Memoria de calculo: {mem_file}")

    return md


def postprocesar_seia(config_path):
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    proyecto = cfg["proyecto"]["nombre"].replace(" ", "_")
    anio = cfg["periodo"]["anio"]
    out_dir = Path(f"data/outputs/{proyecto}_{anio}")

    # ── 1. Generar grillas SEA ─────────────────────────────────────────────
    df_grillas = generar_grillas_receptores(cfg)
    grillas_file = out_dir / "tablas" / "receptores_grillas_sea.csv"
    grillas_file.parent.mkdir(parents=True, exist_ok=True)
    df_grillas.to_csv(grillas_file, index=False)
    print(f"[OK] Grillas SEA: {len(df_grillas)} receptores generados")

    # ── 2. Comparar vs normas ──────────────────────────────────────────────
    conc_dat = Path("data/calpuff/conc.dat")
    df_normas = comparar_normas(conc_dat, cfg)
    normas_file = out_dir / "tablas" / "concentraciones_vs_norma.csv"
    df_normas.to_csv(normas_file, index=False)

    # Excel
    xlsx_file = out_dir / "tablas" / "concentraciones_vs_norma.xlsx"
    df_normas.to_excel(xlsx_file, index=False)
    print(f"[OK] Tabla normas: {xlsx_file}")

    # ── 3. Mapa de isoconcentracion ────────────────────────────────────────
    generar_mapa_isoconcentracion(out_dir, cfg)

    # ── 4. Memoria de calculo ──────────────────────────────────────────────
    generar_memoria_calculo(cfg, df_normas, out_dir)

    print(f"\n[OK] Post-procesamiento SEIA completo. Outputs en {out_dir}/")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 postprocesar_seia.py config.yaml")
        sys.exit(1)
    postprocesar_seia(sys.argv[1])
