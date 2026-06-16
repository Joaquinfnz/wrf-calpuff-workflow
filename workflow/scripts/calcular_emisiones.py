#!/usr/bin/env python3
"""
calcular_emisiones.py — Calculador interactivo de emisiones para CALPUFF
Usa factores EPA AP-42 + SEA Chile desde factores_emision.yaml
Genera emisiones.csv con tasas horarias reales (requisito SEA 2023)

Presets:
  Extraccion de aridos: chancado, acopio, transito interno
  Industrial: calderas, grupos electrogenos
  Personalizado: elegir fuentes una a una
"""

import yaml
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import sys

# ── Constantes ───────────────────────────────────────────────────────────────
FACTORES_FILE = Path(__file__).parent / "factores_emision.yaml"
EMISIONES_FILE = Path("emisiones.csv")
CONFIG_FILE = Path("config.yaml")

# Colores terminal
BOLD = "\033[1m"
CYAN = "\033[0;36m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
NC = "\033[0m"


def load_factores():
    with open(FACTORES_FILE) as f:
        return yaml.safe_load(f)


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return yaml.safe_load(f)
    return {}


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def ask(prompt, default=""):
    """Pregunta interactiva con default"""
    if default:
        resp = input(f"  {prompt} [{default}]: ").strip()
        return resp if resp else default
    return input(f"  {prompt}: ").strip()


def ask_float(prompt, default=None):
    while True:
        d = str(default) if default is not None else ""
        resp = ask(prompt, d)
        try:
            return float(resp)
        except ValueError:
            print(f"  {RED}Ingresa un numero valido{NC}")


def ask_int(prompt, default=None):
    while True:
        d = str(default) if default is not None else ""
        resp = ask(prompt, d)
        try:
            return int(resp)
        except ValueError:
            print(f"  {RED}Ingresa un numero entero{NC}")


# ── Calculos de emision ─────────────────────────────────────────────────────

def calc_caldera(factores):
    """Calcula emisiones de caldera a gas natural o diesel"""
    print(f"\n{CYAN}CALDERA{NC}")
    combustible = ask("Combustible [gas_natural/diesel]", "gas_natural")

    if combustible == "gas_natural":
        f = factores["caldera_gas_natural"]
    else:
        f = factores["caldera_diesel"]

    potencia_mw = ask_float("Potencia termica (MW)", 10)
    horas_dia = ask_int("Horas de operacion al dia", 16)
    horario = ask("Horario inicio (HH:00)", "06")
    t_salida = ask_float("Temperatura salida gases (°C)", 150)
    v_salida = ask_float("Velocidad salida gases (m/s)", 12)
    diametro = ask_float("Diametro chimenea (m)", 1.2)
    altura = ask_float("Altura chimenea (m)", 25)

    x = ask_float("Coordenada X UTM", 640000)
    y = ask_float("Coordenada Y UTM", 5430000)
    elev = ask_float("Elevacion (m.s.n.m.)", 130)

    emisiones = []
    for cont, datos in f["contaminantes"].items():
        tasa_gs = datos["factor_g_MW"] * potencia_mw
        if tasa_gs > 0.001:
            emisiones.append({
                "fuente": "CAL-01",
                "tipo": "P",
                "contaminante": cont,
                "tasa_gs": round(tasa_gs, 4),
                "x_utm": x,
                "y_utm": y,
                "elev_m": elev,
                "diametro_m": diametro,
                "altura_m": altura,
                "temp_k": t_salida + 273.15,
                "vel_ms": v_salida,
                "horas_dia": horas_dia,
                "horario_inicio": int(horario),
                "factor_origen": datos["fuente"],
            })
            print(f"  {GREEN}→{NC} {cont}: {tasa_gs:.4f} g/s  ({datos['fuente']})")

    return emisiones


def calc_chancado(factores, id_fuente=None):
    """Calcula emisiones de chancado/molino de aridos"""
    print(f"\n{CYAN}CHANCADO / MOLINO{NC}")
    fid = id_fuente or "CH-01"

    ton_h = ask_float("Produccion (ton/hora)", 60)
    control = ask("Control de polvo? [s/N]", "n").lower() == "s"
    horas_dia = ask_int("Horas de operacion al dia", 16)
    horario = ask("Horario inicio (HH:00)", "06")

    x = ask_float("Coordenada X UTM", 640100)
    y = ask_float("Coordenada Y UTM", 5430100)
    elev = ask_float("Elevacion (m.s.n.m.)", 135)
    altura = ask_float("Altura descarga (m)", 5)

    f = factores["chancado"]
    emisiones = []
    for cont, datos in f["contaminantes"].items():
        key = "factor_kg_ton_controlado" if control else "factor_kg_ton"
        factor_kg_ton = datos[key]
        tasa_gs = factor_kg_ton * ton_h * (1000 / 3600)  # kg/ton → g/s
        if tasa_gs > 0.0001:
            emisiones.append({
                "fuente": fid,
                "tipo": "P",
                "contaminante": cont,
                "tasa_gs": round(tasa_gs, 4),
                "x_utm": x, "y_utm": y,
                "elev_m": elev,
                "diametro_m": 0.5,
                "altura_m": altura,
                "temp_k": 293,
                "vel_ms": 0.5,
                "horas_dia": horas_dia,
                "horario_inicio": int(horario),
                "factor_origen": datos["fuente"],
            })
            print(f"  {GREEN}→{NC} {cont}: {tasa_gs:.4f} g/s  ({datos['fuente']})")

    return emisiones


def calc_acopio(factores, id_fuente=None):
    """Calcula emisiones de acopio por erosion eolica"""
    print(f"\n{CYAN}ACOPIO DE MATERIAL{NC}")
    fid = id_fuente or "AC-01"

    area_m2 = ask_float("Superficie maxima expuesta (m²)", 5000)
    viento_ms = ask_float("Velocidad viento media (m/s)", 5)
    horas_dia = ask_int("Horas de operacion al dia", 24)  # erosion = 24h
    horario = 0

    x = ask_float("Coordenada X UTM centro", 640200)
    y = ask_float("Coordenada Y UTM centro", 5430200)
    elev = ask_float("Elevacion (m.s.n.m.)", 132)

    f = factores["acopio_aridos"]
    emisiones = []
    for cont, datos in f["contaminantes"].items():
        # Ajuste por velocidad de viento: (v/5)^1.3
        factor_base = datos["factor_base"]
        tasa_gs = factor_base * area_m2 * (viento_ms / 5) ** 1.3
        if tasa_gs > 0.0001:
            emisiones.append({
                "fuente": fid,
                "tipo": "A",
                "contaminante": cont,
                "tasa_gs": round(tasa_gs, 4),
                "x_utm": x, "y_utm": y,
                "elev_m": elev,
                "diametro_m": 0,
                "altura_m": 2,  # altura media del acopio
                "temp_k": 293,
                "vel_ms": 0.1,
                "horas_dia": horas_dia,
                "horario_inicio": horario,
                "factor_origen": datos["fuente"],
            })
            print(f"  {GREEN}→{NC} {cont}: {tasa_gs:.4f} g/s  ({datos['fuente']})")

    return emisiones


def calc_transito(factores, id_fuente=None):
    """Calcula emisiones de transito en caminos no pavimentados"""
    print(f"\n{CYAN}TRANSITO VEHICULAR (no pavimentado){NC}")
    fid = id_fuente or "TR-01"

    camiones_dia = ask_int("Camiones/dia", 40)
    largo_km = ask_float("Largo de la ruta (km)", 2.5)
    horas_dia = ask_int("Horas de operacion al dia", 16)
    horario = ask("Horario inicio (HH:00)", "06")

    x1 = ask_float("Coordenada X inicio UTM", 639900)
    y1 = ask_float("Coordenada Y inicio UTM", 5430000)
    x2 = ask_float("Coordenada X fin UTM", 640400)
    y2 = ask_float("Coordenada Y fin UTM", 5430250)

    f = factores["transito_no_pavimentado"]
    p = f["parametros"]
    silt = ask_float("Fraccion de finos % silt", p["silt_default"])
    peso = ask_float("Peso medio vehiculo (ton)", p["peso_default"])

    # EPA AP-42 §13.2.2: E = k * (s/12)^a * (W/3)^b  lb/VMT
    k = p["k_pm10"]
    a = p["a"]
    b = p["b"]
    factor_lb_vmt = k * (silt / 12) ** a * (peso / 3) ** b

    # lb/VMT → g/s: VKT = (camiones/dia * largo_km * 2 ida+vuelta)
    vkt_dia = camiones_dia * largo_km * 2  # vehicle-km-traveled per day
    vmt_dia = vkt_dia * 0.621371  # km → miles
    lb_dia = factor_lb_vmt * vmt_dia
    g_s = lb_dia * 453.592 / (horas_dia * 3600)  # lb/dia → g/s

    emisiones = []
    if g_s > 0.0001:
        emisiones.append({
            "fuente": fid,
            "tipo": "L",
            "contaminante": "MP10",
            "tasa_gs": round(g_s, 4),
            "x_utm": x1, "y_utm": y1,
            "elev_m": 130,
            "diametro_m": 0, "altura_m": 2,
            "temp_k": 293, "vel_ms": 0.1,
            "horas_dia": horas_dia,
            "horario_inicio": int(horario),
            "factor_origen": f["contaminantes"]["MP10"]["fuente"],
            "x_fin": x2, "y_fin": y2,
        })
        print(f"  {GREEN}→{NC} MP10: {g_s:.4f} g/s  ({f['contaminantes']['MP10']['fuente']})")
        print(f"     VKT: {vkt_dia:.1f} km/dia  |  Factor: {factor_lb_vmt:.4f} lb/VMT")

        # MP2.5 = fraccion de MP10
        frac_mp25 = f["contaminantes"]["MP2_5"]["fraccion_mp10"]
        mp25_gs = g_s * frac_mp25
        emisiones.append({
            "fuente": fid, "tipo": "L",
            "contaminante": "MP2_5",
            "tasa_gs": round(mp25_gs, 4),
            "x_utm": x1, "y_utm": y1,
            "elev_m": 130,
            "diametro_m": 0, "altura_m": 2,
            "temp_k": 293, "vel_ms": 0.1,
            "horas_dia": horas_dia,
            "horario_inicio": int(horario),
            "factor_origen": f["contaminantes"]["MP2_5"]["fuente"],
            "x_fin": x2, "y_fin": y2,
        })
        print(f"  {GREEN}→{NC} MP2.5: {mp25_gs:.4f} g/s  ({frac_mp25*100:.0f}% de MP10)")

    return emisiones


def calc_grupo_electrogeno(factores):
    """Calcula emisiones de grupo electrogeno diesel"""
    print(f"\n{CYAN}GRUPO ELECTROGENO{NC}")
    f = factores["grupo_electrogeno"]

    potencia_kva = ask_float("Potencia (kVA)", 100)
    horas_dia = ask_int("Horas de operacion al dia", 24)
    horario = ask("Horario inicio (HH:00)", "00")
    t_salida = ask_float("Temperatura salida gases (°C)", 400)
    v_salida = ask_float("Velocidad salida gases (m/s)", 20)
    diametro = ask_float("Diametro chimenea (m)", 0.3)
    altura = ask_float("Altura chimenea (m)", 4)

    x = ask_float("Coordenada X UTM", 640050)
    y = ask_float("Coordenada Y UTM", 5430050)
    elev = ask_float("Elevacion (m.s.n.m.)", 130)

    # ~0.8 factor de potencia, 1 kVA ≈ 0.8 kW
    potencia_mw = potencia_kva * 0.8 / 1000

    emisiones = []
    for cont, datos in f["contaminantes"].items():
        tasa_gs = datos["factor_g_MW"] * potencia_mw
        if tasa_gs > 0.0001:
            emisiones.append({
                "fuente": "GE-01",
                "tipo": "P",
                "contaminante": cont,
                "tasa_gs": round(tasa_gs, 4),
                "x_utm": x, "y_utm": y,
                "elev_m": elev,
                "diametro_m": diametro,
                "altura_m": altura,
                "temp_k": t_salida + 273.15,
                "vel_ms": v_salida,
                "horas_dia": horas_dia,
                "horario_inicio": int(horario),
                "factor_origen": datos["fuente"],
            })
            print(f"  {GREEN}→{NC} {cont}: {tasa_gs:.4f} g/s  ({datos['fuente']})")

    return emisiones


# ── Generar CSV ──────────────────────────────────────────────────────────────

def generar_csv(todas_emisiones, cfg):
    """Genera emisiones.csv con tasas horarias reales (1 fila x fuente x hora x contaminante)"""
    periodo = cfg.get("periodo", {})
    inicio_str = periodo.get("inicio", "2024-01-01_00:00:00")
    fin_str = periodo.get("fin", "2024-12-31_23:00:00")

    inicio = datetime.strptime(inicio_str.split("_")[0], "%Y-%m-%d")
    fin = datetime.strptime(fin_str.split("_")[0], "%Y-%m-%d")

    filas = []
    fecha = inicio
    while fecha <= fin:
        for em in todas_emisiones:
            horas_dia = em.get("horas_dia", 24)
            h_inicio = em.get("horario_inicio", 0)

            for h in range(h_inicio, h_inicio + horas_dia):
                if h >= 24:
                    h = h - 24
                hora_str = f"{h:02d}"

                para_calpuff = {
                    "fuente": em["fuente"],
                    "tipo": em["tipo"],
                    "x_utm": em["x_utm"],
                    "y_utm": em["y_utm"],
                    "elev_m": em["elev_m"],
                    "diametro_m": em.get("diametro_m", 0),
                    "altura_m": em.get("altura_m", 0),
                    "temp_k": em.get("temp_k", 293),
                    "vel_ms": em.get("vel_ms", 0.1),
                    "fecha": fecha.strftime("%Y-%m-%d"),
                    "hora": hora_str,
                    "contaminante": em["contaminante"],
                    "tasa_gs": em["tasa_gs"],
                }

                if em["tipo"] == "L" and "x_fin" in em:
                    para_calpuff["x_fin"] = em["x_fin"]
                    para_calpuff["y_fin"] = em["y_fin"]

                filas.append(para_calpuff)
        fecha += timedelta(days=1)

    df = pd.DataFrame(filas)

    # Ordenar
    df = df.sort_values(["fuente", "fecha", "hora", "contaminante"])

    # Guardar
    with open(EMISIONES_FILE, "w") as f:
        f.write("# ── Inventario de Emisiones — Generado automaticamente ─────────────────────\n")
        f.write(f"# Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"# Proyecto: {cfg.get('proyecto', {}).get('nombre', 'Sin Nombre')}\n")
        f.write(f"# Periodo: {inicio_str} → {fin_str}\n")
        f.write(f"# Requisito SEA: tasas horarias reales\n")
        f.write(f"# Fuentes: {len(set(e['fuente'] for e in todas_emisiones))}  |  ")
        f.write(f"Registros: {len(df)}\n")
        f.write("# =============================================================================\n")

    df.to_csv(EMISIONES_FILE, mode="a", index=False)

    # Actualizar config.yaml
    npt = sum(1 for e in todas_emisiones if e["tipo"] == "P")
    nar = sum(1 for e in todas_emisiones if e["tipo"] == "A")
    nln = sum(1 for e in todas_emisiones if e["tipo"] == "L")

    cfg["calpuff"]["npt1"] = npt
    cfg["calpuff"]["nar1"] = nar
    cfg["calpuff"]["nln1"] = nln
    save_config(cfg)

    return df


# ── Presets ──────────────────────────────────────────────────────────────────

def preset_aridos(factores):
    """Preset: Extraccion de aridos (chancado + acopio + transito)"""
    print(f"\n{BOLD}=== EXTRACCION DE ARIDOS ==={NC}")
    print(f"  Fuentes predefinidas: chancado, acopio, tránsito interno\n")

    emisiones = []
    emisiones += calc_chancado(factores, "CH-01")
    emisiones += calc_acopio(factores, "AC-01")
    emisiones += calc_transito(factores, "TR-01")

    return emisiones


def preset_industrial(factores):
    """Preset: Industrial (caldera + opcional GE)"""
    print(f"\n{BOLD}=== INDUSTRIAL ==={NC}")
    emisiones = []
    emisiones += calc_caldera(factores)

    ge = ask("Agregar grupo electrogeno? [s/N]", "n")
    if ge.lower() == "s":
        emisiones += calc_grupo_electrogeno(factores)

    return emisiones


def menu_manual(factores):
    """Menu manual: elegir fuentes una a una"""
    emisiones = []
    while True:
        print(f"\n{CYAN}¿Que fuente agregar?{NC}")
        print(f"  1. Caldera")
        print(f"  2. Chancado / molino")
        print(f"  3. Acopio de material")
        print(f"  4. Transito vehicular (no pavimentado)")
        print(f"  5. Grupo electrogeno")
        print(f"  0. Terminar y generar CSV")

        op = ask("Selecciona (0-5)", "0")
        if op == "1":
            emisiones += calc_caldera(factores)
        elif op == "2":
            fid = f"CH-{len([e for e in emisiones if e.get('fuente','').startswith('CH')])+1:02d}"
            emisiones += calc_chancado(factores, fid)
        elif op == "3":
            fid = f"AC-{len([e for e in emisiones if e.get('fuente','').startswith('AC')])+1:02d}"
            emisiones += calc_acopio(factores, fid)
        elif op == "4":
            emisiones += calc_transito(factores)
        elif op == "5":
            emisiones += calc_grupo_electrogeno(factores)
        elif op == "0":
            break
        else:
            print(f"  {RED}Opcion invalida{NC}")

    return emisiones


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    print(f"{BOLD}{'='*60}{NC}")
    print(f"{BOLD}  CALCULADOR DE EMISIONES PARA CALPUFF{NC}")
    print(f"{BOLD}  Factores: EPA AP-42 + SEA Chile{NC}")
    print(f"{BOLD}{'='*60}{NC}")

    if not FACTORES_FILE.exists():
        print(f"\n{RED}[ERROR] {FACTORES_FILE} no encontrado{NC}")
        sys.exit(1)

    factores = load_factores()
    cfg = load_config()

    # Nombre del proyecto
    nombre = ask("\nNombre del proyecto", cfg.get("proyecto", {}).get("nombre", "Sin Nombre"))
    if "proyecto" not in cfg:
        cfg["proyecto"] = {}
    cfg["proyecto"]["nombre"] = nombre

    # Tipo de proyecto
    print(f"\n{CYAN}Tipo de proyecto:{NC}")
    print(f"  1. Extraccion de aridos (chancado + acopio + transito)")
    print(f"  2. Industrial (caldera, grupo electrogeno)")
    print(f"  3. Personalizado (elegir fuentes una a una)")
    tipo = ask("Selecciona (1-3)", "1")

    if tipo == "1":
        todas = preset_aridos(factores)
    elif tipo == "2":
        todas = preset_industrial(factores)
    else:
        todas = menu_manual(factores)

    if not todas:
        print(f"\n{RED}No se definieron fuentes. Saliendo.{NC}")
        sys.exit(0)

    # ── Resumen ────────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'─'*50}{NC}")
    print(f"{BOLD}  RESUMEN{NC}")
    print(f"{BOLD}{'─'*50}{NC}")

    fuentes = {}
    for e in todas:
        fid = e["fuente"]
        if fid not in fuentes:
            fuentes[fid] = {"tipo": e["tipo"], "conts": {}}
        fuentes[fid]["conts"][e["contaminante"]] = e["tasa_gs"]

    total_gs = 0
    for fid, data in fuentes.items():
        tipo_name = {"P": "Puntual", "A": "Area", "L": "Lineal"}[data["tipo"]]
        conts_str = ", ".join(f"{c} {v:.4f}" for c, v in data["conts"].items())
        print(f"  {fid} ({tipo_name}): {conts_str} g/s")
        total_gs += sum(data["conts"].values())

    npt = sum(1 for d in fuentes.values() if d["tipo"] == "P")
    nar = sum(1 for d in fuentes.values() if d["tipo"] == "A")
    nln = sum(1 for d in fuentes.values() if d["tipo"] == "L")

    print(f"  {'─'*48}")
    print(f"  Total fuentes: {len(fuentes)} (P={npt}, A={nar}, L={nln})")
    print(f"  Suma tasas: {total_gs:.4f} g/s (promedio horario)")

    # ── Generar CSV ────────────────────────────────────────────────────────
    print(f"\n{GREEN}Generando emisiones.csv...{NC}")
    df = generar_csv(todas, cfg)
    print(f"  {GREEN}[OK]{NC} {EMISIONES_FILE} — {len(df)} registros horarios")
    print(f"  {GREEN}[OK]{NC} {CONFIG_FILE} — actualizado (npt1={npt}, nar1={nar}, nln1={nln})")
    print(f"\n{BOLD}Listo. Podes lanzar la modelacion con: bash scripts/run.sh{NC}\n")


if __name__ == "__main__":
    main()
