# ================================
# SaveFood DZ - Multi-Stage Build
# ================================

# ----- Stage 1: Base -----
FROM python:3.11-slim AS base

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libmagic1 \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ----- Stage 2: Dependencies -----
FROM base AS dependencies

# Install Poetry
RUN pip install poetry==1.8.2

COPY pyproject.toml poetry.lock* ./

# Install dependencies (no dev deps for production)
RUN poetry config virtualenvs.create false \
    && poetry install --only=main --no-interaction --no-ansi

# ----- Stage 3: Development -----
FROM dependencies AS development

# Install dev dependencies
RUN poetry install --no-interaction --no-ansi

COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ----- Stage 4: Production -----
FROM dependencies AS production

# Copy application code
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput --settings=config.settings.production || true

# Create non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')" || exit 1

CMD ["gunicorn", "config.wsgi:application", \
    "--bind", "0.0.0.0:8000", \
    "--workers", "4", \
    "--worker-class", "sync", \
    "--worker-connections", "1000", \
    "--timeout", "60", \
    "--keepalive", "5", \
    "--max-requests", "1000", \
    "--max-requests-jitter", "100", \
    "--log-level", "info", \
    "--access-logfile", "-", \
    "--error-logfile", "-"]
