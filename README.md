# WRF + CALWRF (servidor) — Meteorología para calidad del aire SEIA

Pipeline que corre **en un servidor** (AWS) y entrega el **`3D.DAT`** de CALWRF
(~4 GB): la meteorología lista para CALMET. CALWRF corre en el servidor para
reducir el `wrfout` (~40 GB) antes de transferir.

> **Alcance de este repo = solo servidor:** `ERA5 → WPS → WRF → CALWRF → 3D.DAT`.
> En la **PC** sigue (más liviano): `CALMET → CALPUFF → post-proceso SEIA`.
> Todo el lado servidor es **open-source** (WRF/WPS/CALWRF compilan desde fuente),
> no hay binarios propietarios.

Repo: https://github.com/Joaquinfnz/wrf-calpuff-workflow

---

## 1. Instalación en el servidor (una vez)

```bash
ssh -i tu-llave.pem ubuntu@<ip-del-servidor>
git clone https://github.com/Joaquinfnz/wrf-calpuff-workflow.git
cd wrf-calpuff-workflow
bash scripts/setup_server.sh        # Docker + WRF/WPS 4.6 + CALWRF + geog 30s (~1-2 h)
```

`setup_server.sh` compila las imágenes Docker (WRF/WPS desde fuente; CALWRF
desde el fuente FORTRAN de calpuff.org con gfortran), baja el geog 30s y
deshabilita el reinicio automático del SO (clave para corridas de varios días).

## 2. Configurar el proyecto

```bash
python3 workflow/scripts/importar_kmz.py proyecto.kmz --apply config.yaml
export CDSAPI_KEY='<tu-token>'      # crear en cds.climate.copernicus.eu/profile
```

Revisa fechas y físicas en `config.yaml`; ajusta `docker.build.nprocs` al número
de cores físicos del servidor.

## 3. Correr (desatendido, resiliente)

```bash
bash scripts/correWRF.sh
```

Lanza en `tmux` la cadena `ERA5 → WPS → WRF → CALWRF` hasta `data/calwrf/3d.dat`,
con **reintento auto-reanudable**: si un paso se cae, Snakemake reanuda desde el
checkpoint (WRF reinicia cada 6 h); si falla 3 veces seguidas rápido se detiene
para no gastar crédito.

```bash
tmux attach -t wrf     # monitorear (salir sin cortar: Ctrl+B, D)
tail -f correwrf.log
```

## 4. Bajar el 3D.DAT a la PC

```bash
bash scripts/sync_wrf.sh ubuntu@<ip> ~/wrf-calpuff-workflow tu-llave.pem
```

Trae `3d.dat` (~4 GB) + namelists + validación. En la PC: CALMET → CALPUFF → post.

---

## Estrategia de servidor (AWS con créditos)

Una sola instancia **On-Demand** que **redimensionas**: chica para configurar,
grande para correr (el disco EBS persiste el setup).

| Fase | Instancia | vCPU | Costo aprox |
|------|-----------|------|-------------|
| Configurar | `c6i.2xlarge` | 8 | ~$2 |
| Correr | `c6i.16xlarge` | 64 | según uso |

Flujo: lanzar `c6i.2xlarge` (Ubuntu 22.04, disco **300 GB gp3**) → setup →
**Stop → cambiar tipo a `c6i.16xlarge` → Start** → `correWRF.sh`.

> **Mide, no estimes:** corre 1 día simulado (~US$1-2) y cronometra. Para estos
> dominios (61×61×40, 3 anidados) WRF es rápido (~3-6 días en 64 vCPU).

## Parametrizaciones físicas

Validadas para el sur de Chile (Falvey & Garreaud 2009; Schmitz et al. 2021):
WSM6, Kain-Fritsch (d01/d02), YSU, Revised MM5, Noah LSM, Dudhia/RRTM.

## Estructura del repositorio

```
├── config.yaml              # Dominio, fechas, físicas (servidor)
├── docker/
│   ├── wrf/Dockerfile       # WRF 4.6 + WPS 4.6 (compila desde fuente)
│   └── calwrf/Dockerfile    # CALWRF 2.0.3 (compila desde fuente)
├── static/
│   ├── namelist.wps.j2 · namelist.input.j2
│   └── Vtable.ERA5          # tabla ungrib para ERA5 (pl+sfc)
├── workflow/
│   ├── Snakefile            # pipeline hasta 3d.dat
│   └── scripts/             # check_config, download_era5, render_namelist,
│                            #   importar_kmz, gen_calwrf_inp, validar_wrf
└── scripts/
    ├── setup_server.sh · correWRF.sh · sync_wrf.sh
```

## Licencia

MIT. WRF/WPS y CALWRF son open-source (se compilan desde fuente).
