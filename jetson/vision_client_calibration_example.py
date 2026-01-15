#!/usr/bin/env python3
"""
Enhanced Vision Client for Jetson with Calibration Integration

This example demonstrates how to:
1. Send motion commands to the server
2. Request calibration pause during motion execution
3. Signal when calibration is complete

Usage:
    python3 vision_client_calibration_example.py

Environment:
    - JETSON_SERVER_IP: IP of miniPC server (default: 192.168.10.100)
    - SERVER_CMD_PORT: Command server port (default: 5557)
"""

import time
import zmq
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
SERVER_IP = os.getenv("JETSON_SERVER_IP", "192.168.10.100")
SERVER_PORT = int(os.getenv("SERVER_CMD_PORT", "5557"))
SERVER_ADDR = f"tcp://{SERVER_IP}:{SERVER_PORT}"


class VisionClientWithCalibration:
    """Vision client that integrates with server calibration system."""
    
    def __init__(self, server_addr: str = SERVER_ADDR):
        """
        Initialize vision client.
        
        Args:
            server_addr: Server ZMQ address (tcp://ip:port)
        """
        self.server_addr = server_addr
        self.ctx = zmq.Context.instance()
        self.sock = None
        self.connected = False
        
    def connect(self) -> bool:
        """
        Connect to server command server.
        
        Returns:
            bool: True if connected successfully
        """
        try:
            self.sock = self.ctx.socket(zmq.REQ)
            self.sock.setsockopt(zmq.RCVTIMEO, 5000)  # 5s timeout
            self.sock.setsockopt(zmq.SNDTIMEO, 5000)
            self.sock.connect(self.server_addr)
            self.connected = True
            print(f"[VISION] Connected to server at {self.server_addr}")
            return True
        except Exception as e:
            print(f"[VISION] Connection failed: {e}")
            self.connected = False
            return False
    
    def send_command(self, cmd: str) -> dict:
        """
        Send a motion command to the server.
        
        Args:
            cmd: Command string (e.g., "forward 2", "left 1")
            
        Returns:
            dict: Response from server
        """
        if not self.connected:
            print("[VISION] Not connected to server")
            return {"status": "error", "error": "not_connected"}
        
        try:
            print(f"[VISION] Sending command: {cmd}")
            self.sock.send_string(cmd)
            reply_raw = self.sock.recv_string()
            reply = json.loads(reply_raw)
            print(f"[VISION] Reply: {reply}")
            return reply
        except Exception as e:
            print(f"[VISION] Error: {e}")
            self.connected = False
            return {"status": "error", "error": str(e)}
    
    def request_calibration_pause(
        self, 
        phase: str, 
        elapsed: float, 
        total: float
    ) -> dict:
        """
        Request to pause motion for calibration.
        
        This is sent to the server, which will:
        1. Check if the motion phase can be paused (forward/backward/lock/unlock allowed)
        2. Send STOP to RPi
        3. Pause monitoring for this motion
        4. Return response indicating success/rejection
        
        Args:
            phase: Motion phase (forward, backward, left, right, lock, unlock)
            elapsed: Time already elapsed in this phase (seconds)
            total: Total duration of this phase (seconds)
            
        Returns:
            dict: Response with status and whether pause was accepted
        """
        if not self.connected:
            print("[VISION] Not connected to server")
            return {"status": "error", "error": "not_connected"}
        
        try:
            msg = {
                "type": "calibration_pause",
                "phase": phase,
                "elapsed": elapsed,
                "total": total
            }
            print(f"[VISION] Requesting calibration pause: {phase} (elapsed={elapsed:.2f}s, total={total:.2f}s)")
            self.sock.send_string(json.dumps(msg))
            reply_raw = self.sock.recv_string()
            reply = json.loads(reply_raw)
            
            if reply.get("paused"):
                print(f"[VISION] ✓ Pause accepted - motion paused, ready for calibration")
            else:
                print(f"[VISION] ✗ Pause rejected - cannot pause {phase}")
            
            print(f"[VISION] Response: {reply}")
            return reply
        except Exception as e:
            print(f"[VISION] Error requesting pause: {e}")
            self.connected = False
            return {"status": "error", "error": str(e)}
    
    def signal_calibration_complete(self) -> dict:
        """
        Signal that calibration is complete.
        
        The server will then:
        1. Resume the paused motion with remaining duration
        2. Notify the sequence executor to continue
        
        Returns:
            dict: Response from server
        """
        if not self.connected:
            print("[VISION] Not connected to server")
            return {"status": "error", "error": "not_connected"}
        
        try:
            msg = {
                "type": "calibration_done"
            }
            print(f"[VISION] Signaling calibration complete")
            self.sock.send_string(json.dumps(msg))
            reply_raw = self.sock.recv_string()
            reply = json.loads(reply_raw)
            print(f"[VISION] Response: {reply}")
            return reply
        except Exception as e:
            print(f"[VISION] Error signaling complete: {e}")
            self.connected = False
            return {"status": "error", "error": str(e)}
    
    def check_calibration_status(self) -> dict:
        """
        Check current calibration status on server.
        
        Returns:
            dict: Status including whether calibration is active
        """
        if not self.connected:
            print("[VISION] Not connected to server")
            return {"status": "error", "error": "not_connected"}
        
        try:
            msg = {
                "type": "calibration_status"
            }
            self.sock.send_string(json.dumps(msg))
            reply_raw = self.sock.recv_string()
            reply = json.loads(reply_raw)
            print(f"[VISION] Calibration status: {reply}")
            return reply
        except Exception as e:
            print(f"[VISION] Error checking status: {e}")
            return {"status": "error", "error": str(e)}
    
    def close(self):
        """Close connection to server."""
        if self.sock:
            self.sock.close()
        self.connected = False
        print("[VISION] Connection closed")


def demo_basic_command():
    """Demo: Send basic motion command without calibration."""
    print("\n" + "="*60)
    print("DEMO 1: Basic Motion Command (No Calibration)")
    print("="*60)
    
    client = VisionClientWithCalibration()
    if not client.connect():
        return
    
    try:
        # Send simple forward command
        response = client.send_command("forward 2")
        print(f"Result: {response}\n")
        
    finally:
        client.close()


def demo_calibration_pause_resume():
    """Demo: Send motion, pause for calibration, then resume."""
    print("\n" + "="*60)
    print("DEMO 2: Motion with Calibration Pause/Resume")
    print("="*60)
    print("\nScenario: Forward 2 seconds, calibration at 0.5s\n")
    
    client = VisionClientWithCalibration()
    if not client.connect():
        return
    
    try:
        # Step 1: Send forward command
        print("[STEP 1] Sending forward 2 command...")
        response = client.send_command("forward 2")
        if response.get("status") != "ok":
            print("Failed to send command")
            return
        
        # Step 2: Wait 0.5 seconds then request calibration pause
        print("\n[STEP 2] Waiting 0.5 seconds before requesting calibration pause...")
        time.sleep(0.5)
        
        print("[STEP 2] Sending calibration pause request...")
        pause_response = client.request_calibration_pause(
            phase="forward",
            elapsed=0.5,
            total=2.0
        )
        
        if not pause_response.get("paused"):
            print("ERROR: Calibration pause was rejected!")
            return
        
        # Step 3: Perform calibration (simulate 1 second calibration)
        print("\n[STEP 3] Performing calibration (simulating 1 second delay)...")
        for i in range(10):
            time.sleep(0.1)
            print(f"  Calibrating... {(i+1)*0.1:.1f}s")
        
        # Step 4: Signal calibration complete
        print("\n[STEP 4] Signaling calibration complete...")
        done_response = client.signal_calibration_complete()
        print(f"Status: {done_response.get('status')}")
        
        # Step 5: Wait for remaining motion (1.5 seconds)
        print("\n[STEP 5] Waiting for motion to resume and complete (~1.5s)...")
        time.sleep(2.0)
        print("Motion should be complete now")
        
    finally:
        client.close()


def demo_turn_cannot_pause():
    """Demo: Show that turns cannot be paused for calibration."""
    print("\n" + "="*60)
    print("DEMO 3: Turns Cannot Be Paused (Non-Pausable Motions)")
    print("="*60)
    print("\nScenario: Send right turn, then try to pause (should be rejected)\n")
    
    client = VisionClientWithCalibration()
    if not client.connect():
        return
    
    try:
        # Step 1: Send right command
        print("[STEP 1] Sending right 2 command...")
        response = client.send_command("right 2")
        if response.get("status") != "ok":
            print("Failed to send command")
            return
        
        # Step 2: Try to pause the right motion (should fail)
        print("\n[STEP 2] Attempting to pause right motion for calibration...")
        print("(This should be REJECTED because turns are non-pausable)")
        
        time.sleep(0.3)
        pause_response = client.request_calibration_pause(
            phase="right",
            elapsed=0.3,
            total=2.0
        )
        
        if pause_response.get("paused"):
            print("ERROR: Right motion was paused! This should not happen!")
        else:
            print("✓ CORRECT: Right motion cannot be paused (as expected)")
            print(f"  Message: {pause_response.get('message')}")
        
        # Step 3: Wait for motion to complete
        print("\n[STEP 3] Waiting for right motion to complete (2 seconds)...")
        time.sleep(2.0)
        print("✓ Right motion completed without interruption")
        
    finally:
        client.close()


def interactive_mode():
    """Interactive mode for manual testing."""
    print("\n" + "="*60)
    print("INTERACTIVE MODE")
    print("="*60)
    print("\nCommands:")
    print("  cmd <command>              - Send motion command")
    print("  pause <phase> <elapsed> <total>")
    print("                             - Request calibration pause")
    print("  done                       - Signal calibration complete")
    print("  status                     - Check calibration status")
    print("  help                       - Show this help")
    print("  q / quit / exit            - Exit program\n")
    
    client = VisionClientWithCalibration()
    if not client.connect():
        return
    
    try:
        while True:
            try:
                user_input = input("vision> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting...")
                break
            
            if not user_input:
                continue
            
            parts = user_input.split()
            cmd = parts[0].lower()
            
            if cmd in ("q", "quit", "exit"):
                print("Exiting...")
                break
            
            elif cmd == "help":
                print("\nCommands:")
                print("  cmd <command>              - Send motion command")
                print("  pause <phase> <elapsed> <total>")
                print("                             - Request calibration pause")
                print("  done                       - Signal calibration complete")
                print("  status                     - Check calibration status")
                print("  q / quit / exit            - Exit program\n")
            
            elif cmd == "cmd" and len(parts) > 1:
                command = " ".join(parts[1:])
                client.send_command(command)
            
            elif cmd == "pause" and len(parts) >= 4:
                try:
                    phase = parts[1]
                    elapsed = float(parts[2])
                    total = float(parts[3])
                    client.request_calibration_pause(phase, elapsed, total)
                except ValueError:
                    print("Error: elapsed and total must be numbers")
            
            elif cmd == "done":
                client.signal_calibration_complete()
            
            elif cmd == "status":
                client.check_calibration_status()
            
            else:
                print("Unknown command. Type 'help' for available commands.")
    
    finally:
        client.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        demo_type = sys.argv[1].lower()
        
        if demo_type == "1":
            demo_basic_command()
        elif demo_type == "2":
            demo_calibration_pause_resume()
        elif demo_type == "3":
            demo_turn_cannot_pause()
        elif demo_type == "interactive":
            interactive_mode()
        else:
            print(f"Unknown demo: {demo_type}")
            print("\nUsage:")
            print("  python3 vision_client_calibration_example.py 1")
            print("  python3 vision_client_calibration_example.py 2")
            print("  python3 vision_client_calibration_example.py 3")
            print("  python3 vision_client_calibration_example.py interactive")
    else:
        print("Vision Client Calibration Example")
        print("="*60)
        print("\nUsage:")
        print("  python3 vision_client_calibration_example.py 1")
        print("    → Demo 1: Basic motion command (no calibration)")
        print("\n  python3 vision_client_calibration_example.py 2")
        print("    → Demo 2: Motion with calibration pause/resume")
        print("\n  python3 vision_client_calibration_example.py 3")
        print("    → Demo 3: Show turns cannot be paused")
        print("\n  python3 vision_client_calibration_example.py interactive")
        print("    → Interactive manual testing\n")
        
        # Run demo 2 as default
        print("Running Demo 2 (Calibration Pause/Resume) as default...\n")
        demo_calibration_pause_resume()
