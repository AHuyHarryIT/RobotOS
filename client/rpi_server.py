#!/usr/bin/env python3
import json
import time
import zmq

BIND_ADDR = "tcp://0.0.0.0:5555"  # lắng nghe tất cả NIC

def handle_command(cmd: str, args: dict):
    """
    TODO: nối vào code điều khiển thật (GPIO, motor driver, v.v.)
    Ở đây chỉ mock bằng in ra console.
    """
    if cmd == "move":
        # ví dụ: args = {"left": 120, "right": 120, "duration_ms": 500}
        print(f"[ACT] Move L={args.get('left')} R={args.get('right')} for {args.get('duration_ms',0)} ms")
        time.sleep(args.get("duration_ms", 0) / 1000.0)
        return {"ok": True, "msg": "moved"}
    elif cmd == "lock":
        print("[ACT] Lock")
        return {"ok": True, "msg": "locked"}
    elif cmd == "unlock":
        print("[ACT] Unlock")
        return {"ok": True, "msg": "unlocked"}
    elif cmd == "stop":
        print("[ACT] Stop")
        return {"ok": True, "msg": "stopped"}
    else:
        print(f"[WARN] Unknown cmd: {cmd}")
        return {"ok": False, "error": f"unknown_cmd:{cmd}"}

def main():
    ctx = zmq.Context.instance()
    sock = ctx.socket(zmq.REP)
    # Tùy chọn: hạn chế queue để tránh tràn
    sock.setsockopt(zmq.RCVHWM, 100)
    sock.setsockopt(zmq.SNDHWM, 100)
    sock.bind(BIND_ADDR)
    print(f"[SERVER] Listening on {BIND_ADDR}")

    while True:
        try:
            raw = sock.recv()  # blocking
            msg = json.loads(raw.decode("utf-8"))
            cmd = msg.get("cmd")
            args = msg.get("args", {})
            print(f"[SERVER] <- {msg}")

            result = handle_command(cmd, args)
            reply = json.dumps({"status": "ok" if result.get("ok") else "error", **result})
            sock.send_string(reply)
        except KeyboardInterrupt:
            print("\n[SERVER] Shutting down...")
            break
        except Exception as e:
            # Trả lỗi để client biết
            err = json.dumps({"status": "error", "error": str(e)})
            try:
                sock.send_string(err)
            except Exception:
                pass
            print(f"[SERVER] Exception: {e}")

if __name__ == "__main__":
    main()
