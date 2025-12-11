#!/usr/bin/env python3
"""
System Visualization - Run this to see the complete architecture
"""

def print_architecture():
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                    AUTO-BOT 3-TIER ARCHITECTURE                           ║
║                     Jetson → miniPC → RPi → Robot                         ║
╚═══════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────┐
│                          TIER 1: JETSON (Vision)                        │
│                                                                         │
│  📹 Camera Feed                                                         │
│       ↓                                                                 │
│  🔍 Vision Processing                                                   │
│       ├─ Lane Detection (calibrate.py)                                 │
│       ├─ Angle Estimation                                              │
│       └─ Object Detection (static_stop.py)                             │
│       ↓                                                                 │
│  🧠 Decision Logic                                                      │
│       ├─ angle < 85° → RIGHT                                           │
│       ├─ angle > 95° → LEFT                                            │
│       ├─ 85° ≤ angle ≤ 95° → FORWARD                                   │
│       └─ object detected → STOP                                        │
│       ↓                                                                 │
│  📤 VisionClient (ZMQ REQ)                                              │
│       └─ Send commands: "left 0.5", "right 0.5", "stop", etc.         │
│                                                                         │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                  tcp://192.168.1.100:5557 (ZMQ REQ → REP)
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    TIER 2: MINIPC CLIENT (Brain)                        │
│                                                                         │
│  📥 Command Server (ZMQ REP) - Port 5557                                │
│       ├─ Receives from Jetson vision                                   │
│       ├─ Receives from Xbox controller                                 │
│       └─ Receives from sequence mode                                   │
│       ↓                                                                 │
│  ⚙️  Processing & Routing                                               │
│       ├─ Validates commands                                            │
│       ├─ Logs received commands                                        │
│       └─ Forwards to RPi executor                                      │
│       ↓                                                                 │
│  📤 ZMQ Client (ZMQ REQ) - To RPi                                       │
│       └─ Forward commands to GPIO executor                             │
│                                                                         │
│  💓 Heartbeat Monitor (ZMQ SUB) - Port 5556                             │
│       └─ Monitor RPi health status                                     │
│                                                                         │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                  tcp://192.168.31.211:5555 (ZMQ REQ → REP)
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      TIER 3: RASPBERRY PI (Executor)                    │
│                                                                         │
│  📥 ZMQ Server (REP) - Port 5555                                        │
│       └─ Receives commands from miniPC client                          │
│       ↓                                                                 │
│  ⚙️  Command Parser                                                     │
│       ├─ Parse "forward 2" → (FORWARD, 2.0)                           │
│       ├─ Parse "seq forward 2; right 1; stop" → tokens                │
│       └─ Handle STOP priority                                          │
│       ↓                                                                 │
│  🎬 Motion Controller (Threading)                                      │
│       ├─ One motion thread at a time                                   │
│       ├─ New commands cancel old ones                                  │
│       └─ Sleep with interruption support                               │
│       ↓                                                                 │
│  🔌 GPIO Driver (BCM pins 17, 27, 22)                                  │
│       └─ Set 3-bit patterns for motor control                          │
│                                                                         │
│  💓 Heartbeat Publisher (ZMQ PUB) - Port 5556                           │
│       └─ Send status to client every 1 second                          │
│                                                                         │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                          GPIO Pins
                             │
                             ▼
                    ┌────────────────┐
                    │   3-Pin Relay   │
                    │      Board      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │   🚗 RC Car    │
                    │     Motors     │
                    └────────────────┘

═══════════════════════════════════════════════════════════════════════════

🔄 COMMAND FLOW EXAMPLE: Lane Detected Going Left

  1. 📹 Jetson camera captures frame
  2. 🔍 calibrate.py detects lane angle = 102°
  3. 🧠 Decision: angle > 95° → TURN LEFT
  4. 📤 VisionClient sends: "left 0.5"
     └─ ZMQ REQ to tcp://192.168.1.100:5557
  
  5. 📥 miniPC receives: "left 0.5"
  6. ⚙️  miniPC validates and logs command
  7. 📤 miniPC forwards: "left 0.5"
     └─ ZMQ REQ to tcp://192.168.31.211:5555
  
  8. 📥 RPi receives: "left 0.5"
  9. ⚙️  Parser: ("LEFT", 0.5)
  10. 🎬 Cancel old motion, start new thread
  11. 🔌 GPIO: set pins (0,1,1) = LEFT
  12. ⏱️  Hold for 0.5 seconds
  13. 🔌 GPIO: set pins (0,0,0) = STOP
  14. ✅ Motion complete

  Total latency: ~50-100ms

═══════════════════════════════════════════════════════════════════════════

🛑 EMERGENCY STOP FLOW

  1. 📹 Jetson detects obstacle
  2. 🧠 Decision: STOP!
  3. 📤 VisionClient sends: "stop"
  4. 📥 miniPC receives: "stop" (priority handling)
  5. 📤 miniPC forwards immediately: "stop"
  6. 📥 RPi receives: "stop"
  7. 🎬 Cancel ALL motion threads immediately
  8. 🔌 GPIO: set pins (0,0,0) = STOP
  9. ⏱️  Hold STOP for 20 frames (even if object disappears)
  10. ✅ Robot stopped safely

═══════════════════════════════════════════════════════════════════════════

📊 GPIO PIN PATTERNS (BCM Mode)

  Pin 17 | Pin 27 | Pin 22 | Command
  -------+--------+--------+----------
    0    |   0    |   1    | FORWARD
    0    |   1    |   0    | BACKWARD  
    0    |   1    |   1    | LEFT
    1    |   0    |   0    | RIGHT
    1    |   0    |   1    | LOCK
    1    |   1    |   0    | UNLOCK
    0    |   0    |   0    | STOP

═══════════════════════════════════════════════════════════════════════════

🌐 NETWORK TOPOLOGY

  Jetson:        192.168.x.x  (Vision processor)
                    ↓ :5557
  miniPC Client: 192.168.1.100 (Central brain)
                    ↓ :5555
  RPi Server:    192.168.31.211 (GPIO executor)
                    ↓ GPIO
  RC Car:        Motors (Physical hardware)

═══════════════════════════════════════════════════════════════════════════

🚀 STARTUP SEQUENCE

  Terminal 1 - RPi:
    ssh pi@192.168.31.211
    cd /root/test/RobotOS
    ./auto_update.sh
    # Container starts on ports 5555 (commands) & 5556 (heartbeat)

  Terminal 2 - miniPC Client:
    ssh user@192.168.1.100
    cd /root/test/RobotOS/client
    python3 client_main.py
    # Choose option 3: Server Only Mode
    # Binds port 5557 for incoming commands

  Terminal 3 - Jetson:
    cd /root/test/RobotOS/jetson
    python3 test_setup.py         # Verify setup
    python3 calibration_main.py   # Start vision system

  ✅ System ready! Robot will respond to vision commands

═══════════════════════════════════════════════════════════════════════════

🔧 KEY FILES

  Jetson:
    - calibration_main.py   (Main vision program)
    - vision_client.py      (ZMQ sender)
    - config.json           (Tuning parameters)
    - .env                  (Network config)

  miniPC Client:
    - client_main.py        (Main entry point)
    - command_server.py     (Receives from Jetson)
    - controller_mode.py    (Xbox controller)
    - zmq_client.py         (Forwards to RPi)

  RPi:
    - zmq_server.py         (Command receiver)
    - gpio_driver.py        (Pin control)
    - parser.py             (Command parser)
    - states.py             (Pin patterns)

═══════════════════════════════════════════════════════════════════════════
""")

if __name__ == "__main__":
    print_architecture()
