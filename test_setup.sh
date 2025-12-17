#!/bin/bash
# Test script for 3-tier architecture

echo "=================================="
echo "  3-Tier Architecture Test Suite"
echo "=================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load environment
if [ ! -f .env ]; then
    echo -e "${RED}✗ .env file not found${NC}"
    echo "  Copy .env.example to .env and configure it"
    exit 1
fi

source .env

echo -e "${GREEN}✓ Environment loaded${NC}"
echo ""

# Test 1: Check required directories
echo "Test 1: Directory Structure"
for dir in client rpi jetson; do
    if [ -d "$dir" ]; then
        echo -e "  ${GREEN}✓${NC} $dir/ exists"
    else
        echo -e "  ${RED}✗${NC} $dir/ missing"
    fi
done
echo ""

# Test 2: Check Python files
echo "Test 2: Core Python Files"
files=(
    "server/main.py"
    "server/command_server.py"
    "server/zmq_client.py"
    "rpi/zmq_server.py"
    "rpi/gpio_driver.py"
    "jetson/vision_client.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✓${NC} $file"
    else
        echo -e "  ${RED}✗${NC} $file missing"
    fi
done
echo ""

# Test 3: Check configurations
echo "Test 3: Configuration Files"
if [ -f "server/config.py" ] && grep -q "SERVER_PORT" server/config.py; then
    echo -e "  ${GREEN}✓${NC} Server config has SERVER_PORT"
else
    echo -e "  ${RED}✗${NC} Server config missing SERVER_PORT"
fi

if [ -f "jetson/.env.example" ]; then
    echo -e "  ${GREEN}✓${NC} Jetson .env.example exists"
else
    echo -e "  ${RED}✗${NC} Jetson .env.example missing"
fi
echo ""

# Test 4: Check dependencies
echo "Test 4: Python Dependencies"
if python3 -c "import zmq" 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} pyzmq installed"
else
    echo -e "  ${YELLOW}!${NC} pyzmq not installed (pip3 install pyzmq)"
fi

if python3 -c "import dotenv" 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} python-dotenv installed"
else
    echo -e "  ${YELLOW}!${NC} python-dotenv not installed (pip3 install python-dotenv)"
fi
echo ""

# Test 5: Network connectivity (if IPs configured)
echo "Test 5: Network Connectivity"
if [ -n "$RPI_IP" ]; then
    if ping -c 1 -W 2 "$RPI_IP" &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} RPi reachable at $RPI_IP"
    else
        echo -e "  ${YELLOW}!${NC} Cannot reach RPi at $RPI_IP"
    fi
else
    echo -e "  ${YELLOW}!${NC} RPI_IP not configured in .env"
fi

if [ -n "$SERVER_IP" ]; then
    echo -e "  ${GREEN}✓${NC} SERVER_IP configured: $SERVER_IP"
else
    echo -e "  ${YELLOW}!${NC} SERVER_IP not configured in .env"
fi
echo ""

# Test 6: Port configuration
echo "Test 6: Port Configuration"
echo "  ZMQ_PORT:           ${ZMQ_PORT:-'not set'}"
echo "  HEARTBEAT_PORT:     ${HEARTBEAT_PORT:-'not set'}"
echo "  SERVER_PORT: ${SERVER_PORT:-'not set (should be 5557)'}"
echo ""

# Test 7: Documentation
echo "Test 7: Documentation Files"
docs=(
    "README.md"
    "QUICKSTART.md"
    "ARCHITECTURE.md"
    "DIAGRAM.md"
    "jetson/README.md"
)

for doc in "${docs[@]}"; do
    if [ -f "$doc" ]; then
        echo -e "  ${GREEN}✓${NC} $doc"
    else
        echo -e "  ${RED}✗${NC} $doc missing"
    fi
done
echo ""

# Summary
echo "=================================="
echo "  Test Complete"
echo "=================================="
echo ""
echo "Next Steps:"
echo "1. Configure .env file with correct IPs"
echo "2. Deploy RPi: ./setup_auto_bot.sh"
echo "3. Start client: cd server/ && python3 main.py"
echo "4. Setup Jetson: cd jetson/ && cp .env.example .env"
echo ""
echo "For more info, see QUICKSTART.md"
