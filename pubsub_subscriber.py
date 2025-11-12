import os
import time
import zmq
from common.codec import Codec

COORD_PUB_ENDPOINT = os.getenv("COORD_PUB_ENDPOINT", "tcp://127.0.0.1:5556")  # connect tới publisher
SUB_TOPICS = [b"cmd/mctl", b"cmd/lock", b"telemetry/sys"]

ctx = zmq.Context.instance()
sock = ctx.socket(zmq.SUB)
sock.connect(COORD_PUB_ENDPOINT)
for t in SUB_TOPICS:
    sock.setsockopt(zmq.SUBSCRIBE, t)

print(f"[SUB] connect to {COORD_PUB_ENDPOINT}")
last_seq = {}
locked = False
last_cmd_ts = time.time()

def is_dup(topic: str, seq: int) -> bool:
    prev = last_seq.get(topic, -1)
    if seq <= prev:
        return True
    last_seq[topic] = seq
    return False

while True:
    try:
        topic, raw = sock.recv_multipart(flags=zmq.NOBLOCK)
        msg = Codec.unpack(raw)
        tname = topic.decode()

        if is_dup(tname, msg.get("seq", -1)):
            continue

        if tname == "cmd/lock":
            locked = (msg.get("code") == "101")
            print(f"[SUB] LOCK STATE -> {msg.get('state')} (locked={locked})")

        elif tname == "cmd/mctl":
            if not locked:
                left, right = msg.get("left", 0), msg.get("right", 0)
                print(f"[SUB] set_vel left={left} right={right}")
                last_cmd_ts = time.time()
            else:
                print("[SUB] IGNORED set_vel (locked)")

        elif tname == "telemetry/sys":
            # chỉ in cho thấy có heartbeat
            pass

    except zmq.Again:
        # Timeout lệnh → auto stop
        if time.time() - last_cmd_ts > 1.0:
            # Giả lập stop motor khi quá hạn
            print("[SUB] timeout → AUTO STOP")
            last_cmd_ts = time.time()
        time.sleep(0.05)