# Auto-Bot Copilot Instructions

## Architecture Overview

This is a **3-tier distributed robotics control system** for a 3-pin GPIO-controlled RC car:

- **Jetson** (`jetson/`): Vision/calibration system - processes camera data and sends control commands (left, right, stop)
- **Client (Brain)** (`client/`): Runs on miniPC (x86) - central decision hub that receives from multiple sources and coordinates robot control
  - Receives vision commands from Jetson via ZMQ REP socket (port 5557)
  - Receives manual input from Xbox controller
  - Receives text commands via sequence mode
  - Forwards all commands to RPi for execution
- **Server (Executor)** (`rpi/`): Runs on Raspberry Pi - controls GPIO pins (BCM 17, 27, 22) and executes motion commands
- **Communication**: ZeroMQ REQ/REP for commands + PUB/SUB for heartbeat monitoring

```
[Jetson Vision] --ZMQ:5557--> [miniPC Client (Brain)] --ZMQ:5555--> [RPi Server] --GPIO--> [3-pin relay board] --> [Car motors]
[Xbox Controller] --------->         |                     <-ZMQ:5556-- (heartbeat)
[Sequence Mode] ----------->         |
```

### Key Principle: Client is the Central Brain
The miniPC client acts as the **central processing hub** that:
1. Aggregates inputs from multiple sources (Jetson vision, Xbox controller, manual commands)
2. Makes decisions and processes commands
3. Forwards unified commands to RPi for GPIO execution
4. Monitors RPi health via heartbeat

This architecture allows autonomous (Jetson vision) and manual control (Xbox/sequence) to coexist.

## Critical Deployment Pattern

**DO NOT manually copy files to RPi.** Use the automated deployment scripts:

- `./setup_auto_bot.sh` - Full initial setup (Docker install + deploy)
- `./auto_update.sh` - Fast redeploy after code changes

Both scripts:
1. Read `.env` for config (RPI_HOST, RPI_USER, ZMQ_PORT, etc.)
2. Auto-copy `.env` to `client/.env` and `rpi/.env`
3. Build Docker images with timestamp+git-sha tags
4. Deploy via SSH + docker commands

**Never** edit `client/.env` or `rpi/.env` directly - they're auto-generated from root `.env`.

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

## Client Modes

### Command Server Mode (`command_server.py`)
- Runs in background thread automatically when client starts
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
# Client config
RPI_HOST=192.168.31.211         # RPi IP address
ZMQ_PORT=5555                   # Port for client->RPi commands
HEARTBEAT_PORT=5556             # Port for RPi->client heartbeat
CLIENT_SERVER_PORT=5557         # Port for Jetson->client commands
DUR_FORWARD=0.5                 # movement step duration
SEND_COOLDOWN=0.05              # client rate limit

# Jetson config
CLIENT_IP=192.168.10.100        # miniPC IP address
CLIENT_PORT=5557                # Client command server port
```

Client: `config.py` loads from `client/.env`  
Server: `zmq_server.py` loads from `rpi/.env`  
Jetson: `vision_client.py` loads from `jetson/.env`

## Docker Quirks

**Client container**:
- `network_mode: host` to reach RPi on local network
- `devices: /dev/input` needed if reading joystick from container (currently commented out)

**RPi container**:
- `--privileged` required for GPIO access
- `--network host` for ZMQ binding
- Must use `--env-file` to pass `.env` variables

## Development Workflows

**Testing motion**: Run `app.py` standalone on RPi (outside Docker) for quick iteration:
```bash
ssh pi@rpi-host
cd auto-bot-rpi
sudo python3 app.py "seq forward 2; stop"
```

**Debugging ZMQ**: Check firewall on both sides, verify ports with `ss -tlnp | grep 5555`

**Version tracking**: Both scripts write `VERSION=YYYYMMDD-HHMMSS-gitsha` to image tags and `.last_version` file

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

## Safety Principles

1. **Always stop on disconnect/error** - Client sends `stop` on KeyboardInterrupt, controller disconnect, heartbeat loss
2. **Motion cancellation** - New commands immediately cancel old ones via `stop_motion()`
3. **GPIO cleanup** - `GPIODriver.cleanup()` always called in `finally` blocks
4. **Privileged access** - Docker needs `--privileged` for GPIO, never run as root unnecessarily
