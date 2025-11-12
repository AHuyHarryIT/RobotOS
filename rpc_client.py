import os
import time
import zmq

PI_REP_ENDPOINT = os.getenv("PI_REP_ENDPOINT", "tcp://127.0.0.1:5557")  # connect tới Pi REP

ctx = zmq.Context.instance()
req = ctx.socket(zmq.REQ)
req.connect(PI_REP_ENDPOINT)
print(f"[REQ] connect to {PI_REP_ENDPOINT}")

def call(payload: dict, timeout=2.0):
    poller = zmq.Poller()
    poller.register(req, zmq.POLLIN)
    req.send_json(payload)
    sockets = dict(poller.poll(timeout= int(timeout * 1000)))
    if sockets.get(req) == zmq.POLLIN:
        return req.recv_json()
    return {"ok": False, "error": "timeout"}

# Demo vòng lặp gọi service
for _ in range(3):
    print("[REQ] set_vel 80/80 →", call({"cmd": "set_vel", "left": 80, "right": 80}))
    time.sleep(0.5)

print("[REQ] estop →", call({"cmd": "estop"}))