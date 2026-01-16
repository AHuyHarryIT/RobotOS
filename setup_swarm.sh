#!/usr/bin/env bash

# RobotOS Docker Swarm Deployment Script
# Automated setup for Docker Swarm with miniPC as manager and RPi/Jetson as workers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load environment variables
if [ -f .env ]; then
    echo -e "${GREEN}Loading configuration from .env...${NC}"
    set -a
    source .env
    set +a
fi

# Configuration
RPI_IP="${RPI_IP:-192.168.10.50}"
RPI_USER="${RPI_USER:-hellogit}"
RPI_HOSTNAME="${RPI_HOSTNAME:-rpi-node}"

JETSON_HOST="${JETSON_HOST:-192.168.10.210}"
JETSON_USER="${JETSON_USER:-jetson-autocar}"
JETSON_HOSTNAME="${JETSON_HOSTNAME:-jetson-node}"

SERVER_IP="${SERVER_IP:-192.168.10.1}"
SERVER_REGISTRY_PORT="${SERVER_REGISTRY_PORT:-5000}"

RPI_IMAGE="${RPI_IMAGE:-auto-bot-rpi}"
RPI_IMAGE_TAG="${RPI_IMAGE_TAG:-latest}"

JETSON_IMAGE="${JETSON_IMAGE:-jetson-vision}"
JETSON_IMAGE_TAG="${JETSON_IMAGE_TAG:-latest}"

SERVER_IMAGE="${SERVER_IMAGE:-robotos-server}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   RobotOS Docker Swarm Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "  miniPC IP: ${SERVER_IP}"
echo "  Registry Port: ${SERVER_REGISTRY_PORT}"
echo "  RPi IP: ${RPI_IP} (${RPI_HOSTNAME})"
echo "  Jetson IP: ${JETSON_HOST} (${JETSON_HOSTNAME})"
echo ""

# Function to check Docker Swarm status
check_swarm() {
    echo -e "${YELLOW}[1/5] Checking Docker Swarm status...${NC}"
    
    if ! docker info | grep -q "Swarm: active"; then
        echo -e "${RED}✗ Docker Swarm is not initialized${NC}"
        return 1
    fi
    
    SWARM_ROLE=$(docker info | grep "Swarm" | head -1)
    echo -e "${GREEN}✓ ${SWARM_ROLE}${NC}"
    
    # Check if current node is manager
    if ! docker node ls > /dev/null 2>&1; then
        echo -e "${RED}✗ Current node is not a manager${NC}"
        echo -e "${YELLOW}Run 'docker swarm init' on miniPC first${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✓ Current node is manager${NC}"
}

# Function to verify all nodes
verify_nodes() {
    echo -e "${YELLOW}[2/5] Verifying cluster nodes...${NC}"
    
    echo -e "${BLUE}Cluster Nodes:${NC}"
    docker node ls --format "table {{.Hostname}}\t{{.Status}}\t{{.Availability}}\t{{.ManagerStatus}}"
    
    # Count ready nodes
    READY_NODES=$(docker node ls | grep -c "Ready" || true)
    
    if [ "$READY_NODES" -lt 1 ]; then
        echo -e "${RED}✗ Not enough nodes in cluster${NC}"
        echo -e "${YELLOW}Please join RPi and Jetson to swarm first:${NC}"
        echo "  On RPi: docker swarm join --token <TOKEN> ${SERVER_IP}:2377"
        echo "  On Jetson: docker swarm join --token <TOKEN> ${SERVER_IP}:2377"
        return 1
    fi
    
    echo -e "${GREEN}✓ Cluster has ${READY_NODES} ready nodes${NC}"
}

# Function to build images
build_images() {
    echo -e "${YELLOW}[3/5] Building Docker images...${NC}"
    
    echo -e "${BLUE}Building RPI image: ${RPI_IMAGE}:${RPI_IMAGE_TAG}...${NC}"
    docker build -t "${RPI_IMAGE}:${RPI_IMAGE_TAG}" ./rpi
    echo -e "${GREEN}✓ RPI image built${NC}"
    
    echo -e "${BLUE}Building Jetson image: ${JETSON_IMAGE}:${JETSON_IMAGE_TAG}...${NC}"
    docker build -t "${JETSON_IMAGE}:${JETSON_IMAGE_TAG}" ./jetson
    echo -e "${GREEN}✓ Jetson image built${NC}"
    
    echo -e "${BLUE}Building Server image: ${SERVER_IMAGE}...${NC}"
    docker build -t "${SERVER_IMAGE}:latest" ./server
    echo -e "${GREEN}✓ Server image built${NC}"
}

# Function to push images to registry
push_images() {
    echo -e "${YELLOW}[4/5] Pushing images to registry...${NC}"
    
    echo -e "${BLUE}Tagging and pushing RPI image...${NC}"
    docker tag "${RPI_IMAGE}:${RPI_IMAGE_TAG}" "localhost:${SERVER_REGISTRY_PORT}/${RPI_IMAGE}:${RPI_IMAGE_TAG}"
    docker push "localhost:${SERVER_REGISTRY_PORT}/${RPI_IMAGE}:${RPI_IMAGE_TAG}"
    echo -e "${GREEN}✓ RPI image pushed${NC}"
    
    echo -e "${BLUE}Tagging and pushing Jetson image...${NC}"
    docker tag "${JETSON_IMAGE}:${JETSON_IMAGE_TAG}" "localhost:${SERVER_REGISTRY_PORT}/${JETSON_IMAGE}:${JETSON_IMAGE_TAG}"
    docker push "localhost:${SERVER_REGISTRY_PORT}/${JETSON_IMAGE}:${JETSON_IMAGE_TAG}"
    echo -e "${GREEN}✓ Jetson image pushed${NC}"
    
    echo -e "${BLUE}Tagging and pushing Server image...${NC}"
    docker tag "${SERVER_IMAGE}:latest" "localhost:${SERVER_REGISTRY_PORT}/${SERVER_IMAGE}:latest"
    docker push "localhost:${SERVER_REGISTRY_PORT}/${SERVER_IMAGE}:latest"
    echo -e "${GREEN}✓ Server image pushed${NC}"
}

# Function to deploy stack
deploy_stack() {
    echo -e "${YELLOW}[5/5] Deploying Docker Stack...${NC}"
    
    # Create/update stack
    echo -e "${BLUE}Deploying robotos stack...${NC}"
    docker stack deploy -c docker-stack.yml robotos
    
    echo -e "${GREEN}✓ Stack deployed${NC}"
    
    # Wait for services to start
    sleep 5
    
    # Show service status
    echo -e "${BLUE}Service Status:${NC}"
    docker service ls --format "table {{.Name}}\t{{.Mode}}\t{{.Replicas}}\t{{.Image}}"
    
    echo ""
    echo -e "${BLUE}Service Details:${NC}"
    docker stack ps robotos --format "table {{.Name}}\t{{.Node}}\t{{.CurrentState}}\t{{.DesiredState}}"
}

# Function to verify deployment
verify_deployment() {
    echo -e "${BLUE}Verifying deployment...${NC}"
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}   Deployment Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    
    echo -e "${BLUE}Access Points:${NC}"
    echo "  • Web Dashboard: http://${SERVER_IP}:8080"
    echo "  • Portainer: http://${SERVER_IP}:9000"
    echo "  • Docker Registry: ${SERVER_IP}:${SERVER_REGISTRY_PORT}"
    echo ""
    
    echo -e "${BLUE}Useful Commands:${NC}"
    echo "  • View stack services: docker stack ls"
    echo "  • View service status: docker service ls"
    echo "  • View service logs: docker service logs robotos_<service>"
    echo "  • View stack tasks: docker stack ps robotos"
    echo "  • Update stack: docker stack deploy -c docker-stack.yml robotos"
    echo "  • Remove stack: docker stack rm robotos"
    echo "  • Registry images: curl http://localhost:${SERVER_REGISTRY_PORT}/v2/_catalog"
    echo ""
    
    echo -e "${BLUE}Monitoring Services:${NC}"
    echo "  Server (miniPC):"
    docker service ps robotos_server --format "  {{.Name}} - {{.CurrentState}} on {{.Node}}"
    
    echo "  RPi:"
    docker service ps robotos_rpi --format "  {{.Name}} - {{.CurrentState}} on {{.Node}}" 2>/dev/null || echo "  (Waiting to start...)"
    
    echo "  Jetson:"
    docker service ps robotos_jetson --format "  {{.Name}} - {{.CurrentState}} on {{.Node}}" 2>/dev/null || echo "  (Waiting to start...)"
}

# Main execution
main() {
    check_swarm || exit 1
    verify_nodes || exit 1
    
    read -p "Build and push images? [Y/n]: " build_choice
    if [[ ! "$build_choice" =~ ^[Nn]$ ]]; then
        build_images
        push_images
    fi
    
    read -p "Deploy Docker Stack? [Y/n]: " deploy_choice
    if [[ ! "$deploy_choice" =~ ^[Nn]$ ]]; then
        deploy_stack
    fi
    
    verify_deployment
}

main
