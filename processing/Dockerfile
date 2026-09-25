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

FROM ${GDAL_IMAGE}
ARG DROP_APT_SOURCES

RUN rm -f ${DROP_APT_SOURCES} && \
    apt-get update -y && \
    apt-get install -y --no-install-recommends python3-venv curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=tippecanoe /usr/local/bin/tippecanoe* /usr/local/bin/tile-join /usr/local/bin/

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
