FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    gcc python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cho phép override qua .env hoặc -e
ENV ZMQ_PORT=5555

CMD ["python", "zmq_server.py"]
