# Production Dockerfile for Railway deployment
# Optimized for fast builds and small image size (~150MB)

FROM python:3.12-slim

WORKDIR /app

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy all files
COPY . /app/

# Navigate to backend specifically
WORKDIR /app/backend

# Install dependencies with vision extras
ENV UV_LINK_MODE=copy
RUN uv sync --frozen --extra vision

# Expose port (Railway will inject $PORT)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request, os; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", 8000)}/health')"

# Ensure dependencies are synced and start FastAPI server
# Using ENTRYPOINT with sh -c to actively ignore any broken Dashboard UI start commands (like `cd backend...`) passed by Railway.
ENTRYPOINT ["sh", "-c", "uv sync --frozen --extra vision && uv run python run.py"]
