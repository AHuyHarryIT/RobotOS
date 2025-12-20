#!/usr/bin/env bash
set -euo pipefail

# Load environment variables from .env
if [ -f .env ]; then
  # shellcheck disable=SC2046
  set -a
  # shellcheck disable=SC1091
  source <(grep -E '^[A-Za-z_]' .env | sed 's/#.*$//')
  set +a
else
  echo "[ERROR] .env not found. Please copy .env.example to .env and configure it."
  exit 1
fi

PROJECT_NAME="${PROJECT_NAME:-auto-bot}"
RPI_IP="${RPI_IP:-192.168.10.200}"
RPI_USER="${RPI_USER:-pi}"
RPI_DEST_DIR="${RPI_DEST_DIR:-/home/pi/auto-bot-rpi}"

SERVER_BASE="${PROJECT_NAME}-server"
RPI_BASE="${PROJECT_NAME}-rpi"

VERSION="$(date +%Y%m%d-%H%M%S)"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_SHA="$(git rev-parse --short HEAD)"
  VERSION="${VERSION}-${GIT_SHA}"
fi

SERVER_IMAGE="${SERVER_BASE}:${VERSION}"
RPI_IMAGE="${RPI_BASE}:${VERSION}"

echo "[UPDATE] VERSION=${VERSION}"

# Prepare SSH command prefix (with or without password)
if [ -n "${RPI_PASSWORD:-}" ] && command -v sshpass >/dev/null 2>&1; then
  SSH_CMD="sshpass -p '${RPI_PASSWORD}' ssh"
  SCP_CMD="sshpass -p '${RPI_PASSWORD}' scp"
else
  SSH_CMD="ssh"
  SCP_CMD="scp"
fi

# Sync .env to server/ and rpi/ directories
echo "[UPDATE] Syncing .env files..."
cp .env server/.env
cp .env rpi/.env

# 1) Rebuild server image & restart server container
echo "[UPDATE] Rebuilding server image..."
docker build -t "${SERVER_IMAGE}" -t "${SERVER_BASE}:latest" ./server

echo "[UPDATE] Restarting server container..."
(
  cd server
  docker compose down || true
  docker compose up -d
)

# 2) Copy rpi code & rebuild image on RPi
echo "[UPDATE] Copying rpi/ to RPi..."
${SCP_CMD} -r rpi/* "${RPI_USER}@${RPI_IP}:${RPI_DEST_DIR}/"
${SSH_CMD} "${RPI_USER}@${RPI_IP}" bash -s <<EOF
set -e
cd "${RPI_DEST_DIR}"
sudo docker build -t "${RPI_IMAGE}" -t "${RPI_BASE}:latest" .
sudo docker stop "${RPI_BASE}" 2>/dev/null || true
sudo docker rm "${RPI_BASE}" 2>/dev/null || true
sudo docker run -d \
  --name "${RPI_BASE}" \
  --restart unless-stopped \
  --privileged \
  --network host \
  --env-file "${RPI_DEST_DIR}/.env" \
  "${RPI_BASE}:latest"
EOF

echo "${VERSION}" > .last_version
echo "[UPDATE] DONE."
