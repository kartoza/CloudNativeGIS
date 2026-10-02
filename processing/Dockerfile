# GDAL's "full" image is the smallest official one built with Arrow, which
# the (Geo)Parquet driver needs — Debian's own gdal-bin has neither.
ARG GDAL_IMAGE=ghcr.io/osgeo/gdal:ubuntu-full-3.11.4

# The base image's Apache Arrow apt repo fails signature checks (rotated
# key), breaking every `apt-get update` — Arrow itself is already
# installed, so the repo is dropped rather than re-keyed.
ARG DROP_APT_SOURCES=/etc/apt/sources.list.d/apache-arrow.sources

FROM ${GDAL_IMAGE} AS tippecanoe
ARG DROP_APT_SOURCES

RUN rm -f ${DROP_APT_SOURCES} && \
    apt-get update -y && \
    apt-get install -y --no-install-recommends \
    build-essential git libsqlite3-dev zlib1g-dev ca-certificates && \
    git clone --depth 1 https://github.com/felt/tippecanoe.git /tmp/tippecanoe && \
    make -C /tmp/tippecanoe -j$(nproc) && \
    make -C /tmp/tippecanoe install

# PDAL (LAS/LAZ -> COPC), which Ubuntu 24.04 doesn't package. It comes from
# conda-forge as a self-contained environment - its own GDAL, PROJ and
# libgeotiff - rather than built against the base image's GDAL: that GDAL
# carries two PROJs (its internal one and Ubuntu's, via libgeotiff and
# spatialite), and PDAL reading a LAS file's CRS crashes between them.
FROM ${GDAL_IMAGE} AS pdal
ARG DROP_APT_SOURCES
ARG PDAL_VERSION=2.10

RUN rm -f ${DROP_APT_SOURCES} && \
    apt-get update -y && \
    apt-get install -y --no-install-recommends curl bzip2 ca-certificates && \
    arch=$(uname -m | sed 's/x86_64/64/') && \
    curl -fsSL "https://micro.mamba.pm/api/micromamba/linux-${arch}/latest" \
      | tar -xj -C /usr/local bin/micromamba && \
    micromamba create -y -p /opt/pdal -c conda-forge "pdal=${PDAL_VERSION}" && \
    micromamba clean -a -y && \
    # Only the pdal command and the libraries/data it runs with are kept.
    find /opt/pdal/bin -mindepth 1 ! -name pdal -delete && \
    rm -rf /opt/pdal/include /opt/pdal/conda-meta /opt/pdal/man \
      /opt/pdal/share/doc /opt/pdal/share/man /opt/pdal/lib/cmake \
      /opt/pdal/lib/pkgconfig && \
    find /opt/pdal/lib -name "*.a" -delete

FROM ${GDAL_IMAGE}
ARG DROP_APT_SOURCES

RUN rm -f ${DROP_APT_SOURCES} && \
    apt-get update -y && \
    apt-get install -y --no-install-recommends python3-venv curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=tippecanoe /usr/local/bin/tippecanoe* /usr/local/bin/tile-join /usr/local/bin/
COPY --from=pdal /opt/pdal /opt/pdal
# Only `pdal` itself on the PATH, with its environment's own PROJ/GDAL data:
# the rest of /opt/pdal/bin would shadow the base image's GDAL tools.
RUN printf '#!/bin/sh\nexport PROJ_DATA=/opt/pdal/share/proj GDAL_DATA=/opt/pdal/share/gdal\nexec /opt/pdal/bin/pdal "$@"\n' \
      > /usr/local/bin/pdal && chmod +x /usr/local/bin/pdal

# The base image's system Python is externally managed (PEP 668).
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
RUN python3 -m venv ${VIRTUAL_ENV}

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY app /app/app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
