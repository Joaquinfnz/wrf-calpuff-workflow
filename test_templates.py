#!/usr/bin/env python3
"""test_templates.py — Verifica que los templates Jinja2 renderizan sin errores."""
import sys
import yaml
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined


def test_templates_render():
    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)

    # Build context like render_namelist.py does
    from datetime import datetime
    inicio_str = cfg["periodo"]["inicio"].split("_")
    fin_str = cfg["periodo"]["fin"].split("_")
    inicio_dt = datetime.strptime(inicio_str[0], "%Y-%m-%d")
    inicio_time = datetime.strptime(inicio_str[1], "%H:%M:%S")
    fin_dt = datetime.strptime(fin_str[0], "%Y-%m-%d")
    fin_time = datetime.strptime(fin_str[1], "%H:%M:%S")
    ctx = {
        "proyecto": cfg["proyecto"],
        "wrf": cfg["wrf"],
        "calmet": cfg["calmet"],
        "calpuff": cfg["calpuff"],
        "periodo": cfg["periodo"],
        "rutas": cfg.get("rutas", {}),
        "validacion": cfg.get("validacion", {}),
        "normas": cfg.get("normas", {}),
        "inicio_year": inicio_dt.year,
        "inicio_month": inicio_dt.month,
        "inicio_day": inicio_dt.day,
        "inicio_hour": inicio_time.hour,
        "inicio_minute": inicio_time.minute,
        "inicio_second": inicio_time.second,
        "fin_year": fin_dt.year,
        "fin_month": fin_dt.month,
        "fin_day": fin_dt.day,
        "fin_hour": fin_time.hour,
        "fin_minute": fin_time.minute,
        "fin_second": fin_time.second,
        "utm_zone": cfg.get("calmet", {}).get("utm_zone", 18),
        "utm_offset": cfg.get("calmet", {}).get("utm_offset", -4.0),
        "calmet_xorig": cfg.get("calmet", {}).get("xorig", -10.0),
        "calmet_yorig": cfg.get("calmet", {}).get("yorig", -10.0),
    }

    env = Environment(loader=FileSystemLoader("static"), undefined=StrictUndefined)

    templates = ["namelist.wps.j2", "namelist.input.j2", "calmet.inp.j2", "calpuff.inp.j2"]
    for tpl_name in templates:
        tpl = env.get_template(tpl_name)
        try:
            rendered = tpl.render(**ctx)
            print(f"[OK] {tpl_name} rendered ({len(rendered)} chars)")
        except Exception as e:
            print(f"[FAIL] {tpl_name}: {e}")
            return False

    return True


def test_species_names_consistent():
    """Verify PM2_5 is used consistently (not PM25)."""
    calpuff_template = Path("static/calpuff.inp.j2").read_text()
    assert "PM25 " not in calpuff_template, "PM25 found in calpuff.inp.j2 — should be PM2_5"
    assert "PM2_5" in calpuff_template, "PM2_5 not found in calpuff.inp.j2"
    print("[OK] Species names consistent (PM2_5)")


def test_itergrd_matches():
    """Verify calmet.inp.j2 uses itergrd (matching config.yaml key)."""
    calmet_template = Path("static/calmet.inp.j2").read_text()
    assert "iterrgrd" not in calmet_template, "iterrgrd found — should be itergrd (matches config.yaml)"
    assert "itergrd" in calmet_template, "itergrd not found in calmet.inp.j2"
    print("[OK] calmet.inp.j2 uses itergrd (matches config.yaml)")


if __name__ == "__main__":
    repo_root = Path(__file__).parent
    import os
    os.chdir(repo_root)

    ok = True
    ok &= test_templates_render()
    test_species_names_consistent()
    test_itergrd_matches()

    if ok:
        print("\nAll tests passed.")
        sys.exit(0)
    else:
        print("\nSome tests failed.")
        sys.exit(1)
