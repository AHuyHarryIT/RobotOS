# RobotOS - 3-Tier Autonomous RC Car Control System

![Architecture](https://img.shields.io/badge/Architecture-3--Tier-blue)
![Python](https://img.shields.io/badge/Python-3.8+-green)
![ZeroMQ](https://img.shields.io/badge/ZeroMQ-Latest-red)
![GPIO](https://img.shields.io/badge/GPIO-BCM-yellow)

## 🎯 Overview

A distributed robotics control system for an RC car with **three-tier architecture**:

```
┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
│  Jetson  │─────▶│  Client  │─────▶│   RPi    │─────▶│  RC Car  │
│  Vision  │      │  (Brain) │      │ Executor │      │  Motors  │
└──────────┘      └──────────┘      └──────────┘      └──────────┘
   Camera            Multiple           GPIO           3-Pin Relay
  Processing          Sources          Control            Board
```

### Key Features

- **🧠 Central Brain Architecture** - miniPC client coordinates all inputs
- **👁️ Vision-Based Control** - Jetson Nano processes camera for autonomous driving
- **🎮 Manual Override** - Xbox controller for manual control
- **📝 Sequence Mode** - Text-based command sequences for testing
- **🔒 Thread-Safe** - Safe command processing from multiple sources
- **💓 Health Monitoring** - Heartbeat system tracks RPi status
- **🐳 Docker Ready** - Full containerization support

## 📁 Project Structure

```
RobotOS/
├── client/              # miniPC client (Brain)
│   ├── client_main.py      # Main entry point
│   ├── command_server.py   # Receives from Jetson
│   ├── controller_mode.py  # Xbox gamepad control
│   ├── seq_mode.py         # Manual command mode
│   ├── zmq_client.py       # RPi communication
│   └── config.py           # Configuration
├── rpi/                 # Raspberry Pi server (Executor)
│   ├── zmq_server.py       # ZMQ server & motion control
│   ├── gpio_driver.py      # GPIO pin management
│   ├── parser.py           # Command parsing
│   └── states.py           # GPIO state definitions
├── jetson/              # Jetson Nano (Vision)
│   ├── vision_client.py    # Send commands to client
│   ├── calibration.py      # Camera calibration
│   └── README.md           # Jetson setup guide
└── docs/
    ├── QUICKSTART.md       # Quick start guide
    ├── ARCHITECTURE.md     # Full architecture docs
    └── DIAGRAM.md          # System diagrams
```

## 🚀 Quick Start

### 1. Clone and Configure
```bash
git clone https://github.com/AHuyHarryIT/RobotOS.git
cd RobotOS
cp .env.example .env
nano .env  # Set RPI_HOST, CLIENT_IP, etc.
```

### 2. Deploy RPi Server
```bash
./setup_auto_bot.sh
```

### 3. Start Client (Brain)
```bash
cd client/
python3 client_main.py
```

### 4. Setup Jetson (Optional for autonomous mode)
```bash
cd jetson/
cp .env.example .env
nano .env  # Set CLIENT_IP
python3 vision_client.py interactive
```

See [QUICKSTART.md](QUICKSTART.md) for detailed instructions.

## 🎮 Usage Modes

### 1. Sequence Mode (Manual Testing)
```bash
> forward 2
> right 0.5
> stop
> seq forward 1; left 0.3; stop
```

### 2. Controller Mode (Xbox Gamepad)
- **D-Pad**: Movement control
- **A**: Unlock
- **B**: Lock
- **X**: Stop
- **Y**: Demo sequence

### 3. Server Mode (Autonomous via Jetson)
Receives vision-based commands from Jetson:
```python
# On Jetson
from vision_client import VisionClient
client = VisionClient()
client.send_command("left 0.3")
```

## 📡 Network Ports

| Port | Direction | Purpose |
|------|-----------|---------|
| 5555 | Client → RPi | Command execution |
| 5556 | RPi → Client | Heartbeat monitoring |
| 5557 | Jetson → Client | Vision commands |

## 🔧 Commands

| Command | Description | Example |
|---------|-------------|---------|
| `forward [dur]` | Move forward | `forward 2` |
| `backward [dur]` | Move backward | `backward 1.5` |
| `left [dur]` | Turn left | `left 0.3` |
| `right [dur]` | Turn right | `right 0.5` |
| `stop` | Emergency stop | `stop` |
| `lock [dur]` | Parking brake | `lock 0.5` |
| `unlock [dur]` | Release brake | `unlock` |
| `seq ...` | Sequence | `seq forward 1; right 0.5; stop` |

## 🏗️ Architecture

The system uses a **3-tier architecture** where the miniPC client acts as a central brain:

1. **Jetson (Vision Layer)**
   - Processes camera input
   - Detects lanes, objects
   - Sends high-level commands (left, right, stop)

2. **Client (Decision Layer)**
   - Receives from Jetson, Xbox controller, or manual input
   - Coordinates multiple command sources
   - Validates and forwards to RPi

3. **RPi (Execution Layer)**
   - Receives unified commands
   - Controls GPIO pins safely
   - Manages motor states

See [ARCHITECTURE.md](ARCHITECTURE.md) for complete details.

## 🔌 Hardware

- **miniPC** (x86 Linux) - Client brain
- **Raspberry Pi 4** - GPIO controller
- **Jetson Nano** (optional) - Vision processing
- **3-pin relay board** - Motor control
- **RC car** with GPIO-compatible motors
- **Xbox controller** (optional) - Manual control

### GPIO Wiring (BCM Mode)
- **Pin 17** - Control bit 0
- **Pin 27** - Control bit 1
- **Pin 22** - Control bit 2

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 5 minutes
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Complete system design
- **[DIAGRAM.md](DIAGRAM.md)** - Visual diagrams
- **[jetson/README.md](jetson/README.md)** - Jetson setup
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - What changed

## 🐛 Troubleshooting

### Jetson can't connect to client
```bash
ping <CLIENT_IP>
sudo ufw allow 5557/tcp
```

### Client can't reach RPi
```bash
ping <RPI_HOST>
ssh pi@<RPI_HOST> "docker ps"
```

### Car not moving
```bash
ssh pi@<RPI_HOST>
docker logs auto-bot-rpi
```

See [ARCHITECTURE.md](ARCHITECTURE.md) → Troubleshooting for more.

## 🔄 Development

### Quick Redeploy
```bash
./auto_update.sh
```

### Test GPIO Directly
```bash
ssh pi@<RPI_HOST>
cd auto-bot-rpi
sudo python3 app.py "forward 1"
```

### Add New Command Source
```python
from zmq_client import send_command
send_command(sock, "your_command")
```

## 📝 License

MIT License - See LICENSE file for details

## 👥 Contributors

- [AHuyHarryIT](https://github.com/AHuyHarryIT)

## 🙏 Acknowledgments

- ZeroMQ for reliable messaging
- RPi.GPIO for hardware control
- OpenCV for vision processing

---

**Status**: ✅ Production Ready  
**Last Updated**: December 2025  
**Architecture Version**: 3.0 (3-Tier)
