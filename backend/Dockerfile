FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Minimal OS deps for health checks and common binary wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
RUN addgroup --system app && adduser --system --ingroup app app
RUN mkdir -p /home/app /tmp/uv-cache && chown -R app:app /home/app /tmp/uv-cache

# Install uv for dependency management.
RUN pip install --no-cache-dir uv

# Install Python dependencies first for better layer caching.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application source.
COPY backend ./backend
COPY config.py ./config.py
RUN chown -R app:app /app
USER app
ENV HOME=/home/app
ENV UV_CACHE_DIR=/tmp/uv-cache

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
