# RobotOS Documentation Index

Complete documentation for the 3-Tier Autonomous RC Car Control System.

## 📚 Core Documentation

### [QUICKSTART.md](QUICKSTART.md) - **Start Here** ⭐
5-minute guide to get the system running. Covers:
- Basic setup and configuration
- Operating modes overview
- Quick testing procedures
- Troubleshooting common issues

### [ARCHITECTURE.md](ARCHITECTURE.md) - System Design
Deep dive into system architecture:
- 3-tier distributed control system
- Component overview
- Communication patterns
- GPIO control states
- Docker infrastructure basics

### [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment Guide
Complete deployment instructions:
- Environment configuration
- Docker deployment workflow
- Deployment scripts (`jetson_docker.sh`, `auto_update.sh`)
- Network configuration
- Monitoring and scaling
- CI/CD integration

### [CALIBRATION.md](CALIBRATION.md) - Jetson Calibration System
Full calibration integration guide:
- Calibration coordinator overview
- Pause/resume mechanism
- Control flow examples
- Usage patterns
- Testing scenarios
- Troubleshooting

## 🎯 Feature Guides

### Operating Modes
- **Mode 1: Web Dashboard** - Real-time visualization with web UI
- **Mode 2: Controller Mode** - Xbox gamepad control (no calibration)
- **Mode 3: Sequence Mode** - Text-based commands with calibration support
- **Mode 4: Server Only** - Pure autonomous Jetson control

### Motion Commands
- `forward [duration]` - Move forward (pausable)
- `backward [duration]` - Move backward (pausable)
- `left [duration]` - Turn left (non-pausable)
- `right [duration]` - Turn right (non-pausable)
- `lock [duration]` - Parking brake (pausable)
- `unlock [duration]` - Release brake (pausable)
- `stop` - Emergency stop
- `seq ...` - Command sequences

### Calibration Signals (Jetson)
- `calibration_pause` - Request to pause motion
- `calibration_done` - Signal calibration complete
- `calibration_status` - Query current status

## 🏗️ Project Structure

```
RobotOS/
├── docs/                          # Documentation (this folder)
│   ├── INDEX.md                   # This file
│   ├── QUICKSTART.md              # 5-minute setup guide
│   ├── ARCHITECTURE.md            # System design
│   ├── DEPLOYMENT.md              # Deployment instructions
│   └── CALIBRATION.md             # Calibration integration
│
├── server/                        # miniPC Server (Brain)
│   ├── main.py                    # Entry point
│   ├── command_aggregator.py      # Central processing
│   ├── calibration_coordinator.py # Calibration state machine
│   ├── sequence_executor.py       # Enhanced sequence execution
│   └── docker-compose*.yml        # Docker orchestration
│
├── rpi/                           # Raspberry Pi (Executor)
│   ├── app.py                     # Entry point
│   ├── zmq_server.py              # Motion control
│   ├── gpio_driver.py             # GPIO operations
│   └── docker-compose*.yml        # Docker orchestration
│
├── jetson/                        # Jetson Nano (Vision)
│   ├── vision_client.py           # Standard client
│   ├── vision_client_calibration_example.py  # Calibration examples
│   ├── jetson_docker.sh           # Docker management
│   └── docker-compose*.yml        # Docker orchestration
│
├── .env                           # Root configuration (auto-propagated)
├── setup_auto_bot.sh              # Initial system setup
├── auto_update.sh                 # Fast redeployment
└── README.md                      # Project overview
```

## 🚀 Quick Reference

### Setup Checklist
- [ ] Configure `.env` with network IP addresses
- [ ] Run `setup_auto_bot.sh` for initial deployment
- [ ] Verify Docker containers running on all systems
- [ ] Test connectivity with quick tests
- [ ] Start server and select operating mode

### Common Tasks

**Deploy Code Changes**
```bash
./auto_update.sh
```

**Build Jetson Docker Image**
```bash
cd jetson/
./jetson_docker.sh build
```

**Run CI/CD Pipeline**
```bash
./jetson/jetson_docker.sh ci
```

**Monitor Logs**
```bash
./jetson/jetson_docker.sh logs --follow
```

**Test Motion Command**
```bash
cd server
python3 main.py
# Select: 3 (Sequence Mode)
# seq> seq forward 2; stop
```

## 📖 Documentation by Role

### For Developers
1. Start with [QUICKSTART.md](QUICKSTART.md)
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) for system design
3. Check [DEPLOYMENT.md](DEPLOYMENT.md) for Docker workflows
4. See [CALIBRATION.md](CALIBRATION.md) for calibration integration

### For System Administrators
1. Read [DEPLOYMENT.md](DEPLOYMENT.md) completely
2. Configure `.env` based on your network
3. Run deployment scripts
4. Set up monitoring and backups

### For Vision/Calibration Engineers
1. Start with [CALIBRATION.md](CALIBRATION.md)
2. Review `jetson/vision_client_calibration_example.py`
3. Check control flow examples in calibration guide
4. Implement your calibration logic in `jetson/calibrate.py`

### For Hardware Engineers
1. Review GPIO pin configuration in [ARCHITECTURE.md](ARCHITECTURE.md)
2. Check motor wiring with GPIO states (section "GPIO Control States")
3. Test connectivity procedures in [QUICKSTART.md](QUICKSTART.md)
4. Review RPi setup in [DEPLOYMENT.md](DEPLOYMENT.md)

## 🔧 Troubleshooting Index

### Connectivity Issues
- See [QUICKSTART.md - Troubleshooting](QUICKSTART.md#-troubleshooting)
- See [DEPLOYMENT.md - Troubleshooting Deployment](DEPLOYMENT.md#troubleshooting-deployment)

### Motion/GPIO Issues
- See [QUICKSTART.md - Test 2: Test Direct Motion](QUICKSTART.md#test-2-test-direct-motion-rpi)
- GPIO pin configuration in [ARCHITECTURE.md](ARCHITECTURE.md)

### Calibration Issues
- See [CALIBRATION.md - Troubleshooting](CALIBRATION.md#troubleshooting)
- Test scenarios in [CALIBRATION.md - Testing Scenarios](CALIBRATION.md#testing-scenarios)

### Docker Issues
- See [DEPLOYMENT.md - Troubleshooting Deployment](DEPLOYMENT.md#troubleshooting-deployment)
- CI/CD pipeline details in [DEPLOYMENT.md - CI/CD Integration](DEPLOYMENT.md#cicd-integration)

## 📋 Configuration Reference

### Environment Variables (`.env`)

**Network Settings**
```bash
RPI_HOST=192.168.x.x              # Raspberry Pi IP
JETSON_HOST=192.168.x.x           # Jetson IP
CLIENT_IP=192.168.x.x             # miniPC IP (for Jetson to connect)
```

**Port Settings**
```bash
ZMQ_PORT=5555                      # Server ↔ RPi
HEARTBEAT_PORT=5556                # RPi heartbeat
CLIENT_SERVER_PORT=5557            # Jetson ↔ Server
```

**Motion Settings**
```bash
DUR_FORWARD=0.5                    # Default forward duration
DUR_BACKWARD=0.5                   # Default backward duration
DUR_LEFT=0.3                       # Default left turn duration
DUR_RIGHT=0.3                      # Default right turn duration
```

**Calibration Settings**
```bash
CALIBRATION_TIMEOUT=30.0           # Pause timeout (seconds)
```

See [DEPLOYMENT.md - Environment Configuration](DEPLOYMENT.md#environment-configuration) for complete reference.

## 🎓 Learning Path

### Beginner
1. [QUICKSTART.md](QUICKSTART.md) - Get system running
2. [ARCHITECTURE.md](ARCHITECTURE.md) - Understand components
3. Test each operating mode manually

### Intermediate
1. [DEPLOYMENT.md](DEPLOYMENT.md) - Learn deployment process
2. Make code changes and redeploy
3. Monitor logs and debug issues

### Advanced
1. [CALIBRATION.md](CALIBRATION.md) - Implement custom calibration
2. [DEPLOYMENT.md - Scaling & Production](DEPLOYMENT.md#scaling--production)
3. Add custom vision algorithms to Jetson

## 📞 Support

### Documentation Issues
- Check [QUICKSTART.md - Need Help?](QUICKSTART.md#-need-help)
- Review relevant troubleshooting section

### Technical Questions
- Refer to the detailed guide for the component you're working with
- Check troubleshooting sections
- Review code examples in appropriate guides

### Known Limitations

**Turns are Non-Pausable**
- Left/right motions cannot be paused for calibration
- By design (safety feature)
- Alternative: use multiple forward/backward motions with turns

**Single Motion Thread**
- Only one motion executes at a time
- By design (GPIO safety)
- Queue commands in sequence

**30-Second Calibration Timeout**
- Calibration must complete within 30 seconds
- Can be adjusted in `.env` (CALIBRATION_TIMEOUT)
- Prevents infinite hangs

## 📝 Last Updated

- **Documentation Version**: 2.0
- **Last Update**: 2025-01-15
- **System Status**: Production Ready

---

**Quick Links**: [Quick Start](QUICKSTART.md) | [Architecture](ARCHITECTURE.md) | [Deployment](DEPLOYMENT.md) | [Calibration](CALIBRATION.md)
