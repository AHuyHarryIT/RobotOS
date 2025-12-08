# controller_mode.py
import time

import pygame

from config import DUR_FORWARD, DUR_BACKWARD, DUR_TURN, SEND_COOLDOWN, REPEAT_HOLD_INTERVAL
from zmq_client import send_command, get_heartbeat_age


def map_hat_to_cmd(hat_x: int, hat_y: int):
    """
    D-pad mapping:
      (0,  1) -> forward
      (0, -1) -> backward
      (-1, 0) -> left
      (1,  0) -> right
      (0,  0) -> stop
    """
    if (hat_x, hat_y) == (0, 1):
        return f"forward {DUR_FORWARD}"
    elif (hat_x, hat_y) == (0, -1):
        return f"backward {DUR_BACKWARD}"
    elif (hat_x, hat_y) == (-1, 0):
        return f"left {DUR_TURN}"
    elif (hat_x, hat_y) == (1, 0):
        return f"right {DUR_TURN}"
    elif (hat_x, hat_y) == (0, 0):
        return "stop"
    else:
        return None


def get_button_name(btn_index: int):
    """
    Mapping cơ bản cho XBOX controller (thường):
      0 -> A
      1 -> B
      2 -> X
      3 -> Y
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
    Vòng lặp điều khiển bằng Xbox controller, không mở window.
    - D-pad: điều khiển di chuyển, giữ để chạy liên tục (step nhỏ).
    - A: unlock
    - B: lock
    - X: emergency stop
    - Y: seq demo
    - Ctrl+C: thoát khỏi mode controller, quay về menu.
    """
    pygame.init()
    pygame.joystick.init()
    # KHÔNG gọi pygame.display.set_mode -> không mở window

    print("[JOY] Looking for Xbox controller...")
    joystick = None

    def find_joystick():
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
    last_hat_send_time = 0.0
    last_send_time = 0.0
    last_buttons = {}
    controller_connected = True

    print("\n===== CONTROLLER MODE =====")
    print("D-pad: move (hold để chạy liên tục)")
    print("A: unlock | B: lock | X: STOP | Y: demo seq")
    print("Ctrl+C để quay lại menu.\n")

    try:
        while True:
            # HEARTBEAT watchdog
            hb_age = get_heartbeat_age()
            if hb_age > 3.0:
                print("[HEALTH] WARNING: No heartbeat from RPi > 3s")

            # Controller disconnect / reconnect
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

            # Cập nhật trạng thái joystick
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

            # --- D-PAD (hat) + giữ để lặp lệnh ---
            if joystick.get_numhats() > 0:
                hat_x, hat_y = joystick.get_hat(0)
            else:
                hat_x, hat_y = 0, 0

            if (hat_x, hat_y) != last_hat:
                last_hat = (hat_x, hat_y)
                cmd = map_hat_to_cmd(hat_x, hat_y)
                if cmd and (now - last_send_time) >= SEND_COOLDOWN:
                    send_command(sock, cmd)
                    last_send_time = now
                    last_hat_send_time = now
            else:
                # Giữ D-pad → lặp lại lệnh theo REPEAT_HOLD_INTERVAL
                if (hat_x, hat_y) != (0, 0):
                    if (now - last_hat_send_time) >= REPEAT_HOLD_INTERVAL:
                        cmd = map_hat_to_cmd(hat_x, hat_y)
                        if cmd:
                            send_command(sock, cmd)
                            last_send_time = now
                            last_hat_send_time = now

            # --- BUTTONS (A,B,X,Y) ---
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
                if val == 1 and prev_val == 0:
                    btn_name = get_button_name(i)
                    print(f"[JOY] Button pressed: {btn_name} (index={i})")
                    now_btn = time.time()
                    if (now_btn - last_send_time) < SEND_COOLDOWN:
                        continue

                    if btn_name == "A":
                        send_command(sock, "unlock")
                    elif btn_name == "B":
                        send_command(sock, "lock")
                    elif btn_name == "X":
                        send_command(sock, "stop")
                    elif btn_name == "Y":
                        seq_cmd = 'seq forward 1; right 1; backward 1; left 1; stop'
                        send_command(sock, seq_cmd)

                    last_send_time = now_btn

            last_buttons = now_state

            time.sleep(0.02)

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
