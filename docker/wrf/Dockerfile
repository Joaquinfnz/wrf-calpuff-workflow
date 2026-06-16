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
    libjasper-dev \
    openmpi-bin \
    libopenmpi-dev \
    openssh-client \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# ── Compilar NetCDF (necesario para WRF) ─────────────────────────────────────
WORKDIR /tmp/libs

ENV DIR=/opt/netcdf
ENV CC=gcc CXX=g++ FC=gfortran F77=gfortran F90=gfortran
ENV CPPFLAGS="-I${DIR}/include" LDFLAGS="-L${DIR}/lib"
ENV LD_LIBRARY_PATH="${DIR}/lib:${LD_LIBRARY_PATH}"

# NetCDF-C
RUN wget -q https://downloads.unidata.ucar.edu/netcdf-c/4.9.2/netcdf-c-4.9.2.tar.gz \
    && tar xzf netcdf-c-4.9.2.tar.gz \
    && cd netcdf-c-4.9.2 \
    && ./configure --prefix=${DIR} --disable-dap --disable-netcdf-4 --disable-byterange 2>&1 | tee configure.log \
    && make -j$(nproc) 2>&1 | tee make.log \
    && make install 2>&1 | tee install.log

# NetCDF-Fortran
RUN wget -q https://downloads.unidata.ucar.edu/netcdf-fortran/4.6.1/netcdf-fortran-4.6.1.tar.gz \
    && tar xzf netcdf-fortran-4.6.1.tar.gz \
    && cd netcdf-fortran-4.6.1 \
    && CPPFLAGS="-I${DIR}/include" LDFLAGS="-L${DIR}/lib" LIBS="-lnetcdf -lhdf5_hl -lhdf5 -lz -lcurl" \
       ./configure --prefix=${DIR} 2>&1 | tee configure.log \
    && make -j$(nproc) 2>&1 | tee make.log \
    && make install 2>&1 | tee install.log

# ── Variables de entorno WRF ─────────────────────────────────────────────────
ENV NETCDF=${DIR}
ENV WRF_DIR=/opt/wrf
ENV WRFIO_NCD_LARGE_FILE_SUPPORT=1
ENV WRF_EM_CORE=1
ENV WRF_NMM_CORE=0
ENV WRF_CHEM=0
ENV WRF_KPP=0
ENV JASPERLIB=/usr/lib/x86_64-linux-gnu
ENV JASPERINC=/usr/include
ENV HDF5=/usr/lib/x86_64-linux-gnu/hdf5/serial

# ── Compilar WRF 4.6.0 ──────────────────────────────────────────────────────
WORKDIR /opt
RUN wget -q https://github.com/wrf-model/WRF/archive/refs/tags/v4.6.0.tar.gz -O wrf.tar.gz \
    && tar xzf wrf.tar.gz \
    && mv WRF-4.6.0 wrf \
    && cd wrf \
    && echo "35" | ./configure \
    && ./compile em_real -j$(nproc) 2>&1 | tee compile.log \
    && rm -f ../wrf.tar.gz

# ── Compilar WPS 4.6.0 ──────────────────────────────────────────────────────
WORKDIR /opt
RUN wget -q https://github.com/wrf-model/WPS/archive/refs/tags/v4.6.0.tar.gz -O wps.tar.gz \
    && tar xzf wps.tar.gz \
    && mv WPS-4.6.0 wps \
    && cd wps \
    && echo "3" | ./configure \
    && ./compile 2>&1 | tee compile.log \
    && rm -f ../wps.tar.gz

# ── Limpiar ──────────────────────────────────────────────────────────────────
RUN rm -rf /tmp/libs

# ── Entrypoint ───────────────────────────────────────────────────────────────
WORKDIR /data
ENV PATH="/opt/wrf/main:/opt/wrf/run:/opt/wps:${PATH}"
