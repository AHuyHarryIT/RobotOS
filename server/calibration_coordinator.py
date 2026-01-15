#!/usr/bin/env python3
"""
Calibration Coordinator - Manages Jetson calibration integration with sequence commands.

This module coordinates between:
1. Sequence mode (motion commands execution)
2. Jetson calibration requests (pause motion during calibration)
3. Status signaling (both Jetson and server report when calibration completes)

Flow:
    - User runs sequence: "forward 2; right 1; lock 0.5; stop"
    - During forward motion: if Jetson sends calibration request:
        a. Pause the forward motion at current position
        b. Wait for Jetson to complete calibration  
        c. Server and Jetson send calibration_done status
        d. Resume the remaining forward motion
    - Special case: Turns (left/right) DO NOT trigger calibration listening
        - Turns continue uninterrupted even if calibration request arrives

Author: Auto-Bot Team
Date: 2025-01-15
"""

import threading
import time
import json
import zmq
from typing import Optional, Callable, Dict
from enum import Enum
from dotenv import load_dotenv
import os

load_dotenv()

# Configuration
JETSON_CALIBRATION_PORT = int(os.getenv("JETSON_CALIBRATION_PORT", "5558"))
CALIBRATION_HEARTBEAT_PORT = int(os.getenv("CALIBRATION_HEARTBEAT_PORT", "5559"))


class MotionPhase(Enum):
    """Enum for motion phases that can interact with calibration"""
    FORWARD = "forward"
    BACKWARD = "backward"
    LOCK = "lock"
    UNLOCK = "unlock"
    SLEEP = "sleep"
    STOP = "stop"
    
    # Turns do NOT support calibration interruption
    LEFT = "left"
    RIGHT = "right"
    
    @classmethod
    def supports_calibration(cls, phase):
        """Check if a motion phase supports calibration pause/resume"""
        return phase in (cls.FORWARD, cls.BACKWARD, cls.LOCK, cls.UNLOCK, cls.SLEEP)


class CalibrationCoordinator:
    """
    Coordinates calibration requests with ongoing motion commands.
    Manages pausing, resuming, and status signaling.
    """
    
    def __init__(self):
        """Initialize the calibration coordinator"""
        self.lock = threading.Lock()
        
        # Calibration state
        self.calibration_active = False
        self.calibration_paused_motion = None  # Store paused motion info
        self.calibration_event = threading.Event()  # Signaled when calibration completes
        
        # Callbacks
        self.on_pause_motion = None  # Called when motion needs to pause
        self.on_resume_motion = None  # Called when motion should resume
        
        # Statistics
        self.calibration_count = 0
        self.paused_motions_count = 0
        
        # ZMQ for bidirectional calibration signaling
        self.ctx = zmq.Context.instance()
        self.jetson_calibration_sock = None
        self.calibration_status_sock = None
        
        print("[CALIB] Calibration Coordinator initialized")
    
    def register_callbacks(
        self, 
        on_pause: Callable = None, 
        on_resume: Callable = None
    ):
        """
        Register callbacks for motion control.
        
        Args:
            on_pause: Callback when motion should pause (phase, remaining_duration)
            on_resume: Callback when motion should resume (phase, remaining_duration)
        """
        self.on_pause_motion = on_pause
        self.on_resume_motion = on_resume
        print("[CALIB] Motion control callbacks registered")
    
    def can_pause_for_calibration(self, motion_phase: str) -> bool:
        """
        Check if the current motion phase can be paused for calibration.
        Turns (left/right) cannot be paused.
        
        Args:
            motion_phase: The current motion phase
            
        Returns:
            bool: True if motion can be paused for calibration
        """
        try:
            phase = MotionPhase(motion_phase.lower())
            return MotionPhase.supports_calibration(phase)
        except (ValueError, AttributeError):
            return False
    
    def request_calibration_pause(
        self, 
        motion_phase: str, 
        elapsed: float, 
        total_duration: float
    ) -> bool:
        """
        Jetson requests to pause current motion for calibration.
        
        Args:
            motion_phase: Current motion phase (e.g., "forward")
            elapsed: Time already elapsed in this motion
            total_duration: Total duration of this motion
            
        Returns:
            bool: True if pause was successful, False if motion cannot be paused
        """
        with self.lock:
            # Check if motion can be paused
            if not self.can_pause_for_calibration(motion_phase):
                print(f"[CALIB] Cannot pause {motion_phase} for calibration (turns not paused)")
                return False
            
            # Already in calibration
            if self.calibration_active:
                print("[CALIB] Calibration already in progress")
                return False
            
            # Calculate remaining duration
            remaining = total_duration - elapsed
            if remaining <= 0:
                print("[CALIB] Motion almost complete, no pause needed")
                return False
            
            # Mark calibration as active
            self.calibration_active = True
            self.calibration_paused_motion = {
                "phase": motion_phase,
                "remaining_duration": remaining,
                "elapsed": elapsed,
                "total": total_duration,
                "paused_at": time.time()
            }
            self.paused_motions_count += 1
            
            # Call pause callback if registered
            if self.on_pause_motion:
                self.on_pause_motion(motion_phase, remaining)
            
            print(f"[CALIB] Paused {motion_phase}: elapsed={elapsed:.2f}s, remaining={remaining:.2f}s")
            self.calibration_event.clear()
            return True
    
    def wait_for_calibration(self, timeout: float = 30.0) -> bool:
        """
        Wait for Jetson calibration to complete.
        
        Args:
            timeout: Maximum seconds to wait for calibration
            
        Returns:
            bool: True if calibration completed, False if timeout
        """
        print("[CALIB] Waiting for Jetson calibration to complete...")
        success = self.calibration_event.wait(timeout=timeout)
        
        if not success:
            print(f"[CALIB] WARNING: Calibration timeout after {timeout}s")
        
        return success
    
    def signal_calibration_complete(self, source: str = "jetson"):
        """
        Signal that calibration is complete.
        Can be called by either Jetson or server-side calibration detector.
        
        Args:
            source: Source of the signal ("jetson" or "server")
        """
        with self.lock:
            if not self.calibration_active:
                print(f"[CALIB] Calibration complete signal from {source} (not in calibration)")
                return
            
            self.calibration_count += 1
            self.calibration_active = False
            paused = self.calibration_paused_motion
            
            # Call resume callback if registered
            if self.on_resume_motion and paused:
                self.on_resume_motion(
                    paused["phase"], 
                    paused["remaining_duration"]
                )
            
            print(f"[CALIB] Calibration complete from {source}")
            print(f"[CALIB] Resuming: {paused['phase'] if paused else 'unknown'}")
            self.calibration_event.set()
    
    def get_calibration_status(self) -> Dict:
        """
        Get current calibration status.
        
        Returns:
            dict: Status information including whether calibration is active
        """
        with self.lock:
            return {
                "active": self.calibration_active,
                "paused_motion": self.calibration_paused_motion,
                "calibration_count": self.calibration_count,
                "paused_motions_count": self.paused_motions_count
            }
    
    def reset(self):
        """Reset calibration state (emergency stop or end of sequence)"""
        with self.lock:
            if self.calibration_active:
                print("[CALIB] Force-resetting active calibration")
            self.calibration_active = False
            self.calibration_paused_motion = None
            self.calibration_event.set()


# Global instance
_coordinator_instance = None
_coordinator_lock = threading.Lock()


def get_calibration_coordinator() -> CalibrationCoordinator:
    """Get or create the global calibration coordinator instance"""
    global _coordinator_instance
    
    with _coordinator_lock:
        if _coordinator_instance is None:
            _coordinator_instance = CalibrationCoordinator()
        return _coordinator_instance


def reset_calibration_coordinator():
    """Reset the global coordinator instance (for testing)"""
    global _coordinator_instance
    with _coordinator_lock:
        _coordinator_instance = None
