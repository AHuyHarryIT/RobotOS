# 🚗 Jetson Calibration System - Complete Implementation

## ✅ What Has Been Created

### Core Files
1. **`calibration_main.py`** (NEW) ⭐
   - Main integrated vision + command system
   - Processes camera frames in real-time
   - Detects lanes and estimates angle
   - Detects obstacles/stop signs
   - Sends commands to miniPC client
   - Records output video and logs

2. **`vision_client.py`** (ENHANCED)
   - ZMQ client for sending commands
   - Connection management with reconnect
   - Interactive and demo modes
   - 5-second timeout protection

3. **`config.json`** (NEW)
   - Centralized configuration
   - Camera settings
   - Calibration parameters
   - Command timing controls

4. **`test_setup.py`** (NEW) 🔧
   - Pre-flight checklist script
   - Tests all dependencies
   - Validates configuration
   - Tests camera and network

### Documentation
- **`QUICKSTART.md`** - 5-minute setup guide
- **`README.md`** - Comprehensive documentation (updated)
- **`.env.example`** - Network configuration template

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────┐
│                  JETSON NANO                    │
│                                                 │
│  ┌─────────────┐      ┌──────────────────┐    │
│  │   Camera    │─────▶│ Vision Processing│    │
│  └─────────────┘      │  - Lane detect   │    │
│                       │  - Angle calc    │    │
│                       │  - Stop detect   │    │
│                       └────────┬─────────┘    │
│                                │               │
│                       ┌────────▼─────────┐    │
│                       │ Decision Logic   │    │
│                       │ LEFT/RIGHT/STOP  │    │
│                       └────────┬─────────┘    │
│                                │               │
│                       ┌────────▼─────────┐    │
│                       │  VisionClient    │    │
│                       │  (ZMQ REQ)       │    │
│                       └────────┬─────────┘    │
└────────────────────────────────┼──────────────┘
                                 │ tcp://CLIENT_IP:5557
                                 ▼
┌─────────────────────────────────────────────────┐
│              MINIPC CLIENT (Brain)              │
│  ┌──────────────────────────────────────────┐  │
│  │        Command Server (ZMQ REP)          │  │
│  │       Receives from Jetson/Xbox          │  │
│  └──────────────┬───────────────────────────┘  │
│                 │                               │
│  ┌──────────────▼───────────────────────────┐  │
│  │         Command Forwarder                │  │
│  │       (ZMQ REQ to RPi)                   │  │
│  └──────────────┬───────────────────────────┘  │
└─────────────────┼──────────────────────────────┘
                  │ tcp://RPI_IP:5555
                  ▼
┌─────────────────────────────────────────────────┐
│            RASPBERRY PI (Executor)              │
│  ┌──────────────────────────────────────────┐  │
│  │         ZMQ Server (REP)                 │  │
│  └──────────────┬───────────────────────────┘  │
│                 │                               │
│  ┌──────────────▼───────────────────────────┐  │
│  │        GPIO Controller                   │  │
│  │     (BCM pins 17, 27, 22)                │  │
│  └──────────────┬───────────────────────────┘  │
└─────────────────┼──────────────────────────────┘
                  │
                  ▼
            🚗 RC Car Motors
```

## 📋 Decision Logic

### Lane Following
```python
angle = calibrate.estimate_angle(frame)

if angle < 85°:
    send_command("right 0.5")    # Lane curves right
elif angle > 95°:
    send_command("left 0.5")     # Lane curves left
else:
    send_command("forward 0.5")  # Go straight
```

### Obstacle Detection
```python
if object_detected:
    send_command("stop")
    hold_counter = 20  # Hold for N frames
    
while hold_counter > 0:
    send_command("stop")
    hold_counter -= 1
    # Even if object disappears, keep stopping
```

### Command Throttling
```python
# Avoid spamming same command
if command == last_command and time_since_last < 0.3:
    skip()  # Don't send

# Exception: STOP always sends immediately
if command == "stop":
    send_immediately()
```

## 🚀 Usage Examples

### 1. Test Everything First
```bash
cd /root/test/RobotOS/jetson
python3 test_setup.py
```

Expected output:
```
✅ Python 3.8
✅ opencv-python
✅ numpy
✅ pyzmq
✅ .env file exists
✅ CLIENT_IP = 192.168.1.100
✅ config.json loaded
✅ ROI configured
✅ Camera 0 works (640, 480, 3)
✅ Connected to client
✅ ALL TESTS PASSED (9/9)
```

### 2. Run Calibration (Simulation)
```bash
# No commands sent, just vision processing
python3 calibration_main.py --no-send
```

### 3. Run Calibration (Live)
```bash
# Full integration with command sending
python3 calibration_main.py
```

Output:
```
==================================================
  JETSON CALIBRATION STARTED
==================================================

[FRAME 1] Turn: FORWARD (angle: 89.5°)
[VISION] -> Sending: 'forward 0.5'
[VISION] <- Reply: {'status': 'ok', 'forwarded': True}

[FRAME 23] Turn: LEFT (angle: 98.2°)
[VISION] -> Sending: 'left 0.5'

[FRAME 156] STOP DETECTED! (hold: 20)
[VISION] -> Sending: 'stop'
[VISION] <- Reply: {'status': 'ok', 'forwarded': True}
```

### 4. Interactive Testing
```bash
python3 vision_client.py interactive
```

## ⚙️ Configuration

### config.json - Key Parameters
```json
{
  "CAM_DEVICE": 0,              // Camera device ID
  "W": 640,                     // Frame width
  "H": 480,                     // Frame height
  
  "ACCEPTANCE": 5,              // Angle tolerance (degrees)
                                // Smaller = more sensitive steering
                                
  "STOP_HOLD_FRAMES": 20,       // How long to hold STOP
                                // At 30fps, 20 frames ≈ 0.67 seconds
                                
  "COMMAND_COOLDOWN": 0.3,      // Min time between same commands
                                // Prevents command spam
                                
  "MOVEMENT_DURATION": 0.5,     // Duration for each movement
                                // Sent as "forward 0.5", "left 0.5"
  
  "SHOW_DEBUG_WINDOWS": false,  // Show OpenCV windows
                                // Set false for headless operation
                                
  "SEND_COMMANDS": true         // Enable/disable sending
                                // Can also use --no-send flag
}
```

### .env - Network Configuration
```bash
# IP of miniPC client (brain)
CLIENT_IP=192.168.1.100

# Port where client command server listens
CLIENT_PORT=5557
```

## 📊 Output Files

### Video Recording
- **Location**: `output/result_combined.avi`
- **Format**: 3-panel view (Original | Nonfloor mask | Danger zone)
- **Resolution**: `(W * 0.7 * 3) x (H * 0.7)` at 30 FPS

### Detection Logs
- **Location**: `output/logs/detection_log.txt`
- **Contains**:
  - Frame number
  - Detection status (STOP/FORWARD/LEFT/RIGHT)
  - Bounding box info
  - Angle estimation
  - Command sent
  - Processing time

Example log entry:
```
[2025-12-10 14:23:45] Frame 00156 | DETECT=True | HOLD=True(20) | 
x=245,y=180,w=120,h=95 | area%=4.23 | elong=1.26 | fill=0.82 | 
elapsed=15.3ms | angle: 1.5708 | angle_deg: 90.0 | Turn: STOP | 
Command: stop
```

## 🔧 Tuning Guide

### Problem: Robot turns too much
**Solution**: Increase acceptance angle
```json
{"ACCEPTANCE": 8}  // Wider straight zone
```

### Problem: Robot doesn't turn enough  
**Solution**: Decrease acceptance angle
```json
{"ACCEPTANCE": 3}  // Narrower straight zone
```

### Problem: Commands sent too frequently
**Solution**: Increase cooldown
```json
{"COMMAND_COOLDOWN": 0.5}
```

### Problem: Robot reacts too slowly
**Solution**: Decrease cooldown
```json
{"COMMAND_COOLDOWN": 0.1}
```

### Problem: STOP duration too short
**Solution**: Increase hold frames
```json
{"STOP_HOLD_FRAMES": 30}  // 1 second @ 30fps
```

### Problem: Too much noise in detection
**Solution**: Enable/tune blur
```json
{
  "USE_BLUR": true,
  "BLUR_KSIZE": 5  // Larger = more blur
}
```

## 🐛 Troubleshooting

### Camera Issues
```bash
# List cameras
ls /dev/video*

# Test camera
v4l2-ctl --list-devices

# Try different device in config.json
{"CAM_DEVICE": 1}
```

### Connection Issues
```bash
# Test network
ping 192.168.1.100

# Test ZMQ connection
python3 vision_client.py demo

# Check miniPC client is running
ssh user@192.168.1.100
docker ps  # Should see client container
```

### ROI Not Set
```bash
cd AUTO_CAR_V2
python3 main.py
# Click 3 points on road/lane
# Press any key to save
```

### Import Errors
```bash
pip3 install opencv-python numpy pyzmq python-dotenv
```

## 📁 File Structure

```
jetson/
├── calibration_main.py      ⭐ Main integrated program
├── vision_client.py          🌐 ZMQ client
├── test_setup.py             🔧 Pre-flight test
├── config.json               ⚙️ Configuration
├── .env                      🔐 Network settings
├── QUICKSTART.md             📖 Quick start guide
├── README.md                 📚 Full documentation
└── AUTO_CAR_V2/              👁️ Vision processing
    ├── main.py               (Original standalone)
    ├── calibrate.py          (Lane detection)
    ├── static_stop.py        (Object detection)
    ├── ROI.py                (Region of Interest)
    ├── helpers.py            (Utilities)
    └── roi_points.txt        (Saved ROI coords)
```

## 🎯 Next Steps

1. ✅ **Test setup**: `python3 test_setup.py`
2. ✅ **Test vision**: `python3 calibration_main.py --no-send`
3. ✅ **Test network**: `python3 vision_client.py demo`
4. ✅ **Tune parameters**: Edit `config.json`
5. ✅ **Run full system**: `python3 calibration_main.py`
6. ✅ **Monitor logs**: `tail -f output/logs/detection_log.txt`

## 🔗 Related Documentation

- **Main System**: `/root/test/RobotOS/README.md`
- **Architecture**: `/root/test/RobotOS/DIAGRAM.md`
- **Client Docs**: `/root/test/RobotOS/client/README.md`
- **RPi Docs**: `/root/test/RobotOS/rpi/README.md`

## 📞 Support

If you encounter issues:
1. Run `python3 test_setup.py` to diagnose
2. Check logs in `output/logs/`
3. Review `QUICKSTART.md` for common fixes
4. Verify each component individually (camera → vision → network → client → rpi)

---

**Status**: ✅ Implementation Complete  
**Version**: 1.0  
**Date**: December 10, 2025
