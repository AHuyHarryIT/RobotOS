#!/usr/bin/env python3
import json
import time
import zmq

RPI_IP = "172.29.117.141"
PORT = 5555
CONNECT_ADDR = f"tcp://{RPI_IP}:{PORT}"

# timeout mỗi request (ms)
REQ_TIMEOUT_MS = 2000
# số lần thử lại khi timeout
REQ_RETRIES = 3

def send_command(sock, poller, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    for attempt in range(1, REQ_RETRIES + 1):
        print(f"[CLIENT] -> {payload} (attempt {attempt}/{REQ_RETRIES})")
        sock.send(data)

        # chờ phản hồi trong REQ_TIMEOUT_MS
        socks = dict(poller.poll(REQ_TIMEOUT_MS))
        if socks.get(sock) == zmq.POLLIN:
            reply = sock.recv()
            try:
                msg = json.loads(reply.decode("utf-8"))
            except Exception:
                msg = {"status": "error", "error": "invalid_json_reply"}
            print(f"[CLIENT] <- {msg}")
            return msg

        print("[CLIENT] No reply, reconnecting…")
        # nếu timeout: đóng và kết nối lại (mẫu “Lazy Pirate”)
        sock.setsockopt(zmq.LINGER, 0)
        sock.close()
        sock = ctx.socket(zmq.REQ)
        sock.connect(CONNECT_ADDR)
        poller.unregister(sock)  # đảm bảo không duplicate
        poller.register(sock, zmq.POLLIN)

    raise TimeoutError("Server seems offline or not responding.")

if __name__ == "__main__":
    ctx = zmq.Context.instance()
    sock = ctx.socket(zmq.REQ)
    sock.connect(CONNECT_ADDR)
    poller = zmq.Poller()
    poller.register(sock, zmq.POLLIN)

    try:
        # Ví dụ 1: unlock
        send_command(sock, poller, {"cmd": "unlock", "args": {}})

        # Ví dụ 2: move
        send_command(sock, poller, {
            "cmd": "move",
            "args": {"left": 120, "right": 120, "duration_ms": 500}
        })

        # Ví dụ 3: stop
        send_command(sock, poller, {"cmd": "stop", "args": {}})

        # Ví dụ 4: lock
        send_command(sock, poller, {"cmd": "lock", "args": {}})

    except Exception as e:
        print(f"[CLIENT] ERROR: {e}")
