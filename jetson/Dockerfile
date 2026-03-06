FROM nvcr.io/nvidia/l4t-base:r32.7.1

WORKDIR /app/jetson

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Ho_Chi_Minh


# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    python3-opencv \
    python3-numpy \
    libzmq3-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip toolchain
RUN pip3 install --upgrade pip setuptools wheel packaging

# Copy requirements first
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create runtime directories
RUN mkdir -p config /app/logs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "import zmq; print('OK')" || exit 1

CMD ["python3", "vision_client.py"]