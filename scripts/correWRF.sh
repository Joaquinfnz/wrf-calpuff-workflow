#!/bin/bash
# =============================================================================
# correWRF.sh — Lanza la cadena del servidor (ERA5 -> WPS -> WRF -> CALWRF -> 3D.DAT),
#               desatendido y resiliente para corridas de varios dias.
#
# CALWRF corre aqui para reducir el wrfout (~40 GB) a 3D.DAT (~4 GB).
# CALMET -> CALPUFF -> post corren en la PC sobre el 3D.DAT.
#
# Resiliencia ("lo lanzo una vez y no para hasta terminar"):
#   - tmux: sobrevive a desconexiones SSH / cierre del terminal.
#   - bucle de reintento: si un paso se cae, Snakemake reanuda desde el
#     ultimo checkpoint (--rerun-incomplete). WRF tiene restart cada 6h.
#   - corta-circuito: 3 fallos rapidos seguidos (<2 min) = error de config,
#     no transitorio -> aborta para no gastar credito de mas.
#
# Uso (en el servidor, dentro del repo):
#   export CDSAPI_KEY='<tu-token-CDS>'
#   bash scripts/correWRF.sh
#
# Monitoreo:  tmux attach -t wrf   |   tail -f correwrf.log
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WF="$(dirname "$SCRIPT_DIR")"
SELF="$SCRIPT_DIR/correWRF.sh"
cd "$WF"

G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; N='\033[0m'
info(){ echo -e "${G}[INFO]${N}  $1"; }
warn(){ echo -e "${Y}[WARN]${N}  $1"; }
err(){  echo -e "${R}[ERROR]${N} $1"; }

TARGET="data/calwrf/3d.dat"   # salida final del servidor (CALWRF: ~4 GB)
SESSION="wrf"

# ── Modo interno: bucle de reintento auto-reanudable (corre dentro de tmux) ──
if [ "${1:-}" = "__loop" ]; then
    CORES=$(nproc)
    fastfail=0
    while [ ! -f "$TARGET" ]; do
        snakemake --unlock >/dev/null 2>&1 || true   # limpiar lock de una caida previa
        t0=$SECONDS
        info "[$(date '+%F %T')] Iniciando/reanudando Snakemake (rule all -> 3D.DAT + validacion)"
        if snakemake --cores "$CORES" --keep-going --rerun-incomplete --latency-wait 120; then
            info "[$(date '+%F %T')] PIPELINE COMPLETO. 3D.DAT (~4 GB) listo en data/calwrf/."
            exit 0
        fi
        dur=$((SECONDS - t0))
        if [ "$dur" -lt 120 ]; then
            fastfail=$((fastfail + 1))
            warn "[$(date '+%F %T')] Fallo rapido (${dur}s) — $fastfail/3"
            if [ "$fastfail" -ge 3 ]; then
                err "3 fallos rapidos seguidos = error de config/setup (no transitorio)."
                err "Abortando para no gastar credito. Revisa correwrf.log y data/wrf/rsl.error.0000"
                exit 1
            fi
        else
            fastfail=0
            warn "[$(date '+%F %T')] Interrupcion tras ${dur}s. Reanudando en 60s desde el checkpoint..."
        fi
        sleep 60
    done
    info "[$(date '+%F %T')] $TARGET ya existe. Nada que hacer."
    exit 0
fi

# ── 1. Chequeos de setup ────────────────────────────────────────────────────
[ -f config.yaml ] || { err "Falta config.yaml en $WF"; exit 1; }
for img in "wrf-wps:4.6" "calpuff:7"; do
    docker image inspect "$img" >/dev/null 2>&1 || {
        err "Falta la imagen Docker '$img'. Corre primero: bash scripts/setup_server.sh"; exit 1; }
done
[ -f /data/WPS_GEOG/GEOGRID.TBL ] || {
    err "Falta WPS_GEOG en /data/WPS_GEOG. Corre primero: bash scripts/setup_server.sh"; exit 1; }
: "${CDSAPI_KEY:?Define CDSAPI_KEY (token CDS): export CDSAPI_KEY=...}"
command -v tmux >/dev/null 2>&1 || { err "tmux no esta instalado"; exit 1; }
command -v snakemake >/dev/null 2>&1 || { info "Instalando snakemake..."; pip3 install --user -q snakemake; }

CORES=$(nproc)
NP=$(python3 -c "import yaml;print(yaml.safe_load(open('config.yaml'))['docker']['build']['nprocs'])")
info "Cores disponibles: $CORES | WRF mpirun -np: $NP | objetivo: $TARGET"
[ "$NP" -gt "$CORES" ] && warn "nprocs ($NP) > cores ($CORES): ajusta docker.build.nprocs en config.yaml"

# ── 2. Validar config contra la Guia SEA (no fatal: permite benchmarks cortos) ──
python3 workflow/scripts/check_config.py config.yaml || warn "check_config con observaciones (revisa arriba)"

# ── 3. No duplicar si ya hay una corrida en curso ──────────────────────────
if tmux has-session -t "$SESSION" 2>/dev/null; then
    warn "Ya existe una sesion '$SESSION'. Adjunta con: tmux attach -t $SESSION"
    exit 0
fi

# ── 4. Lanzar el bucle resiliente dentro de tmux (sobrevive a la desconexion SSH) ──
tmux new-session -d -s "$SESSION" "bash '$SELF' __loop 2>&1 | tee -a correwrf.log"

info "Lanzado en tmux '$SESSION' (corre aunque cierres la sesion SSH)."
info "  Monitorear:  tmux attach -t $SESSION   (salir sin cortar: Ctrl+B luego D)"
info "  Log:         tail -f correwrf.log"
info "  Al terminar: data/calwrf/3d.dat (~4 GB) -> baja a la PC con scripts/sync_wrf.sh"
