#!/usr/bin/env python3
"""
Smooth Motion Controller for RPi GPIO

Provides three movement modes for smooth robot operation:
- HOLD:     Set GPIO state and maintain until next command (real-time control)
- TIMED:    Set GPIO state for a specific duration, then auto-stop
- SEQUENCE: Execute a list of movements with smooth transitions (no stop gaps)

Key improvements over old thread-per-command model:
1. GPIO state changes are IMMEDIATE (no thread creation overhead)
2. Hold mode has no auto-stop — state persists until explicitly changed
3. Sequences transition directly between states (no stop between steps)
4. Cancel is fast (0.15s join timeout vs old 0.5s)

Thread-safe: only one operation runs at a time. New commands cancel previous.
Safety: all code paths guarantee GPIO stops on completion/cancellation.

Author: Auto-Bot Team
"""

import threading
import time
from typing import List, Tuple, Optional

from gpio_driver import GPIODriver
from states import STATES, DEFAULT_STEP_DURATION


def sleep_interruptible(seconds: float, cancel: threading.Event, step: float = 0.05):
    """Sleep in small increments so cancellation is near-instant."""
    remaining = max(0.0, seconds)
    while remaining > 0:
        if cancel.is_set():
            return
        dt = min(step, remaining)
        time.sleep(dt)
        remaining -= dt


class MotionController:
    """
    Manages GPIO state for smooth robot movement.

    Modes:
      hold     — GPIO stays in state until explicitly changed
      timed    — GPIO on for N seconds, then auto-stop
      sequence — list of (state, duration) with smooth transitions
    """

    def __init__(self, driver: GPIODriver):
        self.driver = driver
        self._state_lock = threading.Lock()   # protects _current_state, _mode
        self._worker_lock = threading.Lock()  # protects _worker lifecycle
        self._current_state = "STOP"
        self._mode = "idle"                   # idle | hold | timed | sequence
        self._cancel = threading.Event()
        self._worker: Optional[threading.Thread] = None

    # ── Public API ──────────────────────────────────────────────

    def hold(self, state_key: str):
        """
        Set GPIO and hold indefinitely until next command.
        Ideal for real-time control (joystick, vision steering).
        Returns immediately — no background thread needed.
        """
        self._cancel_worker()
        bits = STATES.get(state_key)
        if bits is None:
            print(f"[MOTION] Unknown state: {state_key}")
            return
        self.driver.apply_bits(bits)
        with self._state_lock:
            self._current_state = state_key
            self._mode = "hold"
        print(f"[MOTION] HOLD → {state_key} {bits}")

    def timed(self, state_key: str, duration: float):
        """
        Set GPIO for `duration` seconds, then auto-stop.
        Backward compatible with existing timed commands.
        """
        self._cancel_worker()

        if state_key == "SLEEP":
            with self._state_lock:
                self._mode = "timed"
            print(f"[MOTION] SLEEP {duration:.3f}s")
            self._start_worker(self._sleep_worker, (duration,))
            return

        bits = STATES.get(state_key)
        if bits is None:
            print(f"[MOTION] Unknown state: {state_key}")
            return

        # Set GPIO immediately, then schedule auto-stop in background
        self.driver.apply_bits(bits)
        with self._state_lock:
            self._current_state = state_key
            self._mode = "timed"
        print(f"[MOTION] TIMED → {state_key} {bits} for {duration:.3f}s")
        self._start_worker(self._timed_worker, (duration,))

    def sequence(self, steps: List[Tuple[str, float]]):
        """
        Execute steps with SMOOTH transitions (no stop between steps).

        Args:
            steps: list of (state_key, duration) tuples
        """
        self._cancel_worker()
        with self._state_lock:
            self._mode = "sequence"
        print(f"[MOTION] SEQUENCE → {len(steps)} steps")
        self._start_worker(self._sequence_worker, (steps,))

    def stop(self):
        """Immediate emergency stop. Always succeeds, always fast."""
        self._cancel_worker()
        self.driver.stop()
        with self._state_lock:
            self._current_state = "STOP"
            self._mode = "idle"
        print("[MOTION] STOP → all pins LOW")

    def get_state(self) -> dict:
        """Get current motion state (thread-safe)."""
        with self._state_lock:
            return {"state": self._current_state, "mode": self._mode}

    # ── Worker Management ───────────────────────────────────────

    def _cancel_worker(self):
        """Cancel any running background operation. Fast (≤0.15s)."""
        self._cancel.set()
        with self._worker_lock:
            w = self._worker
        if w is not None and w.is_alive():
            w.join(timeout=0.15)       # ← 0.15s vs old 0.5s
        with self._worker_lock:
            self._worker = None
        self._cancel = threading.Event()

    def _start_worker(self, target, args):
        """Launch a background worker thread."""
        cancel = self._cancel
        t = threading.Thread(
            target=target,
            args=args + (cancel,),
            daemon=True,
        )
        with self._worker_lock:
            self._worker = t
        t.start()

    # ── Worker Threads ──────────────────────────────────────────

    def _timed_worker(self, duration: float, cancel: threading.Event):
        """Wait for duration then auto-stop."""
        sleep_interruptible(duration, cancel)
        if not cancel.is_set():
            self.driver.stop()
            with self._state_lock:
                self._current_state = "STOP"
                self._mode = "idle"
            print("[MOTION] Timed complete → STOP")

    def _sleep_worker(self, duration: float, cancel: threading.Event):
        """Just sleep (no GPIO change)."""
        sleep_interruptible(duration, cancel)
        if not cancel.is_set():
            with self._state_lock:
                self._mode = "idle"
            print("[MOTION] Sleep complete")

    def _sequence_worker(self, steps: List[Tuple[str, float]], cancel: threading.Event):
        """
        Execute sequence with smooth GPIO transitions.
        KEY IMPROVEMENT: no driver.stop() between steps — GPIO transitions
        directly from one state to the next.
        """
        try:
            for i, (state_key, duration) in enumerate(steps):
                if cancel.is_set():
                    print("[MOTION] Sequence cancelled")
                    break

                if state_key == "SLEEP":
                    print(f"[MOTION] Seq[{i}] SLEEP {duration:.3f}s")
                    sleep_interruptible(duration, cancel)
                    continue

                if state_key == "STOP":
                    self.driver.stop()
                    with self._state_lock:
                        self._current_state = "STOP"
                    print(f"[MOTION] Seq[{i}] STOP")
                    if duration and duration > 0:
                        sleep_interruptible(duration, cancel)
                    continue

                bits = STATES.get(state_key)
                if bits is None:
                    print(f"[MOTION] Seq[{i}] Unknown: {state_key}, skipping")
                    continue

                # ★ SMOOTH TRANSITION: change GPIO directly, no stop gap! ★
                self.driver.apply_bits(bits)
                with self._state_lock:
                    self._current_state = state_key
                print(f"[MOTION] Seq[{i}] {state_key} → {bits} for {duration:.3f}s")
                sleep_interruptible(duration, cancel)

        finally:
            # Always stop at end of sequence
            self.driver.stop()
            with self._state_lock:
                self._current_state = "STOP"
                self._mode = "idle"
            print("[MOTION] Sequence end → STOP")
