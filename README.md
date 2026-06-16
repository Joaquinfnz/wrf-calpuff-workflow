# WRF → CALPUFF Workflow — Modelacion de Calidad del Aire

Pipeline automatizado de modelacion meteorologica (WRF) y dispersion de
contaminantes (CALPUFF), alineado a la **Guia SEA 2023** (v4, Feb 2023).

Repo: https://github.com/Joaquinfnz/wrf-calpuff-workflow

---

## Instalacion en tu servidor

```bash
# 1. Conectate por SSH a tu servidor
ssh ubuntu@<ip-del-servidor>

# 2. Clona el repositorio
git clone https://github.com/Joaquinfnz/wrf-calpuff-workflow.git
cd wrf-calpuff-workflow

# 3. Ejecuta el script de instalacion (1 sola vez, ~1.5-2 horas)
bash scripts/setup_server.sh
```

**Que hace `setup_server.sh`:**
- Instala Docker, git, Python, tmux, herramientas
- Descarga datos estaticos de terreno WPS_GEOG (~500 MB)
- Construye las imagenes Docker con WRF 4.6 + WPS 4.6 y CALPUFF 7.x
- Deja el servidor listo para modelar

---

## Como correr una modelacion

```bash
# 1. Calcula las emisiones de tu proyecto (interactivo)
python3 workflow/scripts/calcular_emisiones.py

# 2. Configura tu API key de ERA5
export CDSAPI_KEY='uid:api-key'

# 3. Lanza la modelacion
bash scripts/run.sh
```

`run.sh` se encarga de:
- Validar que la configuracion cumple la norma SEA
- Descargar datos ERA5 del periodo
- Generar los namelists automaticamente
- Lanzar el pipeline WRF → CALPUFF en tmux
- Checkpoint cada 6h para reanudar si se cae

```bash
# Para monitorear el progreso
tmux attach -t wrf-calpuff

# Para salir sin detener: Ctrl+B, luego D
```

---

## Como bajar los resultados a tu laptop

```bash
bash scripts/sync_results.sh ubuntu@<ip-del-servidor>
```

Te trae:
- Tablas Excel de concentraciones vs normas DS38
- Mapas de isoconcentracion PNG
- Memoria de calculo en Markdown
- Validacion WRF vs observaciones (metricas + graficos)
- Namelists y archivos CALPUFF para entregar al SEA

---

## Calculador de emisiones

El workflow incluye un calculador interactivo para generar el inventario de
emisiones sin necesidad de hacer los calculos a mano.

```bash
python3 workflow/scripts/calcular_emisiones.py
```

**Presets disponibles:**

| Preset | Fuentes incluidas |
|--------|-------------------|
| Extraccion de aridos | Chancado, acopio, transito interno |
| Industrial | Calderas, grupos electrogenos |
| Personalizado | Elegir fuentes una a una |

**Fuentes soportadas:** calderas (gas/diesel), chancado/molino, acopios,
transito no pavimentado (EPA AP-42 SS13.2.2), grupos electrogenos.

Los factores de emision estan en `workflow/scripts/factores_emision.yaml`
(EPA AP-42 + SEA Chile). Podes editarlos si tu proyecto requiere
factores especificos.

---

## Requisitos del servidor

| Recurso | Minimo |
|---------|--------|
| CPU | 32 cores / 64 threads |
| RAM | 128 GB |
| Disco | 1 TB |
| OS | Ubuntu 22.04 LTS |
| Internet | Para descargar ERA5 y WPS_GEOG |

**Opciones de servidor:**

| Opcion | Cores | Costo/modelacion | Setup | Nota |
|--------|-------|-----------------|-------|------|
| **Hetzner Auction (recomendado)** | 32-64T | **~€15-20** | SSH, listo | Recomendado. Simple, barato, sin IAM. Cancelas al terminar. |
| AWS EC2 spot | 72 vCPU | ~$85 | IAM + VPC + SG | Riesgo: spot puede interrumpir. Checkpoint mitiga. |
| AWS EC2 on-demand | 72 vCPU | ~$566 | IAM + VPC + SG | Caro, solo si necesitas 100% uptime. |

> En Hetzner Auction elegis el server con mas cores disponible en el momento.
> Minimo recomendado: 24 cores / 48 threads, 128 GB RAM, 1 TB disco.

---

## Pipeline

```
ERA5 (CDS API)
    │
    ▼
WPS: geogrid → ungrib → metgrid
    │
    ▼
WRF: real → wrf (corrida continua, checkpoint cada 6h)
    │                 
    ▼
CALWRF → CALMET → CALPUFF
    │
    ▼
Post-procesamiento SEIA
    · 5 grillas de receptores anidadas
    · Tablas vs DS 38/2011 y DS 104/2018
    · Mapas de isoconcentracion
    · Memoria de calculo auto-generada
    · Validacion meteorologica
```

## Tiempos estimados (corrida continua, 1 año)

| Cores | WRF | CALPUFF | Total |
|-------|-----|---------|-------|
| 64 threads (Hetzner Epyc 32C / AWS c5n) | 4-6 dias | 1 dia | **5-7 dias** |
| 48 threads (Hetzner Epyc 24C) | 6-8 dias | 1 dia | **7-9 dias** |
| 32 threads (Hetzner Xeon 16C) | 10-14 dias | 1 dia | **11-15 dias** |

## Parametrizaciones fisicas

Esquemas validados para el sur de Chile (Falvey & Garreaud 2009, Schmitz et al. 2021):

| Esquema | Opcion | Descripcion |
|---------|--------|-------------|
| Microphysics | WSM6 (6) | Hielo, nieve y graupel |
| Cumulus | Kain-Fritsch (1/0) | d01+d02, off en d03 |
| Capa limite | YSU (1) | Non-local closure |
| Capa superficial | Revised MM5 (1) | Monin-Obukhov |
| Suelo | Noah LSM (2) | 4 capas de suelo |
| Radiacion SW | Dudhia (1) | |
| Radiacion LW | RRTM (1) | |

## Archivos que entrega para el SEA

| Archivo | Exigencia SEA 2023 |
|---------|-------------------|
| `namelist.wps` + `namelist.input` | Obligatorio |
| `calmet.inp` + `calmet.dat` | Obligatorio |
| `calpuff.inp` + `conc.dat` | Obligatorio |
| Tablas concentracion vs normas | Necesario |
| Mapas de isoconcentracion | Necesario |
| Validacion WRF vs observaciones | Obligatorio |
| Memoria de calculo | Complementario |

## Estructura del repositorio

```
├── config.yaml              # Dominio, fechas, fisicas, normas
├── emisiones.csv            # Inventario de emisiones (tasas horarias)
├── receptores.csv           # Receptores discretos sensibles
├── docker/
│   ├── wrf/Dockerfile       # WRF 4.6 + WPS 4.6
│   └── calpuff/Dockerfile   # CALMET + CALPUFF + CALWRF
├── static/                  # Templates Jinja2 de namelists
│   ├── namelist.wps.j2
│   ├── namelist.input.j2
│   ├── calmet.inp.j2
│   └── calpuff.inp.j2
├── workflow/
│   ├── Snakefile            # Pipeline Snakemake
│   └── scripts/             # Python: ERA5, renderizado, validacion, SEIA
├── scripts/
│   ├── setup_server.sh      # Instalacion del servidor
│   ├── run.sh               # Lanzar modelacion
│   └── sync_results.sh      # Descargar resultados
├── data/                    # Datos generados (gitignored)
└── outputs/                 # Resultados (gitignored)
```

## Referencias

- SEA (2023). *Guia para el uso de modelos de calidad del aire en el SEIA*, v4.
- Falvey, M. & Garreaud, R.D. (2009). *Regional cooling in a warming world...* GRL.
- Schmitz, H. et al. (2021). *Modelacion de la dispersion de contaminantes...* CNE/MMA.

## Licencia

MIT. Los binarios de CALPUFF requieren licencia de TRC/Exponent (http://www.src.com/).
