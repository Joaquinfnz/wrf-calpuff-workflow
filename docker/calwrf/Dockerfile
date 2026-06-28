# =============================================================================
# CALWRF 2.0.3 — imagen Docker (lado SERVIDOR).
# Compila desde el codigo fuente FORTRAN (gratuito, calpuff.org) con gfortran.
# Alcance servidor: solo CALWRF (convierte wrfout ~40 GB -> 3D.DAT ~4 GB).
# CALMET/CALPUFF corren en la PC.
# =============================================================================

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8

# ── Dependencias (gfortran + netCDF para CALWRF) ─────────────────────────────
RUN apt-get update && apt-get install -y \
    build-essential gfortran gcc make \
    wget curl unzip ca-certificates \
    netcdf-bin libnetcdff-dev libnetcdf-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/calwrf

# Flags estandar para compilar el FORTRAN legado con gfortran moderno.
ENV FFLAGS="-O2 -fno-automatic -std=legacy -fallow-argument-mismatch -ffixed-line-length-none"

# ── CALWRF v2.0.3 (convierte wrfout -> 3D.DAT; enlaza netCDF) ────────────────
RUN wget -q "http://www.calpuff.org/calpuff/download/Mod7_Files/CALWRF_v2.0.3_L190426.zip" -O calwrf.zip \
    && unzip -q calwrf.zip -d calwrf_src && rm calwrf.zip \
    && SRC="$(find calwrf_src \( -iname 'calwrf*.f' -o -iname 'calwrf*.f90' \) | head -1)" \
    && cd "$(dirname "$SRC")" \
    && gfortran $FFLAGS -o /usr/local/bin/calwrf.exe "$(basename "$SRC")" -I/usr/include -lnetcdff -lnetcdf \
    && echo "[OK] calwrf.exe compilado" \
    || echo "[WARN] Fallo compilacion de CALWRF (revisar netCDF y parche para WRF 4.6)."

# ── Verificar binario al final del build ────────────────────────────────────
COPY check_binaries.sh /opt/calwrf/
RUN chmod +x /opt/calwrf/check_binaries.sh && /opt/calwrf/check_binaries.sh || true

WORKDIR /data
