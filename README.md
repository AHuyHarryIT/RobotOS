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
- **🎯 Command Aggregation** - Unified command processing with validation and history
- **👁️ Vision-Based Control** - Jetson Nano processes camera for autonomous driving
- **🎮 Manual Override** - Xbox controller for manual control
- **📝 Sequence Mode** - Text-based command sequences for testing
- **🔒 Thread-Safe** - Safe command processing from multiple sources
- **💓 Health Monitoring** - Heartbeat system tracks RPi status
- **📊 Statistics & Logging** - Real-time command tracking and analytics
- **🐳 Docker Ready** - Full containerization support

## 📁 Project Structure

```
RobotOS/
├── server/              # miniPC server (Brain)
│   ├── main.py                      # Main entry point
│   ├── command_aggregator.py        # Central command processing hub
│   ├── command_server.py            # Receives from Jetson
│   ├── calibration_coordinator.py   # Calibration state machine
│   ├── sequence_executor.py         # Enhanced sequence execution
│   ├── controller_mode.py           # Xbox gamepad control
│   ├── seq_mode.py                  # Manual command mode
│   ├── zmq_client.py                # RPi communication
│   ├── web_dashboard.py             # Web UI
│   ├── config.py                    # Configuration
│   └── docker-compose*.yml          # Docker orchestration
│
├── rpi/                 # Raspberry Pi server (Executor)
│   ├── app.py                       # Main entry point
│   ├── zmq_server.py                # ZMQ server & motion control
│   ├── gpio_driver.py               # GPIO pin management
│   ├── parser.py                    # Command parsing
│   ├── sequencer.py                 # Sequence handling
│   ├── states.py                    # GPIO state definitions
│   └── docker-compose*.yml          # Docker orchestration
│
├── jetson/              # Jetson Nano (Vision)
│   ├── vision_client.py             # Standard vision client
│   ├── vision_client_calibration_example.py
│   ├── calibrate.py                 # Calibration utilities
│   ├── config.py                    # Configuration
│   ├── jetson_docker.sh             # Docker management
│   └── docker-compose*.yml          # Docker orchestration
│
├── docs/                            # Complete documentation
│   ├── INDEX.md                     # Documentation index
│   ├── QUICKSTART.md                # 5-minute quick start
│   ├── ARCHITECTURE.md              # System architecture
│   ├── DEPLOYMENT.md                # Deployment guide
│   └── CALIBRATION.md               # Calibration integration
│
├── .env                             # Configuration (auto-propagated)
├── setup_auto_bot.sh                # Initial system setup
├── auto_update.sh                   # Fast redeployment
└── README.md                        # This file
```

## 🚀 Quick Start

See **[docs/QUICKSTART.md](docs/QUICKSTART.md)** for complete setup instructions.

### Quick 5-Minute Setup
```bash
# 1. Configure environment
cd RobotOS
nano .env  # Set RPI_HOST, CLIENT_IP, JETSON_HOST

# 2. Deploy everything
chmod +x setup_auto_bot.sh
./setup_auto_bot.sh

# 3. Start server
cd server/
python3 main.py

# Select mode:
# 1. Web Dashboard (recommended)
# 2. Controller Mode (Xbox)
# 3. Sequence Mode (manual commands)
# 4. Server Only (Jetson autonomous)
```

## 🎮 Usage Modes

The system supports 4 operating modes:

### 1. Web Dashboard (Recommended) 🌐
Real-time monitoring interface:
- 📊 Command statistics (by source: Jetson, Controller, Manual, Sequence)
- 📜 Live command history
- 💓 RPi connection status monitoring
- ⏱️ System uptime tracking
- Access at `http://localhost:8080`

### 2. Controller Mode (Xbox)
Direct gamepad control without calibration:
- **D-Pad**: Movement (up/down/left/right)
- **A Button**: Unlock, **B Button**: Lock
- **X Button**: Stop, **Y Button**: Demo
- Hold-to-repeat at 150ms intervals
- Immediate response, no delays

### 3. Sequence Mode (Manual Commands)
Text-based command entry with full calibration support:
```bash
seq> forward 2              # Single command
seq> seq forward 2; right 1; lock 0.5; stop    # Sequence
```

**With Calibration Support**:
- Forward/backward/lock/unlock motions are pausable
- Jetson can pause forward motion for calibration
- Turns (left/right) are non-pausable (atomic)

### 4. Server Only (Autonomous)
Pure Jetson-based autonomous control:
- No manual input accepted
- Server only receives Jetson commands
- Full calibration integration

## 📡 Network Ports

| Port | Direction | Purpose |
|------|-----------|---------|
| 5555 | Client → RPi | Command execution |
| 5556 | RPi → Client | Heartbeat monitoring |
| 5557 | Jetson → Client | Vision commands |
| 5000 | Browser → Client | Web Dashboard (HTTP) |

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

The system uses a **3-tier distributed architecture** with Docker-based CI/CD managed from miniPC:

```
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│ JETSON (Vision)  │      │  miniPC (Brain)  │      │ RPi (Executor)   │
│ • Vision proc.   │◀────▶│ • Aggregator     │◀────▶│ • GPIO control   │
│ • Calibration    │ ZMQ  │ • Coordinator    │ ZMQ  │ • Motor driver   │
│                  │ 5557 │ • Dashboard      │ 5555 │ • Motion thread  │
└──────────────────┘      └──────────────────┘      └──────────────────┘
        │                           │                        │
        └─ Docker Agent    ┌───────┴────────────────────────┘
          (managed from    │
           miniPC via      ├─ docker-compose up
           jetson_docker   ├─ jetson_docker.sh
           .sh)            └─ auto_update.sh
```

**Three-Tier Flow**:
1. **Jetson** - Processes camera feed, detects objects, sends commands
2. **miniPC Server** - Central hub aggregating inputs (Jetson, Xbox, Manual), coordinating calibration
3. **RPi** - Executes GPIO commands, controls motors, sends heartbeat

**Key Principles**:
- Centralized command aggregation (no competing commands)
- Thread-safe motion control (single motion thread)
- Calibration coordination (Jetson can pause motion)
- Docker deployment from miniPC (centralized management)

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for complete details.

## 🔌 Hardware

- **miniPC** (x86 Linux) - Client brain
- **Raspberry Pi 4** - GPIO controller
- **Jetson Nano** (optional) - Vision processing
- **3-pin relay board** - Motor control
- **RC car** with GPIO-compatible motors
- **Xbox controller** (optional) - Manual control
COMMAND_AGGREGATION.md](COMMAND_AGGREGATION.md)** - Command processing system
- **[
### GPIO Wiring (BCM Mode)
- **Pin 17** - Control bit 0
- **Pin 27** - Control bit 1
- **Pin 22** - Control bit 2

## 📚 Documentation

**Start Here**: [docs/INDEX.md](docs/INDEX.md) - Complete documentation index

### Core Guides
- **[docs/QUICKSTART.md](docs/QUICKSTART.md)** - 5-minute setup guide
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design and architecture
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Docker deployment workflows
- **[docs/CALIBRATION.md](docs/CALIBRATION.md)** - Jetson calibration integration

### Key Features Documented
- ✅ 3-tier distributed architecture
- ✅ Command aggregation system
- ✅ Docker CI/CD infrastructure (Jetson management from miniPC)
- ✅ Calibration pause/resume for vision processing
- ✅ Web dashboard monitoring
- ✅ Xbox controller support
- ✅ Thread-safe motion control
- ✅ Health monitoring & heartbeat

## 🐛 Troubleshooting

### Common Issues

**Jetson can't connect to server**
```bash
ping $CLIENT_IP
sudo ufw allow 5557/tcp
```

**Server can't reach RPi**
```bash
ping $RPI_HOST
ssh pi@$RPI_HOST "docker ps"
```

**Car doesn't move**
```bash
ssh pi@$RPI_HOST
docker logs auto-bot-rpi
```

For detailed troubleshooting, see [docs/QUICKSTART.md#-troubleshooting](docs/QUICKSTART.md#-troubleshooting).

## 🔄 Development

### Quick Redeploy After Code Changes
```bash
./auto_update.sh
# Pulls latest code, builds Docker images, deploys to all systems
```

### Build Jetson Docker Image (from miniPC)
```bash
cd jetson/
./jetson_docker.sh build
```

### Run CI/CD Pipeline (test, lint, security, validate)
```bash
./jetson/jetson_docker.sh ci
```

### Deploy to Jetson
```bash
./jetson/jetson_docker.sh deploy
```

### Monitor Logs
```bash
./jetson/jetson_docker.sh logs --follow
```

### Test GPIO Directly (on RPi)
```bash
ssh pi@$RPI_HOST
cd auto-bot-rpi
sudo python3 app.py "forward 1"
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for complete deployment workflows.

## 📝 License

MIT License - See LICENSE file for details

## 👥 Contributors

- [AHuyHarryIT](https://github.com/AHuyHarryIT)
- [NhatNam041206](https://github.com/NhatNam041206)

## 🙏 Acknowledgments

- ZeroMQ for reliable messaging
- RPi.GPIO for hardware control
- OpenCV for vision processing

---

**Status**: Development  
**Last Updated**: January 2026  
**Architecture Version**: 3.0 (3-Tier)
