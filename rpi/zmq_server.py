#!/usr/bin/env python3
"""
ZMQ Server for RPi GPIO control — Smooth Motion Edition

Receives motion commands from miniPC via ZMQ REP socket and controls
GPIO pins through the MotionController for smooth, responsive movement.

Supported command formats:
  - Timed:      "forward 2", "left 1.5", "lock", "stop"
  - Hold:       "hold:forward", "hold:left" (continuous until changed)
  - Sequence:   "seq forward 2; right 1; lock 0.5; stop"
  - JSON:       {"mode":"seq","cmd":"forward 2; right 1; stop"}
  - Emergency:  "stop" (always immediate, highest priority)

Author: Auto-Bot Team
"""

import json
import threading
import time
from typing import Optional
import os

import zmq

from gpio_driver import GPIODriver
from parser import parse_command, split_sequence
from states import STATES, ALIASES, DEFAULT_STEP_DURATION, PAUSE_AFTER_SEQ_SECONDS, PINS
from motion_controller import MotionController

from dotenv import load_dotenv

load_dotenv()

# ==== NETWORK CONFIG FROM ENV ====
ZMQ_PORT = int(os.getenv("ZMQ_PORT", "5555"))
HEARTBEAT_PORT = int(os.getenv("HEARTBEAT_PORT", "5556"))
BIND_ADDR = f"tcp://0.0.0.0:{ZMQ_PORT}"
HB_ADDR = f"tcp://0.0.0.0:{HEARTBEAT_PORT}"


# ===== Parse sequence into steps =====
def parse_sequence_steps(seq_str, default_duration=DEFAULT_STEP_DURATION):
    """Parse sequence string 'forward 2; right 1; stop' into [(key, dur), ...]"""
    tokens = split_sequence(seq_str)
    steps = []
    for t in tokens:
        parsed = parse_command(t)
        if not parsed:
            print(f"[SEQ] Skipping invalid token: {t!r}")
            continue
        key, dur = parsed
        if dur is None and key != "SLEEP":
            dur = default_duration
        elif dur is None:
            dur = 0.0
        steps.append((key, dur))
    return steps


# ===== Handle payload from miniPC =====
def handle_payload(controller: MotionController, payload: str) -> dict:
    """
    Process incoming command and route to appropriate MotionController method.

    payload formats:
      - Text: "forward 2", "stop", "hold:left", "seq forward 2; right 1; stop"
      - JSON: {"mode":"seq"|"single"|"auto", "cmd":"..."}
    """
    text = payload.strip()
    if not text:
        return {"ok": False, "error": "empty_payload"}

    # Try JSON first
    mode = "auto"
    cmd_str = text
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "cmd" in obj:
            cmd_str = obj["cmd"]
            mode = obj.get("mode", "auto")
    except json.JSONDecodeError:
        pass

    cmd_lower = cmd_str.strip().lower()

    # === PRIORITY: STOP — always immediate ===
    if cmd_lower in ("stop", "s", "seq stop"):
        print("[SERVER] Emergency STOP requested!")
        controller.stop()
        return {"ok": True, "mode": "stop", "cmd": "stop"}

    # === HOLD MODE: "hold:forward", "hold:left", etc. ===
    if cmd_lower.startswith("hold:"):
        state_name = cmd_lower[5:].strip()
        state_key = ALIASES.get(state_name)
        if state_key and state_key not in ("STOP", "SLEEP"):
            controller.hold(state_key)
            return {"ok": True, "mode": "hold", "state": state_key}
        return {"ok": False, "error": f"invalid hold target: {state_name}"}

    # === SEQUENCE MODE ===
    is_sequence = False
    if mode == "seq":
        is_sequence = True
        if cmd_lower.startswith("seq "):
            cmd_str = cmd_str[4:].strip()
    elif mode == "single":
        is_sequence = False
    else:   # auto-detect
        if cmd_lower.startswith("seq "):
            is_sequence = True
            cmd_str = cmd_str[4:].strip()

    if is_sequence:
        steps = parse_sequence_steps(cmd_str)
        if not steps:
            return {"ok": False, "error": "no valid steps in sequence"}
        print(f"[SERVER] start sequence: {len(steps)} steps, cmd={cmd_str!r}")
        controller.sequence(steps)
        return {"ok": True, "mode": "seq", "cmd": cmd_str, "steps": len(steps)}

    # === SINGLE TIMED COMMAND ===
    parsed = parse_command(cmd_str)
    if not parsed:
        return {"ok": False, "error": f"unknown command: {cmd_str}"}

    key, dur = parsed
    if key == "SLEEP":
        dur = dur if dur is not None else DEFAULT_STEP_DURATION
    elif dur is None:
        dur = DEFAULT_STEP_DURATION

    print(f"[SERVER] start_motion: timed, cmd={key!r}, dur={dur:.3f}s")
    controller.timed(key, dur)
    return {"ok": True, "mode": "single", "cmd": key, "duration": dur}


# ===== Heartbeat publisher =====
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

    # ★ Use MotionController instead of raw thread management
    controller = MotionController(driver)

    ctx = zmq.Context.instance()

    # Heartbeat thread
    hb_thread = threading.Thread(target=heartbeat_loop, args=(ctx,), daemon=True)
    hb_thread.start()

    sock = ctx.socket(zmq.REP)
    sock.bind(BIND_ADDR)

    print(f"[ZMQ SERVER] Listening on {BIND_ADDR}, pins={PINS}")
    print("  Commands:")
    print("  - Timed:    'forward 2', 'left 1.5', 'lock', 'stop'")
    print("  - Hold:     'hold:forward', 'hold:left' (continuous until changed)")
    print("  - Sequence: 'seq forward 2; right 1; lock 0.5; stop'")
    print("  - JSON:     '{\"mode\":\"seq\",\"cmd\":\"forward 2; right 1; stop\"}'")
    print("  - STOP:     send 'stop' at any time for emergency stop")

    try:
        while True:
            try:
                raw = sock.recv()   # blocking
                payload = raw.decode("utf-8", errors="replace")
                print(f"\n[ZMQ SERVER] ← {payload!r}")

                try:
                    result = handle_payload(controller, payload)
                    reply = {"status": "ok" if result.get("ok") else "error", **result}
                except Exception as e:
                    reply = {"status": "error", "ok": False, "error": str(e)}

                sock.send_string(json.dumps(reply))
                print(f"[ZMQ SERVER] → {reply}")

            except KeyboardInterrupt:
                print("\n[ZMQ SERVER] KeyboardInterrupt, exiting…")
                break

    finally:
        try:
            controller.stop()
        except Exception:
            pass
        driver.cleanup()
        print("[ZMQ SERVER] GPIO cleanup complete.")


if __name__ == "__main__":
    main()
