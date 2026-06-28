# WRF → CALMET (servidor) — Modelación meteorológica para calidad del aire SEIA

Pipeline automatizado de modelación meteorológica que corre **en un servidor**
(AWS) y entrega `CALMET.DAT`, la meteorología 3D "lista" que alimenta a CALPUFF.

> **Alcance de este repo = solo servidor:** `ERA5 → WPS → WRF → CALWRF → CALMET`.
> La **dispersión CALPUFF + el post-proceso SEIA corren aparte, en la Mac** (no
> están en este repo). Alineado a la *Guía SEA para el uso de modelos de calidad
> del aire en el SEIA* (2ª ed.).

Repo: https://github.com/Joaquinfnz/wrf-calpuff-workflow

---

## 1. Instalación en el servidor (una vez)

```bash
ssh -i tu-llave.pem ubuntu@<ip-del-servidor>
git clone https://github.com/Joaquinfnz/wrf-calpuff-workflow.git
cd wrf-calpuff-workflow
bash scripts/setup_server.sh        # Docker + WRF/WPS 4.6 + CALMET/CALWRF + geog 30s (~1-2 h)
```

`setup_server.sh` instala Docker y dependencias, compila las imágenes Docker,
descarga el geog de alta resolución (30s) y deja el servidor listo. También
deshabilita el reinicio automático del SO (clave para corridas de varios días).

> **Binarios CALMET/CALWRF:** se **compilan automáticamente** desde el código
> fuente FORTRAN (gratuito, [calpuff.org](http://www.calpuff.org/)) durante el
> build de la imagen Docker, con gfortran. No requieren descarga manual.
> Si la compilación falla en tu gfortran, revisa el log del build (parche
> documentado en [Enviroware](https://www.enviroware.com/compiling-calmet-and-calpuff-models-under-os-x/)).

## 2. Configurar el proyecto

```bash
# Dominio desde el KMZ del proyecto (calcula el centroide y el área ERA5)
python3 workflow/scripts/importar_kmz.py proyecto.kmz --apply config.yaml

# Token del Climate Data Store (crear en cds.climate.copernicus.eu/profile)
export CDSAPI_KEY='<tu-token>'
```

Revisa fechas, dominios y físicas en `config.yaml`. Ajusta `docker.build.nprocs`
al número de cores físicos del servidor antes de la corrida.

## 3. Correr (desatendido, resiliente)

```bash
bash scripts/correWRF.sh
```

Lanza en `tmux` la cadena `ERA5 → WPS → WRF → CALWRF → CALMET` hasta
`data/calmet/calmet.dat`, con **reintento auto-reanudable**: si un paso se cae,
Snakemake retoma desde el checkpoint (WRF reinicia cada 6 h); si falla 3 veces
seguidas rápido (error de config) se detiene para no gastar de más.

```bash
tmux attach -t wrf     # monitorear (salir sin cortar: Ctrl+B, D)
tail -f correwrf.log   # log
```

## 4. Bajar el resultado a la Mac

```bash
# desde la Mac
bash scripts/sync_wrf.sh ubuntu@<ip> ~/wrf-calpuff-workflow tu-llave.pem
```

Trae `CALMET.DAT` (+ `wrfout` y namelists). De ahí en adelante, CALPUFF y el
post-proceso SEIA corren en la Mac.

---

## Estrategia de servidor (AWS con créditos)

Una sola instancia **On-Demand** que **redimensionas**: chica para configurar,
grande para correr (el disco EBS persiste el setup).

| Fase | Instancia | vCPU | Costo aprox |
|------|-----------|------|-------------|
| Configurar | `c6i.2xlarge` | 8 | ~$2 |
| Correr | `c6i.16xlarge` | 64 | Spot/On-Demand según uso |

Flujo: lanzar `c6i.2xlarge` (Ubuntu 22.04, disco **300 GB gp3**) → setup →
**Stop → cambiar tipo a `c6i.16xlarge` → Start** → `correWRF.sh`.
Alternativa: Hetzner Server Auction (~€15-20 por modelación).

> **Mide, no estimes:** corre 1 día simulado (~US$1-2) y cronometra para
> extrapolar el costo real del año. Para estos dominios (61×61×40, 3 anidados)
> WRF es rápido (~3-6 días en 64 vCPU).

## Parametrizaciones físicas

Validadas para el sur de Chile (Falvey & Garreaud 2009; Schmitz et al. 2021):

| Esquema | Opción | |
|---------|--------|--|
| Microphysics | WSM6 (6) | hielo/nieve/graupel |
| Cumulus | Kain-Fritsch (1/0) | d01+d02, off en d03 |
| Capa límite | YSU (1) | non-local |
| Capa superficial | Revised MM5 (1) | Monin-Obukhov |
| Suelo | Noah LSM (2) | 4 capas |
| Radiación | Dudhia (SW) / RRTM (LW) | |

## Lo que entrega el servidor para el SEA

`namelist.wps`, `namelist.input`, `calmet.inp`, **`CALMET.DAT`** y la
**validación meteorológica** WRF vs observaciones (exigencia SEA). Las tablas
de concentración vs norma, mapas y `conc.dat` los genera el lado Mac (CALPUFF).

## Estructura del repositorio

```
├── config.yaml              # Dominio, fechas, físicas (lado servidor)
├── docker/
│   ├── wrf/Dockerfile       # WRF 4.6 + WPS 4.6
│   └── calpuff/Dockerfile   # CALMET + CALWRF (binarios desde src.com)
├── static/
│   ├── namelist.wps.j2 · namelist.input.j2 · calmet.inp.j2
│   └── Vtable.ERA5          # tabla ungrib para ERA5 (pl+sfc)
├── workflow/
│   ├── Snakefile            # pipeline hasta calmet.dat
│   └── scripts/             # check_config, download_era5, render_namelist,
│                            #   importar_kmz, validar_wrf
└── scripts/
    ├── setup_server.sh      # instalación del servidor
    ├── correWRF.sh          # lanza la corrida (tmux, resiliente)
    └── sync_wrf.sh          # baja CALMET.DAT/wrfout a la Mac
```

## Referencias

- SEA. *Guía para el uso de modelos de calidad del aire en el SEIA*, 2ª ed.
- Falvey, M. & Garreaud, R.D. (2009). GRL.
- Schmitz, R. et al. (2021). Modelación de dispersión, sur de Chile.

## Licencia

MIT. Los binarios del sistema CALPUFF (CALMET/CALWRF) se obtienen de
[src.com](http://www.src.com/).
