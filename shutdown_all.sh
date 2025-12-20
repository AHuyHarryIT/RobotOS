#!/usr/bin/env bash

# RobotOS Complete Shutdown Script
# Gracefully stops all components: RPi, Server, and optionally physical devices

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

SERVER_CONTAINER_NAME="${SERVER_CONTAINER_NAME:-robotos-server}"
RPI_CONTAINER_NAME="${RPI_CONTAINER_NAME:-auto-bot-rpi}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   RobotOS Shutdown Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "  RPI_IP: ${RPI_IP}"
echo "  RPI_USER: ${RPI_USER}"
echo "  Server Container: ${SERVER_CONTAINER_NAME}"
echo "  RPi Container: ${RPI_CONTAINER_NAME}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Prepare SSH command prefix (with or without password)
if [ -n "${RPI_PASSWORD:-}" ] && command_exists sshpass; then
    SSH_CMD="sshpass -p '${RPI_PASSWORD}' ssh"
else
    SSH_CMD="ssh"
fi

# Step 1: Send stop command to robot (safety first)
stop_robot() {
    echo -e "${YELLOW}[1/5] Sending STOP command to robot...${NC}"
    
    # Try to send stop command via server API if available
    if curl -sf http://localhost:5000/api/health > /dev/null 2>&1; then
        echo -e "${BLUE}Sending stop command via web API...${NC}"
        curl -X POST http://localhost:5000/api/command \
             -H "Content-Type: application/json" \
             -d '{"command":"stop"}' 2>/dev/null || true
        sleep 1
        echo -e "${GREEN}✓ Stop command sent${NC}"
    else
        echo -e "${YELLOW}⚠ Server not responding, skipping stop command${NC}"
    fi
}

# Step 2: Stop RPi container
stop_rpi_container() {
    echo -e "${YELLOW}[2/5] Stopping RPi container...${NC}"
    
    # Check SSH connectivity
    if ! ${SSH_CMD} -o ConnectTimeout=5 "${RPI_USER}@${RPI_IP}" exit 2>/dev/null; then
        echo -e "${YELLOW}⚠ Cannot connect to RPi via SSH, skipping RPi shutdown${NC}"
        return 1
    fi
    
    echo -e "${BLUE}Stopping container on RPi...${NC}"
    ${SSH_CMD} "${RPI_USER}@${RPI_IP}" bash -s <<EOF
set -e

if sudo docker ps | grep -q "${RPI_CONTAINER_NAME}"; then
    echo "[RPI] Stopping container ${RPI_CONTAINER_NAME}..."
    sudo docker stop "${RPI_CONTAINER_NAME}" -t 10 || true
    echo "[RPI] Container stopped"
else
    echo "[RPI] Container ${RPI_CONTAINER_NAME} not running"
fi
EOF
    
    echo -e "${GREEN}✓ RPi container stopped${NC}"
}

# Step 3: Stop server container
stop_server_container() {
    echo -e "${YELLOW}[3/5] Stopping server container...${NC}"
    
    if docker ps | grep -q "${SERVER_CONTAINER_NAME}"; then
        echo -e "${BLUE}Stopping server container...${NC}"
        (
            cd server
            docker compose down || docker stop "${SERVER_CONTAINER_NAME}" -t 10 || true
        )
        echo -e "${GREEN}✓ Server container stopped${NC}"
    else
        echo -e "${YELLOW}⚠ Server container not running${NC}"
    fi
}

# Step 4: Optional - shutdown physical devices
shutdown_physical_devices() {
    echo -e "${YELLOW}[4/5] Physical device shutdown...${NC}"
    
    read -p "Shutdown Raspberry Pi physically? [y/N]: " shutdown_rpi_choice
    
    if [[ "$shutdown_rpi_choice" =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Initiating RPi shutdown...${NC}"
        ${SSH_CMD} "${RPI_USER}@${RPI_IP}" "sudo shutdown -h now" 2>/dev/null || true
        echo -e "${GREEN}✓ RPi shutdown command sent${NC}"
    else
        echo -e "${YELLOW}⚠ RPi physical shutdown skipped${NC}"
    fi
}

# Step 5: Verify shutdown
verify_shutdown() {
    echo -e "${YELLOW}[5/5] Verifying shutdown...${NC}"
    
    # Check server container
    if docker ps | grep -q "${SERVER_CONTAINER_NAME}"; then
        echo -e "${RED}✗ Server container still running${NC}"
    else
        echo -e "${GREEN}✓ Server container stopped${NC}"
    fi
    
    # Show remaining containers
    local running_containers=$(docker ps --format "{{.Names}}" | wc -l)
    if [ "$running_containers" -gt 0 ]; then
        echo -e "\n${BLUE}Running containers:${NC}"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    else
        echo -e "${GREEN}✓ No containers running${NC}"
    fi
    
    echo ""
}

# Main execution
main() {
    echo -e "${YELLOW}⚠ WARNING: This will stop all RobotOS components${NC}"
    read -p "Continue? [y/N]: " confirm
    
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Shutdown cancelled${NC}"
        exit 0
    fi
    
    echo ""
    
    # Execute shutdown sequence
    stop_robot || echo -e "${YELLOW}⚠ Could not send stop command${NC}"
    sleep 1
    
    stop_rpi_container || echo -e "${YELLOW}⚠ RPi container shutdown incomplete${NC}"
    sleep 1
    
    stop_server_container
    sleep 1
    
    shutdown_physical_devices
    
    verify_shutdown
    
    # Final summary
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}   Shutdown Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}System Status:${NC}"
    echo "  • Server containers: stopped"
    echo "  • RPi containers: stopped"
    echo "  • Robot: stopped"
    echo ""
    echo -e "${BLUE}To restart:${NC}"
    echo "  • Run: ./setup_auto_bot.sh (full setup)"
    echo "  • Or:  ./auto_update.sh (quick redeploy)"
    echo ""
}

# Run main function
main
