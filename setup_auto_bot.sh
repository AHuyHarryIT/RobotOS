#!/usr/bin/env bash

# RobotOS Complete Setup Script
# Automated Docker installation and deployment for both miniPC and Raspberry Pi

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
    source <(grep -E '^[A-Za-z_]' .env | sed 's/#.*$//')
    set +a
fi

# Configuration (can be overridden with env vars)
RPI_IP="${RPI_IP:-192.168.1.20}"
RPI_USER="${RPI_USER:-pi}"
RPI_DEST_DIR="${RPI_DEST_DIR:-~/auto-bot-rpi}"

SERVER_IMAGE="${SERVER_IMAGE:-robotos-server}"
SERVER_CONTAINER_NAME="${SERVER_CONTAINER_NAME:-robotos-server}"

RPI_IMAGE="${RPI_IMAGE:-auto-bot-rpi}"
RPI_CONTAINER_NAME="${RPI_CONTAINER_NAME:-auto-bot-rpi}"

ZMQ_PORT="${ZMQ_PORT:-5555}"
HEARTBEAT_PORT="${HEARTBEAT_PORT:-5556}"
SERVER_PORT="${SERVER_PORT:-5557}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   RobotOS Complete Setup Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "  RPI_IP: ${RPI_IP}"
echo "  RPI_USER: ${RPI_USER}"
echo "  ZMQ_PORT: ${ZMQ_PORT}"
echo "  HEARTBEAT_PORT: ${HEARTBEAT_PORT}"
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
    echo -e "${YELLOW}[5/7] Deploying server (miniPC)...${NC}"
    
    echo -e "${BLUE}Building Docker image for server...${NC}"
    docker build -t "${SERVER_IMAGE}" ./server
    
    echo -e "${BLUE}Starting server container...${NC}"
    (
        cd server
        docker compose down 2>/dev/null || true
        docker compose up -d
    )
    
    echo -e "${GREEN}✓ Server container running${NC}"
    
    # Health check
    sleep 3
    if curl -sf http://localhost:5000/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Server health check passed${NC}"
        echo -e "${GREEN}✓ Web dashboard available at: http://localhost:5000${NC}"
    else
        echo -e "${YELLOW}⚠ Server is starting, health check pending...${NC}"
    fi
}

# Function to deploy RPi
deploy_rpi() {
    echo -e "${YELLOW}[6/7] Deploying to Raspberry Pi...${NC}"
    
    # Check SSH connectivity
    echo -e "${BLUE}Testing SSH connection to ${RPI_USER}@${RPI_IP}...${NC}"
    if ! ssh "${RPI_USER}@${RPI_IP}" exit 2>/dev/null; then
        echo -e "${RED}✗ Cannot connect to RPi via SSH${NC}"
        echo -e "${YELLOW}Please ensure:${NC}"
        echo "  1. RPi is powered on and connected to network"
        echo "  2. SSH is enabled on RPi"
        echo "  3. SSH keys are configured (or password authentication is enabled)"
        echo "  4. RPI_IP is correct: ${RPI_IP}"
        return 1
    fi
    echo -e "${GREEN}✓ SSH connection successful${NC}"
    
    # Install Docker on RPi
    echo -e "${BLUE}Ensuring Docker is installed on RPi...${NC}"
    ssh "${RPI_USER}@${RPI_IP}" bash -s <<'EOF'
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
    echo -e "${BLUE}Copying files to RPi...${NC}"
    ssh "${RPI_USER}@${RPI_IP}" "rm -rf '${RPI_DEST_DIR}' && mkdir -p '${RPI_DEST_DIR}'"
    
    # Copy rpi code
    scp -r rpi/* "${RPI_USER}@${RPI_IP}:${RPI_DEST_DIR}/"
    
    # Copy .env file (create if doesn't exist in rpi/)
    if [ ! -f "rpi/.env" ]; then
        echo -e "${BLUE}Creating rpi/.env from root .env...${NC}"
        cp .env rpi/.env
    fi
    scp rpi/.env "${RPI_USER}@${RPI_IP}:${RPI_DEST_DIR}/.env"
    
    echo -e "${GREEN}✓ Files copied${NC}"
    
    # Build and run container on RPi
    echo -e "${BLUE}Building and starting container on RPi...${NC}"
    ssh "${RPI_USER}@${RPI_IP}" bash -s <<EOF
set -e
cd "${RPI_DEST_DIR}"

echo "[RPI] Building image ${RPI_IMAGE}..."
sudo docker build -t "${RPI_IMAGE}" .

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
  "${RPI_IMAGE}"

echo "[RPI] Container started successfully"
EOF
    
    echo -e "${GREEN}✓ RPi deployment complete${NC}"
}

# Function to verify deployment
verify_deployment() {
    echo -e "${YELLOW}[7/7] Verifying deployment...${NC}"
    
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
    echo ""
    
    # Deploy server if requested
    if [[ ! "$deploy_server_choice" =~ ^[Nn]$ ]]; then
        deploy_server
    fi
    
    # Deploy RPi if requested
    if [[ ! "$deploy_rpi_choice" =~ ^[Nn]$ ]]; then
        deploy_rpi || echo -e "${YELLOW}⚠ RPi deployment skipped or failed${NC}"
    fi
    
    verify_deployment
    
    # Final summary
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}   Setup Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "  • Access web dashboard: http://localhost:5000"
    echo "  • View server logs: docker compose -f server/docker-compose.yml logs -f"
    if [[ ! "$deploy_rpi_choice" =~ ^[Nn]$ ]]; then
        echo "  • View RPi logs: ssh ${RPI_USER}@${RPI_IP} 'sudo docker logs -f ${RPI_CONTAINER_NAME}'"
    fi
    echo ""
    echo -e "${BLUE}Useful commands:${NC}"
    echo "  • Stop server: docker compose -f server/docker-compose.yml down"
    echo "  • Restart server: docker compose -f server/docker-compose.yml restart"
    echo "  • Update config: Edit .env and re-run this script"
    echo ""
}

# Run main function
main
