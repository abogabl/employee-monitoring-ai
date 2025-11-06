# Production Dockerfile (GPU-enabled)
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 python3.10-venv python3.10-distutils python3-pip \
    build-essential ffmpeg libgl1 && \
    rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /app

# Create non-root user
RUN useradd -ms /bin/bash appuser && chown -R appuser:appuser /app

# Copy minimal context first for caching
COPY requirements.txt /app/requirements.txt

# Install Python deps (CPU by default; for GPU PyTorch, override index-url in CI/CD)
RUN python3 -m pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt && \
    pip cache purge

# Copy application
COPY src/ /app/src/
COPY config/ /app/config/
COPY web_app/ /app/web_app/
COPY run_web_app.py /app/run_web_app.py
COPY performance_config.json /app/performance_config.json

# Expose web port
EXPOSE 5000

# Drop privileges
USER appuser

# Default command (can be overridden by docker-compose)
CMD ["python3", "/app/run_web_app.py", "--host", "0.0.0.0", "--port", "5000"]
