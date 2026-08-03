# Backend image: API + scheduler.
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first so application edits do not invalidate the layer.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY alembic.ini ./
COPY scripts ./scripts

# Writable location for the SQLite fallback and any exports.
RUN mkdir -p /app/data && \
    adduser --disabled-password --gecos "" --uid 10001 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# The liveness probe deliberately avoids the database so a DB problem surfaces
# as a degraded /api/health rather than an unschedulable container.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4).status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
