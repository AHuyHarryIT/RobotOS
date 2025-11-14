#!/usr/bin/env python3
import sys
from gpio_driver import GPIODriver
from sequencer import run_sequence, run_single
from states import PINS

def repl(driver: GPIODriver):
    print("Commands:")
    print("  - Single: forward / backward / left / right / lock / unlock / stop / sleep 1.0")
    print("  - Sequence: seq forward 2; right 1; lock 0.5; stop")
    print("  - Exit: exit / quit / q")
    print("")
    while True:
        try:
            cmd = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not cmd:
            continue
        low = cmd.lower()
        if low in ("exit", "quit", "q"):
            break
        elif low.startswith("seq "):
            seq = cmd[4:].strip()
            run_sequence(driver, seq)
        else:
            run_single(driver, cmd)

def main():
    driver = GPIODriver(PINS)
    try:
        driver.setup()
        if len(sys.argv) > 1:
            # Example: sudo python3 app.py "seq forward 2; right 1; lock 0.5; stop"
            arg = " ".join(sys.argv[1:]).strip()
            if arg.lower().startswith("seq "):
                run_sequence(driver, arg[4:].strip())
            else:
                run_single(driver, arg)
        else:
            print(f"GPIO control (pins {PINS}). Press Ctrl+C to exit.")
            repl(driver)
    finally:
        driver.cleanup()
        print("GPIO cleanup complete.")

if __name__ == "__main__":
    main()

