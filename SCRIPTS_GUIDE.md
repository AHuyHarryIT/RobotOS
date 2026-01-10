# RobotOS Scripts Guide

Quick reference for all operational scripts in the RobotOS system.

## 🚀 Deployment Scripts

### `deploy_production.sh` - Production Deployment ⭐
**Purpose**: Deploy entire system with production configuration  
**When to use**: Production environment, live deployment, stable releases

**What it does**:
1. Loads `.env.production` configuration
2. Builds optimized Docker images with version tags
3. Deploys server with production settings (always restart, log rotation, resource limits)
4. Deploys to RPi with production container config
5. Verifies health checks
6. Records deployment version and timestamp

**Usage**:
```bash
./deploy_production.sh
```

**Production features**:
- Always-restart policy for high availability
- Log rotation (10MB max, 3 files)
- Resource limits (CPU/memory)
- Network-accessible dashboard (0.0.0.0)
- INFO-level logging
- Version tracking

---

### `setup_auto_bot.sh` - Initial Setup
**Purpose**: First-time installation and deployment of entire system  
**When to use**: Fresh installation, new RPi, or complete system reset

**What it does**:
1. Checks/installs Docker on miniPC
2. Validates `.env` configuration
3. Builds and deploys server container (miniPC)
4. Installs Docker on RPi (if needed)
5. Deploys and starts RPi container
6. Verifies all deployments

**Usage**:
```bash
./setup_auto_bot.sh
```

**Interactive prompts**:
- Install Docker? [y/N]
- Deploy server (miniPC)? [Y/n]
- Deploy to Raspberry Pi? [Y/n]

---

### `auto_update.sh` - Fast Redeploy
**Purpose**: Quick updates after code changes  
**When to use**: After modifying code in `server/` or `rpi/` directories

**What it does**:
1. Syncs `.env` to subdirectories
2. Rebuilds server image with version tag
3. Restarts server container
4. Copies updated RPi code
5. Rebuilds and restarts RPi container

**Usage**:
```bash
./auto_update.sh
```

**Version tagging**: Creates `YYYYMMDD-HHMMSS-gitsha` tags  
**Speed**: ~30-60 seconds (vs 5-10 minutes for full setup)

---

## 🛑 Shutdown Script

### `shutdown_all.sh` - Graceful System Shutdown
**Purpose**: Safe shutdown of all RobotOS components  
**When to use**: Maintenance, power down, emergency stop

**Shutdown sequence**:
1. ✋ Send STOP command to robot (safety first)
2. 🔌 Stop RPi container (GPIO cleanup)
3. 🖥️ Stop server container (miniPC)
4. ⚡ Optional: Physically shutdown RPi
5. ✅ Verify all stopped

**Usage**:
```bash
./shutdown_all.sh
```

**Safety features**:
- Confirmation prompt before execution
- Sends stop command to robot motors
- Graceful 10-second timeout for containers
- Verifies shutdown completion
- Optional physical RPi shutdown

---

## 🧪 Testing Scripts

### `test_setup.sh`
**Purpose**: Validate system connectivity and configuration  
**Tests**:
- `.env` file existence
- Network connectivity to RPi
- Docker installation
- Container status
- Port accessibility

**Usage**:
```bash
./test_setup.sh
```

---

## � Utility Scripts

### `check_controller.sh` - Xbox Controller Diagnostics
**Purpose**: Diagnose Xbox controller connection issues  
**When to use**: Controller not detected, troubleshooting input devices

**What it checks**:
1. Host system input devices and permissions
2. Docker container device access
3. pygame controller detection
4. API health endpoint status

**Usage**:
```bash
./check_controller.sh
```

**Provides**: Detailed diagnostics and step-by-step fixes

---

## 📋 Script Decision Tree

```
┌─ Need to... ─────────────────────────────┐
│                                          │
├─ Production deployment? ─────────────────┼─> deploy_production.sh ⭐
│                                          │
├─ First time setup? ──────────────────────┼─> setup_auto_bot.sh
│                                          │
├─ Update code (dev)? ─────────────────────┼─> auto_update.sh
│                                          │
├─ Stop everything? ───────────────────────┼─> shutdown_all.sh
│                                          │
├─ Test configuration? ────────────────────┼─> test_setup.sh
│                                          │
├─ Controller issues? ─────────────────────┼─> check_controller.sh
│                                          │
└──────────────────────────────────────────┘
```

---

## 🔧 Prerequisites

All scripts require:
- ✅ `.env` file configured (copy from `.env.example`)
- ✅ SSH access to RPi (key-based or password with sshpass)
- ✅ Network connectivity between miniPC and RPi

### Required `.env` variables:
```bash
RPI_IP=192.168.x.x          # Raspberry Pi IP
RPI_USER=pi                 # RPi username
RPI_PASSWORD=xxx            # Optional: for sshpass
ZMQ_PORT=5555               # Command port
HEARTBEAT_PORT=5556         # Health monitoring
CLIENT_SERVER_PORT=5557     # Jetson->Server port
```

---

## 🚨 Emergency Procedures

### Quick Stop (Robot Only)
```bash
# Via web dashboard
curl -X POST http://localhost:5000/api/command -H "Content-Type: application/json" -d '{"command":"stop"}'

# Or SSH directly to RPi
ssh pi@RPI_IP "sudo docker exec auto-bot-rpi python3 -c 'from gpio_driver import GPIODriver; GPIODriver().stop()'"
```

### Force Stop All Containers
```bash
# miniPC
docker stop robotos-server -t 0

# RPi (remote)
ssh pi@RPI_IP "sudo docker stop auto-bot-rpi -t 0"
```

### Complete System Reset
```bash
./shutdown_all.sh           # Stop everything
sudo reboot                 # Reboot RPi (if needed)
./setup_auto_bot.sh        # Full reinstall
```

---

## 📊 Monitoring Commands

```bash
# Server logs (miniPC)
docker compose -f server/docker-compose.yml logs -f

# RPi logs
ssh pi@RPI_IP "sudo docker logs -f auto-bot-rpi"

# System status
docker ps                                    # Local containers
ssh pi@RPI_IP "sudo docker ps"              # RPi containers

# Web dashboard
xdg-open http://localhost:5000              # Linux
open http://localhost:5000                  # macOS
```

---

## 🔄 Typical Workflows

### Daily Development Cycle
```bash
# 1. Edit code in server/ or rpi/
vim server/main.py

# 2. Quick redeploy
./auto_update.sh

# 3. Monitor logs
docker compose -f server/docker-compose.yml logs -f
```

### Troubleshooting Workflow
```bash
# 1. Test configuration
./test_setup.sh

# 2. Check logs
docker logs robotos-server
ssh pi@RPI_IP "sudo docker logs auto-bot-rpi"

# 3. Clean restart
./shutdown_all.sh
./auto_update.sh
```

### End of Day Shutdown
```bash
# Safe shutdown sequence
./shutdown_all.sh

# When prompted:
# - Confirm shutdown: y
# - Physical RPi shutdown: y (if desired)
```

---

## 📝 Notes

- **Script execution order matters**: Always use `shutdown_all.sh` before `setup_auto_bot.sh` if redeploying
- **Version tracking**: `auto_update.sh` writes version to `.last_version` file
- **Safety first**: `shutdown_all.sh` always sends STOP command before container shutdown
- **Log preservation**: Container logs persist in Docker; use `docker logs` to view after shutdown

---

## 🆘 Common Issues

| Issue | Solution |
|-------|----------|
| SSH connection fails | Check `RPI_IP`, enable SSH, or set `RPI_PASSWORD` |
| Container won't stop | Use `docker stop -t 0` for force stop |
| Port already in use | Run `shutdown_all.sh` first |
| .env not found | Copy `.env.example` to `.env` and configure |
| Permission denied | Run with proper permissions or add to docker group |

---

*Generated for RobotOS v2024 - Last updated: 2025-12-20*
