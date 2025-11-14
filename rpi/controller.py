#!/usr/bin/env python3
import time
import pygame
from typing import Optional

from gpio_driver import GPIODriver
from sequencer import set_state
from states import PINS

# ------------------------
# Controller helpers
# ------------------------
def init_pygame():
    pygame.init()
    pygame.joystick.init()

def get_controller() -> Optional[pygame.joystick.Joystick]:
    """Return the first joystick if available, otherwise None."""
    if pygame.joystick.get_count() == 0:
        return None
    js = pygame.joystick.Joystick(0)
    js.init()
    return js

def wait_for_controller() -> pygame.joystick.Joystick:
    """Block until a controller is connected, printing a friendly prompt."""
    print("🔌 No controller detected. Please plug in / connect your Xbox controller...")
    while True:
        pygame.event.pump()
        js = get_controller()
        if js:
            print(f"🎮 Controller connected: {js.get_name()}")
            return js
        time.sleep(0.5)

# ------------------------
# Movement mapping (D-pad)
# ------------------------
def handle_hat(driver: GPIODriver, hat_value):
    """
    hat_value is a tuple (x, y):
      x: -1=LEFT, 0=neutral, 1=RIGHT
      y: -1=DOWN, 0=neutral, 1=UP
    Priority: vertical over horizontal (UP/DOWN beats LEFT/RIGHT)
    """
    x, y = hat_value
    if y == 1:
        set_state(driver, "FORWARD")
    elif y == -1:
        set_state(driver, "BACKWARD")
    elif x == -1:
        set_state(driver, "LEFT")
    elif x == 1:
        set_state(driver, "RIGHT")
    else:
        driver.stop()

def handle_buttons(driver: GPIODriver, js: pygame.joystick.Joystick):
    """
    Button indices for Xbox (typical on pygame):
      A=0, B=1, X=2, Y=3
    """
    a = js.get_button(0)
    b = js.get_button(1)
    x = js.get_button(2)
    y = js.get_button(3)

    if x:
        set_state(driver, "LOCK")
        time.sleep(0.15)
    if y:
        set_state(driver, "UNLOCK")
        time.sleep(0.15)
    if a or b:
        set_state(driver, "STOP")
        time.sleep(0.05)

# ------------------------
# Main loop
# ------------------------
def main():
    driver = GPIODriver(PINS)
    driver.setup()

    init_pygame()
    js = get_controller()
    if not js:
        js = wait_for_controller()
    else:
        print(f"🎮 Controller connected: {js.get_name()}")

    print("Controls:")
    print("  D-pad ↑ ↓ ← →  -> FORWARD / BACKWARD / LEFT / RIGHT")
    print("  X -> LOCK,  Y -> UNLOCK,  A/B -> STOP")
    print("Press Ctrl+C to exit.\n")

    # Some controllers expose the D-pad as a 'hat'
    hat_index = 0 if js.get_numhats() > 0 else None
    last_hat = (0, 0)

    try:
        while True:
            # Poll events to catch (dis)connect events
            for event in pygame.event.get():
                if event.type == pygame.JOYDEVICEREMOVED:
                    print("⚠️ Controller disconnected. Waiting for reconnection...")
                    js = wait_for_controller()
                    hat_index = 0 if js.get_numhats() > 0 else None
                    last_hat = (0, 0)
                elif event.type == pygame.JOYDEVICEADDED:
                    # If a new device appears, rebind to index 0 for simplicity
                    js = get_controller() or wait_for_controller()
                    hat_index = 0 if js.get_numhats() > 0 else None
                    print(f"🎮 Controller (re)connected: {js.get_name()}")

            # If lost mid-loop (some platforms don’t emit JOYDEVICEREMOVED reliably)
            if pygame.joystick.get_count() == 0 or js is None:
                print("⚠️ Controller not found. Waiting for reconnection...")
                js = wait_for_controller()
                hat_index = 0 if js.get_numhats() > 0 else None
                last_hat = (0, 0)

            # Read buttons for lock/unlock/stop
            handle_buttons(driver, js)

            # D-pad handling
            if hat_index is not None:
                hat = js.get_hat(hat_index)
                # Only act if changed (prevents spamming)
                if hat != last_hat:
                    handle_hat(driver, hat)
                    last_hat = hat
                # If held, keep the last movement; neutral will stop in handle_hat
            else:
                # Fallback: if no hat, just stop (or you could map to sticks here)
                driver.stop()

            time.sleep(0.03)  # ~33 Hz poll
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        driver.cleanup()
        pygame.joystick.quit()
        pygame.quit()
        print("GPIO cleanup complete.")

if __name__ == "__main__":
    main()
