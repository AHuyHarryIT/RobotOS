#!/usr/bin/env bash

# Check Xbox Controller Connection Status
# Shows controller status on both host and inside Docker container

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Xbox Controller Status Check${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check host system
echo -e "${YELLOW}[1/4] Checking host system...${NC}"
echo ""

# Check if user is in input group
if groups | grep -q input; then
    echo -e "${GREEN}✓ User is in 'input' group${NC}"
else
    echo -e "${RED}✗ User is NOT in 'input' group${NC}"
    echo -e "${YELLOW}  Run: sudo usermod -aG input \$USER${NC}"
    echo -e "${YELLOW}  Then logout and login again${NC}"
fi

# Check input devices
echo ""
echo -e "${BLUE}Host /dev/input devices:${NC}"
ls -la /dev/input/ | grep -E "event|js" || echo "No input devices found"

# Check for Xbox controller specifically
echo ""
if ls /dev/input/by-id/*joystick 2>/dev/null | grep -iq "xbox\|360\|shanwan"; then
    CONTROLLER_PATH=$(ls /dev/input/by-id/*joystick 2>/dev/null | grep -i "xbox\|360\|shanwan" | head -1)
    echo -e "${GREEN}✓ Xbox controller found: ${CONTROLLER_PATH}${NC}"
    
    # Show details
    CONTROLLER_NAME=$(basename "$CONTROLLER_PATH")
    REAL_DEVICE=$(readlink -f "$CONTROLLER_PATH")
    echo -e "  Device: ${REAL_DEVICE}"
    ls -l "$REAL_DEVICE"
else
    echo -e "${RED}✗ No Xbox controller found${NC}"
    echo -e "${YELLOW}  Please connect your Xbox controller via USB${NC}"
fi

# Check Docker container
echo ""
echo -e "${YELLOW}[2/4] Checking Docker container...${NC}"
echo ""

CONTAINER_NAME="robotos-server"

if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${RED}✗ Container '${CONTAINER_NAME}' is not running${NC}"
    echo -e "${YELLOW}  Start it with: cd server && docker compose up -d${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Container is running${NC}"

# Check container /dev/input
echo ""
echo -e "${BLUE}Container /dev/input devices:${NC}"
sudo docker exec "$CONTAINER_NAME" ls -la /dev/input/ 2>&1 | grep -E "event|js" || echo "No input devices visible in container"

# Check if controller is accessible in container
echo ""
if sudo docker exec "$CONTAINER_NAME" test -e /dev/input/js0 2>/dev/null; then
    echo -e "${GREEN}✓ Joystick device /dev/input/js0 is accessible in container${NC}"
    sudo docker exec "$CONTAINER_NAME" ls -l /dev/input/js0
else
    echo -e "${RED}✗ Joystick device /dev/input/js0 NOT accessible in container${NC}"
fi

# Test pygame detection
echo ""
echo -e "${YELLOW}[3/4] Testing pygame controller detection...${NC}"
echo ""

PYGAME_TEST=$(sudo docker exec "$CONTAINER_NAME" python3 -c "
import pygame
pygame.init()
pygame.joystick.init()
count = pygame.joystick.get_count()
if count > 0:
    joy = pygame.joystick.Joystick(0)
    joy.init()
    print(f'FOUND:{joy.get_name()}')
else:
    print('NOT_FOUND')
" 2>&1)

if echo "$PYGAME_TEST" | grep -q "FOUND:"; then
    CONTROLLER_NAME=$(echo "$PYGAME_TEST" | grep "FOUND:" | cut -d: -f2)
    echo -e "${GREEN}✓ pygame detected controller: ${CONTROLLER_NAME}${NC}"
else
    echo -e "${RED}✗ pygame could NOT detect controller${NC}"
    echo -e "${YELLOW}  Error output:${NC}"
    echo "$PYGAME_TEST"
fi

# Check health API
echo ""
echo -e "${YELLOW}[4/4] Checking API health endpoint...${NC}"
echo ""

if curl -sf http://localhost:5000/api/health > /dev/null 2>&1; then
    HEALTH_JSON=$(curl -s http://localhost:5000/api/health)
    echo -e "${GREEN}✓ API is responding${NC}"
    echo ""
    echo -e "${BLUE}Controller status from API:${NC}"
    echo "$HEALTH_JSON" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_JSON"
else
    echo -e "${RED}✗ API not responding on http://localhost:5000${NC}"
fi

# Summary and recommendations
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Summary & Recommendations${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if echo "$PYGAME_TEST" | grep -q "FOUND:"; then
    echo -e "${GREEN}✓ Controller is working correctly!${NC}"
    echo ""
    echo "You can now use controller mode from the main menu."
else
    echo -e "${YELLOW}⚠ Controller not detected in Docker${NC}"
    echo ""
    echo -e "${BLUE}Try these steps:${NC}"
    echo ""
    echo "1. Add user to input group (if not already):"
    echo "   ${YELLOW}sudo usermod -aG input \$USER${NC}"
    echo "   Then logout and login"
    echo ""
    echo "2. Restart the container with updated permissions:"
    echo "   ${YELLOW}cd server && docker compose down && docker compose up -d${NC}"
    echo ""
    echo "3. If controller was connected after container started:"
    echo "   ${YELLOW}Unplug and replug the USB controller${NC}"
    echo "   ${YELLOW}Then restart container: docker compose restart${NC}"
    echo ""
    echo "4. Check docker-compose.yml has these lines:"
    echo "   ${YELLOW}devices:${NC}"
    echo "   ${YELLOW}  - \"/dev/input:/dev/input\"${NC}"
    echo "   ${YELLOW}group_add:${NC}"
    echo "   ${YELLOW}  - \"input\"${NC}"
    echo ""
fi

echo -e "${BLUE}For more help, see: ${NC}${YELLOW}SCRIPTS_GUIDE.md${NC}"
echo ""
