#!/usr/bin/env bash
set -euo pipefail

# Load .env
if [ -f .env ]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' .env | xargs -d '\n')
else
  echo "[ERROR] .env not found in current directory"
  exit 1
fi

PROJECT_NAME="${PROJECT_NAME:-auto-bot}"
RPI_HOST="${RPI_HOST:-192.168.10.200}"
RPI_USER="${RPI_USER:-pi}"
RPI_DEST_DIR="${RPI_DEST_DIR:-/home/pi/auto-bot-rpi}"
ZMQ_PORT="${ZMQ_PORT:-5555}"

CLIENT_BASE="${PROJECT_NAME}-client"
RPI_BASE="${PROJECT_NAME}-rpi"

# --- generate version tag ---
VERSION="$(date +%Y%m%d-%H%M%S)"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_SHA="$(git rev-parse --short HEAD)"
  VERSION="${VERSION}-${GIT_SHA}"
fi

CLIENT_IMAGE="${CLIENT_BASE}:${VERSION}"
RPI_IMAGE="${RPI_BASE}:${VERSION}"

echo "[SETUP] PROJECT_NAME=${PROJECT_NAME}"
echo "[SETUP] RPI_HOST=${RPI_HOST}, RPI_USER=${RPI_USER}, RPI_DEST_DIR=${RPI_DEST_DIR}"
echo "[SETUP] ZMQ_PORT=${ZMQ_PORT}"
echo "[SETUP] VERSION=${VERSION}"
echo "[SETUP] CLIENT_IMAGE=${CLIENT_IMAGE}, RPI_IMAGE=${RPI_IMAGE}"

# --- 1. Ensure Docker on miniPC ---
if ! command -v docker &>/dev/null; then
  echo "[SETUP] Installing Docker on miniPC..."
  curl -fsSL https://get.docker.com | sh
fi

if command -v systemctl &>/dev/null; then
  sudo systemctl enable docker || true
  sudo systemctl start docker || true
fi

# --- 2. Copy root .env -> client/.env & rpi/.env ---
echo "[SETUP] Sync .env to client/ and rpi/..."
cp .env client/.env
cp .env rpi/.env

# --- 3. Build & run client Docker (miniPC) ---
echo "[SETUP] Build client image ${CLIENT_IMAGE}..."
docker build -t "${CLIENT_IMAGE}" -t "${CLIENT_BASE}:latest" ./client

echo "[SETUP] Start client container via docker-compose..."
(
  cd client
  # docker-compose sẽ dùng client/.env
  docker compose down || true
  docker compose up -d
)

# --- 4. Ensure Docker on RPi ---
echo "[SETUP] Ensure Docker on RPi ${RPI_USER}@${RPI_HOST}..."

ssh "${RPI_USER}@${RPI_HOST}" bash -s <<EOF
set -e
if ! command -v docker &>/dev/null; then
  echo "[RPI] Installing Docker..."
  curl -fsSL https://get.docker.com | sh
fi
if command -v systemctl &>/dev/null; then
  sudo systemctl enable docker || true
  sudo systemctl start docker || true
fi
mkdir -p "${RPI_DEST_DIR}"
EOF

# --- 5. Copy rpi/ code + .env to RPi ---
echo "[SETUP] Copy rpi/ to RPi..."
scp rpi/* "${RPI_USER}@${RPI_HOST}:${RPI_DEST_DIR}/"

# copy .env root → rpi/.env 
scp .env "${RPI_USER}@${RPI_HOST}:${RPI_DEST_DIR}/.env"

# --- 6. Build & run server Docker on RPi ---
echo "[SETUP] Build & run server image ${RPI_IMAGE} on RPi..."

ssh "${RPI_USER}@${RPI_HOST}" bash -s <<EOF
set -e
cd "${RPI_DEST_DIR}"

echo "[RPI] Build image ${RPI_IMAGE}..."
sudo docker build -t "${RPI_IMAGE}" -t "${RPI_BASE}:latest" .

echo "[RPI] Stop old container if exists..."
sudo docker stop "${RPI_BASE}" 2>/dev/null || true
sudo docker rm "${RPI_BASE}" 2>/dev/null || true

echo "[RPI] Run new container ${RPI_BASE}..."
sudo docker run -d \
  --name "${RPI_BASE}" \
  --restart unless-stopped \
  --privileged \
  --network host \
  --env-file "${RPI_DEST_DIR}/.env" \
  "${RPI_BASE}:latest"

EOF

echo "[SETUP] DONE. Client & server containers are running."
echo "${VERSION}" > .last_version
