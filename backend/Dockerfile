# ── Stage 1: Dependencies ──────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy lock files first (Docker layer cache)
COPY pyproject.toml uv.lock ./

# Install production deps into /app/.venv
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
RUN uv sync --frozen --no-dev

# ── Stage 2: Runtime ───────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Copy venv from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code and startup script
COPY app/ ./app/
COPY run.py ./

# Runtime config
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# Cloud Run injects PORT (always 8080 in practice)
ENV PORT=8080
EXPOSE 8080

# CRITICAL: run.py sets ws=wsproto and ws_per_message_deflate=False
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

CMD ["python", "run.py"]
