import os
import time
import zmq

PI_REP_BIND = os.getenv("PI_REP_BIND", "tcp://*:5557")  # Pi bind

ctx = zmq.Context.instance()
rep = ctx.socket(zmq.REP)
rep.bind(PI_REP_BIND)
print(f"[REP] bind at {PI_REP_BIND}")

while True:
    req = rep.recv_json()
    cmd = req.get("cmd")
    if cmd == "set_vel":
        left, right = req.get("left", 0), req.get("right", 0)
        # Thực thi điều khiển động cơ tại đây
        print(f"[REP] set_vel left={left} right={right}")
        rep.send_json({"ok": True, "ts": time.time()})
    elif cmd == "estop":
        print("[REP] EMERGENCY STOP")
        rep.send_json({"ok": True, "ts": time.time()})
    else:
        rep.send_json({"ok": False, "error": "unknown_cmd"})