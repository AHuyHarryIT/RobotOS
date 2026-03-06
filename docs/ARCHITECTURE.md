# Architecture Overview

## 3-Tier Distributed Control System

RobotOS is a distributed robotics control system for an RC car with three-tier architecture managed through Docker-based CI/CD:

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

### Key Principles

1. **Central Brain Architecture** - miniPC server coordinates all inputs
2. **Command Aggregation** - Unified command processing with validation
3. **Vision-Based Control** - Jetson processes camera for autonomous driving
4. **Manual Override** - Xbox controller for manual control
5. **Thread-Safe Operations** - Safe command processing from multiple sources
6. **Health Monitoring** - Heartbeat system tracks RPi status

## Project Structure

```
RobotOS/
├── server/              # miniPC server (Brain)
│   ├── main.py                      # Main entry point
│   ├── command_aggregator.py        # Central command processing hub
│   ├── command_server.py            # Receives from Jetson
│   ├── controller_mode.py           # Xbox gamepad control
│   ├── seq_mode.py                  # Manual command mode
│   ├── sequence_executor.py         # Enhanced executor with calibration
│   ├── calibration_coordinator.py   # Calibration state machine
│   ├── zmq_client.py                # RPi communication
│   ├── web_dashboard.py             # Web-based UI
│   ├── config.py                    # Configuration
│   ├── docker-compose.yml           # Dev deployment
│   ├── docker-compose.prod.yml      # Production deployment
│   ├── Dockerfile                   # Container image
│   └── requirements.txt
│
├── rpi/                 # Raspberry Pi server (Executor)
│   ├── app.py                       # Main entry point
│   ├── zmq_server.py                # ZMQ server & motion control
│   ├── gpio_driver.py               # GPIO pin management
│   ├── parser.py                    # Command parsing
│   ├── sequencer.py                 # Sequence handling
│   ├── states.py                    # GPIO state definitions
│   ├── rpi_server.py                # Server wrapper
│   ├── docker-compose.yml           # Dev deployment
│   ├── docker-compose.prod.yml      # Production deployment
│   ├── Dockerfile                   # Container image
│   └── requirements.txt
│
├── jetson/              # Jetson Nano (Vision)
│   ├── vision_client.py             # Standard vision client
│   ├── vision_client_calibration_example.py
│   ├── calibrate.py                 # Calibration utilities
│   ├── calibration_main.py          # Main calibration module
│   ├── config.py                    # Configuration
│   ├── helpers.py                   # Utility functions
│   ├── docker-compose.yml           # Dev deployment
│   ├── docker-compose.prod.yml      # Production deployment
│   ├── docker-compose.ci.yml        # CI/CD pipeline
│   ├── Dockerfile                   # Production image
│   ├── Dockerfile.ci                # CI/CD test image
│   ├── jetson_docker.sh             # Docker management script
│   ├── .dockerignore
│   ├── requirements.txt
│   └── config/                      # Configuration files
│
├── docs/                # Documentation
├── deploy/              # Deployment scripts
├── vids/                # Demo videos
└── output/              # Generated outputs
```

## Communication Patterns

### ZeroMQ Channels

- **5555 (REQ/REP)**: Server → RPi command channel
- **5556 (PUB/SUB)**: RPi → Server heartbeat
- **5557 (REP)**: Jetson → Server command channel
- **5558 (PUB/SUB)**: Calibration pause/resume signaling
- **5559 (PUB/SUB)**: Calibration heartbeat monitoring

### Message Types

#### Motion Commands
```
forward [duration]
backward [duration]
left [duration]
right [duration]
lock [duration]
unlock [duration]
stop
sleep [duration]
```

#### Calibration Signals (Jetson → Server)
```json
{
  "type": "calibration_pause",
  "phase": "forward",
  "elapsed": 0.5,
  "total": 2.0
}

{
  "type": "calibration_done"
}

{
  "type": "calibration_status"
}
```

## Operating Modes

### 1. Controller Mode (Xbox)
- Direct command execution
- No calibration pausing
- Immediate response to input
- D-pad: Movement, Buttons: Actions

### 2. Sequence Mode (Text)
- Text-based command entry
- Supports pausable motions (forward, backward, lock, unlock)
- Turns (left, right) are non-pausable
- Full calibration support

### 3. Jetson Autonomous (Vision)
- Jetson processes camera feed
- Sends motion commands and calibration signals
- Server coordinates pause/resume
- Full integration with calibration system

### 4. Server Only
- No manual control
- Accepts only Jetson commands
- Pure autonomous mode

## GPIO Control States

The 3-bit GPIO patterns control the car:

```python
FORWARD:  (0,0,1)  # BCM pins 17,27,22
BACKWARD: (0,1,0)
LEFT:     (0,1,1)
RIGHT:    (1,0,0)
LOCK:     (1,0,1)  # parking brake
UNLOCK:   (1,1,0)
STOP:     (0,0,0)  # all LOW
```

## Threading Model

### Server (miniPC)
- Main thread: Menu and mode selection
- Controller thread: Reads Xbox input
- Command receiver thread: Accepts Jetson commands
- Executor thread: Runs sequences with calibration support

### RPi Motion Worker
- Single motion thread: Executes one command at a time
- Cancellation via threading.Event
- All motions end with driver.stop() for safety

## Docker Infrastructure

### Development
- `docker-compose.yml`: Basic service definition with volume mounts
- Live code reloading
- Used for local testing

### Production
- `docker-compose.prod.yml`: Health checks, resource limits, logging
- Restart policies
- Metadata labels for monitoring

### CI/CD (Jetson only)
- `docker-compose.ci.yml`: 4 services (test, lint, security, validate)
- Full quality gate pipeline
- Automated testing from miniPC

## Deployment Strategy

All deployments managed from miniPC server:

1. Make code changes in local workspace
2. Build Docker image: `./jetson/jetson_docker.sh build`
3. Run CI/CD: `./jetson/jetson_docker.sh ci`
4. Deploy: `./jetson/jetson_docker.sh deploy`
5. Monitor: `./jetson/jetson_docker.sh logs --follow`

Configuration via `.env` file (auto-propagated to all components).

## Safety Features

- **Motion Cancellation**: New commands immediately cancel old ones
- **GPIO Cleanup**: Always called in finally blocks
- **Heartbeat Monitoring**: Detects disconnects
- **Timeout Protection**: 30-second calibration timeout
- **Thread-Safe Locks**: RLock/Lock usage throughout
- **Emergency Stop**: STOP command always available

---

**See Also**: [docs/QUICKSTART.md](QUICKSTART.md), [docs/DEPLOYMENT.md](DEPLOYMENT.md)
