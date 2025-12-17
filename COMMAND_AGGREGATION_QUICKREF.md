# Command Aggregation - Quick Reference

## 📋 Quick Facts

- **Module**: `client/command_aggregator.py`
- **Pattern**: Singleton (one global instance)
- **Thread-Safe**: Yes
- **History Size**: Last 100 commands
- **Validation**: All commands checked before execution

## 🎯 Command Sources

| Source | Usage | Priority Default |
|--------|-------|------------------|
| `JETSON` | Autonomous vision control | HIGH (10) |
| `CONTROLLER` | Xbox manual control | NORMAL (5) |
| `MANUAL` | Text command input | NORMAL (5) |
| `SEQUENCE` | Sequence mode | NORMAL (5) |

## 📊 Priority Levels

| Level | Value | Use Case |
|-------|-------|----------|
| `HIGH` | 10 | Emergency stops, critical commands |
| `NORMAL` | 5 | Regular movement, manual control |
| `LOW` | 1 | Background tasks |

## ✅ Allowed Commands

```
forward, backward, left, right
stop, lock, unlock, sleep
seq <commands>
```

## 🔧 Using the Aggregator

### Get Instance (Singleton)
```python
from command_aggregator import get_aggregator

agg = get_aggregator()
```

### Process a Command
```python
from command_aggregator import CommandSource, CommandPriority

success, processed_cmd, msg = agg.process_command(
    command="forward 2",
    source=CommandSource.JETSON,
    priority=CommandPriority.HIGH
)

if success:
    # Send processed_cmd to RPi
    send_command(sock, processed_cmd)
else:
    print(f"Error: {msg}")
```

### Get Statistics
```python
stats = agg.get_stats()
print(f"Total: {stats['total_commands']}")
print(f"Errors: {stats['errors']}")
print(f"By source: {stats['by_source']}")
print(f"Last: {stats['last_command']}")
```

### Get History
```python
recent = agg.get_recent_history(5)
for entry in recent:
    print(f"{entry['timestamp']:.2f} | {entry['source']} | {entry['processed']}")
```

### Clear History
```python
agg.clear_history()
```

## 📝 Example Usage in Different Modes

### Command Server (Jetson Input)
```python
# In command_server.py
aggregator = get_aggregator()

# Process command from Jetson
success, processed, msg = aggregator.process_command(
    command=payload,
    source=CommandSource.JETSON,
    priority=CommandPriority.HIGH
)

if success:
    send_command(zmq_to_rpi_sock, processed)
```

### Controller Mode
```python
# In controller_mode.py
aggregator = get_aggregator()

# D-pad command
success, processed, msg = aggregator.process_command(
    command="forward 0.5",
    source=CommandSource.CONTROLLER,
    priority=CommandPriority.NORMAL
)

# Emergency stop (X button)
success, processed, msg = aggregator.process_command(
    command="stop",
    source=CommandSource.CONTROLLER,
    priority=CommandPriority.HIGH  # High priority!
)
```

### Sequence Mode
```python
# In seq_mode.py
aggregator = get_aggregator()

success, processed, msg = aggregator.process_command(
    command=user_input,
    source=CommandSource.MANUAL,
    priority=CommandPriority.NORMAL
)

if success:
    send_command(sock, processed)
else:
    print(f"Invalid command: {msg}")
```

## 🧪 Testing

### Run Test Suite
```bash
cd client
python3 test_aggregator.py
```

### Test Individual Command
```python
from command_aggregator import get_aggregator, CommandSource, CommandPriority

agg = get_aggregator()

# Test valid command
success, cmd, msg = agg.process_command("forward 2", CommandSource.MANUAL, CommandPriority.NORMAL)
print(f"Valid: {success} -> {cmd}")  # True -> "forward 2"

# Test invalid command
success, cmd, msg = agg.process_command("xyz", CommandSource.MANUAL, CommandPriority.NORMAL)
print(f"Invalid: {success} -> {msg}")  # False -> "Invalid command: xyz"
```

## 📈 Statistics Fields

```python
stats = {
    "total_commands": int,      # Total processed
    "by_source": {              # Count per source
        "jetson": int,
        "controller": int,
        "manual": int
    },
    "errors": int,              # Validation failures
    "last_command": str,        # Last processed command
    "last_command_age": float,  # Seconds since last command
    "history_size": int         # Number of entries in history
}
```

## 📚 History Entry Format

```python
entry = {
    "timestamp": float,      # Unix timestamp
    "raw": str,              # Original input
    "processed": str,        # Normalized command
    "source": str,           # CommandSource value
    "priority": int          # Priority level
}
```

## 🚨 Common Patterns

### Safe Command Sending
```python
aggregator = get_aggregator()

def safe_send(cmd, source=CommandSource.MANUAL):
    success, processed, msg = aggregator.process_command(
        cmd, source, CommandPriority.NORMAL
    )
    if success:
        send_command(sock, processed)
        return True
    else:
        print(f"Command rejected: {msg}")
        return False
```

### Emergency Stop
```python
# Always use HIGH priority for stops
safe_send("stop", CommandSource.CONTROLLER)
```

### Batch Processing
```python
commands = ["forward 1", "right 0.5", "stop"]
for cmd in commands:
    safe_send(cmd)
```

## 🔍 Debugging

### Enable Logging
The aggregator uses Python's logging module:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Recent Activity
```python
agg = get_aggregator()
for entry in agg.get_recent_history(10):
    print(f"{entry['timestamp']:.2f} | {entry['source']:10} | {entry['processed']}")
```

### Monitor Error Rate
```python
stats = agg.get_stats()
error_rate = stats['errors'] / stats['total_commands'] if stats['total_commands'] > 0 else 0
print(f"Error rate: {error_rate:.2%}")
```

## ⚙️ Configuration

Commands are defined in `command_aggregator.py`:

```python
# Add new allowed commands here
self.allowed_commands = {
    "forward", "backward", "left", "right",
    "stop", "lock", "unlock", "sleep",
    # Add more here...
}
```

## 📖 Documentation Links

- Full Guide: [COMMAND_AGGREGATION.md](COMMAND_AGGREGATION.md)
- Summary: [COMMAND_AGGREGATION_SUMMARY.md](COMMAND_AGGREGATION_SUMMARY.md)
- Architecture: [ARCHITECTURE.md](ARCHITECTURE.md)
- Main README: [README.md](README.md)

---

**Quick Help**: Run `python3 command_aggregator.py` for built-in tests  
**Status Check**: Press 's' in client menu for real-time statistics
