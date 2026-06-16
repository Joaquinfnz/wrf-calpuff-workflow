# WRF → CALPUFF Workflow — Modelacion de Calidad del Aire

Pipeline reproducible de modelacion meteorologica (WRF) y dispersion de
contaminantes (CALPUFF), alineado a la **Guia SEA 2023** para el uso de
modelos de calidad del aire en el SEIA (v4, Feb 2023).

## Requisitos

- Servidor con **≥ 32 cores, ≥ 128 GB RAM, ≥ 1 TB disco** (Hetzner Auction, AWS EC2 c5n.18xlarge, etc.)
- Ubuntu 22.04 LTS
- Docker + Docker Compose
- API key de CDS (Copernicus) para ERA5
- Binarios de CALPUFF (licencia TRC/Exponent)

## Instalacion rapida

```bash
# 1. Conectate al servidor
ssh user@server

# 2. Ejecuta el script de setup (1 sola vez, ~1.5-2h)
curl -O https://raw.githubusercontent.com/Joaquinfnz/wrf-calpuff-workflow/main/scripts/setup_server.sh
bash setup_server.sh

# 3. Edita config.yaml con tu dominio, fechas y emisiones
nano config.yaml

# 4. Lanza la modelacion
export CDSAPI_KEY='tu-uid:tu-api-key'
bash scripts/run.sh
```

## Pipeline

```
ERA5 download (CDS API)
    │
    ▼
WPS: geogrid → ungrib → metgrid
    │
    ▼
WRF: real → wrf (12 segmentos mensuales, spin-up 24h c/u)
    │                       checkpoint wrfrst cada 6h
    ▼
CALWRF: convierte wrfout → inputs CALMET
    │
    ▼
CALMET: campos 3D diagnosticos
    │
    ▼
CALPUFF: dispersion año completo
    │
    ▼
Post-procesamiento SEIA:
  · 5 grillas de receptores
  · Tablas concentracion vs normas (DS 38/2011)
  · Mapas de isoconcentracion
  · Memoria de calculo auto-generada
  · Validacion WRF vs observaciones
```

## Parametrizaciones fisicas WRF

| Esquema | Opcion | Descripcion |
|---------|--------|-------------|
| mp_physics | 6 | WSM6 microphysics |
| cu_physics | 1/0 | Kain-Fritsch (d01,d02), off d03 |
| bl_pbl_physics | 1 | YSU boundary layer |
| sf_sfclay_physics | 1 | Revised MM5 surface layer |
| sf_surface_physics | 2 | Noah LSM |
| ra_sw_physics | 1 | Dudhia shortwave |
| ra_lw_physics | 1 | RRTM longwave |

Validado para el sur de Chile (Falvey & Garreaud 2009, Schmitz et al. 2021).

## Estructura

```
├── config.yaml              # Configuracion del proyecto
├── emisiones.csv            # Inventario de emisiones (tasas horarias)
├── receptores.csv           # Receptores discretos sensibles
├── docker/
│   ├── wrf/                 # Dockerfile WRF 4.6 + WPS 4.6
│   └── calpuff/             # Dockerfile CALMET + CALPUFF + CALWRF
├── static/
│   ├── namelist.wps.j2      # Templates Jinja2
│   ├── namelist.input.j2
│   ├── calmet.inp.j2
│   └── calpuff.inp.j2
├── workflow/
│   ├── Snakefile            # Pipeline Snakemake
│   └── scripts/             # Python scripts
├── scripts/
│   ├── setup_server.sh      # Instalacion del servidor
│   ├── run.sh               # Lanzar modelacion
│   └── sync_results.sh      # Descargar resultados
├── data/                    # Datos generados (ignorados por git)
└── outputs/                 # Resultados finales
```

## Archivos para la evaluacion SEA

Al terminar la modelacion, el workflow empaqueta automaticamente:

| Archivo | Requisito SEA |
|---------|--------------|
| `namelist.wps` | Obligatorio |
| `namelist.input` | Obligatorio |
| `calmet.inp` + `calmet.dat` | Obligatorio |
| `calpuff.inp` + `conc.dat` | Obligatorio |
| Tablas de concentracion vs normas | Necesario |
| Mapas de isoconcentracion | Necesario |
| Memoria de calculo | Bueno entregar |
| Validacion meteorologica | Obligatorio |

## Referencias

- SEA (2023). *Guia para el uso de modelos de calidad del aire en el SEIA*, v4.
- Falvey, M. & Garreaud, R.D. (2009). *Regional cooling in a warming world...* GRL.
- Schmitz, H. et al. (2021). *Modelacion de la dispersion de contaminantes...* CNE/MMA.

## Licencia

MIT — El workflow es open source. Los binarios de CALPUFF requieren licencia
de TRC/Exponent (http://www.src.com/).
