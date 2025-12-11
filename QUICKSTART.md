# Quick Start Guide - 3-Tier Architecture

## 🎯 Architecture Summary

```
Jetson (Vision) → miniPC Client (Brain) → RPi (GPIO Executor) → Car
     Port 5557          Port 5555           GPIO 17,27,22
```

## 🚀 Quick Setup

### 1️⃣ Configure Environment
```bash
cp .env.example .env
nano .env
```
Set these values:
- `RPI_HOST` - RPi IP address
- `CLIENT_IP` - miniPC IP address (for Jetson to connect)

### 2️⃣ Deploy Everything
```bash
# Deploy RPi server
./setup_auto_bot.sh

# Start miniPC client
cd client/
python3 client_main.py
```

### 3️⃣ Test Jetson Connection
```bash
# On Jetson
cd jetson/
cp .env.example .env
nano .env  # Set CLIENT_IP
python3 vision_client.py interactive
```

## 📋 Usage Modes

### Client Menu Options
```
1. Sequence mode    - Manual text commands
2. Controller mode  - Xbox gamepad control
3. Server only mode - Only receive from Jetson (autonomous)
q. Quit
```

### Jetson Commands
```python
from vision_client import VisionClient
client = VisionClient()
client.connect()

# Send commands
client.send_command("left")
client.send_command("right 0.5")
client.send_command("stop")
client.send_command("seq forward 1; right 0.5; stop")
```

## 🔧 Common Commands

| Command | Description | Example |
|---------|-------------|---------|
| `forward [dur]` | Move forward | `forward 2` |
| `backward [dur]` | Move backward | `backward 1.5` |
| `left [dur]` | Turn left | `left 0.3` |
| `right [dur]` | Turn right | `right 0.5` |
| `stop` | Emergency stop | `stop` |
| `lock [dur]` | Parking brake | `lock 0.5` |
| `unlock [dur]` | Release brake | `unlock` |
| `seq ...` | Command sequence | `seq forward 1; right 0.5; stop` |

## 🐛 Quick Troubleshooting

### Jetson can't connect
```bash
ping <CLIENT_IP>
nc -zv <CLIENT_IP> 5557
sudo ufw allow 5557/tcp
```

### Client can't reach RPi
```bash
ping <RPI_HOST>
nc -zv <RPI_HOST> 5555
ssh pi@<RPI_HOST> "docker ps"
```

### Car not moving
```bash
# Check RPi logs
ssh pi@<RPI_HOST>
docker logs auto-bot-rpi

# Test GPIO directly
sudo python3 app.py "forward 1"
```

## 📊 Port Reference

| Port | Direction | Purpose |
|------|-----------|---------|
| 5555 | Client → RPi | Command execution |
| 5556 | RPi → Client | Heartbeat monitoring |
| 5557 | Jetson → Client | Vision commands |

## 🔄 Update After Code Changes

```bash
# Quick redeploy
./auto_update.sh

# Or manually
docker-compose -f client/docker-compose.yml up -d --build
ssh pi@<RPI_HOST> "cd auto-bot-rpi && docker build -t auto-bot-rpi . && docker restart auto-bot-rpi"
```

## 📚 More Information

- Full architecture: `ARCHITECTURE.md`
- Jetson setup: `jetson/README.md`
- Deployment details: `.github/copilot-instructions.md`
