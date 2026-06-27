#!/bin/bash
# =============================================================================
# correWRF.sh — Lanza la cadena meteorologica en AWS hasta CALMET.DAT, desatendido.
#
# Arquitectura: ERA5 -> WPS -> WRF -> CALWRF -> CALMET corren en AWS.
# CALPUFF (dispersion) + post corren en la Mac sobre CALMET.DAT.
# "Lo lanzo y listo": chequea el setup, valida la config y corre Snakemake en tmux.
#
# Uso (en el servidor, dentro del repo):
#   export CDSAPI_KEY='<tu-token-CDS>'
#   bash scripts/correWRF.sh
#
# Monitoreo:  tmux attach -t wrf   |   tail -f correwrf.log
# Al terminar: data/calmet/calmet.dat -> bajar a la Mac con scripts/sync_wrf.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WF="$(dirname "$SCRIPT_DIR")"
cd "$WF"

G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; N='\033[0m'
info(){ echo -e "${G}[INFO]${N}  $1"; }
warn(){ echo -e "${Y}[WARN]${N}  $1"; }
err(){  echo -e "${R}[ERROR]${N} $1"; }

TARGET="data/calmet/calmet.dat"   # meteorologia "lista para CALPUFF"
SESSION="wrf"

# ── 1. Chequeos de setup ────────────────────────────────────────────────────
[ -f config.yaml ] || { err "Falta config.yaml en $WF"; exit 1; }
for img in "wrf-wps:4.6" "calpuff:7"; do
    docker image inspect "$img" >/dev/null 2>&1 || {
        err "Falta la imagen Docker '$img'. Corre primero: bash scripts/setup_server.sh"; exit 1; }
done
[ -f /data/WPS_GEOG/GEOGRID.TBL ] || {
    err "Falta WPS_GEOG en /data/WPS_GEOG. Corre primero: bash scripts/setup_server.sh"; exit 1; }
: "${CDSAPI_KEY:?Define CDSAPI_KEY (token CDS) antes de correr: export CDSAPI_KEY=...}"
command -v tmux >/dev/null 2>&1 || { err "tmux no esta instalado"; exit 1; }
command -v snakemake >/dev/null 2>&1 || { info "Instalando snakemake..."; pip3 install --user -q snakemake; }

CORES=$(nproc)
NP=$(python3 -c "import yaml;print(yaml.safe_load(open('config.yaml'))['docker']['build']['nprocs'])")
info "Cores disponibles: $CORES | WRF mpirun -np: $NP | objetivo: $TARGET"
[ "$NP" -gt "$CORES" ] && warn "nprocs ($NP) > cores ($CORES): ajusta docker.build.nprocs en config.yaml"

# ── 2. Validar config contra la Guia SEA (no fatal: un benchmark corto debe poder correr) ──
python3 workflow/scripts/check_config.py config.yaml || warn "check_config con observaciones (revisa arriba)"

# ── 3. No duplicar si ya hay una corrida en curso ──────────────────────────
if tmux has-session -t "$SESSION" 2>/dev/null; then
    warn "Ya existe una sesion '$SESSION'. Adjunta con: tmux attach -t $SESSION"
    exit 0
fi

# ── 4. Lanzar desatendido (resumible ante caidas/checkpoints) ──────────────
tmux new-session -d -s "$SESSION" \
    "snakemake --cores $CORES --keep-going --rerun-incomplete --latency-wait 60 $TARGET 2>&1 | tee correwrf.log"

info "Lanzado en tmux '$SESSION'."
info "  Monitorear:  tmux attach -t $SESSION   (salir sin cortar: Ctrl+B luego D)"
info "  Log:         tail -f correwrf.log"
info "  Al terminar: data/calmet/calmet.dat listo -> bajar a la Mac con scripts/sync_wrf.sh"
