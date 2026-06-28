#!/bin/bash
# Verifica que CALWRF (unico binario del servidor) este compilado.
# CALMET/CALPUFF corren en la PC, no aqui.

echo "=== Verificando binario servidor (CALWRF) ==="

if command -v calwrf.exe >/dev/null 2>&1 || [ -f /usr/local/bin/calwrf.exe ]; then
    echo "  OK: calwrf.exe"
    echo "Binario del servidor presente."
else
    echo "  FALTA: calwrf.exe"
    echo ""
    echo "ADVERTENCIA: el Dockerfile compila CALWRF desde el fuente de calpuff.org;"
    echo "si la compilacion con gfortran fallo, revisa el log del build y el parche"
    echo "para gfortran/WRF 4.6 (foro CALPUFF / Enviroware)."
    exit 1
fi
