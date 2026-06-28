# =============================================================================
# CALMET 6.5 + CALWRF 2.0.3 — imagen Docker (lado SERVIDOR).
# Compila desde el codigo fuente FORTRAN (gratuito, calpuff.org) con gfortran.
# Alcance servidor: solo CALWRF + CALMET (la dispersion CALPUFF corre en la Mac).
# =============================================================================

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8

# ── Dependencias (gfortran + netCDF para CALWRF) ─────────────────────────────
RUN apt-get update && apt-get install -y \
    build-essential gfortran gcc make \
    wget curl unzip ca-certificates \
    python3 python3-pip \
    netcdf-bin libnetcdff-dev libnetcdf-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/calpuff

# Flags estandar para compilar el FORTRAN legado de CALPUFF con gfortran moderno.
# -fno-automatic ~ SAVE implicito (evita segfaults clasicos del codigo legado).
ENV FFLAGS="-O2 -fno-automatic -std=legacy -fallow-argument-mismatch -ffixed-line-length-none"

# ── CALMET v6.5.0 (modelo meteorologico diagnostico) ────────────────────────
RUN wget -q "http://www.calpuff.org/calpuff/download/Mod7_Files/CALMET_v6.5.0_L150223.zip" -O calmet.zip \
    && unzip -q calmet.zip -d calmet_src && rm calmet.zip \
    && SRC="$(find calmet_src -iname 'calmet.for' | head -1)" \
    && cd "$(dirname "$SRC")" \
    && gfortran $FFLAGS -o /usr/local/bin/calmet.exe calmet.for \
    && echo "[OK] calmet.exe compilado" \
    || echo "[WARN] Fallo compilacion de CALMET con gfortran. Ver: https://www.enviroware.com/compiling-calmet-and-calpuff-models-under-os-x/"

# ── CALWRF v2.0.3 (convierte wrfout -> input CALMET; enlaza netCDF) ──────────
RUN wget -q "http://www.calpuff.org/calpuff/download/Mod7_Files/CALWRF_v2.0.3_L190426.zip" -O calwrf.zip \
    && unzip -q calwrf.zip -d calwrf_src && rm calwrf.zip \
    && SRC="$(find calwrf_src \( -iname 'calwrf*.f' -o -iname 'calwrf*.f90' \) | head -1)" \
    && cd "$(dirname "$SRC")" \
    && gfortran $FFLAGS -o /usr/local/bin/calwrf.exe "$(basename "$SRC")" -I/usr/include -lnetcdff -lnetcdf \
    && echo "[OK] calwrf.exe compilado" \
    || echo "[WARN] Fallo compilacion de CALWRF (revisar netCDF y parche para WRF 4.6)."

# ── Verificar binarios al final del build ───────────────────────────────────
COPY check_binaries.sh /opt/calpuff/
RUN chmod +x /opt/calpuff/check_binaries.sh && /opt/calpuff/check_binaries.sh || true

WORKDIR /data
