#!/bin/bash
# =============================================================================
# sync_results.sh — Descarga resultados del servidor a tu laptop
#
# Uso (desde tu laptop):
#   bash sync_results.sh user@server_ip /ruta/proyecto
#
# Descarga:
#   - Tablas SEIA (XLSX/CSV)
#   - Mapas de isoconcentracion (PNG)
#   - Memoria de calculo (MD)
#   - Namelists usados
#   - Archivos CALPUFF obligatorios (para entregar al SEA)
# =============================================================================

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ── Parsear argumentos ──────────────────────────────────────────────────────
SERVER="${1:-}"
WORKFLOW_DIR="${2:-/home/ubuntu/wrf-calpuff-workflow}"

if [ -z "$SERVER" ]; then
    echo "Uso: bash sync_results.sh user@server_ip [/ruta/workflow]"
    echo ""
    echo "Ejemplos:"
    echo "  bash sync_results.sh ubuntu@52.15.146.167"
    echo "  bash sync_results.sh root@hetzner-1234 /root/wrf-calpuff-workflow"
    exit 1
fi

# ── Directorio local de destino ────────────────────────────────────────────
LOCAL_DIR="./resultados_modelacion_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOCAL_DIR"

log_info "Descargando resultados desde $SERVER:$WORKFLOW_DIR"
log_info "Destino local: $LOCAL_DIR"

# ── Descargar outputs ──────────────────────────────────────────────────────
log_info "Descargando tablas y mapas..."

rsync -avz --progress \
    "$SERVER:$WORKFLOW_DIR/data/outputs/" \
    "$LOCAL_DIR/outputs/" \
    2>/dev/null || {
    log_info "rsync fallo, intentando scp..."
    scp -r "$SERVER:$WORKFLOW_DIR/data/outputs/" "$LOCAL_DIR/outputs/" 2>/dev/null || \
        log_error "No se pudo descargar outputs/"
}

log_info "Descargando namelists..."

scp "$SERVER:$WORKFLOW_DIR/data/wps/namelist.wps" "$LOCAL_DIR/" 2>/dev/null || log_error "namelist.wps no encontrado"
scp "$SERVER:$WORKFLOW_DIR/data/wrf/namelist.input" "$LOCAL_DIR/" 2>/dev/null || log_error "namelist.input no encontrado"
scp "$SERVER:$WORKFLOW_DIR/data/calmet/calmet.inp" "$LOCAL_DIR/" 2>/dev/null || log_error "calmet.inp no encontrado"
scp "$SERVER:$WORKFLOW_DIR/data/calpuff/calpuff.inp" "$LOCAL_DIR/" 2>/dev/null || log_error "calpuff.inp no encontrado"

# ── Descargar archivos CALPUFF obligatorios SEA ────────────────────────────
log_info "Descargando archivos CALPUFF requeridos por SEA..."

mkdir -p "$LOCAL_DIR/calpuff"
scp "$SERVER:$WORKFLOW_DIR/data/calmet/calmet.dat" "$LOCAL_DIR/calpuff/" 2>/dev/null || log_error "calmet.dat no encontrado"
scp "$SERVER:$WORKFLOW_DIR/data/calpuff/conc.dat" "$LOCAL_DIR/calpuff/" 2>/dev/null || log_error "conc.dat no encontrado"
scp "$SERVER:$WORKFLOW_DIR/data/calmet/calmet.log" "$LOCAL_DIR/calpuff/" 2>/dev/null || true
scp "$SERVER:$WORKFLOW_DIR/data/calpuff/calpuff.log" "$LOCAL_DIR/calpuff/" 2>/dev/null || true

# ── Descargar validacion ───────────────────────────────────────────────────
log_info "Descargando validacion meteorologica..."

mkdir -p "$LOCAL_DIR/validacion"
scp -r "$SERVER:$WORKFLOW_DIR/data/outputs/*/validacion/" "$LOCAL_DIR/validacion/" 2>/dev/null || \
    log_error "Datos de validacion no encontrados"

# ── Resumen ─────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║   RESULTADOS DESCARGADOS                                     ║"
echo "║                                                              ║"
echo "║   $LOCAL_DIR/"
echo "║   ├── outputs/         Tablas XLSX + Mapas PNG               ║"
echo "║   ├── calpuff/         Archivos CALPUFF para SEA             ║"
echo "║   ├── validacion/      Metricas y graficos                   ║"
echo "║   ├── namelist.wps     Configuracion WPS                     ║"
echo "║   ├── namelist.input   Configuracion WRF                     ║"
echo "║   ├── calmet.inp       Configuracion CALMET                  ║"
echo "║   └── calpuff.inp      Configuracion CALPUFF                 ║"
echo "║                                                              ║"
echo "║   Para la evaluacion SEA, entrega:                           ║"
echo "║   ✓ namelist.wps + namelist.input                            ║"
echo "║   ✓ calmet.inp + calmet.dat                                  ║"
echo "║   ✓ calpuff.inp + conc.dat                                   ║"
echo "║   ✓ Tablas de concentracion vs normas                        ║"
echo "║   ✓ Mapas de isoconcentracion                                ║"
echo "║   ✓ Memoria de calculo                                       ║"
echo "║   ✓ Validacion meteorologica                                 ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

log_info "Descarga completa: $LOCAL_DIR"
