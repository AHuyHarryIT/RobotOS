#!/usr/bin/env bash

# RobotOS Production Deployment Script
# Deploys server and RPi with production configuration

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   RobotOS Production Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if .env.production exists
if [ ! -f .env.production ]; then
    echo -e "${RED}✗ .env.production not found!${NC}"
    echo -e "${YELLOW}Create it from .env.production template${NC}"
    exit 1
fi

# Confirm production deployment
echo -e "${YELLOW}⚠ WARNING: This will deploy to PRODUCTION environment${NC}"
echo -e "${YELLOW}⚠ Make sure all settings in .env.production are correct${NC}"
echo ""
read -p "Continue with production deployment? [y/N]: " confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Deployment cancelled${NC}"
    exit 0
fi

# Backup current .env if exists
if [ -f .env ]; then
    echo -e "${YELLOW}Backing up current .env to .env.backup...${NC}"
    cp .env .env.backup
fi

# Copy production env
echo -e "${BLUE}[1/7] Loading production environment...${NC}"
cp .env.production .env
echo -e "${GREEN}✓ Production environment loaded${NC}"

# Load environment variables
set -a
# shellcheck disable=SC1091
source .env
set +a

echo ""
echo -e "${BLUE}Production Configuration:${NC}"
echo "  Environment: ${ENVIRONMENT:-production}"
echo "  RPI_IP: ${RPI_IP}"
echo "  SERVER_IP: ${SERVER_IP}"
echo "  Flask Host: ${FLASK_HOST:-0.0.0.0}"
echo "  Log Level: ${LOG_LEVEL:-INFO}"
echo ""

# Sync .env to subdirectories
echo -e "${BLUE}[2/7] Syncing environment files...${NC}"
cp .env server/.env
cp .env rpi/.env
echo -e "${GREEN}✓ Environment files synchronized${NC}"

# Build server with production config
echo -e "${BLUE}[3/7] Building server Docker image...${NC}"
VERSION="$(date +%Y%m%d-%H%M%S)"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_SHA="$(git rev-parse --short HEAD)"
  VERSION="${VERSION}-${GIT_SHA}"
fi

SERVER_IMAGE="robotos-server:${VERSION}"

docker build -t "${SERVER_IMAGE}" -t "robotos-server:latest" \
  --build-arg ENVIRONMENT=production \
  ./server

echo -e "${GREEN}✓ Server image built: ${SERVER_IMAGE}${NC}"

# Stop existing containers
echo -e "${BLUE}[4/7] Stopping existing containers...${NC}"
(
  cd server
  docker compose -f docker-compose.prod.yml down 2>/dev/null || true
)
echo -e "${GREEN}✓ Old containers stopped${NC}"

# Start server in production mode
echo -e "${BLUE}[5/7] Starting server in production mode...${NC}"
(
  cd server
  docker compose -f docker-compose.prod.yml up -d
)
echo -e "${GREEN}✓ Server started${NC}"

# Wait for server to be healthy
echo -e "${BLUE}[6/7] Waiting for server to be healthy...${NC}"
for i in {1..30}; do
  if curl -sf http://localhost:5000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Server is healthy${NC}"
    break
  fi
  if [ $i -eq 30 ]; then
    echo -e "${RED}✗ Server health check timeout${NC}"
    echo -e "${YELLOW}Check logs: docker compose -f server/docker-compose.prod.yml logs${NC}"
    exit 1
  fi
  echo -n "."
  sleep 1
done
echo ""

# Deploy to RPi
echo -e "${BLUE}[7/7] Deploying to Raspberry Pi...${NC}"

# Prepare SSH command prefix
if [ -n "${RPI_PASSWORD:-}" ] && command -v sshpass >/dev/null 2>&1; then
  SSH_CMD="sshpass -p '${RPI_PASSWORD}' ssh"
  SCP_CMD="sshpass -p '${RPI_PASSWORD}' scp"
else
  SSH_CMD="ssh"
  SCP_CMD="scp"
fi

# Test SSH connection
if ! ${SSH_CMD} -o ConnectTimeout=5 "${RPI_USER}@${RPI_IP}" exit 2>/dev/null; then
    echo -e "${RED}✗ Cannot connect to RPi via SSH${NC}"
    echo -e "${YELLOW}⚠ Server deployed, but RPi deployment failed${NC}"
    exit 1
fi

# Copy files to RPi
echo -e "${BLUE}Copying files to RPi...${NC}"
${SSH_CMD} "${RPI_USER}@${RPI_IP}" "mkdir -p '${RPI_DEST_DIR}'"
${SCP_CMD} -r rpi/* "${RPI_USER}@${RPI_IP}:${RPI_DEST_DIR}/"
${SCP_CMD} rpi/.env "${RPI_USER}@${RPI_IP}:${RPI_DEST_DIR}/.env"

# Build and deploy on RPi
echo -e "${BLUE}Building and deploying on RPi...${NC}"
${SSH_CMD} "${RPI_USER}@${RPI_IP}" bash -s <<EOF
set -e
cd "${RPI_DEST_DIR}"

echo "[RPI] Building production image..."
sudo docker build -t "auto-bot-rpi:${VERSION}" -t "auto-bot-rpi:latest" .

echo "[RPI] Stopping old container..."
sudo docker stop auto-bot-rpi 2>/dev/null || true
sudo docker rm auto-bot-rpi 2>/dev/null || true

echo "[RPI] Starting production container..."
sudo docker run -d \
  --name auto-bot-rpi \
  --restart always \
  --privileged \
  --network host \
  --env-file "${RPI_DEST_DIR}/.env" \
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  auto-bot-rpi:latest

echo "[RPI] Container deployed successfully"
EOF

echo -e "${GREEN}✓ RPi deployment complete${NC}"

# Save version info
echo "${VERSION}" > .last_production_version
echo "$(date -Iseconds)" > .last_production_deploy

# Final summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Production Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Deployment Info:${NC}"
echo "  Version: ${VERSION}"
echo "  Environment: production"
echo "  Web Dashboard: http://${SERVER_IP}:5000"
echo "  RPi Container: auto-bot-rpi:latest"
echo ""
echo -e "${BLUE}Monitoring:${NC}"
echo "  Server logs: docker compose -f server/docker-compose.prod.yml logs -f"
echo "  RPi logs: ssh ${RPI_USER}@${RPI_IP} 'sudo docker logs -f auto-bot-rpi'"
echo "  Health check: curl http://localhost:5000/api/health"
echo ""
echo -e "${BLUE}Management:${NC}"
echo "  Stop all: ./shutdown_all.sh"
echo "  Restart server: docker compose -f server/docker-compose.prod.yml restart"
echo "  Rollback: Restore .env.backup and redeploy"
echo ""
echo -e "${GREEN}✓ Production system is now running${NC}"
echo ""
