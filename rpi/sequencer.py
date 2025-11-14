import time
from typing import Optional, Tuple, List
from gpio_driver import GPIODriver
from parser import parse_command, split_sequence
from states import STATES, DEFAULT_STEP_DURATION, PAUSE_AFTER_SEQ_SECONDS

def set_state(driver: GPIODriver, key: str, hold_seconds: Optional[float] = None):
    """
    key: 'FORWARD','BACKWARD','LEFT','RIGHT','LOCK','UNLOCK','STOP','SLEEP'
    """
    if key == "SLEEP":
        dur = max(0.0, hold_seconds or 0.0)
        print(f"Sleep: {dur:.3f}s")
        time.sleep(dur)
        return

    bits = STATES.get(key, STATES["STOP"])
    driver.apply_bits(bits)
    print(f"State: {key} -> {bits}")
    if hold_seconds is not None:
        time.sleep(max(0.0, hold_seconds))
        driver.stop()
        print("State: STOP")

def run_sequence(driver: GPIODriver, seq_str: str, default_duration: float = DEFAULT_STEP_DURATION,
                 pause_after_seq: float = PAUSE_AFTER_SEQ_SECONDS):
    """
    Execute a sequence like: 'forward 2; right 1; lock 0.5; stop'
    After completion, hold STOP for `pause_after_seq` seconds.
    """
    tokens = split_sequence(seq_str)
    steps: List[Tuple[str, Optional[float]]] = []

    for t in tokens:
        parsed = parse_command(t)
        if not parsed:
            print(f"[Skip] Invalid token: '{t}'")
            continue
        key, dur = parsed
        if dur is None and key not in ("SLEEP",):
            dur = default_duration
        steps.append((key, dur))

    if not steps:
        print("No valid steps to run.")
        return

    print("=== Running sequence ===")
    for i, (key, dur) in enumerate(steps, 1):
        if key == "STOP" and (dur is None or dur <= 0):
            driver.stop()
            print("State: STOP")
            continue
        set_state(driver, key, hold_seconds=dur)

    # Pause after sequence
    print(f"=== Sequence complete — pausing {pause_after_seq:.3f}s ===")
    driver.stop()
    time.sleep(max(0.0, pause_after_seq))

def run_single(driver: GPIODriver, cmd: str, default_duration: float = DEFAULT_STEP_DURATION):
    parsed = parse_command(cmd)
    if not parsed:
        print("Unknown command. Try: forward, backward, left, right, lock, unlock, stop, sleep.")
        return
    key, dur = parsed
    if dur is None and key != "SLEEP":
        dur = default_duration
    set_state(driver, key, hold_seconds=dur)

