#!/bin/bash
# =============================================================================
# run.sh — Lanza la modelacion completa WRF → CALPUFF
#
# Uso:
#   1. Edita config.yaml con tu dominio, fechas y emisiones
#   2. bash run.sh
#
# Este script:
#   - Valida la configuracion contra requisitos SEA
#   - Descarga ERA5 del periodo
#   - Renderiza namelists
#   - Lanza Snakemake (soporta tmux para desatendido)
#   - Monitorea el progreso
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKFLOW_DIR="$(dirname "$SCRIPT_DIR")"
cd "$WORKFLOW_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ── Verificar config ────────────────────────────────────────────────────────
if [ ! -f "config.yaml" ]; then
    log_error "config.yaml no encontrado. Copia y edita config.yaml primero."
    exit 1
fi

# ── Verificar que las imagenes Docker existen ──────────────────────────────
WRF_IMAGE="wrf-wps:4.6"
CALPUFF_IMAGE="calpuff:7"

for img in "$WRF_IMAGE" "$CALPUFF_IMAGE"; do
    if ! docker image inspect "$img" >/dev/null 2>&1; then
        log_error "Imagen $img no encontrada. Corre setup_server.sh primero."
        exit 1
    fi
done
log_info "Imagenes Docker verificadas"

# ── Verificar WPS_GEOG ──────────────────────────────────────────────────────
WPS_GEOG_DIR="/data/WPS_GEOG"
if [ ! -f "$WPS_GEOG_DIR/GEOGRID.TBL" ]; then
    log_error "WPS_GEOG no encontrado en $WPS_GEOG_DIR"
    log_error "Corre setup_server.sh primero para descargarlo."
    exit 1
fi
log_info "WPS_GEOG verificado"

# ── 1. Validar configuracion SEA ───────────────────────────────────────────
log_info "Paso 1/5: Validando configuracion (Guia SEA 2023)..."
python3 workflow/scripts/check_config.py config.yaml || {
    log_error "La configuracion no cumple requisitos minimos SEA."
    exit 1
}

# ── 2. Descargar ERA5 ─────────────────────────────────────────────────────
log_info "Paso 2/5: Descargando ERA5..."
echo ""
echo "  NOTA: La descarga de 1 año de ERA5 puede tomar 4-6 horas."
echo "  Asegurate de tener la variable CDSAPI_KEY configurada:"
echo "    export CDSAPI_KEY='uid:api-key'"
echo ""
read -p "  Continuar con la descarga? [S/n] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ss]$ ]] && [[ -n $REPLY ]]; then
    log_info "Omitiendo descarga. Si ERA5 ya fue descargado, continua."
fi

python3 workflow/scripts/download_era5.py config.yaml
log_info "ERA5 descargado"

# ── 3. Renderizar namelists ───────────────────────────────────────────────
log_info "Paso 3/5: Renderizando namelists..."
python3 workflow/scripts/render_namelist.py config.yaml
log_info "Namelists generados"

# ── 4. Lanzar Snakemake ──────────────────────────────────────────────────
log_info "Paso 4/5: Lanzando Snakemake..."

# Verificar si Snakemake esta instalado
if ! command -v snakemake &> /dev/null; then
    log_info "Instalando Snakemake..."
    pip3 install --user snakemake
fi

N_CORES=$(nproc)
log_info "Cores detectados: $N_CORES"
log_info "Cores a usar en WRF: $(python3 -c "import yaml; f=open('config.yaml'); c=yaml.safe_load(f); print(c['docker']['build']['nprocs'])")"

# ── Usar tmux para sesion desatendida ──────────────────────────────────────
SESSION_NAME="wrf-calpuff"

if command -v tmux &> /dev/null; then
    echo ""
    echo "  ┌───────────────────────────────────────────────────────┐"
    echo "  │  Snakemake se lanzara en tmux (sesion: $SESSION_NAME)    │"
    echo "  │                                                       │"
    echo "  │  Para monitorear:  tmux attach -t $SESSION_NAME         │"
    echo "  │  Para salir:       Ctrl+B, luego D                     │"
    echo "  │  Para ver log:     tail -f snakemake.log               │"
    echo "  └───────────────────────────────────────────────────────┘"
    echo ""

    read -p "  Lanzar ahora? [S/n] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]] && [[ -n $REPLY ]]; then
        log_info "Cancelado por el usuario."
        exit 0
    fi

    tmux new-session -d -s "$SESSION_NAME" \
        "snakemake --cores $N_CORES --keep-going --rerun-incomplete --latency-wait 60 2>&1 | tee snakemake.log"

    log_info "Snakemake lanzado en tmux sesion '$SESSION_NAME'"
    log_info "Progreso: tmux attach -t $SESSION_NAME"
    log_info "Log: tail -f snakemake.log"
    log_info ""
    log_info "Duracion estimada: ~20-25 dias (para 1 año, 3 dominios, 32 cores)"
    log_info "El workflow maneja checkpoints automaticamente."
    log_info "Si el servidor se cae, re-ejecuta run.sh para reanudar."
else
    log_info "tmux no disponible. Lanzando en foreground..."
    log_info "Tiempo estimado: ~20-25 dias. Usa Ctrl+Z + bg para background."
    snakemake --cores "$N_CORES" --keep-going --rerun-incomplete --latency-wait 60 2>&1 | tee snakemake.log
fi

# ── 5. Post-procesamiento ─────────────────────────────────────────────────
log_info "Paso 5/5: Verificando resultados..."

if snakemake --summary 2>/dev/null | grep -q "postprocesar_seia.*done"; then
    log_info "Pipeline completo."
    log_info ""
    log_info "  Outputs en: data/outputs/"
    log_info "  Para descargar a tu laptop: bash scripts/sync_results.sh"
else
    log_warn "Pipeline aun en ejecucion o con errores."
    log_warn "Revisa: snakemake --summary | grep -E '(FAIL|update)'"
fi
