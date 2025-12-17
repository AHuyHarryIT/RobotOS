#!/usr/bin/env python3
"""
ZMQ Client Module

Handles ZeroMQ communication with RPi server:
    - REQ/REP pattern for sending commands to RPi
    - PUB/SUB pattern for receiving heartbeat from RPi
    - Connection management and error handling

Architecture:
    Client [REQ] ──5555──> [REP] RPi Server
    Client [SUB] <─5556── [PUB] RPi Server (heartbeat)

Author: Auto-Bot Team
"""
import time
import threading
import zmq

from config import ADDR, HB_ADDR

# Global heartbeat tracking
last_heartbeat_ts = 0.0
heartbeat_lock = threading.Lock()


def start_heartbeat_subscriber(ctx: zmq.Context):
    """
    Start background thread to listen for heartbeat from RPi.
    
    The heartbeat is a periodic PUB/SUB message that indicates
    the RPi server is alive and responsive.
    
    Args:
        ctx: ZMQ Context instance
    """
    global last_heartbeat_ts

    sub = ctx.socket(zmq.SUB)
    sub.connect(HB_ADDR)
    sub.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all messages
    print(f"[HB] Subscribed to RPi heartbeat at {HB_ADDR}")

    def loop():
        """Heartbeat listener loop (runs in background thread)."""
        global last_heartbeat_ts
        while True:
            try:
                msg = sub.recv_json()
                if msg.get("type") == "heartbeat":
                    ts = msg.get("ts", time.time())
                    with heartbeat_lock:
                        last_heartbeat_ts = time.time()
                    # Uncomment for debugging:
                    # print(f"[HB] heartbeat ts={ts}")
            except Exception as e:
                print(f"[HB] Error in heartbeat subscriber: {e}")
                time.sleep(1.0)

    # Start daemon thread (will exit when main program exits)
    t = threading.Thread(target=loop, daemon=True)
    t.start()


def init_zmq():
    """
    Initialize ZMQ connection to RPi.
    
    Sets up:
        1. REQ socket for sending commands
        2. SUB socket for receiving heartbeat (background thread)
    
    Returns:
        Tuple of (context, req_socket)
    """
    ctx = zmq.Context.instance()
    sock = ctx.socket(zmq.REQ)
    sock.connect(ADDR)
    print(f"[NET] Connected to RPi at {ADDR}")
    
    # Start heartbeat monitoring
    start_heartbeat_subscriber(ctx)
    
    return ctx, sock


def send_command(sock, cmd: str):
    """
    Send a command to RPi via REQ/REP pattern.
    
    This is a blocking call that waits for RPi to acknowledge.
    
    Args:
        sock: ZMQ REQ socket
        cmd: Command string to send
    """
    try:
        print(f"[NET] -> Sending to RPi: {cmd!r}")
        sock.send_string(cmd)
        
        # Wait for reply from RPi
        reply = sock.recv().decode("utf-8", errors="replace")
        print(f"[NET] <- Reply from RPi: {reply}")
    except Exception as e:
        print(f"[NET] ERROR: {e}")


def get_heartbeat_age() -> float:
    """
    Get time elapsed since last heartbeat.
    
    Returns:
        Seconds since last heartbeat (float('inf') if never received)
    """
    with heartbeat_lock:
        ts = last_heartbeat_ts
    if ts <= 0:
        return float("inf")
    return time.time() - ts
