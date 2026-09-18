FROM python:3.12-slim-bookworm

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
    gcc g++ make build-essential \
    gdal-bin \
    libsqlite3-dev \
    libprotobuf-dev protobuf-compiler zlib1g-dev git \
    curl && \
    echo "Installing Tippecanoe" && \
    git clone https://github.com/felt/tippecanoe.git /tmp/tippecanoe && \
    cd /tmp/tippecanoe && \
    make -j$(nproc) && make install && \
    rm -rf /tmp/tippecanoe && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY app /app/app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
