# System Architecture Diagram

## Complete 3-Tier Data Flow

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                         JETSON NANO (Vision System)                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                       │
                         Camera Input  │  Vision Processing
                         Lane Detection│  Object Detection
                                       │
                                       ▼
                          ┌────────────────────────┐
                          │  vision_client.py      │
                          │  - Process frames      │
                          │  - Generate commands   │
                          │  - ZMQ REQ client      │
                          └────────────┬───────────┘
                                       │
                         ZMQ REQ       │  Commands: left, right, stop
                         tcp://CLIENT_IP:5557
                                       │
╔══════════════════════════════════════▼══════════════════════════════════════╗
║                      MINIPC CLIENT (Brain/Host)                             ║
╠═════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  ┌─────────────────────┐    ┌──────────────────┐    ┌──────────────────┐  ║
║  │  command_server.py  │    │  controller.py   │    │   seq_mode.py    │  ║
║  │  REP Socket :5557   │    │  Xbox gamepad    │    │  Manual REPL     │  ║
║  │  Receives: Jetson   │    │  D-pad + buttons │    │  Text commands   │  ║
║  └──────────┬──────────┘    └────────┬─────────┘    └────────┬─────────┘  ║
║             │                        │                       │             ║
║             └────────────────────────┼───────────────────────┘             ║
║                                      ▼                                      ║
║                          ┌───────────────────────┐                         ║
║                          │       main.py         │                         ║
║                          │   Central Coordinator │                         ║
║                          │   - Route commands    │                         ║
║                          │   - Decision logic    │                         ║
║                          │   - Validation        │                         ║
║                          └───────────┬───────────┘                         ║
║                                      │                                     ║
║                          ┌───────────▼───────────┐                         ║
║                          │    zmq_client.py      │                         ║
║                          │    REQ Socket         │                         ║
║                          │    Unified sender     │                         ║
║                          └───────────┬───────────┘                         ║
╚══════════════════════════════════════┼══════════════════════════════════════╝
                                       │
                         ZMQ REQ       │  Unified commands
                         tcp://RPI_HOST:5555
                                       │
╔══════════════════════════════════════▼══════════════════════════════════════╗
║                      RASPBERRY PI (GPIO Executor)                           ║
╠═════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║                          ┌───────────────────────┐                          ║
║                          │   zmq_server.py       │                          ║
║                          │   REP Socket :5555    │                          ║
║                          │   - Parse commands    │                          ║
║                          │   - Motion control    │                          ║
║                          └───────────┬───────────┘                          ║
║                                      │                                      ║
║                          ┌───────────▼───────────┐                          ║
║                          │    parser.py          │                          ║
║                          │    - Regex parsing    │                          ║
║                          │    - Command aliases  │                          ║
║                          └───────────┬───────────┘                          ║
║                                      │                                      ║
║                          ┌───────────▼───────────┐                          ║
║                          │   Motion Worker       │                          ║
║                          │   - Thread management │                          ║
║                          │   - Cancellation      │                          ║
║                          └───────────┬───────────┘                          ║
║                                      │                                      ║
║                          ┌───────────▼───────────┐                          ║
║                          │   gpio_driver.py      │                          ║
║                          │   - RPi.GPIO control  │                          ║
║                          │   - Pin management    │                          ║
║                          └───────────┬───────────┘                          ║
║                                      │                                      ║
╚══════════════════════════════════════┼══════════════════════════════════════╝
                                       │
                         GPIO Pins     │  BCM 17, 27, 22
                         3-bit control │  
                                       │
                          ┌────────────▼──────────┐
                          │   3-Pin Relay Board   │
                          │   - Motor control     │
                          └───────────┬───────────┘
                                      │
                          ┌───────────▼───────────┐
                          │    RC Car Motors      │
                          │    Movement execution │
                          └───────────────────────┘


═══════════════════════════════════════════════════════════════════════════════

## Heartbeat Monitoring (Reverse Direction)

                          ┌───────────────────────┐
                          │   RPi Heartbeat       │
                          │   PUB Socket :5556    │
                          │   Every 1 second      │
                          └───────────┬───────────┘
                                      │
                         ZMQ PUB      │  Status: ok
                         tcp://0.0.0.0:5556
                                      │
                          ┌───────────▼───────────┐
                          │   Client Subscriber   │
                          │   SUB Socket          │
                          │   Health monitoring   │
                          └───────────────────────┘


═══════════════════════════════════════════════════════════════════════════════

## State Encoding (GPIO Pins)

Pin Pattern (BCM 17, 27, 22):
  FORWARD:  (0, 0, 1)
  BACKWARD: (0, 1, 0)
  LEFT:     (0, 1, 1)
  RIGHT:    (1, 0, 0)
  LOCK:     (1, 0, 1)
  UNLOCK:   (1, 1, 0)
  STOP:     (0, 0, 0)  ← Safety default
```

## Key Design Principles

1. **Single Responsibility:**
   - Jetson: Vision only
   - Client: Coordination only
   - RPi: Execution only

2. **Thread Safety:**
   - Only ONE motion thread on RPi at a time
   - New commands cancel old motions
   - All motions end with STOP

3. **Fail-Safe:**
   - Emergency STOP on any error
   - GPIO cleanup in finally blocks
   - Heartbeat monitoring

4. **Extensibility:**
   - Easy to add new command sources
   - Centralized command validation
   - Modular component design
