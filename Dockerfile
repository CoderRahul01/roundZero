# Root-level Dockerfile for Railway deployment
# This builds the backend from the repository root

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for PyAV (av package) and other native packages
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswscale-dev \
    libavdevice-dev \
    pkg-config \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy backend dependency files
COPY backend/pyproject.toml ./
COPY backend/uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy entire backend application
COPY backend/ ./

# Expose port
EXPOSE 8000

# Start command (Railway will override with $PORT)
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
