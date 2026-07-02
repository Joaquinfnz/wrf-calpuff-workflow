# =============================================================================
# WRF 4.6 + WPS 4.6 — Docker image
# Basado en Ubuntu 22.04 LTS, gfortran 11, OpenMPI, NetCDF, HDF5, Jasper
# =============================================================================

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# ── Dependencias del sistema ─────────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    build-essential \
    gfortran \
    gcc \
    g++ \
    cpp \
    m4 \
    make \
    cmake \
    libtool \
    automake \
    autoconf \
    pkg-config \
    wget \
    curl \
    git \
    ca-certificates \
    unzip \
    bzip2 \
    tar \
    tcsh \
    ksh \
    time \
    file \
    vim \
    nano \
    netcdf-bin \
    libnetcdff-dev \
    libnetcdf-dev \
    libhdf5-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    libz-dev \
    liblapack-dev \
    libblas-dev \
    libpng-dev \
    libjpeg-dev \
    zlib1g-dev \
    openmpi-bin \
    libopenmpi-dev \
    openssh-client \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# ── Compilar Jasper 1.900.1 desde fuente (ya no está en Ubuntu 22.04) ────────
# WPS/ungrib lo necesita para decodificar GRIB2 (JPEG2000). CFLAGS=-fcommon
# para que compile con gcc 11.
WORKDIR /tmp/jasper
RUN wget -q https://www2.mmm.ucar.edu/wrf/OnLineTutorial/compile_tutorial/tar_files/jasper-1.900.1.tar.gz \
    && tar xzf jasper-1.900.1.tar.gz \
    && cd jasper-1.900.1 \
    && CFLAGS="-fcommon" ./configure --prefix=/opt/jasper \
    && make -j$(nproc) \
    && make install \
    && cd / && rm -rf /tmp/jasper

# ── Compilar NetCDF (necesario para WRF) ─────────────────────────────────────
WORKDIR /tmp/libs

ENV DIR=/opt/netcdf
ENV CC=gcc CXX=g++ FC=gfortran F77=gfortran F90=gfortran
ENV CPPFLAGS="-I${DIR}/include" LDFLAGS="-L${DIR}/lib"
ENV LD_LIBRARY_PATH="${DIR}/lib:${LD_LIBRARY_PATH}"

# NetCDF: usar el de los paquetes apt (netcdf-bin, libnetcdf-dev, libnetcdff-dev)
# enlazado a ${DIR}, porque WRF espera headers/libs bajo $NETCDF/{include,lib}.
# (Compilar desde fuente fallaba en silencio: el pipe a `tee` ocultaba el exit
# code de make/make install, dejando /opt/netcdf vacio.)
RUN mkdir -p ${DIR}/include ${DIR}/lib \
    && for f in /usr/include/netcdf*; do ln -sf "$f" ${DIR}/include/; done \
    && for f in /usr/lib/x86_64-linux-gnu/libnetcdf*; do ln -sf "$f" ${DIR}/lib/; done \
    && test -f ${DIR}/include/netcdf.inc && test -f ${DIR}/lib/libnetcdff.so

# ── Variables de entorno WRF ─────────────────────────────────────────────────
ENV NETCDF=${DIR}
ENV WRF_DIR=/opt/wrf
ENV WRFIO_NCD_LARGE_FILE_SUPPORT=1
ENV WRF_EM_CORE=1
ENV WRF_NMM_CORE=0
ENV WRF_CHEM=0
ENV WRF_KPP=0
ENV JASPERLIB=/opt/jasper/lib
ENV JASPERINC=/opt/jasper/include
ENV LD_LIBRARY_PATH="/opt/jasper/lib:${LD_LIBRARY_PATH}"
ENV HDF5=/usr/lib/x86_64-linux-gnu/hdf5/serial

# ── Compilar WRF 4.6.0 ──────────────────────────────────────────────────────
WORKDIR /opt
# WRF se clona con submodulos (NoahMP es un git submodule; el tarball de GitHub
# NO lo incluye y el compile falla con "NoahMP submodule files not populating").
RUN git clone --depth 1 --recurse-submodules --shallow-submodules --branch v4.6.0 https://github.com/wrf-model/WRF.git wrf \
    && cd wrf \
    && cp share/landread.c.dist share/landread.c \
    && echo "35" | ./configure \
    && ./compile -j $(nproc) em_real 2>&1 | tee compile.log \
    && test -f main/wrf.exe && test -f main/real.exe

# ── Compilar WPS 4.6.0 ──────────────────────────────────────────────────────
WORKDIR /opt
RUN wget -q https://github.com/wrf-model/WPS/archive/refs/tags/v4.6.0.tar.gz -O wps.tar.gz \
    && tar xzf wps.tar.gz \
    && mv WPS-4.6.0 wps \
    && cd wps \
    && echo "3" | ./configure \
    && sed -i '/^LDFLAGS/ s|=.*|= -fopenmp|' configure.wps \
    && ./compile 2>&1 | tee compile.log \
    && test -f geogrid.exe && test -f ungrib.exe && test -f metgrid.exe \
    && rm -f ../wps.tar.gz

# ── Limpiar ──────────────────────────────────────────────────────────────────
RUN rm -rf /tmp/libs

# ── Entrypoint ───────────────────────────────────────────────────────────────
WORKDIR /data
ENV PATH="/opt/wrf/main:/opt/wrf/run:/opt/wps:${PATH}"
