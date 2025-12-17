FROM python:3.11-slim

# Install build dependencies for RPi.GPIO and ZMQ
RUN apt-get update && apt-get install -y \
    gcc python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY *.py ./

# Default environment variables (can be overridden)
ENV ZMQ_PORT=5555
ENV HEARTBEAT_PORT=5556
ENV PYTHONUNBUFFERED=1

# Expose ZMQ ports
EXPOSE 5555 5556

# Run ZMQ server
CMD ["python", "zmq_server.py"]
