#!/usr/bin/env bash
set -euo pipefail

### ==== CONFIG (có thể override bằng env khi chạy) ====
RPI_HOST="${RPI_HOST:-192.168.10.200}"
RPI_USER="${RPI_USER:-pi}"
RPI_DEST_DIR="${RPI_DEST_DIR:-/home/pi/auto-bot-rpi}"

CLIENT_IMAGE="${CLIENT_IMAGE:-auto-bot-xbox-client}"
CLIENT_CONTAINER_NAME="${CLIENT_CONTAINER_NAME:-auto-bot-xbox-client}"

RPI_IMAGE="${RPI_IMAGE:-auto-bot-rpi}"
RPI_CONTAINER_NAME="${RPI_CONTAINER_NAME:-auto-bot-rpi}"

ZMQ_PORT="${ZMQ_PORT:-5555}"

echo "[SETUP] RPI_HOST=${RPI_HOST}, RPI_USER=${RPI_USER}, ZMQ_PORT=${ZMQ_PORT}"
echo "[SETUP] RPI_DEST_DIR=${RPI_DEST_DIR}"
echo "[SETUP] CLIENT_IMAGE=${CLIENT_IMAGE}, RPI_IMAGE=${RPI_IMAGE}"

### ==== 1. Kiểm tra Docker trên miniPC ====
if ! command -v docker &>/dev/null; then
  echo "[SETUP] Docker chưa cài trên miniPC. Đang cài (Ubuntu/Debian)..."
  curl -fsSL https://get.docker.com | sh
fi

if ! command -v docker &>/dev/null; then
  echo "[ERROR] Docker vẫn chưa dùng được sau khi cài. Thoát."
  exit 1
fi

if command -v systemctl &>/dev/null; then
  sudo systemctl enable docker || true
  sudo systemctl start docker || true
fi

### ==== 2. Tạo server/.env nếu chưa có ====
SERVER_ENV="server/.env"
if [ ! -f "$SERVER_ENV" ]; then
  echo "[SETUP] Tạo server/.env với default…"
  cat > "$SERVER_ENV" <<EOF
RPI_IP=${RPI_HOST}
ZMQ_PORT=${ZMQ_PORT}
DUR_FORWARD=0.5
DUR_BACKWARD=0.5
DUR_TURN=0.3
SEND_COOLDOWN=0.05
EOF
else
  echo "[SETUP] server/.env đã tồn tại, giữ nguyên."
fi

### ==== 3. Build & chạy Docker client trên miniPC ====
echo "[SETUP] Build Docker image cho xbox_client (miniPC)…"
docker build -t "${CLIENT_IMAGE}" ./server

echo "[SETUP] Start container client bằng docker-compose…"
(
  cd client
  docker compose down || true
  docker compose up -d
)

echo "[SETUP] Docker client đang chạy (container: ${CLIENT_CONTAINER_NAME})."

### ==== 4. Cài & chuẩn bị Docker trên RPi ====
echo "[SETUP] Đảm bảo RPi có Docker…"

ssh "${RPI_USER}@${RPI_HOST}" bash -s <<EOF
set -e
if ! command -v docker &>/dev/null; then
  echo "[RPI] Docker chưa cài, cài bằng get.docker.com…"
  curl -fsSL https://get.docker.com | sh
fi

if command -v systemctl &>/dev/null; then
  sudo systemctl enable docker || true
  sudo systemctl start docker || true
fi

mkdir -p "${RPI_DEST_DIR}"
EOF
### ==== 5. Copy code rpi/ + .env sang RPi ====
echo "[SETUP] Copy rpi code + .env sang RPi..."

ssh "${RPI_USER}@${RPI_HOST}" "mkdir -p '${RPI_DEST_DIR}'"
scp rpi/* "${RPI_USER}@${RPI_HOST}:${RPI_DEST_DIR}/"

### ==== 6. Build & run Docker server trên RPi ====
echo "[SETUP] Build & run docker server trên RPi..."

ssh "${RPI_USER}@${RPI_HOST}" bash -s <<EOF
set -e
cd "${RPI_DEST_DIR}"

echo "[RPI] Build image ${RPI_IMAGE}..."
sudo docker build -t "${RPI_IMAGE}" .

echo "[RPI] Stop old container..."
sudo docker stop "${RPI_CONTAINER_NAME}" 2>/dev/null || true
sudo docker rm "${RPI_CONTAINER_NAME}" 2>/dev/null || true

echo "[RPI] Start new container using .env..."
sudo docker run -d \
  --name "${RPI_CONTAINER_NAME}" \
  --restart unless-stopped \
  --privileged \
  --network host \
  --env-file "${RPI_DEST_DIR}/.env" \
  "${RPI_IMAGE}"

echo "[RPI] Server container started."
EOF

echo "[SETUP] DONE."
echo "  - Client docker (xbox) đang chạy trên miniPC."
echo "  - Server docker (zmq_server + GPIO) đang chạy trên RPi."
echo "Bạn có thể đổi IP/port bằng env hoặc sửa server/.env rồi chạy lại script."
