#!/usr/bin/env python3
"""
Vision client for Jetson.
Processes camera/vision data and sends control commands (left, right, stop, etc.)
to the miniPC client (brain) via ZMQ REQ socket.

Usage:
    python3 vision_client.py
    
Environment Variables:
    CLIENT_IP: IP address of miniPC client (default: 192.168.10.100)
    CLIENT_SERVER_PORT: Port of client command server (default: 5557)
"""

import time
import zmq
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
CLIENT_IP = os.getenv("CLIENT_IP", "192.168.1.100")
CLIENT_PORT = int(os.getenv("CLIENT_SERVER_PORT", "5557"))
CLIENT_ADDR = f"tcp://{CLIENT_IP}:{CLIENT_PORT}"


class VisionClient:
    """Client that sends vision-based commands to miniPC."""
    
    def __init__(self):
        self.ctx = zmq.Context.instance()
        self.sock = None
        self.connected = False
        
    def connect(self):
        """Connect to miniPC command server."""
        try:
            self.sock = self.ctx.socket(zmq.REQ)
            self.sock.connect(CLIENT_ADDR)
            self.sock.setsockopt(zmq.RCVTIMEO, 5000)  # 5s timeout
            self.sock.setsockopt(zmq.SNDTIMEO, 5000)
            self.connected = True
            print(f"[VISION] Connected to client at {CLIENT_ADDR}")
        except Exception as e:
            print(f"[VISION] Connection error: {e}")
            self.connected = False
            
    def send_command(self, cmd: str) -> dict:
        """
        Send a command to the client.
        
        Args:
            cmd: Command string (e.g., "left", "right", "stop", "forward 2")
            
        Returns:
            dict: Response from client
        """
        if not self.connected or not self.sock:
            print("[VISION] Not connected, attempting reconnect...")
            self.connect()
            if not self.connected:
                return {"status": "error", "error": "not_connected"}
        
        try:
            print(f"[VISION] -> Sending: {cmd!r}")
            self.sock.send_string(cmd)
            
            reply_raw = self.sock.recv()
            reply = json.loads(reply_raw.decode("utf-8"))
            print(f"[VISION] <- Reply: {reply}")
            return reply
            
        except zmq.Again:
            print("[VISION] Timeout waiting for reply")
            self.connected = False
            return {"status": "error", "error": "timeout"}
        except Exception as e:
            print(f"[VISION] Send error: {e}")
            self.connected = False
            return {"status": "error", "error": str(e)}
    
    def close(self):
        """Close connection."""
        if self.sock:
            self.sock.close()
        self.connected = False
        print("[VISION] Connection closed")


def calibration_demo():
    """
    Demo function for calibration testing.
    Sends test commands to verify the connection.
    """
    client = VisionClient()
    client.connect()
    
    if not client.connected:
        print("[VISION] Failed to connect. Check CLIENT_IP and CLIENT_PORT in .env")
        return
    
    print("\n=== Calibration Demo ===")
    print("Sending test commands to client...")
    
    # Test sequence
    test_commands = [
        ("stop", 0.5),
        ("forward 0.5", 1.0),
        ("left 0.3", 1.0),
        ("right 0.3", 1.0),
        ("backward 0.5", 1.0),
        ("stop", 0.5),
    ]
    
    try:
        for cmd, delay in test_commands:
            print(f"\n[TEST] Sending: {cmd}")
            result = client.send_command(cmd)
            
            if result.get("status") != "ok":
                print(f"[TEST] Command failed: {result}")
            
            time.sleep(delay)
            
        print("\n[TEST] Calibration demo complete!")
        
    except KeyboardInterrupt:
        print("\n[TEST] Interrupted by user")
        client.send_command("stop")
    finally:
        client.close()


def interactive_mode():
    """
    Interactive mode for manual command testing.
    """
    client = VisionClient()
    client.connect()
    
    if not client.connected:
        print("[VISION] Failed to connect. Check CLIENT_IP and CLIENT_PORT in .env")
        return
    
    print("\n=== Interactive Vision Client ===")
    print("Enter commands to send to client (left, right, stop, forward, backward, etc.)")
    print("Type 'q' or 'quit' to exit\n")
    
    try:
        while True:
            cmd = input("vision> ").strip()
            
            if not cmd:
                continue
                
            if cmd.lower() in ("q", "quit", "exit"):
                print("Exiting...")
                break
            
            result = client.send_command(cmd)
            
            if result.get("status") != "ok":
                print(f"[ERROR] {result.get('error', 'unknown error')}")
                
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        client.send_command("stop")
        client.close()


def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "demo":
            calibration_demo()
        elif mode == "interactive":
            interactive_mode()
        else:
            print(f"Unknown mode: {mode}")
            print("Usage: python3 vision_client.py [demo|interactive]")
    else:
        print("Jetson Vision Client")
        print("====================")
        print("Usage:")
        print("  python3 vision_client.py demo        - Run calibration demo")
        print("  python3 vision_client.py interactive - Interactive command mode")
        print("\nStarting interactive mode by default...\n")
        interactive_mode()


if __name__ == "__main__":
    main()
