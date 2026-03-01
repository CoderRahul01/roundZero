# Production Dockerfile for Railway deployment
# Optimized for fast builds and small image size (~150MB)

FROM python:3.12-slim

WORKDIR /app

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY backend/pyproject.toml backend/uv.lock ./

# Install dependencies with vision extras
# UV_LINK_MODE=copy ensures proper file handling in containers
ENV UV_LINK_MODE=copy
RUN uv sync --frozen --extra vision

# Copy application code
COPY backend/ ./

# Expose port (Railway will inject $PORT)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Start FastAPI server
CMD ["sh", "-c", "uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
