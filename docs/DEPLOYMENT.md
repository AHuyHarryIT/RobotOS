# Deployment Guide

Complete guide for deploying RobotOS to Jetson, RPi, and miniPC server using Docker.

## Overview

RobotOS uses a **centralized Docker management approach** where the miniPC server manages deployments to both Jetson and RPi:

```
miniPC Server
├─ Builds/tests Jetson Docker image
├─ Deploys to Jetson via SSH + Docker daemon
├─ Manages RPi Docker deployment
└─ Runs central orchestration (docker-compose)
```

## Prerequisites

### miniPC Server
- Docker installed: `docker --version`
- Docker Compose: `docker-compose --version`
- SSH access to Jetson and RPi
- Linux/macOS terminal
- `.env` file configured

### Jetson Nano
- Nvidia L4T runtime installed
- Docker daemon running
- SSH server enabled
- Network connectivity to miniPC
- 2GB free disk space minimum

### Raspberry Pi
- Docker installed
- GPIO access configured (privileged mode)
- SSH server enabled
- Network connectivity to miniPC
- 1GB free disk space minimum

## Environment Configuration

### Root `.env` File

```bash
# Network Configuration
RPI_HOST=192.168.31.211           # RPi IP address
RPI_USER=pi                        # RPi SSH user
JETSON_HOST=192.168.10.200        # Jetson IP address
JETSON_USER=jetson                # Jetson SSH user
CLIENT_IP=192.168.31.100          # miniPC server IP (for Jetson to connect)

# Port Configuration
ZMQ_PORT=5555                      # Server → RPi motion commands
HEARTBEAT_PORT=5556                # RPi → Server heartbeat
CLIENT_SERVER_PORT=5557            # Jetson → Server commands
SEND_COOLDOWN=0.05                 # Server rate limit

# Motion Configuration
DUR_FORWARD=0.5                    # Default forward motion duration
DUR_BACKWARD=0.5                   # Default backward duration
DUR_LEFT=0.3                       # Default left turn duration
DUR_RIGHT=0.3                      # Default right turn duration

# Calibration Configuration
CALIBRATION_TIMEOUT=30.0           # Seconds to wait for calibration_done
```

### Deployment

All `.env` values are automatically propagated to:
- `server/.env` - miniPC server configuration
- `rpi/.env` - Raspberry Pi server configuration
- `jetson/.env` - Jetson vision system configuration

**Never edit subdirectory `.env` files directly** - they're auto-generated from root `.env`.

## Deployment Scripts

### `jetson_docker.sh` - Jetson Docker Management

Located in `jetson/` directory. Provides unified CLI for building, testing, and deploying Jetson container from miniPC.

#### Build Production Image
```bash
cd jetson/
./jetson_docker.sh build

# Creates timestamped + git-sha tagged image:
# jetson-vision:20250115-143025-a1b2c3d
```

#### Run CI/CD Pipeline
```bash
./jetson_docker.sh ci

# Runs 4-stage pipeline:
# 1. test         - pytest with coverage
# 2. lint         - pylint code quality
# 3. security     - bandit security scan
# 4. validate     - config validation
```

Collect test reports:
```bash
./jetson_docker.sh ci --collect-reports
```

#### Deploy to Jetson
```bash
./jetson_docker.sh deploy

# Or deploy specific image tag:
./jetson_docker.sh deploy 20250115-143025-a1b2c3d
```

#### Container Lifecycle Management
```bash
./jetson_docker.sh start              # Start vision container
./jetson_docker.sh stop               # Stop gracefully
./jetson_docker.sh restart            # Restart container
./jetson_docker.sh logs               # View logs
./jetson_docker.sh logs --follow      # Stream logs
```

#### Development Utilities
```bash
./jetson_docker.sh build-dev          # Dev image with hot reload
./jetson_docker.sh dev-up             # Start dev environment
./jetson_docker.sh test-local         # Run local tests
./jetson_docker.sh monitor            # Watch container metrics
./jetson_docker.sh shell              # SSH into container
```

#### Information
```bash
./jetson_docker.sh status             # Show container status
./jetson_docker.sh --help             # Show all commands
```

### `setup_auto_bot.sh` - Initial System Setup

Complete one-time setup (install Docker, deploy all components):

```bash
chmod +x setup_auto_bot.sh
./setup_auto_bot.sh

# Interactive prompts for:
# 1. SSH credentials (RPi, Jetson)
# 2. IP addresses verification
# 3. Docker installation (if needed)
# 4. Initial deployment
```

### `auto_update.sh` - Fast Redeployment

Quick redeploy after code changes:

```bash
chmod +x auto_update.sh
./auto_update.sh

# 1. Pull latest code from git
# 2. Propagate .env to all components
# 3. Build new Docker images
# 4. Deploy to Jetson and RPi
# 5. Restart all services
```

## Deployment Workflow

### Step 1: Initial Setup (One-Time)
```bash
cd /home/mobileos/autocar/RobotOS

# Configure .env with your network details
nano .env

# Run complete setup
chmod +x setup_auto_bot.sh
./setup_auto_bot.sh

# Verify all systems are running
./jetson/jetson_docker.sh status
ssh pi@$RPI_HOST docker ps
docker ps  # miniPC server
```

### Step 2: Make Code Changes
```bash
# Edit files locally on miniPC
nano jetson/vision_client.py
# or
nano server/main.py
# or
nano rpi/zmq_server.py
```

### Step 3: Build & Test
```bash
cd jetson/

# Build production image
./jetson_docker.sh build

# Run full CI/CD pipeline
./jetson_docker.sh ci

# If tests fail, fix code and repeat build step
```

### Step 4: Deploy
```bash
# Deploy to Jetson
./jetson_docker.sh deploy

# For RPi, use standard Docker deployment:
cd rpi/
docker build -t auto-bot-rpi:latest .
ssh pi@$RPI_HOST docker pull auto-bot-rpi:latest
ssh pi@$RPI_HOST docker-compose -f docker-compose.prod.yml up -d

# Or use auto_update.sh for both:
./auto_update.sh
```

### Step 5: Verify Deployment
```bash
# Check Jetson container
./jetson/jetson_docker.sh logs --follow

# Check RPi container
ssh pi@$RPI_HOST docker logs -f auto-bot-rpi

# Test motion command
cd server && python3 main.py
# Select: 4 (Server Only)
# Then send command from Jetson
```

## Docker Compose Variants

### Development (`docker-compose.yml`)
Used for local testing with live code reloading:

```bash
# Jetson
cd jetson/
docker-compose up -d

# RPi
cd rpi/
docker-compose up -d

# Server
cd server/
docker-compose up -d
```

### Production (`docker-compose.prod.yml`)
Used for production deployment with health checks, logging, resource limits:

```bash
# Jetson
cd jetson/
docker-compose -f docker-compose.prod.yml up -d

# RPi
cd rpi/
docker-compose -f docker-compose.prod.yml up -d

# Server
cd server/
docker-compose -f docker-compose.prod.yml up -d
```

### CI/CD Pipeline (`docker-compose.ci.yml` - Jetson only)
Run complete quality gate:

```bash
cd jetson/
docker-compose -f docker-compose.ci.yml up --abort-on-container-exit
```

Services:
- `test` - pytest with coverage (validation gate)
- `lint` - pylint code quality
- `security` - bandit security scanning
- `validate` - configuration validation

## Docker Image Configuration

### Jetson Dockerfile
```dockerfile
# Base: NVIDIA L4T runtime (CUDA-enabled)
FROM nvcr.io/nvidia/l4t-runtime:r35.3.1

# Install Python dependencies
RUN apt-get update && apt-get install -y python3-pip

# Copy application
COPY jetson/ /app/jetson/
WORKDIR /app/jetson

# Install requirements
RUN pip3 install -r requirements.txt

# Run vision client
CMD ["python3", "vision_client.py"]
```

**Key Features**:
- NVIDIA CUDA pre-optimized
- Minimal base image (~500MB)
- Fast inference
- GPU support out-of-box

### RPi Dockerfile
```dockerfile
# Base: Raspberry Pi OS
FROM arm32v7/python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-rpi.gpio \
    python3-dev

# Copy application
COPY rpi/ /app/rpi/
WORKDIR /app/rpi

# Install requirements
RUN pip3 install -r requirements.txt

# Run server (requires --privileged for GPIO)
CMD ["python3", "app.py"]
```

**Key Features**:
- Raspberry Pi OS compatible
- GPIO support (requires --privileged)
- Minimal footprint
- 32-bit architecture support

### Server Dockerfile
```dockerfile
# Base: Python 3.9
FROM python:3.9-slim

# Install system dependencies
COPY server/ /app/server/
WORKDIR /app/server

# Install requirements
RUN pip3 install -r requirements.txt

# Run server
CMD ["python3", "main.py"]
```

**Key Features**:
- Pure x86 Python environment
- No special permissions needed
- Optional web dashboard enabled

## Network Configuration

### Ports Used

| Port | Protocol | Direction | Purpose |
|------|----------|-----------|---------|
| 5555 | ZMQ REQ/REP | Server → RPi | Motion commands |
| 5556 | ZMQ PUB/SUB | RPi → Server | Heartbeat monitoring |
| 5557 | ZMQ REP | Jetson → Server | Vision commands |
| 5558 | ZMQ PUB/SUB | Server → Jetson | Calibration pause signal |
| 5559 | ZMQ PUB/SUB | Jetson → Server | Calibration heartbeat |
| 8080 | HTTP | - | Web dashboard (optional) |

### Firewall Configuration

On miniPC server:
```bash
sudo ufw allow 5555/tcp
sudo ufw allow 5556/udp
sudo ufw allow 5557/tcp
sudo ufw allow 5558/udp
sudo ufw allow 5559/udp
sudo ufw allow 8080/tcp
```

On RPi:
```bash
sudo ufw allow 5555/tcp
sudo ufw allow 5556/udp
sudo ufw allow 22/tcp  # SSH
```

On Jetson:
```bash
sudo ufw allow 5557/tcp
sudo ufw allow 5558/udp
sudo ufw allow 5559/udp
sudo ufw allow 22/tcp  # SSH
```

## Troubleshooting Deployment

### Issue: Build fails on Jetson
```bash
# Check Docker daemon is running
ssh jetson@$JETSON_HOST "docker ps"

# Check image build locally first
cd jetson/
docker build -t jetson-vision:test -f Dockerfile .

# If local build fails, fix dockerfile locally then retry
```

### Issue: SSH connection fails
```bash
# Test SSH connectivity
ssh -v jetson@$JETSON_HOST "echo OK"

# Add public key to Jetson (if not already done)
ssh-copy-id jetson@$JETSON_HOST

# Verify .env has correct IP
grep JETSON_HOST .env
```

### Issue: Container won't start
```bash
# Check container logs
docker logs auto-bot-rpi  # or auto-bot-jetson

# Check resource limits
docker stats

# Check .env is mounted
docker inspect auto-bot-rpi | grep -A 5 Mounts

# Rebuild image
docker build -t auto-bot-rpi:latest -f rpi/Dockerfile rpi/
```

### Issue: Network communication fails
```bash
# Verify ports are listening
ss -tlnp | grep 5555

# Check firewall
sudo ufw status

# Test connectivity between containers
docker exec auto-bot-rpi ping $JETSON_HOST

# Check .env propagation
docker exec auto-bot-server cat /app/server/.env
```

## Monitoring Deployments

### Check All Container Status
```bash
# miniPC (server)
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Jetson
./jetson/jetson_docker.sh status

# RPi
ssh pi@$RPI_HOST "docker ps --format 'table {{.Names}}\t{{.Status}}'"
```

### View Container Logs
```bash
# Real-time logs
./jetson/jetson_docker.sh logs --follow

# RPi logs
ssh pi@$RPI_HOST "docker logs -f auto-bot-rpi"

# Server logs
docker logs -f auto-bot-server
```

### Monitor Resource Usage
```bash
# Watch CPU/memory usage
docker stats

# Or per-container
docker stats auto-bot-rpi auto-bot-jetson auto-bot-server
```

## Scaling & Production

### Multi-Jetson Deployment
```bash
# Deploy to multiple Jetson boards:
for jetson in jetson1 jetson2 jetson3; do
  export JETSON_HOST=$jetson
  ./jetson/jetson_docker.sh deploy
done
```

### Centralized Logging
```bash
# Configure logging driver in docker-compose.prod.yml
services:
  vision:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Health Checks
```yaml
services:
  vision:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5557"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Automatic Recovery
```yaml
services:
  vision:
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

## CI/CD Integration

### Local Testing Before Deploy
```bash
cd jetson/

# Run tests locally
./jetson_docker.sh test-local

# Run linting
docker run --rm -v $PWD:/app -w /app jetson-vision:latest pylint jetson/*.py

# Run security scan
docker run --rm -v $PWD:/app -w /app jetson-vision:latest bandit -r jetson/
```

### Automated Deployment Pipeline
```bash
# Build → Test → Lint → Security → Deploy
./jetson/jetson_docker.sh ci && \
./jetson/jetson_docker.sh deploy && \
./jetson/jetson_docker.sh logs --follow
```

## Backup & Recovery

### Backup Configuration
```bash
# Backup .env
cp .env .env.backup

# Backup all code
git stash  # or commit changes

# Backup container images
docker save auto-bot-rpi:latest | gzip > auto-bot-rpi.tar.gz
```

### Restore Configuration
```bash
# Restore from backup
cp .env.backup .env

# Redeploy
./auto_update.sh
```

---

**See Also**: [Architecture](ARCHITECTURE.md) | [Quick Start](QUICKSTART.md) | [Calibration](CALIBRATION.md)
