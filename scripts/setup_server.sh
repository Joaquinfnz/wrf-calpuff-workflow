#!/bin/bash
# =============================================================================
# setup_server.sh — Instalacion completa en servidor (AWS / Hetzner / etc.)
#
# Uso:
#   1. Conectate via SSH al servidor
#   2. curl -O https://raw.github.com/.../setup_server.sh
#   3. bash setup_server.sh
#
# Este script:
#   - Instala Docker, git, Python
#   - Clona el repo
#   - Construye las imagenes Docker (WRF + CALPUFF)
#   - Descarga WPS_GEOG (datos estaticos de terreno)
#   - Descarga ERA5 si se requiere
#
# Tiempo estimado: 1.5 - 2 horas (principalmente compilando WRF)
# =============================================================================

set -euo pipefail

# ── Configuracion ───────────────────────────────────────────────────────────
GITHUB_REPO="${GITHUB_REPO:-https://github.com/Joaquinfnz/wrf-calpuff-workflow.git}"
GITHUB_BRANCH="${GITHUB_BRANCH:-main}"
DATA_DIR="${DATA_DIR:-/data/wrf-calpuff}"
WPS_GEOG_DIR="${WPS_GEOG_DIR:-/data/WPS_GEOG}"
WRF_IMAGE="wrf-wps:4.6"
CALPUFF_IMAGE="calpuff:7"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()  { echo -e "\n${CYAN}━━━ $1 ━━━${NC}\n"; }

# ── Verificar SO ────────────────────────────────────────────────────────────
log_step "Verificando sistema operativo"

if [ -f /etc/os-release ]; then
    . /etc/os-release
    log_info "OS: $NAME $VERSION_ID"
else
    log_error "No se pudo detectar el SO. Se requiere Ubuntu 22.04 o similar."
    exit 1
fi

# ── 1. Instalar dependencias ───────────────────────────────────────────────
log_step "Paso 1/7: Instalando dependencias del sistema"

sudo apt-get update -qq
sudo apt-get install -y \
    docker.io \
    docker-compose-v2 \
    git \
    wget \
    curl \
    python3 \
    python3-pip \
    python3-venv \
    tmux \
    htop \
    ncdu \
    unzip \
    build-essential \
    2>&1 | tail -5

log_info "Dependencias instaladas"

# ── 2. Configurar Docker ───────────────────────────────────────────────────
log_step "Paso 2/7: Configurando Docker"

sudo systemctl enable docker --now
sudo usermod -aG docker "$USER"
log_info "Docker configurado (re-login para usar sin sudo)"

# ── 3. Crear estructura de directorios ────────────────────────────────────
log_step "Paso 3/7: Creando directorios de datos"

sudo mkdir -p "$DATA_DIR" "$WPS_GEOG_DIR"
sudo mkdir -p "$DATA_DIR"/{raw,wps,wrf,calmet,calpuff,outputs}
sudo chown -R "$USER:$USER" "$DATA_DIR" "$WPS_GEOG_DIR"
log_info "Directorios creados en $DATA_DIR"

# ── 4. Clonar repositorio ─────────────────────────────────────────────────
log_step "Paso 4/7: Clonando workflow"

WORKFLOW_DIR="$HOME/wrf-calpuff-workflow"

if [ -d "$WORKFLOW_DIR" ]; then
    log_info "Repositorio ya existe, actualizando..."
    cd "$WORKFLOW_DIR"
    git pull origin "$GITHUB_BRANCH" 2>/dev/null || log_warn "No se pudo hacer pull (repo local?)"
else
    git clone --branch "$GITHUB_BRANCH" "$GITHUB_REPO" "$WORKFLOW_DIR" 2>/dev/null || {
        log_warn "No se pudo clonar de GitHub. Creando desde local..."
        log_warn "Asegurate de copiar el repo a $WORKFLOW_DIR antes de continuar."
        mkdir -p "$WORKFLOW_DIR"
    }
    log_info "Repositorio clonado"
fi

cd "$WORKFLOW_DIR"

# ── 5. Construir imagenes Docker ──────────────────────────────────────────
log_step "Paso 5/7: Construyendo imagen WRF + WPS (~50 min)"

log_info "Construyendo wrf-wps:4.6 ..."
docker build -t "$WRF_IMAGE" docker/wrf/ 2>&1 | tail -10
log_info "Imagen WRF construida: $WRF_IMAGE"

log_step "Paso 6/7: Construyendo imagen CALPUFF (~15 min)"

log_info "Construyendo $CALPUFF_IMAGE ..."
docker build -t "$CALPUFF_IMAGE" docker/calpuff/ 2>&1 | tail -10
log_info "Imagen CALPUFF construida: $CALPUFF_IMAGE"

# ── 6. Descargar WPS_GEOG ──────────────────────────────────────────────────
log_step "Paso 7/7: Descargando datos estaticos WPS_GEOG"

# Alta resolucion (30s) — obligatorio para 1 km en terreno complejo (precordillera andina)
WPS_GEOG_URL="https://www2.mmm.ucar.edu/wrf/src/wps_files/geog_high_res_mandatory.tar.gz"

if [ -f "$WPS_GEOG_DIR/GEOGRID.TBL" ]; then
    log_info "WPS_GEOG ya existe en $WPS_GEOG_DIR"
else
    log_info "Descargando WPS_GEOG alta resolucion 30s (~2.6 GB)..."
    cd /tmp
    wget -q --show-progress "$WPS_GEOG_URL" -O geog_highres.tar.gz || {
        log_warn "No se pudo descargar WPS_GEOG automaticamente."
        log_warn "Descargalo manualmente de: https://www2.mmm.ucar.edu/wrf/src/wps_files/"
        log_warn "(geog_high_res_mandatory.tar.gz) y extraelo en: $WPS_GEOG_DIR"
    }
    if [ -f geog_highres.tar.gz ]; then
        sudo tar -xzf geog_highres.tar.gz -C "$WPS_GEOG_DIR" --strip-components=1
        sudo chown -R "$USER:$USER" "$WPS_GEOG_DIR"
        rm geog_highres.tar.gz
        log_info "WPS_GEOG (30s) descargado y extraido"
    fi
    cd "$WORKFLOW_DIR"
fi

# ── 7. Instalar dependencias Python ────────────────────────────────────────
log_info "Instalando dependencias Python..."
python3 -m pip install --user --quiet \
    pyyaml \
    jinja2 \
    numpy \
    pandas \
    xarray \
    matplotlib \
    netCDF4 \
    cdsapi \
    cfgrib \
    openpyxl \
    2>&1 | tail -3

# ── Resumen ─────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║   SETUP COMPLETO — WRF/CALPUFF Workflow                      ║"
echo "║                                                              ║"
echo "║   Imagenes Docker:                                           ║"
echo "║     $WRF_IMAGE ($(docker image inspect $WRF_IMAGE --format='{{.Size}}' 2>/dev/null | awk '{printf "%.0f MB", $1/1024/1024}'))       ║"
echo "║     $CALPUFF_IMAGE ($(docker image inspect $CALPUFF_IMAGE --format='{{.Size}}' 2>/dev/null | awk '{printf "%.0f MB", $1/1024/1024}'))    ║"
echo "║                                                              ║"
echo "║   Siguiente paso:                                            ║"
echo "║     1. Edita config.yaml con tu dominio y fechas             ║"
echo "║     2. Coloca tus binarios CALPUFF en la imagen              ║"
echo "║     3. bash run.sh para lanzar la modelacion                 ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
