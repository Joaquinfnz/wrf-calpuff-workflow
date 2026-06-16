# =============================================================================
# CALMET 6.5 + CALPUFF 7 + CALWRF — Docker image
# Basado en Ubuntu 22.04, gfortran
# =============================================================================

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8

# ── Dependencias ─────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    build-essential \
    gfortran \
    gcc \
    make \
    wget \
    curl \
    unzip \
    git \
    ca-certificates \
    vim \
    nano \
    python3 \
    python3-pip \
    netcdf-bin \
    libnetcdff-dev \
    libnetcdf-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Instalar dependencias Python ─────────────────────────────────────────────
RUN pip3 install --no-cache-dir numpy pandas xarray netCDF4 matplotlib

# ── Directorio de modelos ───────────────────────────────────────────────────
WORKDIR /opt/calpuff

# ── NOTA: Los binarios de CALPUFF/CALMET/CALWRF/CALPOST son propietarios ──
# ── y se distribuyen bajo licencia de TRC/Exponent.                         ──
# ── Debes obtenerlos de: http://www.src.com/                                 ──
# ── Coloca los binarios compilados en: ./binarios/                           ──
# ──                                                                          ──
# ── Estructura esperada:                                                     ──
# ──   binarios/                                                              ──
# ──     calmet_v6.5/                                                         ──
# ──       calmet.exe                                                         ──
# ──     calpuff_v7.x/                                                        ──
# ──       calpuff.exe                                                        ──
# ──     calwrf_v2.x/                                                         ──
# ──       calwrf.exe                                                         ──
# ──     calpost_v6.x/                                                        ──
# ──       calpost.exe                                                        ──
# ──                                                                          ──
# ── Para development/testing público, este Dockerfile compila versiones      ──
# ── de los utilitarios de la EPA que son open source.                        ──

RUN mkdir -p /opt/calpuff/binarios /opt/calpuff/inputs /opt/calpuff/outputs

# ── Compilar utilitarios open-source de EPA ──────────────────────────────────
# Scimere2 (pre/post processor, parte de la suite CALPUFF)
WORKDIR /opt/calpuff
RUN wget -q https://gaftp.epa.gov/Air/aqmg/SCRAM/models/other/calpuff/CALPUFF_v7.2.1_L150618.zip -O calpuff_pkg.zip \
    && unzip -q calpuff_pkg.zip -d calpuff_src \
    && rm calpuff_pkg.zip \
    || echo "EPA source not available. Place licensed binaries in ./binarios/"

# ── Verificar binarios ──────────────────────────────────────────────────────
COPY check_binaries.sh /opt/calpuff/
RUN chmod +x /opt/calpuff/check_binaries.sh

# ── Entrypoint ───────────────────────────────────────────────────────────────
WORKDIR /data
ENV PATH="/opt/calpuff/binarios/calmet_v6.5:/opt/calpuff/binarios/calpuff_v7.x:/opt/calpuff/binarios/calwrf_v2.x:/opt/calpuff/binarios/calpost_v6.x:${PATH}"
