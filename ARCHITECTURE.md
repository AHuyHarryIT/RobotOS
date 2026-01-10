# 3-Tier Architecture Implementation Guide

## Overview

The system now uses a **3-tier architecture** where the miniPC client acts as the central brain:

```
┌─────────────────┐
│  Jetson Nano    │  Vision System
│  Vision Client  │  - Camera processing
└────────┬────────┘  - Lane detection
         │           - Object detection
         │ ZMQ REQ (port 5557)
         │ Commands: left, right, stop, forward, etc.
         ▼
┌─────────────────┐
│  miniPC Client  │  BRAIN / CENTRAL HUB
│  (x86 Linux)    │  - Command server (receives from Jetson)
│                 │  - Xbox controller input
│  Command Server │  - Sequence mode (manual)
│  + Controller   │  - Decision logic
│  + Sequence     │  - Command forwarding
└────────┬────────┘
         │ ZMQ REQ (port 5555)
         │ Unified commands to executor
         ▼
┌─────────────────┐
│  Raspberry Pi   │  GPIO EXECUTOR
│  Server         │  - Motion control
│                 │  - GPIO pin management
│  GPIO Driver    │  - Thread-safe execution
└────────┬────────┘
         │ GPIO pins: 17, 27, 22
         ▼
┌─────────────────┐
│  3-Pin Relay    │
│  RC Car Motors  │
└─────────────────┘
```

## Key Architectural Benefits

1. **Separation of Concerns:**
   - Jetson: Vision processing only
   - Client: Decision-making and coordination
   - RPi: Hardware control only

2. **Multiple Input Sources:**
   - Autonomous mode (Jetson vision)
   - Manual mode (Xbox controller)
   - Debug mode (Sequence commands)
   - All can coexist without conflicts

3. **Centralized Control:**
   - All commands flow through client brain
   - Easier to add new input sources
   - Unified command validation and logging

## Communication Flow

### Jetson → Client
```python
# On Jetson
from vision_client import VisionClient
client = VisionClient()
client.connect()
client.send_command("left 0.3")  # Sends to miniPC:5557
```

### Client → RPi
```python
# Client automatically forwards to RPi
# command_server.py receives from Jetson
# zmq_client.py sends to RPi:5555
```

### RPi Execution
```python
# RPi receives command
# zmq_server.py parses and executes
# gpio_driver.py controls pins
```

## Setup Instructions

### 1. Deploy Client (miniPC)
```bash
# On miniPC
cd /path/to/RobotOS
cp .env.example .env
nano .env  # Configure RPI_HOST, CLIENT_IP, etc.

# Build and run
docker-compose -f server/docker-compose.yml up -d

# Or run locally for testing
cd server/
python3 main.py
```

### 2. Deploy RPi Server
```bash
# From miniPC (uses auto deployment)
./setup_auto_bot.sh

# Or manually on RPi
cd rpi/
sudo python3 app.py  # For testing
```

### 3. Setup Jetson
```bash
# On Jetson
cd jetson/
cp .env.example .env
nano .env  # Set CLIENT_IP to miniPC address

# Install dependencies
pip3 install -r requirements.txt

# Test connection
python3 vision_client.py interactive
```

## Testing the System

### Test 1: Client → RPi Connection
```bash
# On miniPC
cd server/
python3 main.py

# Choose mode 1 (Sequence mode)
# Try: forward 1
# Try: stop
```

### Test 2: Jetson → Client → RPi Chain
```bash
# On Jetson
python3 vision_client.py demo

# Should see:
# [VISION] Connected to client at tcp://192.168.10.100:5557
# [VISION] -> Sending: 'stop'
# [VISION] <- Reply: {'status': 'ok', 'forwarded': True}
```

### Test 3: Parallel Control (Advanced)
```bash
# Terminal 1 (miniPC): Run client with controller mode
python3 main.py
# Choose mode 2 (Controller)

# Terminal 2 (Jetson): Send vision commands
python3 vision_client.py interactive
vision> left

# Both should work! Client processes both sources
```

## Troubleshooting

### Issue: Jetson can't connect to client
```bash
# Check 1: Is client running?
docker ps  # Or ps aux | grep python

# Check 2: Can Jetson reach miniPC?
ping 192.168.10.100

# Check 3: Is port open?
nc -zv 192.168.10.100 5557

# Check 4: Firewall rules
sudo ufw allow 5557/tcp
```

### Issue: Commands not executing on car
```bash
# Check 1: Is RPi server running?
ssh pi@192.168.31.211
docker ps

# Check 2: Check client → RPi connection
# On miniPC client logs
docker logs auto-bot-client

# Check 3: Check RPi logs
ssh pi@192.168.31.211
docker logs auto-bot-rpi
```

### Issue: Multiple command sources conflicting
This should **NOT** happen because:
- Client uses a single ZMQ REQ socket to RPi (thread-safe)
- RPi server processes commands sequentially
- Each new command cancels the previous motion

If issues occur:
- Check for timing issues (commands too frequent)
- Add cooldown in Jetson vision loop
- Check client logs for errors

## Performance Tuning

### Vision Loop Frequency
```python
# In your Jetson calibration code
while True:
    ret, frame = cap.read()
    direction = detect_lane(frame)
    
    vision_client.send_command(direction)
    time.sleep(0.1)  # 10Hz max rate (adjust as needed)
```

### Client Cooldown
```python
# client/config.py
SEND_COOLDOWN = 0.05  # Minimum time between RPi commands
```

### RPi Motion Interruption
```python
# rpi/states.py
DEFAULT_STEP_DURATION = 0.5  # Command execution time
PAUSE_AFTER_SEQ_SECONDS = 0.2  # Pause after sequence
```

## Development Workflow

### Adding New Command Sources
1. Create new module (e.g., `web_server.py`)
2. Import `send_command` from `zmq_client`
3. Call `send_command(sock, "your_command")`
4. Client will automatically forward to RPi

### Modifying Command Processing
- **Client-side logic**: Edit `command_server.py` line 30-40
- **RPi-side execution**: Edit `rpi/zmq_server.py` `handle_payload()`

## Next Steps

1. **Integrate vision code**: Move calibration logic from `trash_code/` to `jetson/`
2. **Add decision logic**: Enhance `command_server.py` with filtering/validation
3. **Add logging**: Track all commands for debugging
4. **Add web UI**: Create HTTP server that sends commands via `zmq_client`
5. **Add safety checks**: Emergency stop on vision loss, timeouts, etc.
