#!/usr/bin/env python3
"""
Auto-Bot Client Main Entry Point

This is the central brain of the Auto-Bot system running on miniPC.
It aggregates commands from multiple sources and forwards them to RPi for execution.

Command Sources:
    1. Jetson vision system (autonomous control via ZMQ)
    2. Xbox controller (manual control)
    3. Sequence mode (text commands)
    
Architecture:
    [Jetson] ──┐
    [Xbox]   ──┼──> [Client Brain] ──> [RPi GPIO] ──> [Car Motors]
    [Manual] ──┘

Author: Auto-Bot Team
"""
from zmq_client import init_zmq, send_command
from seq_mode import seq_console_loop
from controller_mode import controller_loop
from command_server import start_command_server, stop_command_server
from command_aggregator import get_aggregator
from web_dashboard import run_dashboard_background


def main():
    """Main entry point for the Auto-Bot client."""
    
    # Initialize ZMQ connection to RPi
    ctx, sock = init_zmq()
    
    # Initialize command aggregator (central processing hub)
    aggregator = get_aggregator()
    print(f"[INIT] Command aggregator initialized")
    
    # Start command server to receive from Jetson/external sources
    print("\n[INIT] Starting command server for Jetson/external sources...")
    start_command_server(sock)
    print("[INIT] Command server is running in background")
    print("[INIT] All commands will be processed through central aggregator\n")

    # Auto-start web dashboard
    print("="*60)
    print("🌐 AUTO-BOT WEB DASHBOARD")
    print("="*60)
    print("Starting web interface automatically...")
    print("")
    
    dashboard_thread = run_dashboard_background(host='0.0.0.0', port=5000, sock=sock)
    
    print("")
    print("="*60)
    print("✅ WEB DASHBOARD IS RUNNING")
    print("="*60)
    print("📊 Dashboard URL (local):  http://localhost:5000")
    print("📊 Dashboard URL (network): http://<your-ip>:5000")
    print("")
    print("🎯 You can now:")
    print("   - Select operation mode from web")
    print("   - Control robot with buttons")
    print("   - Send sequence commands")
    print("   - Monitor real-time statistics")
    print("")
    print("="*60)
    print("Press Ctrl+C to stop the server")
    print("="*60)
    print("")
    
    try:
        # Keep the main thread alive
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n[SHUTDOWN] Stopping Auto-Bot client...")
        print("[SHUTDOWN] Sending final STOP command...")
        try:
            send_command(sock, "stop")
        except Exception:
            pass
        stop_command_server()
        print("[SHUTDOWN] Goodbye! 👋")


if __name__ == "__main__":
    main()
