#!/usr/bin/env python3
"""
Sequence Mode - Text Command REPL

Interactive command-line interface for:
    - Single commands: 'forward 2', 'left', 'stop'
    - Sequences: 'seq forward 2; right 1; lock 0.5; stop'
    - Emergency stop: 'stop' (interrupt any running sequence)
    
Commands:
    back/menu - Return to mode selection
    exit/quit/q - Exit entire program

Author: Auto-Bot Team
"""
from zmq_client import send_command
from command_aggregator import get_aggregator, CommandSource, CommandPriority


def seq_console_loop(sock):
    """
    REPL console for entering commands (single or sequences).
    
    Supported commands:
      - Single: 'forward 2', 'backward', 'left', 'right', 'lock', 'unlock', 'stop', 'sleep 1.0'
      - Sequence: 'seq forward 2; right 1; lock 0.5; stop'
      - Emergency: 'stop' (interrupts any running sequence)
      - Navigation: 'back'/'menu' (return to mode selection)
      - Exit: 'exit'/'quit'/'q' (exit entire program)
    
    Args:
        sock: ZMQ socket for sending commands to RPi
    """
    aggregator = get_aggregator()
    
    print("\n===== SEQUENCE MODE =====")
    print("Enter commands:")
    print("  - Single: forward / backward / left / right / lock / unlock / stop / sleep 1.0")
    print("  - Sequence: seq forward 2; right 1; lock 0.5; stop")
    print("  - back / menu: return to mode selection")
    print("  - exit / quit / q: exit client program\n")

    while True:
        try:
            line = input("seq> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[SEQ] KeyboardInterrupt -> sending STOP and exiting mode.")
            try:
                send_command(sock, "stop")
            except Exception:
                pass
            return

        if not line:
            continue

        low = line.lower()
        if low in ("back", "menu"):
            print("[SEQ] Returning to mode selection.")
            return
        if low in ("exit", "quit", "q"):
            print("[SEQ] Exiting entire client.")
            raise SystemExit(0)

        # Process command through aggregator
        success, processed_cmd, msg = aggregator.process_command(
            command=line,
            source=CommandSource.MANUAL,
            priority=CommandPriority.NORMAL
        )
        
        if success and processed_cmd:
            # Send validated command to RPi
            send_command(sock, processed_cmd)
        else:
            print(f"[SEQ] Command rejected: {msg}")
