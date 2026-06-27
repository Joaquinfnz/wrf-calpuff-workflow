#!/usr/bin/env python3
"""
emisiones_a_calpuff.py — Acople inventario de emisiones -> fuentes CALPUFF.

Lee emisiones.csv (una fila por fuente/hora/contaminante) y:
  1. Agrupa por fuente, separa por tipo (P/A/L/V) y arma la tasa por especie.
  2. Cuenta fuentes -> npt1 / nar1 / nvol1 / nln1.
  3. Genera el bloque de fuentes CALPUFF en data/calpuff/sources.inc.
  4. Con --apply, escribe los conteos y CSPEC en config.yaml.

OJO: el calpuff.inp.j2 hoy NO incluye los Input Groups de fuentes. sources.inc
es el fragmento a insertar (Grupos 13 punto / 14 area / 16 volumen). El formato
fino de CALPUFF 7.x se valida en la primera corrida.

CSV: fuente,tipo,x_utm,y_utm,elev_m,diametro_m,altura_m,temp_k,vel_ms,fecha,hora,contaminante,tasa_gs
  tipo: P=puntual  A=area  L=lineal  V=volumetrica
"""

import csv
import sys
import re
from pathlib import Path
from collections import OrderedDict

TIPO_A_COUNT = {"P": "npt1", "A": "nar1", "V": "nvol1", "L": "nln1"}


def leer_fuentes(csv_path):
    """Devuelve OrderedDict fuente -> {tipo, x, y, elev, diam, alt, temp, vel, sp:{}}."""
    fuentes = OrderedDict()
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(r for r in f if not r.lstrip().startswith("#"))
        for row in reader:
            name = row["fuente"].strip()
            if name not in fuentes:
                fuentes[name] = {
                    "tipo": row["tipo"].strip().upper(),
                    "x": float(row["x_utm"]), "y": float(row["y_utm"]),
                    "elev": float(row["elev_m"]), "diam": float(row["diametro_m"]),
                    "alt": float(row["altura_m"]), "temp": float(row["temp_k"]),
                    "vel": float(row["vel_ms"]), "sp": {},
                }
            cont = row["contaminante"].strip()
            # tasa constante = promedio de las filas de esa fuente/especie
            prev = fuentes[name]["sp"].get(cont, [])
            prev.append(float(row["tasa_gs"]))
            fuentes[name]["sp"][cont] = prev
    # colapsar listas de tasas a promedio
    for s in fuentes.values():
        s["sp"] = {k: round(sum(v) / len(v), 4) for k, v in s["sp"].items()}
    return fuentes


def resumen(fuentes):
    counts = {"npt1": 0, "nar1": 0, "nvol1": 0, "nln1": 0}
    especies = []
    for s in fuentes.values():
        key = TIPO_A_COUNT.get(s["tipo"])
        if key:
            counts[key] += 1
        for sp in s["sp"]:
            if sp not in especies:
                especies.append(sp)
    return counts, especies


def render_sources_inc(fuentes):
    """Bloque de fuentes CALPUFF (X/Y en km). Fragmento para Input Groups 13/14/16."""
    out = ["! Generado por emisiones_a_calpuff.py — fuentes con tasa constante (g/s)\n"]
    for name, s in fuentes.items():
        xkm, ykm = s["x"] / 1000.0, s["y"] / 1000.0
        out.append(f"! SRCNAM = {name} !  (tipo {s['tipo']})")
        out.append(f"! X = {xkm:.3f} !  ! Y = {ykm:.3f} !  ! BASE_ELEV = {s['elev']:.1f} !")
        if s["tipo"] == "P":
            out.append(f"! STK_HT = {s['alt']:.1f} !  ! DIAM = {s['diam']:.2f} !  "
                       f"! EXIT_VEL = {s['vel']:.2f} !  ! EXIT_TEMP = {s['temp']:.1f} !")
        elif s["tipo"] in ("A", "V"):
            out.append(f"! EFF_HT = {s['alt']:.1f} !  ! INIT_SIZE = {s['diam']:.2f} !  "
                       f"(area/volumen: requiere geometria/vertices reales)")
        rates = "  ".join(f"! {sp} = {r} !" for sp, r in s["sp"].items())
        out.append(f"! TASAS_GS:  {rates}")
        out.append("")
    return "\n".join(out)


def apply_config(counts, especies, config_path):
    p = Path(config_path)
    txt = p.read_text()
    for key, val in counts.items():
        txt = re.sub(rf"(^\s*{key}:\s*)\d+", rf"\g<1>{val}", txt, count=1, flags=re.MULTILINE)
    txt = re.sub(r"(^\s*nspt1:\s*)\d+", rf"\g<1>{len(especies)}", txt, count=1, flags=re.MULTILINE)
    p.write_text(txt)
    print(f"[OK] {p.name}: npt1/nar1/nvol1/nln1 y nspt1 actualizados")


def main():
    args = sys.argv[1:]
    csv_path = args[0] if args else "emisiones.csv"
    fuentes = leer_fuentes(csv_path)
    counts, especies = resumen(fuentes)

    out_inc = Path("data/calpuff/sources.inc")
    out_inc.parent.mkdir(parents=True, exist_ok=True)
    out_inc.write_text(render_sources_inc(fuentes))

    print(f"  Fuentes leidas : {len(fuentes)}")
    print(f"  Conteos        : {counts}")
    print(f"  Especies       : {especies}")
    print(f"  Bloque CALPUFF : {out_inc}")
    if "--apply" in args:
        i = args.index("--apply")
        cfg = args[i + 1] if i + 1 < len(args) else "config.yaml"
        apply_config(counts, especies, cfg)


def _demo():
    """Auto-chequeo: 2 fuentes (1 punto, 1 area), 2 especies."""
    import tempfile, os
    csv_txt = (
        "fuente,tipo,x_utm,y_utm,elev_m,diametro_m,altura_m,temp_k,vel_ms,fecha,hora,contaminante,tasa_gs\n"
        "CHANC-01,V,640000,5430000,130,5,3,290,0.1,2024-01-01,01,PM10,2.0\n"
        "CHANC-01,V,640000,5430000,130,5,3,290,0.1,2024-01-01,02,PM10,4.0\n"
        "ACOPIO-1,A,640200,5430100,128,10,2,290,0.1,2024-01-01,01,PM2_5,1.5\n"
    )
    d = tempfile.mkdtemp()
    f = os.path.join(d, "e.csv")
    open(f, "w").write(csv_txt)
    fuentes = leer_fuentes(f)
    counts, esp = resumen(fuentes)
    assert counts["nvol1"] == 1 and counts["nar1"] == 1, counts
    assert fuentes["CHANC-01"]["sp"]["PM10"] == 3.0, fuentes["CHANC-01"]["sp"]  # promedio 2 y 4
    assert set(esp) == {"PM10", "PM2_5"}, esp
    print("[demo OK] conteos y promedio de tasas correctos")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo()
    else:
        main()
