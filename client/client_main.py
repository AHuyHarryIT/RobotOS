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

    while True:
        print("\n========================")
        print("  AUTO-BOT CLIENT MENU ")
        print("========================")
        print("1. Sequence mode (text commands / sequences with STOP interrupt)")
        print("2. Controller mode (Xbox controller)")
        print("3. Server mode only (receive from Jetson, no manual control)")
        print("s. Show statistics")
        print("q. Exit")
        choice = input("Select mode (1/2/3/s/q): ").strip().lower()

        if choice == "1":
            seq_console_loop(sock)
        elif choice == "2":
            controller_loop(sock)
        elif choice == "3":
            print("\n[SERVER MODE] Client is running command server")
            print("Receiving commands from Jetson and forwarding to RPi")
            print("Press Ctrl+C or 'q' to return to menu")
            try:
                while True:
                    cmd = input("(Press 'q' to return to menu): ").strip().lower()
                    if cmd in ("q", "quit", "back", "menu"):
                        break
            except KeyboardInterrupt:
                print("\nReturning to menu...")
        elif choice == "s":
            # Show aggregator statistics
            stats = aggregator.get_stats()
            print("\n=== Command Aggregator Statistics ===")
            print(f"Total commands processed: {stats['total_commands']}")
            print(f"Errors: {stats['errors']}")
            print(f"Commands by source:")
            for source, count in stats['by_source'].items():
                print(f"  - {source}: {count}")
            print(f"Last command: {stats['last_command']}")
            if stats['last_command_age'] is not None:
                print(f"Last command age: {stats['last_command_age']:.2f}s")
            print(f"History size: {stats['history_size']}")
            
            # Show recent history
            print("\n=== Recent Commands (last 5) ===")
            for entry in aggregator.get_recent_history(5):
                ts = entry['timestamp']
                src = entry['source']
                cmd = entry['processed']
                print(f"[{ts:.2f}] {src:10} -> {cmd}")
            
            input("\nPress Enter to continue...")
        elif choice in ("q", "quit", "exit"):
            print("Exiting client, sending final STOP command...")
            try:
                send_command(sock, "stop")
            except Exception:
                pass
            stop_command_server()
            break
        else:
            print("Invalid choice, please enter 1, 2, 3, s, or q.")


if __name__ == "__main__":
    main()
