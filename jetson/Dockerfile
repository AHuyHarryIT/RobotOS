# Jetson Docker - CI/CD Pipeline & Vision System

FROM ubuntu:20.04

# Set environment for non-interactive install
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Set working directory
WORKDIR /app/jetson

# Install system dependencies including CUDA runtime
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    libzmq3-dev \
    pkg-config \
    ca-certificates \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create config directory if not exists
RUN mkdir -p config && \
    mkdir -p /app/logs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "import zmq; print('OK')" || exit 1

# Default command: run vision client
CMD ["python3", "vision_client.py"]
