# Pin major image; --platform can be set at build time for ARM servers if needed.
FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.title="TranscriptFlow API" \
      org.opencontainers.image.description="FastAPI transcript extraction service"

# Non-root user: fixed UID/GID 1000 so host bind-mounts can chown 1000:1000 if needed.
RUN groupadd --system --gid 1000 app \
    && useradd --system --uid 1000 --gid app --no-create-home --home-dir /app app

WORKDIR /app

# System deps for reportlab / cffi
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY app/ app/

# Writable app data: transcript cache, metrics DB, generated files under data/tmp
RUN mkdir -p /app/data/transcript_cache /app/data/tmp \
    && chown -R app:app /app

# SECURITY: No .env baked into the image — inject at runtime (Compose, Render, Railway, etc.).

USER app

ENV HOME=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TEMP=/tmp \
    TMPDIR=/tmp \
    FILE_STORAGE_DIR=/app/data/tmp \
    TRANSCRIPT_CACHE_DIR=/app/data/transcript_cache \
    IN_PROCESS_CLEANUP_ENABLED=true

EXPOSE 8000

# Logs to stdout/stderr for `docker logs` / platform log drains.
# Workers: increase GUNICORN_WORKERS via Compose if the host has CPU headroom (each worker = separate rate-limit memory).
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--max-requests", "2000", \
     "--max-requests-jitter", "200"]
