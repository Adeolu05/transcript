FROM python:3.12-slim

WORKDIR /app

# System deps for reportlab PDF generation
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

# SECURITY: No .env file is copied into the image.
# All secrets (TELEGRAM_BOT_TOKEN, SENTRY_DSN, etc.) are injected
# via Render environment variables at runtime.

# TEMP_DIR is ephemeral — created at import time by file_service.py
# On Render, /tmp survives within a single deploy but is wiped on redeploy (fine for TTL files)

EXPOSE 8000

CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--graceful-timeout", "30"]
