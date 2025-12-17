# Jetson Calibration Quick Start Guide

## What This Does

The Jetson processes camera frames and automatically:
1. **Detects lanes** and estimates driving angle
2. **Detects obstacles** (stop signs, objects)
3. **Sends commands** to miniPC client: `left`, `right`, `forward`, `stop`

## Prerequisites

✅ ROI configured (3-point triangular region)  
✅ miniPC client running with command server enabled  
✅ RPi connected and ready for GPIO control  
✅ Camera connected to Jetson  

## Quick Setup (5 minutes)

### Step 1: Install Dependencies
```bash
cd /root/test/RobotOS/jetson
pip3 install -r requirements.txt
```

### Step 2: Configure Network
```bash
# Create .env file
cat > .env << EOF
CLIENT_IP=192.168.1.100
CLIENT_PORT=5557
EOF
```
*Replace `192.168.1.100` with your miniPC IP*

### Step 3: Setup ROI (First Time Only)
```bash
cd AUTO_CAR_V2
python3 main.py
# Window opens - click 3 points on the road/lane area
# Press any key to save and exit
```

### Step 4: Test Connection
```bash
cd /root/test/RobotOS/jetson
python3 vision_client.py demo
```

Expected output:
```
[VISION] Connected to client at tcp://192.168.1.100:5557
[TEST] Sending: stop
[VISION] <- Reply: {'status': 'ok', 'forwarded': True}
```

### Step 5: Run Calibration
```bash
python3 calibration_main.py
```

## What You'll See

```
==================================================
  JETSON CALIBRATION STARTED
==================================================
Press 'q' in console or Ctrl+C to stop

[FRAME 1] Turn: FORWARD (angle: 90.2°)
[VISION] -> Sending: 'forward 0.5'
[VISION] <- Reply: {'status': 'ok', 'forwarded': True}

[FRAME 42] Turn: LEFT (angle: 102.8°)
[VISION] -> Sending: 'left 0.5'

[FRAME 156] STOP DETECTED! (hold: 20)
[VISION] -> Sending: 'stop'
```

## Command Mapping

| Vision Result | Angle Range | Command Sent | Meaning |
|--------------|-------------|--------------|---------|
| FORWARD | 85° - 95° | `forward 0.5` | Go straight |
| LEFT | > 95° | `left 0.5` | Turn left |
| RIGHT | < 85° | `right 0.5` | Turn right |
| STOP | Object detected | `stop` | Emergency stop |

## Configuration Files

### config.json - Main Settings
```json
{
  "CAM_DEVICE": 0,           // Camera ID
  "ACCEPTANCE": 5,           // ±5° tolerance for straight
  "STOP_HOLD_FRAMES": 20,    // Hold STOP for 20 frames
  "COMMAND_COOLDOWN": 0.3,   // Wait 0.3s between same commands
  "MOVEMENT_DURATION": 0.5   // Each movement is 0.5 seconds
}
```

### .env - Network Settings
```bash
CLIENT_IP=192.168.1.100    # Where to send commands
CLIENT_PORT=5557           # Client command server port
```

## Common Issues

### ❌ Connection Failed
```
[VISION] Failed to connect. Check CLIENT_IP and CLIENT_PORT in .env
```
**Fix:** 
1. Check miniPC is running: `ssh user@192.168.1.100 'docker ps'`
2. Verify IP: `ping 192.168.1.100`
3. Test client: `python3 vision_client.py demo`

### ❌ Camera Not Found
```
[ERR] Could not open 0
```
**Fix:**
```bash
# Find camera
ls /dev/video*
v4l2-ctl --list-devices

# Update config.json
{
  "CAM_DEVICE": 1  // or "/dev/video1"
}
```

### ❌ ROI Not Set
```
[ERR] ROI not set (need 3 points).
```
**Fix:**
```bash
cd AUTO_CAR_V2
python3 main.py
# Click 3 points to define region
```

### ❌ Commands Not Executed on Robot
**Check chain:**
```bash
# 1. Jetson → Client connection
python3 vision_client.py demo

# 2. Client → RPi connection  
ssh minipc@192.168.1.100
cd /root/test/RobotOS/server
python3 main.py
# Choose option 3 (Server Only Mode)

# 3. RPi server running
ssh pi@rpi-ip
docker ps  # Should see auto-bot-rpi container
```

## Testing Workflow

### 1. Dry Run (No Commands)
```bash
python3 calibration_main.py --no-send
# Vision processing only, no commands sent
```

### 2. Interactive Test
```bash
python3 vision_client.py interactive
vision> left
vision> right
vision> stop
```

### 3. Demo Sequence
```bash
python3 vision_client.py demo
# Runs: stop → forward → left → right → backward → stop
```

### 4. Full Integration
```bash
python3 calibration_main.py
# Live vision → commands → robot movement
```

## Output Files

After running, check:
- **Video**: `output/result_combined.avi` - Visual recording
- **Logs**: `output/logs/detection_log.txt` - Frame-by-frame analysis

```bash
# View logs
tail -f output/logs/detection_log.txt

# Play video
vlc output/result_combined.avi
```

## Performance Tuning

### Sensitive Steering (More Turns)
```json
{
  "ACCEPTANCE": 3,           // Narrower straight zone
  "COMMAND_COOLDOWN": 0.2    // Faster response
}
```

### Stable Steering (Less Jitter)
```json
{
  "ACCEPTANCE": 8,           // Wider straight zone
  "COMMAND_COOLDOWN": 0.5    // Slower response
}
```

### Long STOP Duration
```json
{
  "STOP_HOLD_FRAMES": 30,    // Hold for 1 second @ 30fps
}
```

## Safety Tips

🛑 **Always test without commands first:**
```bash
python3 calibration_main.py --no-send
```

🛑 **Emergency stop:** Press `Ctrl+C` anytime

🛑 **Place robot on blocks** during initial testing

🛑 **Have manual controller ready** as backup

## Next Steps

✅ Test vision processing: `python3 calibration_main.py --no-send`  
✅ Verify commands received: `python3 vision_client.py demo`  
✅ Tune parameters in `config.json`  
✅ Run full system: `python3 calibration_main.py`  
✅ Monitor logs: `tail -f output/logs/detection_log.txt`  

## Full System Startup

```bash
# Terminal 1 - RPi
ssh pi@rpi
cd /root/test/RobotOS
./auto_update.sh

# Terminal 2 - miniPC Client
ssh user@minipc
cd /root/test/RobotOS/server
python3 main.py
# Choose option 3

# Terminal 3 - Jetson
cd /root/test/RobotOS/jetson
python3 calibration_main.py
```

## Support

- Main README: `/root/test/RobotOS/README.md`
- Architecture: `/root/test/RobotOS/DIAGRAM.md`
- Server docs: `/root/test/RobotOS/server/README.md`
