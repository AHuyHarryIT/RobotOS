# Jetson Vision Client

This module runs on Jetson Nano/Xavier to process vision/camera data and send control commands to the miniPC client.

## Architecture

```
[Jetson Vision] --ZMQ:5557--> [miniPC Client]
```

The Jetson processes camera/calibration data and sends high-level commands like:
- `left` / `right` - steering adjustments
- `stop` - emergency stop
- `forward 2` / `backward 1.5` - movement with duration
- `lock` / `unlock` - parking brake control

## Setup

1. **Install dependencies:**
   ```bash
   cd jetson/
   pip3 install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   nano .env
   ```
   
   Set the miniPC client IP address:
   ```
   CLIENT_IP=192.168.10.100  # Your miniPC IP
   CLIENT_PORT=5557
   ```

## Usage

### Interactive Testing Mode
Test the connection and send commands manually:
```bash
python3 vision_client.py interactive
```

Commands you can try:
```
vision> left
vision> right
vision> stop
vision> forward 2
vision> seq forward 1; right 0.5; stop
```

### Calibration Demo
Run a pre-defined test sequence:
```bash
python3 vision_client.py demo
```

### Integration with Calibration Code

Use `VisionClient` in your calibration/vision code:

```python
from vision_client import VisionClient

# Initialize client
vision = VisionClient()
vision.connect()

# Process camera frame
direction = calibrate_direction(frame)

# Send command based on vision
if direction == "left":
    vision.send_command("left 0.3")
elif direction == "right":
    vision.send_command("right 0.3")
elif direction == "stop":
    vision.send_command("stop")

# Close when done
vision.close()
```

## Integration with Existing Calibration Code

To integrate with your existing calibration code (in `trash_code/AUTO_CAR_V2/`):

1. Import the vision client
2. Initialize connection
3. Send commands based on detection results

Example:
```python
from vision_client import VisionClient

vision_client = VisionClient()
vision_client.connect()

# In your main detection loop
while True:
    ret, frame = cap.read()
    
    # Your existing detection logic
    result = detect_lane_and_objects(frame)
    
    # Send command based on result
    if result == "turn_left":
        vision_client.send_command("left 0.3")
    elif result == "turn_right":
        vision_client.send_command("right 0.3")
    elif result == "obstacle_detected":
        vision_client.send_command("stop")
    else:
        vision_client.send_command("forward 0.5")
```

## Troubleshooting

**Connection timeout:**
- Check if miniPC client is running: `docker ps` on miniPC
- Verify CLIENT_IP is correct
- Test connectivity: `ping <CLIENT_IP>`
- Check firewall rules: `sudo ufw status`

**Commands not executing:**
- Check client logs on miniPC
- Verify RPi is connected to client
- Test with `vision_client.py interactive` first

## API Reference

### VisionClient Class

**`connect()`**
- Establishes connection to miniPC client
- Returns: None

**`send_command(cmd: str) -> dict`**
- Sends a command to the client
- Args: `cmd` - command string
- Returns: Response dict with `status`, `forwarded`, etc.

**`close()`**
- Closes the connection
- Returns: None

## Next Steps

- Integrate with your calibration code from `trash_code/AUTO_CAR_V2/`
- Add lane detection → command mapping logic
- Implement obstacle avoidance commands
- Add logging for debugging vision decisions
