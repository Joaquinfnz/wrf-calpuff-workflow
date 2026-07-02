#!/bin/bash
# =============================================================================
# setup_server.sh — Instalacion completa en servidor (AWS / Hetzner / etc.)
#
# Uso:
#   1. Conectate via SSH al servidor (Ubuntu 22.04 / 24.04)
#   2. git clone https://github.com/Joaquinfnz/wrf-calpuff-workflow.git
#   3. bash wrf-calpuff-workflow/scripts/setup_server.sh
#
# Este script:
#   - Instala Docker, git, Python
#   - Clona el repo
#   - Construye las imagenes Docker (WRF/WPS + CALWRF)
#   - Descarga WPS_GEOG (datos estaticos de terreno, 30s)
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
CALWRF_IMAGE="calwrf:2.0.3"

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

# El grupo docker recien agregado NO aplica en esta misma sesion: los builds
# de abajo fallarian con "permission denied". Usar sudo si hace falta.
DOCKER="docker"
docker info >/dev/null 2>&1 || DOCKER="sudo docker"

# Evitar que el SO se reinicie por updates automaticos durante una corrida de varios dias
echo 'Unattended-Upgrade::Automatic-Reboot "false";' | sudo tee /etc/apt/apt.conf.d/99-no-auto-reboot >/dev/null
log_info "Reinicio automatico por updates deshabilitado (corridas largas seguras)"

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
$DOCKER build -t "$WRF_IMAGE" docker/wrf/ 2>&1 | tail -10
log_info "Imagen WRF construida: $WRF_IMAGE"

log_step "Paso 6/7: Construyendo imagen CALWRF (compila desde fuente, ~5 min)"

log_info "Construyendo $CALWRF_IMAGE ..."
$DOCKER build -t "$CALWRF_IMAGE" docker/calwrf/ 2>&1 | tail -10
log_info "Imagen CALWRF construida: $CALWRF_IMAGE"

# ── 6. Descargar WPS_GEOG ──────────────────────────────────────────────────
log_step "Paso 7/7: Descargando datos estaticos WPS_GEOG"

# Alta resolucion (30s) — obligatorio para 1 km en terreno complejo (precordillera andina)
WPS_GEOG_URL="https://www2.mmm.ucar.edu/wrf/src/wps_files/geog_high_res_mandatory.tar.gz"

# WPS_GEOG trae carpetas de terreno (topo_gmted2010_30s, landuse, etc.);
# GEOGRID.TBL es parte de WPS, no de estos datos — chequear carpeta no-vacia.
if [ -d "$WPS_GEOG_DIR" ] && [ -n "$(ls -A "$WPS_GEOG_DIR" 2>/dev/null)" ]; then
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
# Ubuntu 24.04: pip --user requiere --break-system-packages (PEP 668)
log_info "Instalando dependencias Python (requirements.txt)..."
PIP_FLAGS="--user --quiet"
python3 -m pip install $PIP_FLAGS pyyaml 2>/dev/null || PIP_FLAGS="$PIP_FLAGS --break-system-packages"
python3 -m pip install $PIP_FLAGS -r "$WORKFLOW_DIR/requirements.txt" 2>&1 | tail -3

# ── Resumen ─────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "   SETUP COMPLETO — Servidor WRF + CALWRF"
echo ""
echo "   Imagenes Docker:"
echo "     $WRF_IMAGE   ($(docker image inspect $WRF_IMAGE --format='{{.Size}}' 2>/dev/null | awk '{printf "%.0f MB", $1/1024/1024}'))"
echo "     $CALWRF_IMAGE ($(docker image inspect $CALWRF_IMAGE --format='{{.Size}}' 2>/dev/null | awk '{printf "%.0f MB", $1/1024/1024}'))"
echo ""
echo "   Siguiente paso:"
echo "     1. python3 workflow/scripts/importar_kmz.py proyecto.kmz --apply config.yaml"
echo "     2. export CDSAPI_KEY=...   (token del CDS)"
echo "     3. bash scripts/correWRF.sh   (corre hasta 3D.DAT, en tmux)"
echo ""
