#!/usr/bin/env python3
"""
check_config.py — Pre-flight validation del config.yaml
Verifica requisitos minimos de la Guia SEA 2023:
  - Resolucion <= 1 km en dominio mas fino
  - Minimo 50 celdas por direccion
  - Minimo 2-3 dominios anidados
  - Emisiones con tasas horarias
Y consistencia interna:
  - era5.area cubre el dominio exterior d01 (si no, metgrid falla a mitad
    de corrida por datos faltantes en el borde)
"""
import math
import sys
import yaml


def era5_area_minima(wrf):
    """[N, W, S, E] minimo que debe cubrir era5.area para contener d01."""
    d01 = list(wrf["dominios"].values())[0]
    half_km = (d01["e_we"] - 1) * d01["resolution_km"] / 2.0
    dlat = half_km / 111.0
    dlon = half_km / (111.0 * math.cos(math.radians(wrf["ref_lat"])))
    return [wrf["ref_lat"] + dlat, wrf["ref_lon"] - dlon,
            wrf["ref_lat"] - dlat, wrf["ref_lon"] + dlon]


def check_config(config_path):
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    errors = []
    warnings = []

    wrf = cfg["wrf"]
    dominios = wrf["dominios"]

    # ── Numero de dominios (SEA: 2-3) ───────────────────────────────────────
    ndom = wrf["max_dom"]
    if ndom < 2:
        errors.append(f"max_dom={ndom}. SEA exige minimo 2 dominios anidados (recomendado 3).")
    elif ndom < 3:
        warnings.append(f"max_dom={ndom}. SEA recomienda 3 dominios anidados.")

    # ── Celdas minimas (SEA: >= 50) ─────────────────────────────────────────
    for name, dom in dominios.items():
        if dom["e_we"] < 50 or dom["e_sn"] < 50:
            errors.append(
                f"Dominio {name}: e_we={dom['e_we']}, e_sn={dom['e_sn']}. "
                f"SEA exige >= 50 celdas en cada direccion."
            )

    # ── Resolucion dominio fino (SEA: <= 1 km) ─────────────────────────────
    dom_fino = list(dominios.values())[-1]
    if dom_fino["resolution_km"] > 1:
        errors.append(
            f"Dominio fino ({dom_fino['resolution_km']} km) excede 1 km. "
            f"SEA exige resolucion <= 1 km en dominio mas fino."
        )

    # ── Parent grid ratio (max 5 recomendado) ───────────────────────────────
    for name, dom in dominios.items():
        if dom["parent_grid_ratio"] > 5:
            warnings.append(
                f"Dominio {name}: parent_grid_ratio={dom['parent_grid_ratio']}. "
                f"Se recomienda ratio <= 5 para estabilidad numerica."
            )

    # ── Periodo minimo 1 año ───────────────────────────────────────────────
    inicio = cfg["periodo"]["inicio"].split("_")[0]
    fin = cfg["periodo"]["fin"].split("_")[0]
    yi, mi, di = map(int, inicio.split("-"))
    yf, mf, df = map(int, fin.split("-"))
    from datetime import date
    dias = (date(yf, mf, df) - date(yi, mi, di)).days
    if dias < 365:
        errors.append(
            f"Periodo modelado: {dias} dias. SEA exige minimo 1 año completo "
            f"para contaminantes primarios."
        )

    # ── Cobertura ERA5 vs dominio d01 ───────────────────────────────────────
    area = cfg.get("era5", {}).get("area")
    if area:
        n, w, s, e = area
        n_min, w_min, s_min, e_min = era5_area_minima(wrf)
        if n < n_min or w > w_min or s > s_min or e < e_min:
            errors.append(
                f"era5.area {area} NO cubre el dominio d01 "
                f"(minimo [N,W,S,E] = [{n_min:.2f}, {w_min:.2f}, {s_min:.2f}, {e_min:.2f}]). "
                f"metgrid fallaria por datos faltantes. Recalcula con importar_kmz.py."
            )

    # ── Emisiones horarias ─────────────────────────────────────────────────
    formato = cfg["emisiones"].get("formato", "")
    if formato.lower() != "horario":
        warnings.append(
            "SEA exige emisiones con tasas horarias reales, no promedios diarios."
        )

    # ── Validacion meteorologica ────────────────────────────────────────────
    val = cfg.get("validacion", {})
    obs_file = val.get("observaciones", "")
    if not obs_file:
        warnings.append(
            "No se especifico archivo de observaciones meteorologicas. "
            "SEA exige validacion WRF vs obs >= 1 año."
        )

    # ── Output ─────────────────────────────────────────────────────────────
    print("=" * 70)
    print("  CHECK CONFIGURACION — Guia SEA 2023 (v4)")
    print("=" * 70)

    if errors:
        print(f"\n  ERRORES ({len(errors)}):")
        for e in errors:
            print(f"    [ERROR] {e}")
        print(f"\n  CORRIGE los errores en config.yaml antes de continuar.\n")
        sys.exit(1)

    if warnings:
        print(f"\n  ADVERTENCIAS ({len(warnings)}):")
        for w in warnings:
            print(f"    [WARN]  {w}")

    phys = wrf.get("physics", {})
    print(f"\n  [OK] {ndom} dominios anidados")
    print(f"  [OK] Dominio fino: {dom_fino['resolution_km']} km")
    print(f"  [OK] Celdas: {dom_fino['e_we']}x{dom_fino['e_sn']}")
    print(f"  [OK] Periodo: {dias} dias")
    print(f"  [OK] mp_physics={phys.get('mp_physics')}  cu_physics={phys.get('cu_physics')}")
    print(f"  [OK] bl_pbl={phys.get('bl_pbl_physics')}  sf_surface={phys.get('sf_surface_physics')}")
    print(f"  [OK] Proyeccion: {wrf['map_proj']}")
    if area:
        print(f"  [OK] era5.area cubre d01")
    print(f"\n  Configuracion validada. Listo para correr.\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 check_config.py config.yaml")
        sys.exit(1)
    check_config(sys.argv[1])
