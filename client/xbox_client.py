#!/usr/bin/env python3
import sys
import time
import json
import os
import pygame
import zmq

from dotenv import load_dotenv 


# ==== LOAD ENV ====
# Tự động đọc file .env trong cùng thư mục (nếu có)
load_dotenv()

# ==== CONFIG NETWORK (đọc từ ENV) ====
RPI_IP = os.getenv("RPI_IP", "192.168.10.200")
ZMQ_PORT = int(os.getenv("ZMQ_PORT", "5555"))
ADDR = f"tcp://{RPI_IP}:{ZMQ_PORT}"

# Thời lượng mỗi bước di chuyển (giây) – cũng lấy từ env, có default
DUR_FORWARD = float(os.getenv("DUR_FORWARD", "0.5"))
DUR_BACKWARD = float(os.getenv("DUR_BACKWARD", "0.5"))
DUR_TURN = float(os.getenv("DUR_TURN", "0.3"))

SEND_COOLDOWN = float(os.getenv("SEND_COOLDOWN", "0.05"))  # giãn cách giữa 2 lệnh


def init_zmq():
    ctx = zmq.Context.instance()
    sock = ctx.socket(zmq.REQ)
    sock.connect(ADDR)
    print(f"[NET] Connected to {ADDR}")
    return ctx, sock

def send_command(sock, cmd: str):
    """
    Gửi lệnh dạng text tới RPi.
    Ví dụ:
      'forward 0.5'
      'stop'
      'seq forward 2; right 1; stop'
    """
    try:
        print(f"[NET] -> {cmd!r}")
        sock.send_string(cmd)
        reply = sock.recv().decode("utf-8", errors="replace")
        print(f"[NET] <- {reply}")
    except Exception as e:
        print(f"[NET] ERROR: {e}")

def map_hat_to_cmd(hat_x: int, hat_y: int):
    """
    D-pad mapping:
      (0,  1) -> forward
      (0, -1) -> backward
      (-1, 0) -> left
      (1,  0) -> right
      (0,  0) -> stop
    Trả về string command hoặc None nếu không gửi gì.
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
        # thả D-pad -> STOP khẩn
        return "stop"
    else:
        return None

def get_button_name(joystick, btn_index: int):
    """
    Mapping cơ bản cho XBOX controller (thường):
      0 -> A
      1 -> B
      2 -> X
      3 -> Y
    Các nút khác bạn có thể in ra để debug.
    """
    mapping = {
        0: "A",
        1: "B",
        2: "X",
        3: "Y",
    }
    return mapping.get(btn_index, f"BTN_{btn_index}")

def main():
    pygame.init()
    pygame.joystick.init()

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
        print(f"[JOY] Connected: {joystick.get_name()} (axes={joystick.get_numaxes()}, buttons={joystick.get_numbuttons()}, hats={joystick.get_numhats()})")
        return True

    # Thử kết nối ban đầu
    while not find_joystick():
        print("[JOY] No controller found. Please connect an Xbox controller...")
        time.sleep(1.0)

    ctx, sock = init_zmq()

    last_hat = (0, 0)
    last_send_time = 0.0
    last_buttons = {}
    controller_connected = True

    try:
        while True:
            # Kiểm tra kết nối controller
            if pygame.joystick.get_count() == 0:
                if controller_connected:
                    controller_connected = False
                    print("[JOY] Controller disconnected! Sending STOP...")
                    # khi mất kết nối -> gửi lệnh STOP
                    send_command(sock, "stop")
                    print("[JOY] Please reconnect the controller.")
                # thử tìm lại
                find_joystick()
                time.sleep(0.5)
                continue
            else:
                if not controller_connected:
                    controller_connected = True
                    print("[JOY] Controller reconnected.")

            # Xử lý event của pygame
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    print("[JOY] Quit signal received.")
                    return

            if joystick is None:
                # trong trường hợp hiếm, joystick chưa được init lại
                time.sleep(0.1)
                continue

            # Đọc D-pad (hat 0)
            if joystick.get_numhats() > 0:
                hat_x, hat_y = joystick.get_hat(0)
            else:
                hat_x, hat_y = 0, 0

            # Nếu D-pad thay đổi -> gửi lệnh tương ứng
            if (hat_x, hat_y) != last_hat:
                last_hat = (hat_x, hat_y)
                cmd = map_hat_to_cmd(hat_x, hat_y)
                now = time.time()
                if cmd and (now - last_send_time) >= SEND_COOLDOWN:
                    send_command(sock, cmd)
                    last_send_time = now

            # Đọc các nút để xử lý lock/unlock/stop
            num_buttons = joystick.get_numbuttons()
            now_state = {}
            for i in range(num_buttons):
                val = joystick.get_button(i)
                now_state[i] = val

            # Phát hiện nút "vừa bấm xuống" (edge)
            for i, val in now_state.items():
                prev_val = last_buttons.get(i, 0)
                if val == 1 and prev_val == 0:
                    # button i vừa được nhấn
                    btn_name = get_button_name(joystick, i)
                    print(f"[JOY] Button pressed: {btn_name} (index={i})")
                    now = time.time()
                    if (now - last_send_time) < SEND_COOLDOWN:
                        continue

                    if btn_name == "A":
                        send_command(sock, "unlock")
                        last_send_time = now
                    elif btn_name == "B":
                        send_command(sock, "lock")
                        last_send_time = now
                    elif btn_name == "X":
                        # Emergency stop
                        send_command(sock, "stop")
                        last_send_time = now
                    elif btn_name == "Y":
                        # Ví dụ: một seq ngắn demo (bạn có thể đổi tuỳ ý)
                        seq_cmd = 'seq forward 1; right 1; backward 1; left 1; stop'
                        send_command(sock, seq_cmd)
                        last_send_time = now
                    else:
                        # Các nút khác nếu muốn dùng, map thêm ở đây
                        pass

            last_buttons = now_state

            # vòng lặp ~50Hz
            time.sleep(0.02)

    except KeyboardInterrupt:
        print("\n[MAIN] KeyboardInterrupt, exiting...")
    finally:
        # đảm bảo gửi STOP khi thoát
        try:
            send_command(sock, "stop")
        except Exception:
            pass
        pygame.joystick.quit()
        pygame.quit()
        print("[MAIN] Shutdown complete.")

if __name__ == "__main__":
    main()
