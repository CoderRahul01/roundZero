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



# Ensure dependencies are synced and start the framework-aligned server
ENTRYPOINT ["sh", "-c", "uv sync --frozen --extra vision && uv run python run.py"]
