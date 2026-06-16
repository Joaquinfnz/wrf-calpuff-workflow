#!/bin/bash
# Verifica que los binarios de CALPUFF esten presentes
set -e

echo "=== Verificando binarios CALPUFF ==="

BINARIES=(
    "calmet_v6.5/calmet.exe"
    "calpuff_v7.x/calpuff.exe"
    "calwrf_v2.x/calwrf.exe"
    "calpost_v6.x/calpost.exe"
)

missing=0
for bin in "${BINARIES[@]}"; do
    if [ -f "/opt/calpuff/binarios/$bin" ]; then
        echo "  OK: $bin"
    else
        echo "  FALTA: $bin"
        missing=1
    fi
done

if [ $missing -eq 1 ]; then
    echo ""
    echo "ADVERTENCIA: Faltan binarios de CALPUFF."
    echo "Los binarios de CALPUFF son software propietario de TRC/Exponent."
    echo "Debes obtenerlos de http://www.src.com/ y colocarlos en:"
    echo "  binarios/"
    exit 1
fi

echo "Todos los binarios presentes."
