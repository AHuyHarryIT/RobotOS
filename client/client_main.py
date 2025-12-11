# client_main.py
from zmq_client import init_zmq, send_command
from seq_mode import seq_console_loop
from controller_mode import controller_loop
from command_server import start_command_server, stop_command_server


def main():
    ctx, sock = init_zmq()
    
    # Start command server to receive from Jetson
    print("\n[INIT] Starting command server for Jetson/external sources...")
    start_command_server(sock)
    print("[INIT] Command server is running in background")

    while True:
        print("\n========================")
        print("  AUTO-BOT CLIENT MENU ")
        print("========================")
        print("1. Sequence mode (gõ lệnh / seq, có STOP chen ngang)")
        print("2. Controller mode (Xbox)")
        print("3. Server mode only (chỉ nhận từ Jetson, không điều khiển thủ công)")
        print("q. Thoát")
        choice = input("Chọn mode (1/2/3/q): ").strip().lower()

        if choice == "1":
            seq_console_loop(sock)
        elif choice == "2":
            controller_loop(sock)
        elif choice == "3":
            print("\n[SERVER MODE] Client đang chạy command server")
            print("Nhận lệnh từ Jetson và forward tới RPi")
            print("Nhấn Ctrl+C hoặc 'q' để quay lại menu")
            try:
                while True:
                    cmd = input("(Nhấn 'q' để quay lại menu): ").strip().lower()
                    if cmd in ("q", "quit", "back", "menu"):
                        break
            except KeyboardInterrupt:
                print("\nQuay lại menu...")
        elif choice in ("q", "quit", "exit"):
            print("Thoát client, gửi STOP lần cuối...")
            try:
                send_command(sock, "stop")
            except Exception:
                pass
            stop_command_server()
            break
        else:
            print("Lựa chọn không hợp lệ, hãy nhập 1, 2, 3, hoặc q.")


if __name__ == "__main__":
    main()
