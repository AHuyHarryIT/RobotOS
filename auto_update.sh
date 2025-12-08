#!/usr/bin/env bash
set -euo pipefail

if [ -f .env ]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' .env | xargs -d '\n')
else
  echo "[ERROR] .env not found"
  exit 1
fi

PROJECT_NAME="${PROJECT_NAME:-auto-bot}"
RPI_HOST="${RPI_HOST:-192.168.10.200}"
RPI_USER="${RPI_USER:-pi}"
RPI_DEST_DIR="${RPI_DEST_DIR:-/home/pi/auto-bot-rpi}"

CLIENT_BASE="${PROJECT_NAME}-client"
RPI_BASE="${PROJECT_NAME}-rpi"

VERSION="$(date +%Y%m%d-%H%M%S)"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_SHA="$(git rev-parse --short HEAD)"
  VERSION="${VERSION}-${GIT_SHA}"
fi

CLIENT_IMAGE="${CLIENT_BASE}:${VERSION}"
RPI_IMAGE="${RPI_BASE}:${VERSION}"

echo "[UPDATE] VERSION=${VERSION}"

# Sync .env
cp .env client/.env
cp .env rpi/.env

# 1) Rebuild client image & restart client container
echo "[UPDATE] Rebuild client image..."
docker build -t "${CLIENT_IMAGE}" -t "${CLIENT_BASE}:latest" ./client

echo "[UPDATE] Restart client container..."
(
  cd client
  docker compose down || true
  docker compose up -d
)

# 2) Copy rpi code & rebuild image on RPi
echo "[UPDATE] Copy rpi/ to RPi..."
scp rpi/* "${RPI_USER}@${RPI_HOST}:${RPI_DEST_DIR}/"

echo "[UPDATE] Rebuild & restart server on RPi..."
ssh "${RPI_USER}@${RPI_HOST}" bash -s <<EOF
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
