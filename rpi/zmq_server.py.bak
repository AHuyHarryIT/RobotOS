#!/usr/bin/env python3
import json
import threading
import time
from typing import Optional
import os

import zmq

from gpio_driver import GPIODriver
from parser import parse_command, split_sequence
from states import STATES, DEFAULT_STEP_DURATION, PAUSE_AFTER_SEQ_SECONDS, PINS

from dotenv import load_dotenv 

load_dotenv()

# ==== NETWORK CONFIG FROM ENV ====
ZMQ_PORT = int(os.getenv("ZMQ_PORT", "5555"))
HEARTBEAT_PORT = int(os.getenv("HEARTBEAT_PORT", "5556"))
BIND_ADDR = f"tcp://0.0.0.0:{ZMQ_PORT}"
HB_ADDR = f"tcp://0.0.0.0:{HEARTBEAT_PORT}"

# ===== Global motion state (1 thread điều khiển xe) =====
motion_thread: Optional[threading.Thread] = None
motion_cancel = threading.Event()
motion_lock = threading.Lock()   # bảo vệ motion_thread & motion_cancel


# ===== Helper: sleep có thể bị interrupt =====
def sleep_interruptible(seconds: float, cancel_event: threading.Event, step: float = 0.05):
    """Ngủ từng bước nhỏ, để có thể thoát nhanh khi có stop."""
    remaining = max(0.0, seconds)
    step = max(0.005, step)
    while remaining > 0:
        if cancel_event.is_set():
            break
        dt = min(step, remaining)
        time.sleep(dt)
        remaining -= dt


# ===== Thực thi 1 command (FORWARD, BACKWARD, LEFT, RIGHT, LOCK, UNLOCK, STOP, SLEEP) =====
def execute_token(driver: GPIODriver, token: str,
                  cancel_event: threading.Event,
                  default_duration: float = DEFAULT_STEP_DURATION):
    """Chạy 1 token (vd: 'forward 2', 'sleep 1') có hỗ trợ interrupt."""
    if cancel_event.is_set():
        return

    parsed = parse_command(token)
    if not parsed:
        print(f"[MOTION] Unknown token: {token!r}")
        return

    key, dur = parsed
    if key == "SLEEP":
        dur = default_duration if dur is None else dur
        print(f"[MOTION] Sleep {dur:.3f}s")
        sleep_interruptible(dur, cancel_event)
        return

    dur = default_duration if dur is None else dur
    bits = STATES.get(key)
    if bits is None:
        print(f"[MOTION] Unknown state key: {key}")
        return

    print(f"[MOTION] {key} for {dur:.3f}s -> bits={bits}")
    driver.apply_bits(bits)
    sleep_interruptible(dur, cancel_event)
    # Sau mỗi step, nếu chưa bị cancel thì có thể stop nhẹ nhàng
    if not cancel_event.is_set():
        driver.stop()


# ===== Thực thi sequence nhiều lệnh =====
def execute_sequence(driver: GPIODriver, seq: str,
                     cancel_event: threading.Event,
                     pause_after_seq: float = PAUSE_AFTER_SEQ_SECONDS):
    """
    seq: 'forward 2; right 1; lock 0.5; stop'
    """
    tokens = split_sequence(seq)
    print(f"[MOTION] Sequence tokens: {tokens}")
    for token in tokens:
        if cancel_event.is_set():
            print("[MOTION] Sequence interrupted by cancel flag.")
            break
        execute_token(driver, token, cancel_event)

    # Đảm bảo dừng xe
    driver.stop()
    # Nếu không bị interrupt thì giữ STOP 1 thời gian
    if not cancel_event.is_set():
        print(f"[MOTION] Sequence complete, pause {pause_after_seq:.3f}s")
        sleep_interruptible(pause_after_seq, cancel_event)


# ===== Worker thread chạy chuyển động =====
def motion_worker(driver: GPIODriver,
                  cmd_str: str,
                  is_sequence: bool,
                  cancel_event: threading.Event):
    """
    Chạy trong thread riêng. Khi cancel_event được set, worker sẽ thoát sớm nhất có thể.
    """
    try:
        if is_sequence:
            execute_sequence(driver, cmd_str, cancel_event)
        else:
            # Single command, vẫn dùng cùng cơ chế interrupt
            execute_token(driver, cmd_str, cancel_event)
            # Giữ STOP 1 chút nếu chưa bị cancel
            if not cancel_event.is_set():
                driver.stop()
    except Exception as e:
        print(f"[MOTION] Worker exception: {e}")
    finally:
        # đảm bảo cuối cùng xe luôn STOP
        driver.stop()
        print("[MOTION] Worker finished, STOP all pins.")


# ===== Quản lý thread =====
def stop_motion(driver: GPIODriver):
    """
    Yêu cầu dừng tất cả chuyển động hiện tại.
    - Set cancel_event để worker dừng càng sớm càng tốt.
    - Đợi một chút cho thread kết thúc.
    - Đảm bảo driver.stop()
    """
    global motion_thread, motion_cancel

    with motion_lock:
        t = motion_thread
        if not t:
            # không có chuyển động hiện tại
            driver.stop()
            return
        print("[MOTION] stop_motion() -> cancel current worker")
        motion_cancel.set()

    if t.is_alive():
        t.join(timeout=0.5)

    driver.stop()
    with motion_lock:
        motion_thread = None
        motion_cancel = threading.Event()
    print("[MOTION] All motion stopped.")


def start_motion(driver: GPIODriver, cmd_str: str, is_sequence: bool):
    """
    Bắt đầu motion mới:
    - Hủy motion cũ (nếu có).
    - Tạo thread mới chạy cmd_str.
    """
    global motion_thread, motion_cancel

    # Hủy motion cũ
    stop_motion(driver)

    with motion_lock:
        cancel_event = motion_cancel
        t = threading.Thread(
            target=motion_worker,
            args=(driver, cmd_str, is_sequence, cancel_event),
            daemon=True,
        )
        motion_thread = t

    print(f"[MOTION] Start new motion: is_sequence={is_sequence}, cmd={cmd_str!r}")
    t.start()


# ===== Xử lý message từ miniPC =====
def handle_payload(driver: GPIODriver, payload: str) -> dict:
    """
    payload:
      - Text: "forward 2", "stop", "seq forward 2; right 1; stop"
      - Hoặc JSON: {"mode":"seq"|"single"|"auto","cmd":"..."}
    """
    text = payload.strip()
    if not text:
        return {"ok": False, "error": "empty_payload"}

    # Thử parse JSON trước
    mode = "auto"
    cmd_str = text
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "cmd" in obj:
            cmd_str = obj["cmd"]
            mode = obj.get("mode", "auto")
    except json.JSONDecodeError:
        # không phải JSON -> giữ text
        pass

    cmd_lower = cmd_str.strip().lower()

    # === ƯU TIÊN: STOP NGAY LẬP TỨC ===
    # Bất cứ khi nào nhận 'stop', ta lập tức hủy mọi motion và dừng xe.
    if cmd_lower in ("stop", "s", "seq stop"):
        print("[SERVER] Emergency STOP requested!")
        stop_motion(driver)
        return {"ok": True, "mode": "stop", "cmd": "stop"}

    # auto/seq/single xác định có phải sequence không
    is_sequence = False
    if mode == "seq":
        is_sequence = True
        # nếu người dùng gửi 'seq ' ở đầu thì bỏ
        if cmd_lower.startswith("seq "):
            cmd_str = cmd_str[4:].strip()
    elif mode == "single":
        is_sequence = False
    else:  # auto
        if cmd_lower.startswith("seq "):
            is_sequence = True
            cmd_str = cmd_str[4:].strip()
        else:
            is_sequence = False

    # Các lệnh LOCK/UNLOCK hoặc move mới cũng sẽ HỦY motion cũ và tạo motion mới
    print(f"[SERVER] start_motion: is_sequence={is_sequence}, cmd={cmd_str!r}")
    start_motion(driver, cmd_str, is_sequence=is_sequence)
    return {"ok": True, "mode": "seq" if is_sequence else "single", "cmd": cmd_str}


def heartbeat_loop(ctx: zmq.Context):
    pub = ctx.socket(zmq.PUB)
    pub.bind(HB_ADDR)
    print(f"[HB] Heartbeat PUB on {HB_ADDR}")
    try:
        while True:
            msg = {
                "type": "heartbeat",
                "ts": time.time(),
                "status": "ok"
            }
            pub.send_json(msg)
            time.sleep(1.0)
    except Exception as e:
        print(f"[HB] Heartbeat loop stopped: {e}")
    finally:
        pub.close()


# ===== Main ZMQ loop =====
def main():
    driver = GPIODriver(PINS)
    driver.setup()

    ctx = zmq.Context.instance()

     # heartbeat thread
    hb_thread = threading.Thread(target=heartbeat_loop, args=(ctx,), daemon=True)
    hb_thread.start()
    
    sock = ctx.socket(zmq.REP)
    sock.bind(BIND_ADDR)

    print(f"[ZMQ SERVER] Listening on {BIND_ADDR}, pins={PINS}")
    print("  - Single:  'forward 2', 'backward', 'left 1.5', 'lock', 'unlock', 'stop'")
    print("  - Seq:     'seq forward 2; right 1; lock 0.5; stop'")
    print("  - JSON:    '{\"mode\":\"seq\",\"cmd\":\"forward 2; right 1; stop\"}'")
    print("  - EMERGENCY STOP: send 'stop' bất cứ lúc nào.")

    try:
        while True:
            try:
                raw = sock.recv()  # blocking chờ request
                payload = raw.decode("utf-8", errors="replace")
                print(f"[ZMQ SERVER] <- {payload!r}")

                try:
                    result = handle_payload(driver, payload)
                    reply = {"status": "ok" if result.get("ok") else "error", **result}
                except Exception as e:
                    reply = {"status": "error", "ok": False, "error": str(e)}

                sock.send_string(json.dumps(reply))
                print(f"[ZMQ SERVER] -> {reply}")

            except KeyboardInterrupt:
                print("\n[ZMQ SERVER] KeyboardInterrupt, exiting…")
                break

    finally:
        # dừng mọi thứ trước khi thoát
        try:
            stop_motion(driver)
        except Exception:
            pass
        driver.cleanup()
        print("[ZMQ SERVER] GPIO cleanup complete.")


if __name__ == "__main__":
    main()
