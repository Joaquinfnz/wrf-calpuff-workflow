#!/usr/bin/env python3
"""
validar_wrf.py — Validacion meteorologica WRF vs observaciones
Requisito SEA: comparar >= 1 año, >= 1 estacion
Metricas: RMSE, MAE, Sesgo (MB), IOA (Index of Agreement), R2
Variables: T2, WS10, WD10
"""

import sys
import yaml
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def compute_metrics(obs, mod, circular=False):
    """Calcula metricas estadisticas de validacion.

    circular=True (direccion de viento): los errores se calculan con la
    diferencia angular minima (350 vs 10 = 20 grados, no 340)."""
    valid = ~np.isnan(obs) & ~np.isnan(mod)
    o = obs[valid].values
    m = mod[valid].values

    if len(o) < 10:
        return {"n": 0, "rmse": np.nan, "mae": np.nan, "sesgo": np.nan,
                "ioa": np.nan, "fb": np.nan, "nmse": np.nan, "r2": np.nan}

    if circular:
        d = ((m - o + 180.0) % 360.0) - 180.0  # error angular en [-180, 180]
        return {"n": len(o), "rmse": np.sqrt(np.mean(d ** 2)),
                "mae": np.mean(np.abs(d)), "sesgo": np.mean(d),
                "ioa": np.nan, "fb": np.nan, "nmse": np.nan, "r2": np.nan}

    rmse = np.sqrt(np.mean((m - o) ** 2))
    mae = np.mean(np.abs(m - o))
    sesgo = np.mean(m - o)
    r2 = np.corrcoef(o, m)[0, 1] ** 2

    # Index of Agreement (Willmott 1981)
    o_mean = np.mean(o)
    num = np.sum((m - o) ** 2)
    den = np.sum((np.abs(m - o_mean) + np.abs(o - o_mean)) ** 2)
    ioa = 1 - num / den if den > 0 else np.nan

    # FB (Fractional Bias) and NMSE (Normalized Mean Square Error) — SEA 2023
    fb = 2 * (np.mean(m) - np.mean(o)) / (np.mean(m) + np.mean(o)) if (np.mean(m) + np.mean(o)) != 0 else np.nan
    nmse = np.mean((m - o) ** 2) / (np.mean(m) * np.mean(o)) if np.mean(m) * np.mean(o) != 0 else np.nan

    return {"n": len(o), "rmse": rmse, "mae": mae, "sesgo": sesgo, "ioa": ioa, "fb": fb, "nmse": nmse, "r2": r2}


def _punto_estacion(ds, val_cfg):
    """(j, i) de la celda mas cercana a la estacion (validacion.estacion_lat/lon).
    Sin estacion configurada usa el centro del dominio."""
    lat = val_cfg.get("estacion_lat")
    lon = val_cfg.get("estacion_lon")
    ny = ds.sizes["south_north"]
    nx = ds.sizes["west_east"]
    if lat is None or lon is None:
        print(f"[WARN] validacion.estacion_lat/lon no definidos: uso el centro del dominio")
        return ny // 2, nx // 2
    xlat = ds["XLAT"].isel(Time=0).values
    xlon = ds["XLONG"].isel(Time=0).values
    dist2 = (xlat - lat) ** 2 + ((xlon - lon) * np.cos(np.radians(lat))) ** 2
    j, i = np.unravel_index(np.argmin(dist2), dist2.shape)
    print(f"[INFO] Estacion ({lat}, {lon}) -> celda (j={j}, i={i}), "
          f"lat/lon de celda: ({xlat[j, i]:.3f}, {xlon[j, i]:.3f})")
    return int(j), int(i)


def validar_wrf(config_path):
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    proyecto = cfg["proyecto"]["nombre"].replace(" ", "_")
    anio = cfg["periodo"]["anio"]
    val_cfg = cfg.get("validacion", {})
    out_dir = Path(f"data/outputs/{proyecto}_{anio}/validacion")
    out_dir.mkdir(parents=True, exist_ok=True)

    wrf_dir = Path("data/wrf")
    obs_file = Path(val_cfg.get("observaciones", "observaciones.csv"))
    # La validacion SEA se hace sobre el dominio fino (la estacion cae en d03)
    dominio = val_cfg.get("dominio", "d03")

    # ── Cargar WRF outputs ──────────────────────────────────────────────────
    wrf_files = sorted(wrf_dir.glob(f"wrfout_{dominio}_*"))
    if not wrf_files:
        print(f"[WARN] No se encontraron wrfout_{dominio}_*. Saltando validacion.")
        return

    # ── Extraer T2, WS10, WD10 de wrfout ───────────────────────────────────
    fig, axes = plt.subplots(3, 1, figsize=(12, 15), sharex=True)

    variables = {
        "T2": {"wrf_var": "T2", "units": "°C", "obs_col": "t2", "ax": axes[0], "title": "Temperatura 2m (°C)", "convert": lambda x: x - 273.15},
        "WS10": {"wrf_var": "U10_V10_wspd", "units": "m/s", "obs_col": "ws10", "ax": axes[1], "title": "Vel. Viento 10m (m/s)", "convert": lambda x: x},
        "WD10": {"wrf_var": "U10_V10_wdir", "units": "deg", "obs_col": "wd10", "ax": axes[2], "title": "Dir. Viento 10m (deg)", "circular": True, "convert": lambda x: x},
    }

    if obs_file.exists():
        obs_df = pd.read_csv(obs_file, parse_dates=["fecha"])
        obs_df = obs_df.set_index("fecha")
        # WRF esta en UTC; si las obs vienen en hora local, declarar el offset
        # (Chile continental: -4 invierno / -3 verano; usar el de la estacion).
        utc_offset = val_cfg.get("obs_utc_offset", 0)
        if utc_offset:
            obs_df.index = obs_df.index - pd.Timedelta(hours=utc_offset)
            print(f"[INFO] Obs desplazadas {-utc_offset:+d} h a UTC (obs_utc_offset={utc_offset})")
    else:
        print("[WARN] Archivo de observaciones no encontrado. Solo graficos WRF.")
        obs_df = pd.DataFrame()

    ds = xr.open_mfdataset(wrf_files, combine="by_coords")
    j, i = _punto_estacion(ds, val_cfg)

    resultados_metricas = []

    for var, cfg_var in variables.items():
        ax = cfg_var["ax"]

        # WRF outputs U10/V10, not wspd10/wdir10 — compute from components
        if cfg_var["wrf_var"] == "U10_V10_wspd":
            u10 = ds["U10"].isel(south_north=j, west_east=i).to_pandas()
            v10 = ds["V10"].isel(south_north=j, west_east=i).to_pandas()
            wrf_ts = np.sqrt(u10**2 + v10**2)
        elif cfg_var["wrf_var"] == "U10_V10_wdir":
            u10 = ds["U10"].isel(south_north=j, west_east=i).to_pandas()
            v10 = ds["V10"].isel(south_north=j, west_east=i).to_pandas()
            wrf_ts = (270.0 - np.degrees(np.arctan2(v10, u10))) % 360.0
        else:
            wrf_var = ds[cfg_var["wrf_var"]]
            wrf_ts = wrf_var.isel(south_north=j, west_east=i).to_pandas()

        # Convert WRF units to obs units if needed
        if "convert" in cfg_var:
            wrf_ts = cfg_var["convert"](wrf_ts)

        ax.plot(wrf_ts.index, wrf_ts.values, "b-", alpha=0.7, label="WRF", linewidth=0.5)

        if not obs_df.empty and cfg_var["obs_col"] in obs_df.columns:
            obs_ts = obs_df[cfg_var["obs_col"]]
            ax.plot(obs_ts.index, obs_ts.values, "r.", alpha=0.5, label="Obs", markersize=2)

            # Alinear series para metricas
            common_idx = wrf_ts.index.intersection(obs_ts.index)
            obs_aligned = obs_ts.loc[common_idx]
            wrf_aligned = wrf_ts.loc[common_idx]

            metrics = compute_metrics(obs_aligned, wrf_aligned,
                                      circular=cfg_var.get("circular", False))
            resultados_metricas.append({"variable": var, **metrics})

            ax.text(0.02, 0.95,
                    f"RMSE={metrics['rmse']:.2f}  MAE={metrics['mae']:.2f}\n"
                    f"Sesgo={metrics['sesgo']:.2f}  IOA={metrics['ioa']:.2f}\n"
                    f"FB={metrics['fb']:.2f}  NMSE={metrics['nmse']:.2f}  R2={metrics['r2']:.2f}  N={metrics['n']}",
                    transform=ax.transAxes, fontsize=8, verticalalignment="top",
                    bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))

        ax.set_ylabel(cfg_var["units"])
        ax.set_title(cfg_var["title"])
        ax.legend(loc="lower right", fontsize=8)
        ax.grid(True, alpha=0.3)

    axes[-1].xaxis.set_major_locator(mdates.MonthLocator())
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    plt.xticks(rotation=45)

    fig.suptitle(f"Validacion WRF vs Observaciones — {proyecto} {anio}", fontsize=14, fontweight="bold")
    fig.tight_layout()

    out_file = out_dir / "validacion_wrf.png"
    fig.savefig(out_file, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[OK] Grafico guardado: {out_file}")

    # ── Guardar metricas ────────────────────────────────────────────────────
    if resultados_metricas:
        df_metrics = pd.DataFrame(resultados_metricas)
        metrics_file = out_dir / "metricas_validacion.csv"
        df_metrics.to_csv(metrics_file, index=False)
        print(f"[OK] Metricas guardadas: {metrics_file}")

        # Tabla LaTeX para informe
        latex_file = out_dir / "metricas_validacion.tex"
        latex = df_metrics[["variable", "n", "rmse", "mae", "sesgo", "ioa", "fb", "nmse", "r2"]].to_latex(
            index=False, float_format="%.2f", caption="Metricas de validacion WRF vs observaciones",
            label="tab:validacion_wrf"
        )
        latex_file.write_text(latex)

    ds.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 validar_wrf.py config.yaml")
        sys.exit(1)
    validar_wrf(sys.argv[1])
