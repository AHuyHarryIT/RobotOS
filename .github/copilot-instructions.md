# Auto-Bot Copilot Instructions

## System Architecture

### 3-Tier Distributed Control System
This is a **3-tier distributed robotics control system** for a 3-pin GPIO-controlled RC car with Docker-based CI/CD:

```
┌─────────────────────────────────────────────────────────────────┐
│                    JETSON (Nvidia L4T)                          │
│  Vision System with Docker Agent                               │
│  • Camera processing & object detection                         │
│  • Calibration coordination                                     │
│  • Docker: jetson_docker.sh manages deployment                  │
│  • Ports: 5557 (command), 5558 (calib pause), 5559 (heartbeat) │
└────────────────────┬────────────────────────────────────────────┘
                     │ ZMQ:5557
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│            miniPC SERVER (x86 - Central Brain)                  │
│  Command Aggregator & Coordinator                               │
│  • Docker: docker-compose orchestration                         │
│  • Receives: Jetson commands, Xbox input, text sequences        │
│  • Forwards: unified commands to RPi                            │
│  • Monitors: RPi heartbeat & calibration status                 │
│  • Ports: 5555→RPi, 5556←RPi (heartbeat), 5557←Jetson          │
└────────────────────┬────────────────────────────────────────────┘
                     │ ZMQ:5555
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│         RASPBERRY PI (GPIO Executor)                            │
│  Motion Worker & GPIO Control                                   │
│  • Docker: privileged for GPIO access                           │
│  • GPIO pins: BCM 17, 27, 22 (3-pin relay board)                │
│  • Single motion thread with cancellation support               │
│  • Heartbeat: UDP:5556 → miniPC server                          │
└─────────────────────────────────────────────────────────────────┘
```

**Key Principle**: miniPC server is the **central processing hub** that:
1. Aggregates inputs from Jetson vision, Xbox controller, manual sequences
2. Applies calibration coordination & priority rules
3. Forwards unified motion commands to RPi
4. Monitors RPi health & calibration status via heartbeat

## Critical Deployment Pattern

### Centralized Management from miniPC Server

**Docker Architecture** (`miniPC` manages both Jetson & RPi):
- miniPC server runs `docker-compose up` to manage Jetson vision container
- miniPC runs deployment scripts to build, test, and deploy to both systems
- Jetson & RPi have Docker daemons running, awaiting commands from miniPC
- All deployments coordinated from central location with `.env` config

### Automated Deployment Scripts

**DO NOT manually copy files to Jetson/RPi.** Use automated deployment scripts:

- `jetson_docker.sh` - Manages Jetson Docker deployment from miniPC
  - Build production image: `./jetson_docker.sh build`
  - Deploy to running container: `./jetson_docker.sh deploy`
  - Run tests/CI pipeline: `./jetson_docker.sh ci`
  - Manage container lifecycle: `./jetson_docker.sh start|stop|logs`
  - Full usage: `./jetson_docker.sh --help`

- `./setup_auto_bot.sh` - Full initial setup (Docker install + deploy)
- `./auto_update.sh` - Fast redeploy after code changes

All scripts:
1. Read `.env` for config (RPI_HOST, RPI_USER, JETSON_HOST, JETSON_USER, ZMQ_PORT, etc.)
2. Auto-copy `.env` to `server/.env`, `rpi/.env`, and `jetson/.env`
3. Build Docker images with timestamp+git-sha tags
4. Deploy via SSH + docker commands

**Never** edit `server/.env`, `rpi/.env`, or `jetson/.env` directly - they're auto-generated from root `.env`.

## GPIO Control States

3-bit patterns control the car via `states.py`:
```python
FORWARD:  (0,0,1)  # BCM pins 17,27,22
BACKWARD: (0,1,0)
LEFT:     (0,1,1)
RIGHT:    (1,0,0)
LOCK:     (1,0,1)  # parking brake
UNLOCK:   (1,1,0)
STOP:     (0,0,0)  # all LOW
```

**Threading Model (RPi server)**: 
- Only ONE motion thread runs at a time
- New commands cancel previous motion via `threading.Event`
- All motions end with `driver.stop()` (safety-critical)
- Use `sleep_interruptible()` for cancellable delays

## Command Syntax

Single commands: `forward`, `forward 2`, `right:1.5`, `sleep 0.3`  
Sequences: `seq forward 2; right 1; lock 0.5; stop`

Parsing: `parser.py` uses `CMD_PATTERN` regex + `ALIASES` dict. Always handle both formats (space/colon separated).

## Server Modes

### Command Server Mode (`command_server.py`)
- Runs in background thread automatically when server starts
- Binds ZMQ REP socket on port 5557
- Receives commands from Jetson vision system
- Forwards all received commands to RPi via existing zmq_client
- Thread-safe command forwarding with error handling

### Controller Mode (`controller_mode.py`)
- D-pad: movement with hold-to-repeat (REPEAT_HOLD_INTERVAL=0.15s)
- Buttons: A=unlock, B=lock, X=stop, Y=demo seq
- Auto-disconnection handling: sends STOP on disconnect
- Heartbeat watchdog: warns if >3s since last RPi heartbeat
- **No pygame window** - runs headless via `pygame.joystick` without `display.set_mode()`

### Sequence Mode (`seq_mode.py`)
- Text REPL for manual command entry
- Accepts single commands or `seq` prefixed sequences
- `back`/`menu` returns to mode selection, `q` exits entirely

### Server Only Mode
- Client runs command server without manual control
- Useful for pure autonomous operation via Jetson
- Still allows returning to menu for manual override

## Environment Config Pattern

All timing/network params read from `.env` via `python-dotenv`:
```python
# Server config
RPI_HOST=192.168.31.211         # RPi IP address
ZMQ_PORT=5555                   # Port for server->RPi commands
HEARTBEAT_PORT=5556             # Port for RPi->server heartbeat
SERVER_PORT=5557         # Port for Jetson->server commands
DUR_FORWARD=0.5                 # movement step duration
SEND_COOLDOWN=0.05              # server rate limit

# Jetson config
SERVER_IP=192.168.10.100        # miniPC IP address
SERVER_PORT=5557                # Server command server port
```

Server: `config.py` loads from `server/.env`  
RPi: `zmq_server.py` loads from `rpi/.env`  
Jetson: `vision_client.py` loads from `jetson/.env`

## Docker Infrastructure

### Three-Tier Docker Strategy

**Jetson Docker** (`jetson/`):
- `Dockerfile` - Production image for Jetson vision system
- `docker-compose.yml` - Standard deployment (vision container only)
- `docker-compose.prod.yml` - Production deployment with metrics, logging, health checks, resource limits
- `Dockerfile.ci` - CI/CD testing image with pytest, coverage, linting (test variants included)

**RPi Docker** (`rpi/`):
- `Dockerfile` - Production image for GPIO executor (privileged mode)
- `docker-compose.yml` - Standard deployment (motion container only)
- `docker-compose.prod.yml` - Production with logging and resource limits

**Server Docker** (`server/`):
- `docker-compose.yml` - Orchestrates command aggregator, controller mode, sequence mode
- `docker-compose.prod.yml` - Production deployment with web dashboard enabled

### Docker Compose Variants

**Development** (`docker-compose.yml`):
- Basic service definition
- Volume mounts for live code reloading
- Standard networking
- Used for local development/testing

**Production** (`docker-compose.prod.yml`):
- Health checks enabled
- Resource limits (CPU, memory, PID limits)
- Logging configured (json-file driver, log rotation)
- Metadata labels for monitoring (version, app name, environment)
- Restart policies

**CI/CD** (`docker-compose.ci.yml`) - Jetson only:
```
Services:
├── test         - pytest with coverage reporting
├── lint         - pylint and code style checks
├── security     - bandit for security scanning
└── validate     - config validation and environment checks

Pipeline Flow:
1. test (validation gate - must pass)
2. lint (quality gate)
3. security (vulnerability scanning)
4. validate (environment & config verification)
```

### Docker Quirks

**Server container**:
- `network_mode: host` to reach RPi on local network
- `devices: /dev/input` needed if reading joystick from container (currently commented out)
- Volumes: `.env`, config files, web templates

**RPi container**:
- `--privileged` required for GPIO access (bcm2835 kernel module)
- `--network host` for ZMQ binding to LAN
- Volumes: `.env`, GPIO devices via privileged mode
- Must use `--env-file` to pass `.env` variables

**Jetson container**:
- Based on NVIDIA L4T runtime (`nvcr.io/nvidia/l4t-runtime:r35.3.1`)
- CUDA compute capability pre-optimized
- `network_mode: host` for ZMQ to miniPC
- Volume mounts: camera device, config files, `.env`
- Resource limits: 2 CPU cores, 2GB memory (adjust for Jetson model)

## Deployment Management with jetson_docker.sh

The `jetson_docker.sh` script in `jetson/` provides unified CLI management from miniPC:

```bash
# Build production image with version tag (YYYYMMDD-HHMMSS-gitsha)
./jetson_docker.sh build

# Deploy built image to running Jetson Docker daemon
./jetson_docker.sh deploy [IMAGE_TAG]

# Run complete CI/CD pipeline (test → lint → security → validate)
./jetson_docker.sh ci [--collect-reports]

# Container lifecycle management
./jetson_docker.sh start                # Start vision container
./jetson_docker.sh stop                 # Stop container gracefully
./jetson_docker.sh restart              # Restart container
./jetson_docker.sh logs [--follow]      # View container logs
./jetson_docker.sh shell                # SSH into running container

# Development utilities
./jetson_docker.sh build-dev            # Dev image with hot reload
./jetson_docker.sh dev-up               # Start dev environment
./jetson_docker.sh test-local           # Local test suite
./jetson_docker.sh monitor              # Watch container metrics

# Information
./jetson_docker.sh status               # Show container status and versions
./jetson_docker.sh --help               # Show all available commands
```

**Workflow from miniPC Server**:
1. Make code changes in `jetson/` on miniPC
2. Run `./jetson/jetson_docker.sh build` (builds image locally)
3. Run `./jetson/jetson_docker.sh ci` to validate quality gate
4. Run `./jetson/jetson_docker.sh deploy` to push to Jetson Docker daemon
5. Run `./jetson/jetson_docker.sh logs --follow` to monitor

## Development Workflows

**Testing motion**: Run `app.py` standalone on RPi (outside Docker) for quick iteration:
```bash
ssh pi@rpi-host
cd auto-bot-rpi
sudo python3 app.py "seq forward 2; stop"
```

**Debugging ZMQ**: Check firewall on both sides, verify ports with `ss -tlnp | grep 5555`

**Version tracking**: Both scripts write `VERSION=YYYYMMDD-HHMMSS-gitsha` to image tags and `.last_version` file

**Local Jetson Docker Testing**:
```bash
# On miniPC, build and run Jetson image locally (requires Docker)
cd jetson
docker build -t jetson-vision:test -f Dockerfile.ci .
docker-compose -f docker-compose.ci.yml up --abort-on-container-exit
```

**Remote Deployment**:
```bash
# Deploy to Jetson via docker daemon on remote host
export DOCKER_HOST=ssh://jetson@192.168.10.200
docker images  # Verify remote connection
docker-compose -f docker-compose.prod.yml up -d
```

## Code Conventions

- **Language**: Comments/prints mix English and Vietnamese (preserve as-is)
- **Error handling**: Use `try/except` around ZMQ sends, always fallback to `driver.stop()`
- **Thread safety**: Access `motion_thread`/`motion_cancel` only inside `with motion_lock:`
- **Naming**: snake_case for functions/variables, UPPER_CASE for constants/states
- **Pin references**: Always use BCM mode (`GPIO.setmode(GPIO.BCM)`), not BOARD

## Key Files Reference

- `states.py` - GPIO bit patterns and command aliases
- `zmq_server.py` - Motion worker thread logic (lines 100-200)
- `controller_mode.py` - Xbox controller mapping and hold-to-repeat logic
- `gpio_driver.py` - Low-level RPi.GPIO wrapper (cleanup safety)
- `calibration_coordinator.py` - Calibration state machine and pause/resume logic
- `sequence_executor.py` - Enhanced executor with calibration monitoring
- `jetson_docker.sh` - Centralized Jetson Docker management from miniPC

### Docker File Reference

**Jetson Deployment**:
- `jetson/Dockerfile` - Production NVIDIA L4T-based image
- `jetson/Dockerfile.ci` - CI/CD test image with pytest and coverage
- `jetson/docker-compose.yml` - Development/standard deployment
- `jetson/docker-compose.prod.yml` - Production with health checks, logging, resource limits
- `jetson/docker-compose.ci.yml` - CI/CD pipeline (4 services: test, lint, security, validate)
- `jetson/.dockerignore` - Lean image optimization

**RPi Deployment**:
- `rpi/Dockerfile` - Production image with GPIO support
- `rpi/docker-compose.yml` - Standard deployment
- `rpi/docker-compose.prod.yml` - Production configuration

**Server Deployment**:
- `server/docker-compose.yml` - Development deployment
- `server/docker-compose.prod.yml` - Production with web dashboard

## Safety Principles

1. **Always stop on disconnect/error** - Server sends `stop` on KeyboardInterrupt, controller disconnect, heartbeat loss
2. **Motion cancellation** - New commands immediately cancel old ones via `stop_motion()`
3. **GPIO cleanup** - `GPIODriver.cleanup()` always called in `finally` blocks
4. **Privileged access** - Docker needs `--privileged` for GPIO, never run as root unnecessarily
