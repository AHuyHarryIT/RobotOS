#!/usr/bin/env python3
"""
Sequence Mode - Text Command REPL with Calibration Support

Interactive command-line interface for:
    - Single commands: 'forward 2', 'left', 'stop'
    - Sequences: 'seq forward 2; right 1; lock 0.5; stop'
    - Emergency stop: 'stop' (interrupt any running sequence)
    
When executing sequences, the server coordinates with Jetson for calibration:
    - During pausable motions (forward, backward, lock, unlock):
      * Jetson can request calibration pause
      * Server pauses motion, waits for calibration to complete
      * Server resumes motion with remaining duration
    - During non-pausable motions (left, right):
      * Motion continues without interruption
    
Commands:
    back/menu - Return to mode selection
    exit/quit/q - Exit entire program

Author: Auto-Bot Team
"""
import threading
from zmq_client import send_command
from command_aggregator import get_aggregator, CommandSource, CommandPriority
from sequence_executor import get_sequence_executor


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
    executor = get_sequence_executor(zmq_send_callback=lambda cmd: send_command(sock, cmd))
    
    print("\n===== SEQUENCE MODE (WITH CALIBRATION SUPPORT) =====")
    print("Enter commands:")
    print("  - Single: forward / backward / left / right / lock / unlock / stop / sleep 1.0")
    print("  - Sequence: seq forward 2; right 1; lock 0.5; stop")
    print("")
    print("  Note: Pausable motions (forward/backward/lock/unlock/sleep)")
    print("        can pause for Jetson calibration. Turns (left/right) cannot.")
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

        # Check if this is a sequence command (starts with "seq ")
        if low.startswith("seq "):
            # Execute sequence with calibration support
            sequence_cmd = line[4:].strip()  # Remove "seq " prefix
            
            print(f"[SEQ] Executing sequence with calibration support...")
            print(f"[SEQ] Command: {sequence_cmd}")
            
            # Run sequence in a separate thread to allow REPL to remain responsive
            def run_sequence_thread():
                try:
                    executor.execute_sequence_with_calibration(sequence_cmd)
                except Exception as e:
                    print(f"[SEQ] Sequence error: {e}")
            
            seq_thread = threading.Thread(target=run_sequence_thread, daemon=True)
            seq_thread.start()
            seq_thread.join(timeout=300)  # Wait up to 5 minutes for sequence to complete
            
            if seq_thread.is_alive():
                print("[SEQ] WARNING: Sequence still running, returning to prompt anyway")
        else:
            # Process single command through aggregator
            success, processed_cmd, msg = aggregator.process_command(
                command=line,
                source=CommandSource.MANUAL,
                priority=CommandPriority.NORMAL
            )
            
            if success and processed_cmd:
                # Send validated command to RPi
                send_command(sock, processed_cmd)
                try:
                    from web_dashboard import send_dashboard_update
                    send_dashboard_update()
                except:
                    pass
            else:
                print(f"[SEQ] Command rejected: {msg}")
