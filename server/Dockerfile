FROM python:3.11-slim

# Install dependencies for pygame and system packages
RUN apt-get update && apt-get install -y \
    python3-dev build-essential \
    libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY *.py ./
COPY templates/ ./templates/

# Create directory for runtime data
RUN mkdir -p /app/data

# .env will be mounted from host or provided via env_file
# Port 5000 for web dashboard
EXPOSE 5000

# Run main application
CMD ["python", "main.py"]
