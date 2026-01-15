# Quick Start Guide

## 🎯 System Architecture Summary

```
Jetson (Vision) → miniPC Client (Brain) → RPi (GPIO Executor) → Car
     Port 5557          Port 5555           GPIO 17,27,22
```

## ⚡ 5-Minute Setup

### Step 1: Configure Environment
```bash
cd /home/mobileos/autocar/RobotOS
cp .env.example .env
nano .env
```

Set these critical values:
- `RPI_HOST=192.168.x.x` - Raspberry Pi IP address
- `CLIENT_IP=192.168.x.x` - miniPC server IP (for Jetson to connect)
- `JETSON_HOST=192.168.x.x` - Jetson IP address
- `ZMQ_PORT=5555` - Port for server ↔ RPi communication

### Step 2: Deploy System
```bash
# Deploy everything (Docker install + RPi setup + Server setup)
chmod +x setup_auto_bot.sh
./setup_auto_bot.sh

# Or deploy manually
chmod +x auto_update.sh
./auto_update.sh
```

### Step 3: Start Server
```bash
cd server/
python3 main.py

# Select mode:
# 1. Web Dashboard
# 2. Controller Mode (Xbox)
# 3. Sequence Mode (Text commands)
# 4. Server Only (Jetson autonomous)
```

### Step 4: Test Jetson Connection
```bash
# On Jetson, test vision client
cd jetson/
python3 vision_client.py

# Send test command
# forward
# stop
```

## 📋 Operating Modes

### Mode 1: Web Dashboard (Recommended)
- Real-time visualization
- Command history
- RPi status monitoring
- Web-based interface at `localhost:8080`

### Mode 2: Controller Mode (Xbox)
- D-pad: Movement (up/down/left/right)
- A: Unlock, B: Lock, X: Stop, Y: Demo
- Hold-to-repeat with 150ms interval
- Immediate response

### Mode 3: Sequence Mode (Manual Commands)
- Text-based command entry
- Single commands: `forward 2`, `left 0.5`, `stop`
- Sequences: `seq forward 2; right 1; lock 0.5; stop`
- **Full calibration support** - Jetson can pause forward motion

### Mode 4: Server Only (Autonomous)
- No manual input
- Accepts only Jetson commands
- Pure vision-based control

## 🎮 Common Commands

| Command | Description | Duration | Pausable? |
|---------|-------------|----------|-----------|
| `forward [s]` | Move forward | seconds | ✅ Yes |
| `backward [s]` | Move backward | seconds | ✅ Yes |
| `left [s]` | Turn left | seconds | ❌ No |
| `right [s]` | Turn right | seconds | ❌ No |
| `lock [s]` | Parking brake | seconds | ✅ Yes |
| `unlock [s]` | Release brake | seconds | ✅ Yes |
| `sleep [s]` | Pause | seconds | ✅ Yes |
| `stop` | Emergency stop | immediate | - |

### Sequence Examples
```bash
# Simple forward motion
seq forward 2; stop

# Navigate: forward, turn right, forward again
seq forward 1.5; right 0.3; forward 1; stop

# Complex with brake
seq forward 2; lock 0.5; backward 1; unlock 0.3; stop

# Jetson will pause during forward motion for calibration
seq forward 5; right 0.5; forward 2; stop
```

## 🐳 Docker Deployment (from miniPC)

### Build Jetson Image
```bash
cd jetson/
./jetson_docker.sh build
```

### Run CI/CD Pipeline
```bash
./jetson_docker.sh ci

# Or collect test reports
./jetson_docker.sh ci --collect-reports
```

### Deploy to Jetson
```bash
./jetson_docker.sh deploy
```

### Monitor Logs
```bash
./jetson_docker.sh logs --follow
```

### Container Management
```bash
./jetson_docker.sh start          # Start container
./jetson_docker.sh stop           # Stop container
./jetson_docker.sh restart        # Restart
./jetson_docker.sh status         # Check status
./jetson_docker.sh shell          # SSH into container
```

## 🧪 Quick Testing

### Test 1: Check Connectivity
```bash
# From miniPC, verify RPi is reachable
ping $RPI_HOST

# From miniPC, verify Jetson will connect
ping $JETSON_HOST

# From Jetson, verify miniPC is reachable
ping $CLIENT_IP
```

### Test 2: Test Direct Motion (RPi)
```bash
# SSH into RPi and test GPIO directly
ssh pi@$RPI_HOST
cd auto-bot-rpi
sudo python3 app.py "forward 1"

# If car moves, GPIO is working
```

### Test 3: Test Server ↔ RPi Communication
```bash
# Terminal 1: Start server
cd server && python3 main.py
# Select: 3 (Sequence Mode)

# Terminal 2: Send command via sequence mode
# seq> seq forward 1; stop
# If car moves, ZMQ communication is working
```

### Test 4: Test Jetson → Server Communication
```bash
# Terminal 1: Start server in Server Only mode
cd server && python3 main.py
# Select: 4 (Server Only)

# Terminal 2: Send command from Jetson
cd jetson
python3 -c "
from vision_client import VisionClient
client = VisionClient()
client.connect()
client.send_command('forward 2')
"

# If car moves, Jetson communication is working
```

### Test 5: Test Calibration Pause/Resume
```bash
# Terminal 1: Start server in Sequence Mode
cd server && python3 main.py
# Select: 3 (Sequence Mode)

# Terminal 2: Start sequence that takes time
# seq> seq forward 5; stop
# (This will run for 5 seconds)

# Terminal 3: Send calibration pause at ~1 second
python3 -c "
from jetson.vision_client_calibration_example import VisionClientWithCalibration
client = VisionClientWithCalibration()
client.connect()
client.request_calibration_pause('forward', elapsed=1.0, total=5.0)
# Wait 1 second for calibration
import time
time.sleep(1.0)
client.signal_calibration_complete()
"

# Expected: Car pauses, then resumes for remaining 4 seconds
```

## 🔧 Troubleshooting

### Issue: Server can't reach RPi
```bash
# 1. Check RPi IP is correct in .env
cat .env | grep RPI_HOST

# 2. Ping RPi
ping $RPI_HOST

# 3. Check firewall on RPi
ssh pi@$RPI_HOST
sudo ufw allow 5555/tcp
sudo ufw allow 5556/udp

# 4. Restart RPi Docker container
ssh pi@$RPI_HOST
docker restart auto-bot-rpi
```

### Issue: Jetson can't reach Server
```bash
# 1. Check SERVER IP is correct on Jetson
cat jetson/.env | grep CLIENT_IP

# 2. Ping from Jetson
ssh jetson@$JETSON_HOST
ping $CLIENT_IP

# 3. Check server firewall
sudo ufw allow 5557/tcp

# 4. Restart server
cd server && python3 main.py
```

### Issue: Car doesn't move
```bash
# 1. Check RPi GPIO is accessible
ssh pi@$RPI_HOST
python3 -c "import RPi.GPIO; print('GPIO OK')"

# 2. Test GPIO directly
sudo python3 app.py "forward 1"

# 3. Check motor power supply
# (Verify 5V power to relay board)

# 4. Check GPIO pins (BCM 17, 27, 22)
gpio readall
```

### Issue: Commands sent but no response
```bash
# 1. Check RPi heartbeat
# In server logs, look for "[HEARTBEAT]"

# 2. Check ZMQ ports
ss -tlnp | grep 5555

# 3. Verify .env propagation
# All three (.env, server/.env, rpi/.env) should match

# 4. Check server logs
cd server && python3 main.py 2>&1 | tee server.log
```

## 📚 Next Steps

- **Calibration Integration**: See [docs/CALIBRATION.md](CALIBRATION.md)
- **Docker Deployment**: See [docs/DEPLOYMENT.md](DEPLOYMENT.md)
- **Architecture Details**: See [docs/ARCHITECTURE.md](ARCHITECTURE.md)
- **Web Dashboard**: See [docs/DASHBOARD.md](DASHBOARD.md)

## 🆘 Need Help?

1. Check the relevant guide in the `docs/` folder
2. Review logs in `output/logs/`
3. Test connectivity between systems
4. Verify `.env` configuration matches your network
5. Check GPIO pins are correctly connected

---

**Quick Reference**: [Architecture](ARCHITECTURE.md) | [Calibration](CALIBRATION.md) | [Deployment](DEPLOYMENT.md) | [Dashboard](DASHBOARD.md)
