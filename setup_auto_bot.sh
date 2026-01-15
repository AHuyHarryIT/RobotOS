#!/usr/bin/env bash

# RobotOS Complete Setup Script
# Automated Docker installation and deployment for miniPC, Raspberry Pi, and Jetson

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load environment variables from .env if it exists
if [ -f .env ]; then
    echo -e "${GREEN}Loading configuration from .env...${NC}"
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

# Configuration (can be overridden with env vars)
RPI_IP="${RPI_IP:-192.168.1.20}"
RPI_USER="${RPI_USER:-pi}"
RPI_DEST_DIR="${RPI_DEST_DIR:-~/auto-bot-rpi}"

JETSON_HOST="${JETSON_HOST:-192.168.10.200}"
JETSON_USER="${JETSON_USER:-jetson}"

SERVER_IP="${SERVER_IP:-192.168.1.100}"
SERVER_PORT="${SERVER_PORT:-5000}"

SERVER_IMAGE="${SERVER_IMAGE:-robotos-server}"
SERVER_CONTAINER_NAME="${SERVER_CONTAINER_NAME:-robotos-server}"

RPI_IMAGE="${RPI_IMAGE:-auto-bot-rpi}"
RPI_IMAGE_TAG="${RPI_IMAGE_TAG:-latest}"
RPI_CONTAINER_NAME="${RPI_CONTAINER_NAME:-auto-bot-rpi}"

JETSON_IMAGE="${JETSON_IMAGE:-jetson-vision}"
JETSON_IMAGE_TAG="${JETSON_IMAGE_TAG:-latest}"

ZMQ_PORT="${ZMQ_PORT:-5555}"
HEARTBEAT_PORT="${HEARTBEAT_PORT:-5556}"
SERVER_PORT="${SERVER_PORT:-5557}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   RobotOS Complete Setup Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "  SERVER_IP: ${SERVER_IP}"
echo "  SERVER_PORT: ${SERVER_PORT}"
echo "  RPI_IP: ${RPI_IP}"
echo "  RPI_USER: ${RPI_USER}"
echo "  JETSON_HOST: ${JETSON_HOST}"
echo "  JETSON_USER: ${JETSON_USER}"
echo "  ZMQ_PORT: ${ZMQ_PORT}"
echo "  HEARTBEAT_PORT: ${HEARTBEAT_PORT}"
echo ""
echo -e "${BLUE}Image Registry (running on miniPC):${NC}"
echo "  Registry: ${SERVER_IP}:${SERVER_PORT}"
echo "  RPI will pull: ${SERVER_IP}:${SERVER_PORT}/${RPI_IMAGE}:${RPI_IMAGE_TAG}"
echo "  Jetson will pull: ${SERVER_IP}:${SERVER_PORT}/${JETSON_IMAGE}:${JETSON_IMAGE_TAG}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Docker installation
check_docker() {
    echo -e "${YELLOW}[1/7] Checking Docker installation...${NC}"
    
    if command_exists docker; then
        DOCKER_VERSION=$(docker --version)
        echo -e "${GREEN}✓ Docker is installed: ${DOCKER_VERSION}${NC}"
        return 0
    else
        echo -e "${RED}✗ Docker is not installed${NC}"
        return 1
    fi
}

# Function to install Docker
install_docker() {
    echo -e "${YELLOW}[2/7] Installing Docker...${NC}"
    
    echo -e "${BLUE}Installing Docker via get.docker.com...${NC}"
    curl -fsSL https://get.docker.com | sh
    
    # Add current user to docker group
    sudo usermod -aG docker $USER || true
    
    echo -e "${GREEN}✓ Docker installed successfully${NC}"
    echo -e "${YELLOW}⚠ You may need to log out and back in for group changes to take effect${NC}"
}

# Function to start Docker service
start_docker() {
    echo -e "${YELLOW}[3/7] Starting Docker service...${NC}"
    
    if command_exists systemctl; then
        sudo systemctl enable docker || true
        sudo systemctl start docker || true
        echo -e "${GREEN}✓ Docker service started${NC}"
    else
        echo -e "${YELLOW}⚠ systemctl not found, skipping service start${NC}"
    fi
    
    # Check if Docker daemon is running
    if ! docker info > /dev/null 2>&1; then
        echo -e "${YELLOW}Waiting for Docker daemon to start...${NC}"
        sleep 3
    fi
}

# Function to check and create environment files
check_env_files() {
    echo -e "${YELLOW}[4/7] Checking environment configuration...${NC}"
    
    # Check if root .env exists
    if [ ! -f ".env" ]; then
        echo -e "${RED}✗ .env file not found!${NC}"
        
        if [ -f ".env.example" ]; then
            echo -e "${YELLOW}Creating .env from .env.example...${NC}"
            cp .env.example .env
            echo -e "${GREEN}✓ Created .env file${NC}"
            echo -e "${YELLOW}⚠ IMPORTANT: Edit .env and configure your network settings:${NC}"
            echo "    - RPI_IP (Raspberry Pi IP)"
            echo "    - SERVER_IP (miniPC IP)"
            echo ""
            read -p "Press Enter after editing .env to continue..."
        else
            echo -e "${RED}✗ .env.example not found either!${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✓ .env file exists${NC}"
    fi
    
    # Copy .env to server/ and rpi/ directories
    echo -e "${BLUE}Copying .env to server/ and rpi/ directories...${NC}"
    cp .env server/.env
    cp .env rpi/.env
    echo -e "${GREEN}✓ Environment files synchronized${NC}"
}


# Function to deploy server (miniPC)
deploy_server() {
    echo -e "${YELLOW}[5/8] Deploying server (miniPC)...${NC}"
    
    echo -e "${BLUE}Building Docker images on server...${NC}"
    
    # Build RPI image
    echo -e "${BLUE}Building RPI image: ${RPI_IMAGE}:${RPI_IMAGE_TAG}...${NC}"
    docker build -t "${RPI_IMAGE}:${RPI_IMAGE_TAG}" ./rpi
    
    # Build Jetson image
    echo -e "${BLUE}Building Jetson image: ${JETSON_IMAGE}:${JETSON_IMAGE_TAG}...${NC}"
    docker build -t "${JETSON_IMAGE}:${JETSON_IMAGE_TAG}" ./jetson
    
    # Build server image
    echo -e "${BLUE}Building server image: ${SERVER_IMAGE}...${NC}"
    docker build -t "${SERVER_IMAGE}" ./server
    
    echo -e "${BLUE}Starting Docker Registry on port ${SERVER_PORT}...${NC}"
    # Stop existing registry if running
    docker stop robotos-registry 2>/dev/null || true
    docker rm robotos-registry 2>/dev/null || true
    
    # Start Docker Registry container
    docker run -d \
        --name robotos-registry \
        --restart unless-stopped \
        -p "${SERVER_PORT}:5000" \
        registry:2
    
    echo -e "${GREEN}✓ Docker Registry started on ${SERVER_IP}:${SERVER_PORT}${NC}"
    
    # Tag and push images to local registry
    echo -e "${BLUE}Tagging and pushing images to registry...${NC}"
    
    docker tag "${RPI_IMAGE}:${RPI_IMAGE_TAG}" "localhost:${SERVER_PORT}/${RPI_IMAGE}:${RPI_IMAGE_TAG}"
    docker push "localhost:${SERVER_PORT}/${RPI_IMAGE}:${RPI_IMAGE_TAG}"
    echo -e "${GREEN}✓ Pushed RPI image to registry${NC}"
    
    docker tag "${JETSON_IMAGE}:${JETSON_IMAGE_TAG}" "localhost:${SERVER_PORT}/${JETSON_IMAGE}:${JETSON_IMAGE_TAG}"
    docker push "localhost:${SERVER_PORT}/${JETSON_IMAGE}:${JETSON_IMAGE_TAG}"
    echo -e "${GREEN}✓ Pushed Jetson image to registry${NC}"
    
    echo -e "${BLUE}Starting server container...${NC}"
    (
        cd server
        docker compose down 2>/dev/null || true
        docker compose up -d
    )
    
    echo -e "${GREEN}✓ Server container running${NC}"
    
    # Health check
    sleep 3
    if curl -sf http://localhost:8080/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Server health check passed${NC}"
        echo -e "${GREEN}✓ Web dashboard available at: http://localhost:8080${NC}"
    else
        echo -e "${YELLOW}⚠ Server is starting, health check pending...${NC}"
    fi
}

# Function to deploy RPi
deploy_rpi() {
    echo -e "${YELLOW}[6/8] Deploying to Raspberry Pi...${NC}"
    
    # Prepare SSH command prefix (with or without password)
    if [ -n "${RPI_PASSWORD}" ] && command_exists sshpass; then
        SSH_CMD="sshpass -p '${RPI_PASSWORD}' ssh"
        SCP_CMD="sshpass -p '${RPI_PASSWORD}' scp"
    else
        SSH_CMD="ssh"
        SCP_CMD="scp"
    fi
    
    # Check SSH connectivity
    echo -e "${BLUE}Testing SSH connection to ${RPI_USER}@${RPI_IP}...${NC}"
    if ! ${SSH_CMD} -o ConnectTimeout=5 "${RPI_USER}@${RPI_IP}" exit 2>/dev/null; then
        echo -e "${RED}✗ Cannot connect to RPi via SSH${NC}"
        echo -e "${YELLOW}Please ensure:${NC}"
        echo "  1. RPi is powered on and connected to network"
        echo "  2. SSH is enabled on RPi"
        echo "  3. SSH keys are configured (or password authentication is enabled)"
        echo "  4. RPI_IP is correct: ${RPI_IP}"
        echo "  5. RPI_PASSWORD is set in .env if using password auth"
        return 1
    fi
    echo -e "${GREEN}✓ SSH connection successful${NC}"
    
    # Install Docker on RPi
    echo -e "${BLUE}Ensuring Docker is installed on RPi...${NC}"
    ${SSH_CMD} "${RPI_USER}@${RPI_IP}" bash -s <<'EOF'
set -e
if ! command -v docker &>/dev/null; then
  echo "[RPI] Installing Docker..."
  curl -fsSL https://get.docker.com | sh
fi

if command -v systemctl &>/dev/null; then
  sudo systemctl enable docker || true
  sudo systemctl start docker || true
fi
EOF
    echo -e "${GREEN}✓ Docker installed on RPi${NC}"
    
    # Create directory and copy files
    echo -e "${BLUE}Copying configuration to RPi...${NC}"
    ${SSH_CMD} "${RPI_USER}@${RPI_IP}" "rm -rf '${RPI_DEST_DIR}' && mkdir -p '${RPI_DEST_DIR}'"
    
    # Copy .env file
    if [ ! -f "rpi/.env" ]; then
        echo -e "${BLUE}Creating rpi/.env from root .env...${NC}"
        cp .env rpi/.env
    fi
    ${SCP_CMD} rpi/.env "${RPI_USER}@${RPI_IP}:${RPI_DEST_DIR}/.env"
    
    echo -e "${GREEN}✓ Configuration copied${NC}"
    
    # Pull image from registry and run container on RPi
    echo -e "${BLUE}Pulling image from server registry and starting container on RPi...${NC}"
    ${SSH_CMD} "${RPI_USER}@${RPI_IP}" bash -s <<EOF
set -e

echo "[RPI] Configuring Docker to use insecure registry..."
mkdir -p /etc/docker
echo '{"insecure-registries": ["${SERVER_IP}:${SERVER_PORT}"]}' | sudo tee /etc/docker/daemon.json > /dev/null
sudo systemctl restart docker || true
sleep 2

echo "[RPI] Pulling image from ${SERVER_IP}:${SERVER_PORT}/${RPI_IMAGE}:${RPI_IMAGE_TAG}..."
sudo docker pull "${SERVER_IP}:${SERVER_PORT}/${RPI_IMAGE}:${RPI_IMAGE_TAG}"

echo "[RPI] Tagging image locally..."
sudo docker tag "${SERVER_IP}:${SERVER_PORT}/${RPI_IMAGE}:${RPI_IMAGE_TAG}" "${RPI_IMAGE}:${RPI_IMAGE_TAG}"

echo "[RPI] Stopping old container..."
sudo docker stop "${RPI_CONTAINER_NAME}" 2>/dev/null || true
sudo docker rm "${RPI_CONTAINER_NAME}" 2>/dev/null || true

echo "[RPI] Starting new container..."
sudo docker run -d \
  --name "${RPI_CONTAINER_NAME}" \
  --restart unless-stopped \
  --privileged \
  --network host \
  --env-file "${RPI_DEST_DIR}/.env" \
  "${RPI_IMAGE}:${RPI_IMAGE_TAG}"

echo "[RPI] Container started successfully"
EOF
    
    echo -e "${GREEN}✓ RPi deployment complete${NC}"
}

# Function to deploy Jetson
deploy_jetson() {
    echo -e "${YELLOW}[7/8] Deploying to Jetson...${NC}"
    
    # Prepare SSH command prefix (with or without password)
    if [ -n "${JETSON_PASSWORD}" ] && command_exists sshpass; then
        SSH_CMD="sshpass -p '${JETSON_PASSWORD}' ssh"
        SCP_CMD="sshpass -p '${JETSON_PASSWORD}' scp"
    else
        SSH_CMD="ssh"
        SCP_CMD="scp"
    fi
    
    # Check SSH connectivity
    echo -e "${BLUE}Testing SSH connection to ${JETSON_USER}@${JETSON_HOST}...${NC}"
    if ! ${SSH_CMD} -o ConnectTimeout=5 "${JETSON_USER}@${JETSON_HOST}" exit 2>/dev/null; then
        echo -e "${RED}✗ Cannot connect to Jetson via SSH${NC}"
        echo -e "${YELLOW}Please ensure:${NC}"
        echo "  1. Jetson is powered on and connected to network"
        echo "  2. SSH is enabled on Jetson"
        echo "  3. SSH keys are configured (or password authentication is enabled)"
        echo "  4. JETSON_HOST is correct: ${JETSON_HOST}"
        echo "  5. JETSON_PASSWORD is set in .env if using password auth"
        return 1
    fi
    echo -e "${GREEN}✓ SSH connection successful${NC}"
    
    # Install Docker on Jetson
    echo -e "${BLUE}Ensuring Docker is installed on Jetson...${NC}"
    ${SSH_CMD} "${JETSON_USER}@${JETSON_HOST}" bash -s <<'EOF'
set -e
if ! command -v docker &>/dev/null; then
  echo "[JETSON] Installing Docker..."
  curl -fsSL https://get.docker.com | sh
fi

if command -v systemctl &>/dev/null; then
  sudo systemctl enable docker || true
  sudo systemctl start docker || true
fi
EOF
    echo -e "${GREEN}✓ Docker installed on Jetson${NC}"
    
    # Copy .env file
    echo -e "${BLUE}Copying configuration to Jetson...${NC}"
    
    if [ ! -f "jetson/.env" ]; then
        echo -e "${BLUE}Creating jetson/.env from root .env...${NC}"
        cp .env jetson/.env
    fi
    
    ${SSH_CMD} "${JETSON_USER}@${JETSON_HOST}" "mkdir -p ~/auto-bot-jetson"
    ${SCP_CMD} jetson/.env "${JETSON_USER}@${JETSON_HOST}:~/auto-bot-jetson/.env"
    
    echo -e "${GREEN}✓ Configuration copied${NC}"
    
    # Pull image from registry and run container on Jetson
    echo -e "${BLUE}Pulling image from server registry and starting container on Jetson...${NC}"
    ${SSH_CMD} "${JETSON_USER}@${JETSON_HOST}" bash -s <<EOF
set -e

echo "[JETSON] Configuring Docker to use insecure registry..."
mkdir -p /etc/docker
echo '{"insecure-registries": ["${SERVER_IP}:${SERVER_PORT}"]}' | sudo tee /etc/docker/daemon.json > /dev/null
sudo systemctl restart docker || true
sleep 2

echo "[JETSON] Pulling image from ${SERVER_IP}:${SERVER_PORT}/${JETSON_IMAGE}:${JETSON_IMAGE_TAG}..."
sudo docker pull "${SERVER_IP}:${SERVER_PORT}/${JETSON_IMAGE}:${JETSON_IMAGE_TAG}"

echo "[JETSON] Tagging image locally..."
sudo docker tag "${SERVER_IP}:${SERVER_PORT}/${JETSON_IMAGE}:${JETSON_IMAGE_TAG}" "${JETSON_IMAGE}:${JETSON_IMAGE_TAG}"

echo "[JETSON] Stopping old container..."
sudo docker stop autobot-jetson-vision 2>/dev/null || true
sudo docker rm autobot-jetson-vision 2>/dev/null || true

echo "[JETSON] Starting new container..."
sudo docker run -d \
  --name autobot-jetson-vision \
  --restart unless-stopped \
  --network host \
  --env-file ~/auto-bot-jetson/.env \
  "${JETSON_IMAGE}:${JETSON_IMAGE_TAG}"

echo "[JETSON] Container started successfully"
EOF
    
    echo -e "${GREEN}✓ Jetson deployment complete${NC}"
}

# Function to verify Jetson deployment
verify_jetson() {
    local SSH_CMD="ssh"
    if [ -n "${JETSON_PASSWORD}" ] && command_exists sshpass; then
        SSH_CMD="sshpass -p '${JETSON_PASSWORD}' ssh"
    fi
    
    echo -e "${BLUE}Jetson container status:${NC}"
    ${SSH_CMD} "${JETSON_USER}@${JETSON_HOST}" "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'" 2>/dev/null || true
}

# Function to verify deployment
verify_deployment() {
    echo -e "${YELLOW}[8/8] Verifying deployment...${NC}"
    
    # Check server container
    if docker ps | grep -q "${SERVER_CONTAINER_NAME}"; then
        echo -e "${GREEN}✓ Server container is running${NC}"
    else
        echo -e "${YELLOW}⚠ Server container not running${NC}"
    fi
    
    # Show running containers
    echo -e "\n${BLUE}Local containers:${NC}"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "NAME|${SERVER_CONTAINER_NAME}" || true
    
    echo ""
}

# Main execution
main() {
    # Check Docker
    if ! check_docker; then
        read -p "Install Docker? [y/N]: " install_choice
        if [[ "$install_choice" =~ ^[Yy]$ ]]; then
            install_docker
            start_docker
        else
            echo -e "${RED}Docker is required. Exiting.${NC}"
            exit 1
        fi
    else
        start_docker
    fi
    
    check_env_files
    
    # Ask what to deploy
    echo ""
    read -p "Deploy server (miniPC)? [Y/n]: " deploy_server_choice
    read -p "Deploy to Raspberry Pi? [Y/n]: " deploy_rpi_choice
    read -p "Deploy to Jetson? [Y/n]: " deploy_jetson_choice
    echo ""
    
    # Deploy server if requested
    if [[ ! "$deploy_server_choice" =~ ^[Nn]$ ]]; then
        deploy_server
    fi
    
    # Deploy RPi if requested
    if [[ ! "$deploy_rpi_choice" =~ ^[Nn]$ ]]; then
        deploy_rpi || echo -e "${YELLOW}⚠ RPi deployment skipped or failed${NC}"
    fi
    
    # Deploy Jetson if requested
    if [[ ! "$deploy_jetson_choice" =~ ^[Nn]$ ]]; then
        deploy_jetson || echo -e "${YELLOW}⚠ Jetson deployment skipped or failed${NC}"
    fi
    
    verify_deployment
    
    # Verify Jetson if deployed
    if [[ ! "$deploy_jetson_choice" =~ ^[Nn]$ ]]; then
        verify_jetson
    fi
    
    # Final summary
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}   Setup Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}Deployment Summary:${NC}"
    echo "  • Server (miniPC) - Docker Registry + Central Brain"
    echo "    Registry: ${SERVER_IP}:${SERVER_PORT}"
    echo "    Dashboard: http://localhost:8080"
    if [[ ! "$deploy_rpi_choice" =~ ^[Nn]$ ]]; then
        echo "  • RPi - Pulled image from server registry"
        echo "    Image: ${SERVER_IP}:${SERVER_PORT}/${RPI_IMAGE}:${RPI_IMAGE_TAG}"
    fi
    if [[ ! "$deploy_jetson_choice" =~ ^[Nn]$ ]]; then
        echo "  • Jetson - Pulled image from server registry"
        echo "    Image: ${SERVER_IP}:${SERVER_PORT}/${JETSON_IMAGE}:${JETSON_IMAGE_TAG}"
    fi
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "  • Access web dashboard: http://localhost:8080"
    echo "  • View server logs: docker compose -f server/docker-compose.yml logs -f"
    if [[ ! "$deploy_rpi_choice" =~ ^[Nn]$ ]]; then
        echo "  • View RPi logs: ssh ${RPI_USER}@${RPI_IP} 'sudo docker logs -f ${RPI_CONTAINER_NAME}'"
    fi
    if [[ ! "$deploy_jetson_choice" =~ ^[Nn]$ ]]; then
        echo "  • View Jetson logs: ssh ${JETSON_USER}@${JETSON_HOST} 'sudo docker logs -f autobot-jetson-vision'"
    fi
    echo ""
    echo -e "${BLUE}Useful commands:${NC}"
    echo "  • View registry images: docker image ls | grep -E 'RPI_IMAGE|JETSON_IMAGE|robotos'"
    echo "  • Registry API: curl http://localhost:${SERVER_PORT}/v2/_catalog"
    echo "  • Stop server: docker compose -f server/docker-compose.yml down"
    echo "  • Stop registry: docker stop robotos-registry"
    echo "  • Update and redeploy: Edit .env and re-run this script"
    echo ""
}

# Run main function
main
