# zmq_client.py
import time
import threading
import zmq

from config import ADDR, HB_ADDR

last_heartbeat_ts = 0.0
heartbeat_lock = threading.Lock()


def start_heartbeat_subscriber(ctx: zmq.Context):
    """Listen heartbeat from RPi via PUB/SUB."""
    global last_heartbeat_ts

    sub = ctx.socket(zmq.SUB)
    sub.connect(HB_ADDR)
    sub.setsockopt_string(zmq.SUBSCRIBE, "")
    print(f"[HB] Subscribed to RPi heartbeat at {HB_ADDR}")

    def loop():
        global last_heartbeat_ts
        while True:
            try:
                msg = sub.recv_json()
                if msg.get("type") == "heartbeat":
                    ts = msg.get("ts", time.time())
                    with heartbeat_lock:
                        last_heartbeat_ts = time.time()
                    # print(f"[HB] heartbeat ts={ts}")
            except Exception as e:
                print(f"[HB] Error in heartbeat subscriber: {e}")
                time.sleep(1.0)

    t = threading.Thread(target=loop, daemon=True)
    t.start()


def init_zmq():
    """Init REQ socket + heartbeat subscriber."""
    ctx = zmq.Context.instance()
    sock = ctx.socket(zmq.REQ)
    sock.connect(ADDR)
    print(f"[NET] Connected to {ADDR}")
    start_heartbeat_subscriber(ctx)
    return ctx, sock


def send_command(sock, cmd: str):
    """Send text command to RPi (REQ/REP)."""
    try:
        print(f"[NET] -> {cmd!r}")
        sock.send_string(cmd)
        reply = sock.recv().decode("utf-8", errors="replace")
        print(f"[NET] <- {reply}")
    except Exception as e:
        print(f"[NET] ERROR: {e}")


def get_heartbeat_age() -> float:
    """Return how many seconds since last heartbeat."""
    with heartbeat_lock:
        ts = last_heartbeat_ts
    if ts <= 0:
        return float("inf")
    return time.time() - ts
