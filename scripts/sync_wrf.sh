#!/bin/bash
# =============================================================================
# sync_wrf.sh — Baja los wrfout del servidor AWS a la Mac (flujo WRF-en-AWS).
#
# Arquitectura: WRF corre en AWS; CALMET/CALPUFF/post se hacen en la Mac M1.
# Este script trae solo los wrfout* (lo que la Mac necesita para CALWRF->CALMET).
#
# Uso (desde la Mac):
#   bash sync_wrf.sh ubuntu@<IP> [/ruta/workflow] [llave.pem]
#
# Ejemplo:
#   bash sync_wrf.sh ubuntu@1.2.3.4 ~/wrf-calpuff-workflow ~/keys/mi_aws.pem
# =============================================================================
set -euo pipefail

SERVER="${1:-}"
REMOTE_DIR="${2:-/home/ubuntu/wrf-calpuff-workflow}"
PEM="${3:-}"

if [ -z "$SERVER" ]; then
    echo "Uso: bash sync_wrf.sh user@server [/ruta/workflow] [llave.pem]"
    exit 1
fi

SSH_OPT=""
[ -n "$PEM" ] && SSH_OPT="-e \"ssh -i $PEM\""

LOCAL_DIR="./wrfout_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOCAL_DIR"
echo "[INFO] Bajando wrfout desde $SERVER:$REMOTE_DIR/data/wrf/  ->  $LOCAL_DIR/"

# rsync con reanudacion; los wrfout son grandes (decenas de GB)
if [ -n "$PEM" ]; then
    rsync -avz --partial --progress -e "ssh -i $PEM" \
        "$SERVER:$REMOTE_DIR/data/wrf/wrfout_d0*" "$LOCAL_DIR/"
else
    rsync -avz --partial --progress \
        "$SERVER:$REMOTE_DIR/data/wrf/wrfout_d0*" "$LOCAL_DIR/"
fi

# namelists usados (para el expediente SEA)
SCP="scp"; [ -n "$PEM" ] && SCP="scp -i $PEM"
$SCP "$SERVER:$REMOTE_DIR/data/wrf/namelist.input" "$LOCAL_DIR/" 2>/dev/null || true
$SCP "$SERVER:$REMOTE_DIR/data/wps/namelist.wps"  "$LOCAL_DIR/" 2>/dev/null || true

echo "[OK] wrfout descargados en $LOCAL_DIR"
echo "     Siguiente: CALWRF -> CALMET -> CALPUFF en la Mac (Docker x86 emulado)."
