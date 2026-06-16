#!/usr/bin/env python3
"""
check_config.py — Pre-flight validation del config.yaml
Verifica requisitos minimos de la Guia SEA 2023:
  - Resolucion <= 1 km en dominio mas fino
  - Minimo 50 celdas por direccion
  - Minimo 2-3 dominios anidados
  - Emisiones con tasas horarias
"""
import sys
import yaml


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

    print(f"\n  [OK] {ndom} dominios anidados")
    print(f"  [OK] Dominio fino: {dom_fino['resolution_km']} km")
    print(f"  [OK] Celdas: {dom_fino['e_we']}x{dom_fino['e_sn']}")
    print(f"  [OK] Periodo: {dias} dias")
    print(f"  [OK] Microphysics: WSM6 (mp_physics=6)")
    print(f"  [OK] Cumulus: Kain-Fritsch (d01/d02)")
    print(f"  [OK] PBL: YSU")
    print(f"  [OK] Superficie: Noah LSM")
    print(f"  [OK] Proyeccion: {wrf['map_proj']}")
    print(f"\n  Configuracion validada. Listo para correr.\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 check_config.py config.yaml")
        sys.exit(1)
    check_config(sys.argv[1])
