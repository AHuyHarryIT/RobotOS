#!/usr/bin/env python3
"""
Xbox Controller Mode

Manual control using Xbox controller:
    - D-pad: Movement with hold-to-repeat
    - Buttons: A=unlock, B=lock, X=emergency stop, Y=demo sequence
    - Auto-reconnection on disconnect
    - Heartbeat monitoring with warnings

Runs headless (no pygame window).

Author: Auto-Bot Team
"""
import time
import pygame

from config import SEND_COOLDOWN
from zmq_client import send_command, get_heartbeat_age
from command_aggregator import get_aggregator, CommandSource, CommandPriority


def map_hat_to_cmd(hat_x: int, hat_y: int):
    """
    Map D-pad (hat) position to movement command.
    
    Uses HOLD mode for continuous smooth movement:
      (0,  1) -> hold:forward  (continuous until released)
      (0, -1) -> hold:backward
      (-1, 0) -> hold:left
      (1,  0) -> hold:right
      (0,  0) -> stop          (release = stop)
    
    Args:
        hat_x: Horizontal position (-1, 0, 1)
        hat_y: Vertical position (-1, 0, 1)
    
    Returns:
        Command string or None if no mapping
    """
    if (hat_x, hat_y) == (0, 1):
        return "hold:forward"
    elif (hat_x, hat_y) == (0, -1):
        return "hold:backward"
    elif (hat_x, hat_y) == (-1, 0):
        return "hold:left"
    elif (hat_x, hat_y) == (1, 0):
        return "hold:right"
    elif (hat_x, hat_y) == (0, 0):
        return "stop"
    else:
        return None


def get_button_name(btn_index: int):
    """
    Get human-readable button name for Xbox controller.
    
    Standard Xbox mapping:
      0 -> A
      1 -> B
      2 -> X
      3 -> Y
    
    Args:
        btn_index: Button index from pygame
    
    Returns:
        Button name string
    """
    mapping = {
        0: "A",
        1: "B",
        2: "X",
        3: "Y",
    }
    return mapping.get(btn_index, f"BTN_{btn_index}")


def controller_loop(sock):
    """
    Xbox controller main loop (runs headless - no window).
    
    Controls:
        - D-pad: Movement control with hold-to-repeat
        - A button: unlock
        - B button: lock
        - X button: emergency stop
        - Y button: demo sequence
        - Ctrl+C: exit controller mode and return to menu
    
    Features:
        - Auto-reconnection on controller disconnect
        - Heartbeat monitoring with health warnings
        - Command validation through central aggregator
    
    Args:
        sock: ZMQ socket for sending commands to RPi
    """
    aggregator = get_aggregator()
    
    pygame.init()
    pygame.joystick.init()
    # Note: NOT calling pygame.display.set_mode -> runs headless

    print("[JOY] Looking for Xbox controller...")
    joystick = None

    def find_joystick():
        """Detect and initialize controller."""
        nonlocal joystick
        pygame.joystick.quit()
        pygame.joystick.init()
        count = pygame.joystick.get_count()
        if count == 0:
            joystick = None
            return False
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        print(
            f"[JOY] Connected: {joystick.get_name()} "
            f"(axes={joystick.get_numaxes()}, buttons={joystick.get_numbuttons()}, hats={joystick.get_numhats()})"
        )
        return True

    while not find_joystick():
        print("[JOY] No controller found. Please connect an Xbox controller...")
        time.sleep(1.0)

    last_hat = (0, 0)
    last_send_time = 0.0
    last_buttons = {}
    controller_connected = True

    print("\n===== CONTROLLER MODE (SMOOTH HOLD) =====")
    print("D-pad: movement (hold = continuous, release = stop)")
    print("A: unlock | B: lock | X: STOP | Y: demo sequence")
    print("Ctrl+C to return to menu.\n")

    try:
        while True:
            # Heartbeat watchdog - monitor RPi health
            hb_age = get_heartbeat_age()
            if hb_age > 3.0:
                print("[HEALTH] WARNING: No heartbeat from RPi > 3s")

            # Controller disconnect/reconnect handling
            if pygame.joystick.get_count() == 0:
                if controller_connected:
                    controller_connected = False
                    print("[JOY] Controller disconnected! Sending STOP...")
                    send_command(sock, "stop")
                    print("[JOY] Please reconnect the controller.")
                find_joystick()
                time.sleep(0.5)
                continue
            else:
                if not controller_connected:
                    controller_connected = True
                    print("[JOY] Controller reconnected.")

            # Update joystick state
            try:
                pygame.event.pump()
            except Exception as e:
                print(f"[JOY] pygame.event.pump() error: {e}")
                time.sleep(0.1)
                continue

            if joystick is None:
                time.sleep(0.1)
                continue

            now = time.time()

            # --- D-PAD (hat) with hold-to-repeat ---
            if joystick.get_numhats() > 0:
                hat_x, hat_y = joystick.get_hat(0)
            else:
                hat_x, hat_y = 0, 0

            if (hat_x, hat_y) != last_hat:
                # D-pad position changed → send ONE command
                # Hold mode: robot keeps moving until D-pad released (stop)
                # No more hold-to-repeat needed!
                last_hat = (hat_x, hat_y)
                cmd = map_hat_to_cmd(hat_x, hat_y)
                if cmd and (now - last_send_time) >= SEND_COOLDOWN:
                    # Process through aggregator
                    success, processed_cmd, msg = aggregator.process_command(
                        command=cmd,
                        source=CommandSource.CONTROLLER,
                        priority=CommandPriority.NORMAL
                    )
                    if success and processed_cmd:
                        send_command(sock, processed_cmd)
                        try:
                            from web_dashboard import send_dashboard_update
                            send_dashboard_update()
                        except:
                            pass
                        last_send_time = now
            # Hold mode: no repeat needed — RPi holds state until changed

            # --- BUTTONS (A, B, X, Y) ---
            num_buttons = joystick.get_numbuttons()
            now_state = {}
            for i in range(num_buttons):
                try:
                    val = joystick.get_button(i)
                except Exception:
                    val = 0
                now_state[i] = val

            for i, val in now_state.items():
                prev_val = last_buttons.get(i, 0)
                if val == 1 and prev_val == 0:  # Button just pressed
                    btn_name = get_button_name(i)
                    print(f"[JOY] Button pressed: {btn_name} (index={i})")
                    now_btn = time.time()
                    if (now_btn - last_send_time) < SEND_COOLDOWN:
                        continue

                    # Map button to command
                    cmd = None
                    if btn_name == "A":
                        cmd = "unlock"
                    elif btn_name == "B":
                        cmd = "lock"
                    elif btn_name == "X":
                        cmd = "stop"
                    elif btn_name == "Y":
                        cmd = 'seq forward 1; right 1; backward 1; left 1; stop'
                    
                    if cmd:
                        # Process through aggregator
                        success, processed_cmd, msg = aggregator.process_command(
                            command=cmd,
                            source=CommandSource.CONTROLLER,
                            priority=CommandPriority.HIGH if btn_name == "X" else CommandPriority.NORMAL
                        )
                        if success and processed_cmd:
                            send_command(sock, processed_cmd)
                            try:
                                from web_dashboard import send_dashboard_update
                                send_dashboard_update()
                            except:
                                pass
                            last_send_time = now_btn

            last_buttons = now_state

            time.sleep(0.02)  # Small delay to reduce CPU usage

    except KeyboardInterrupt:
        print("\n[CTRL] Controller mode interrupted, sending STOP and returning to menu...")
        try:
            send_command(sock, "stop")
        except Exception:
            pass
    finally:
        pygame.joystick.quit()
        pygame.quit()
        print("[CTRL] Controller mode exit.")
