#!/bin/bash
# Verifica que los binarios del lado SERVIDOR (CALWRF + CALMET) esten compilados.
# (CALPUFF/CALPOST corren en la Mac, no aqui.)

echo "=== Verificando binarios servidor (CALWRF + CALMET) ==="

BINARIES=( "calwrf.exe" "calmet.exe" )

missing=0
for bin in "${BINARIES[@]}"; do
    if command -v "$bin" >/dev/null 2>&1 || [ -f "/usr/local/bin/$bin" ]; then
        echo "  OK: $bin"
    else
        echo "  FALTA: $bin"
        missing=1
    fi
done

if [ "$missing" -eq 1 ]; then
    echo ""
    echo "ADVERTENCIA: faltan binarios. El Dockerfile los compila desde el fuente"
    echo "de calpuff.org; si la compilacion con gfortran fallo, revisa el log del"
    echo "build y el parche para gfortran (Enviroware / foro CALPUFF)."
    exit 1
fi

echo "Binarios del servidor presentes."
