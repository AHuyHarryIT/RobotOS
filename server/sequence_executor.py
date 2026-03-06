#!/usr/bin/env python3
"""
Enhanced Sequence Executor - Integrates with Jetson calibration system.

This module provides sequence execution with calibration pause/resume support.
When executing motion commands (forward, backward, etc.), it monitors for
Jetson calibration requests and pauses/resumes motion accordingly.

Key features:
    - Pausable motion execution (forward/backward/lock/unlock)
    - Non-interruptible turns (left/right continue without pausing)
    - Calibration event waiting with timeout
    - Graceful resume of paused motions with remaining duration calculation

Author: Auto-Bot Team
Date: 2025-01-15
"""

import threading
import time
from typing import Optional, Callable, Tuple
from calibration_coordinator import (
    get_calibration_coordinator, 
    MotionPhase
)


class EnhancedSequenceExecutor:
    """
    Executes motion sequences with calibration integration.
    Handles pausing/resuming of motion based on calibration events.
    """
    
    def __init__(self, zmq_send_callback: Callable):
        """
        Initialize the sequence executor.
        
        Args:
            zmq_send_callback: Function to send commands to RPi: (cmd_str) -> dict
        """
        self.send_command = zmq_send_callback
        self.coordinator = get_calibration_coordinator()
        self.is_paused = False
        self.pause_lock = threading.Lock()
        self.resume_event = threading.Event()
        
        # Register callbacks with coordinator
        self.coordinator.register_callbacks(
            on_pause=self._on_motion_pause,
            on_resume=self._on_motion_resume
        )
        
        print("[SEQ_EXEC] Enhanced Sequence Executor initialized")
    
    def _on_motion_pause(self, phase: str, remaining_duration: float):
        """
        Called by coordinator when motion should pause.
        Sends stop command to RPi.
        """
        print(f"[SEQ_EXEC] Motion pause callback: {phase} ({remaining_duration:.2f}s remaining)")
        with self.pause_lock:
            self.is_paused = True
            self.resume_event.clear()
        
        # Send stop to RPi
        try:
            self.send_command("stop")
            print(f"[SEQ_EXEC] Sent STOP to RPi")
        except Exception as e:
            print(f"[SEQ_EXEC] Error sending STOP: {e}")
    
    def _on_motion_resume(self, phase: str, remaining_duration: float):
        """
        Called by coordinator when motion should resume.
        Sends resume command (remaining duration of same motion).
        """
        print(f"[SEQ_EXEC] Motion resume callback: {phase} ({remaining_duration:.2f}s remaining)")
        with self.pause_lock:
            self.is_paused = False
        
        # Send resume motion with remaining duration
        try:
            if remaining_duration > 0:
                resume_cmd = f"{phase} {remaining_duration:.3f}"
                print(f"[SEQ_EXEC] Sending resume: {resume_cmd}")
                self.send_command(resume_cmd)
            else:
                print(f"[SEQ_EXEC] No remaining duration, motion complete")
        except Exception as e:
            print(f"[SEQ_EXEC] Error sending resume: {e}")
        
        self.resume_event.set()
    
    def execute_pausable_motion(
        self, 
        motion_cmd: str, 
        duration: float,
        check_calibration_interval: float = 0.1
    ) -> bool:
        """
        Execute a motion command that can be paused for calibration.
        
        Args:
            motion_cmd: Motion command (forward, backward, lock, unlock, sleep)
            duration: Duration of motion in seconds
            check_calibration_interval: How often to check calibration status (seconds)
            
        Returns:
            bool: True if motion completed successfully, False if interrupted
        """
        start_time = time.time()
        phase = motion_cmd.split()[0].lower()
        
        print(f"[SEQ_EXEC] Executing pausable motion: {motion_cmd} ({duration:.2f}s)")
        
        # Send initial motion command
        full_cmd = f"{motion_cmd} {duration:.3f}"
        try:
            self.send_command(full_cmd)
        except Exception as e:
            print(f"[SEQ_EXEC] Error sending motion command: {e}")
            return False
        
        # Monitor for calibration requests while motion executes
        while True:
            elapsed = time.time() - start_time
            
            # Check if motion is complete
            if elapsed >= duration:
                print(f"[SEQ_EXEC] Motion complete: {motion_cmd}")
                return True
            
            # Check if coordinator wants to pause
            status = self.coordinator.get_calibration_status()
            if status.get("active"):
                # Calibration initiated - wait for it to complete
                print(f"[SEQ_EXEC] Calibration detected, waiting for completion...")
                
                # Wait for calibration to complete (with timeout)
                calib_complete = self.coordinator.wait_for_calibration(timeout=30.0)
                
                if not calib_complete:
                    print(f"[SEQ_EXEC] Calibration timeout, resuming anyway")
                    # Try to resume the remaining motion
                    remaining = duration - elapsed
                    if remaining > 0:
                        resume_cmd = f"{phase} {remaining:.3f}"
                        try:
                            self.send_command(resume_cmd)
                        except Exception as e:
                            print(f"[SEQ_EXEC] Error resuming: {e}")
                        # Wait for resume motion to complete
                        time.sleep(remaining + 0.5)
                    return True
                
                # Calibration complete, resume_event should be set by coordinator
                # Wait a bit for resume motion to be sent
                self.resume_event.wait(timeout=5.0)
                self.resume_event.clear()
                
                # Recalculate elapsed time after calibration
                start_time = time.time() - elapsed
                
            # Sleep briefly before checking again
            time.sleep(check_calibration_interval)
    
    def execute_non_pausable_motion(
        self,
        motion_cmd: str,
        duration: float
    ) -> bool:
        """
        Execute a motion command that CANNOT be paused (turns).
        
        Args:
            motion_cmd: Motion command (left, right)
            duration: Duration of motion in seconds
            
        Returns:
            bool: True if motion completed successfully
        """
        print(f"[SEQ_EXEC] Executing non-pausable motion: {motion_cmd} ({duration:.2f}s)")
        
        # Send motion command
        full_cmd = f"{motion_cmd} {duration:.3f}"
        try:
            self.send_command(full_cmd)
        except Exception as e:
            print(f"[SEQ_EXEC] Error sending motion command: {e}")
            return False
        
        # For non-pausable motions, just wait for duration to complete
        # (no calibration interruption check)
        time.sleep(duration + 0.1)
        return True
    
    def execute_sequence_with_calibration(
        self,
        sequence_cmd: str,
        default_duration: float = 1.0
    ) -> bool:
        """
        Execute a full sequence with calibration support.
        
        Args:
            sequence_cmd: Full sequence command (e.g., "forward 2; right 1; lock 0.5; stop")
            default_duration: Default duration for commands without duration
            
        Returns:
            bool: True if sequence completed, False if interrupted
        """
        print(f"[SEQ_EXEC] Starting sequence with calibration support...")
        print(f"[SEQ_EXEC] Command: {sequence_cmd}")
        
        # Reset coordinator state at start of sequence
        self.coordinator.reset()
        
        try:
            # Parse sequence into tokens
            tokens = [t.strip() for t in sequence_cmd.split(";") if t.strip()]
            
            for token in tokens:
                if not token:
                    continue
                
                parts = token.split()
                if not parts:
                    continue
                
                cmd = parts[0].lower()
                
                # Get duration from token or use default
                try:
                    duration = float(parts[1]) if len(parts) > 1 else default_duration
                except (ValueError, IndexError):
                    duration = default_duration
                
                # Execute based on command type
                if cmd in ("left", "right"):
                    # Non-pausable turns
                    success = self.execute_non_pausable_motion(cmd, duration)
                elif cmd in ("forward", "backward", "lock", "unlock", "sleep"):
                    # Pausable motions
                    success = self.execute_pausable_motion(cmd, duration)
                elif cmd == "stop":
                    # Stop command
                    print(f"[SEQ_EXEC] Executing STOP")
                    try:
                        self.send_command("stop")
                    except Exception as e:
                        print(f"[SEQ_EXEC] Error sending STOP: {e}")
                    success = True
                else:
                    print(f"[SEQ_EXEC] Unknown command: {cmd}")
                    success = False
                
                if not success:
                    print(f"[SEQ_EXEC] Sequence aborted due to command failure: {token}")
                    return False
                
                # Small delay between tokens
                time.sleep(0.1)
            
            print(f"[SEQ_EXEC] Sequence complete!")
            return True
            
        finally:
            # Reset coordinator state at end
            self.coordinator.reset()


# Global instance for sequence execution
_executor_instance = None
_executor_lock = threading.Lock()


def get_sequence_executor(zmq_send_callback: Callable = None) -> EnhancedSequenceExecutor:
    """Get or create the global sequence executor instance"""
    global _executor_instance
    
    with _executor_lock:
        if _executor_instance is None and zmq_send_callback:
            _executor_instance = EnhancedSequenceExecutor(zmq_send_callback)
        return _executor_instance


def reset_sequence_executor():
    """Reset the global executor instance (for testing)"""
    global _executor_instance
    with _executor_lock:
        _executor_instance = None
