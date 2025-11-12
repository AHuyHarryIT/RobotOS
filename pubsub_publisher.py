import os
import time
import zmq
from common.codec import Codec

# ENV cấu hình
COORD_PUB_BIND = os.getenv("COORD_PUB_BIND", "tcp://*:5556")  # Coordinator bind
TOPICS = {
    "cmd_mctl": b"cmd/mctl",
    "cmd_lock": b"cmd/lock",
    "sys_hb":   b"telemetry/sys",
}

ctx = zmq.Context.instance()
sock = ctx.socket(zmq.PUB)
sock.bind(COORD_PUB_BIND)
codec = Codec()

def send(topic: bytes, payload: dict):
    sock.send_multipart([topic, codec.pack(payload)])

print(f"[PUB] bind at {COORD_PUB_BIND}")
time.sleep(0.3)  # warm-up PUB/SUB

t = 0
locked = False
while True:
    # Heartbeat mỗi 1s
    send(TOPICS["sys_hb"], {"node": "coordinator", "alive": True})

    # Mỗi 3s: toggle lock/unlock (mã 101/110 như bạn dùng)
    if t % 3 == 0:
        locked = not locked
        send(TOPICS["cmd_lock"], {
            "state": "lock" if locked else "unlock",
            "code": "101" if locked else "110"
        })

    # Mỗi 0.5s: gửi lệnh set_vel
    left = 100 if not locked else 0
    right = 100 if not locked else 0
    send(TOPICS["cmd_mctl"], {
        "cmd": "set_vel",
        "left": left,
        "right": right,
        "timeout_ms": 800
    })

    t += 1
    time.sleep(0.5)
