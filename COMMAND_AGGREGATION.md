# Command Aggregation System

## Overview

The Auto-Bot client now features a **centralized command aggregation system** that acts as the brain of the robot. All commands from multiple sources (Jetson vision, Xbox controller, manual input) are processed through a single hub before being forwarded to the RPi for execution.

## Architecture

```
┌─────────────────┐
│ Jetson Vision   │────┐
│ (Autonomous)    │    │
└─────────────────┘    │
                       │     ┌──────────────────────┐
┌─────────────────┐    │     │  Command Aggregator  │      ┌─────────────┐
│ Xbox Controller │────┼────>│  (Central Brain)     │─────>│ RPi Server  │
│ (Manual)        │    │     │  - Validation        │      │ (GPIO)      │
└─────────────────┘    │     │  - Processing        │      └─────────────┘
                       │     │  - History           │
┌─────────────────┐    │     │  - Statistics        │
│ Sequence Mode   │────┘     └──────────────────────┘
│ (Text Commands) │
└─────────────────┘
```

## Key Components

### 1. Command Aggregator (`command_aggregator.py`)

The central processing hub that:
- **Validates** all incoming commands
- **Processes** commands from multiple sources
- **Tracks** command history and statistics
- **Applies** priority rules
- **Logs** all operations

#### Features

**Command Validation**
- Checks if commands are in the allowed list
- Supports single commands: `forward`, `backward`, `left`, `right`, `stop`, `lock`, `unlock`, `sleep`
- Supports sequences: `seq forward 2; right 1; stop`
- Normalizes commands (trim whitespace, lowercase)

**Command Sources**
```python
class CommandSource:
    JETSON = "jetson"        # Autonomous vision control
    CONTROLLER = "controller" # Xbox manual control
    MANUAL = "manual"        # Text command input
    SEQUENCE = "sequence"    # Sequence mode
```

**Priority Levels**
```python
class CommandPriority:
    LOW = 1       # Background tasks
    NORMAL = 5    # Regular commands
    HIGH = 10     # Emergency stops, critical commands
```

**Statistics Tracking**
- Total commands processed
- Commands per source
- Error count
- Last command and timestamp
- Command history (last 100 commands)

### 2. Command Server (`command_server.py`)

Receives commands from Jetson vision system via ZMQ REP socket on port 5557.

**Process Flow:**
1. Receive command from Jetson
2. Process through aggregator with HIGH priority
3. Forward validated command to RPi
4. Send JSON response back to Jetson

**Response Format:**
```json
{
  "status": "ok",
  "cmd": "forward 2",
  "original": "forward 2",
  "forwarded": true,
  "message": "Command processed successfully"
}
```

### 3. Updated Client Modes

#### Sequence Mode (`seq_mode.py`)
- All commands validated through aggregator
- Commands marked as `CommandSource.MANUAL`
- Invalid commands are rejected with error message

#### Controller Mode (`controller_mode.py`)
- D-pad and button commands validated
- Commands marked as `CommandSource.CONTROLLER`
- Emergency stop (X button) has HIGH priority
- Regular movements have NORMAL priority

### 4. Server Main (`main.py`)

Enhanced menu with new statistics option:

```
========================
  AUTO-BOT CLIENT MENU 
========================
1. Sequence mode (text commands / sequences with STOP interrupt)
2. Controller mode (Xbox controller)
3. Server mode only (receive from Jetson, no manual control)
s. Show statistics
q. Exit
```

**Statistics Display:**
- Total commands processed
- Error count
- Commands by source (jetson, controller, manual)
- Last command and age
- Recent command history (last 5)

## Usage Examples

### Starting the Client

```bash
cd server
python3 main.py
```

The command server starts automatically in the background, listening for Jetson commands.

### Sending Commands from Jetson

```python
from vision_client import VisionClient

client = VisionClient()
client.connect()

# Send command - it will be processed through aggregator
response = client.send_command("left 1.5")
print(response)  # {'status': 'ok', 'cmd': 'left 1.5', ...}
```

### Viewing Statistics

Press `s` in the main menu to see:
```
=== Command Aggregator Statistics ===
Total commands processed: 127
Errors: 3
Commands by source:
  - jetson: 45
  - controller: 62
  - manual: 20
Last command: forward 2
Last command age: 1.23s
History size: 100

=== Recent Commands (last 5) ===
[1702834567.12] controller -> forward 0.5
[1702834567.45] controller -> right 0.3
[1702834568.89] jetson     -> left 1.0
[1702834569.12] manual     -> stop
[1702834570.34] controller -> forward 0.5
```

## Configuration

All settings are in `.env` file:

```bash
# Network
RPI_HOST=192.168.10.200
ZMQ_PORT=5555              # Client -> RPi commands
HEARTBEAT_PORT=5556        # RPi -> Client heartbeat
CLIENT_SERVER_PORT=5557    # Jetson -> Client commands

# Movement
DUR_FORWARD=0.5
DUR_BACKWARD=0.5
DUR_TURN=0.3

# Control
SEND_COOLDOWN=0.05
REPEAT_HOLD_INTERVAL=0.15
```

## Benefits

1. **Centralized Control**: All commands flow through one validation point
2. **Better Debugging**: Full command history and statistics
3. **Improved Safety**: Command validation prevents invalid operations
4. **Multi-Source Support**: Seamless integration of autonomous and manual control
5. **Extensibility**: Easy to add new command sources or processing rules
6. **Monitoring**: Real-time statistics and health tracking

## Code Quality Improvements

- ✅ All comments in English
- ✅ Comprehensive docstrings
- ✅ Type hints for better IDE support
- ✅ Proper error handling
- ✅ Thread-safe operations
- ✅ Logging for debugging
- ✅ Configuration via environment variables

## Testing the Aggregator

Run the aggregator standalone to test validation:

```bash
cd client
python3 command_aggregator.py
```

This will run built-in tests showing:
- Command validation
- Processing from different sources
- Statistics tracking
- History management

## Future Enhancements

Possible additions:
- Command queuing for busy periods
- Advanced priority scheduling
- Command filtering/transformation rules
- Web API endpoint for remote control
- Real-time monitoring dashboard
- Command replay functionality

## Troubleshooting

**Problem**: Commands from Jetson not working
- Check CLIENT_SERVER_PORT (default 5557) is open
- Verify Jetson has correct CLIENT_IP in its `.env`
- Check command server is running: look for `[CMD SERVER] Listening on...`

**Problem**: Statistics not updating
- Ensure all code paths use `aggregator.process_command()`
- Check for errors in logs

**Problem**: Invalid commands passing through
- Review `allowed_commands` set in `command_aggregator.py`
- Add new commands to the allowed list as needed

---

**Author**: Auto-Bot Team  
**Last Updated**: 2024-12-17  
**Version**: 1.0
