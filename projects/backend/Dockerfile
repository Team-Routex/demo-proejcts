# ==============================================================================
# RaftFramework Full-Stack Blog - Backend Dockerfile
# ==============================================================================
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app:/app/projects/backend"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy framework core and package files
COPY pyproject.toml README.md ./
COPY raft ./raft
COPY raftsql ./raftsql

# Upgrade pip and install framework with ORM extras
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[orm]"

# Copy backend application source code
COPY projects/backend ./projects/backend

# Create directory for media uploads
RUN mkdir -p /app/projects/backend/uploads

WORKDIR /app/projects/backend

# Expose backend port
EXPOSE 8000

# Healthcheck for backend container
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/api/health || exit 1

# Start Raft ASGI application with uvicorn
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

