FROM python:3.11-slim

# cài lib cho pygame
RUN apt-get update && apt-get install -y \
    python3-dev build-essential \
    libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .

# .env sẽ được mount từ ngoài (hoặc env_file trong compose)
CMD ["python", "main.py"]
