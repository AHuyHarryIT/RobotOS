# client_main.py
from zmq_client import init_zmq, send_command
from seq_mode import seq_console_loop
from controller_mode import controller_loop


def main():
    ctx, sock = init_zmq()

    while True:
        print("\n========================")
        print("  AUTO-BOT CLIENT MENU ")
        print("========================")
        print("1. Sequence mode (gõ lệnh / seq, có STOP chen ngang)")
        print("2. Controller mode (Xbox)")
        print("q. Thoát")
        choice = input("Chọn mode (1/2/q): ").strip().lower()

        if choice == "1":
            seq_console_loop(sock)
        elif choice == "2":
            controller_loop(sock)
        elif choice in ("q", "quit", "exit"):
            print("Thoát client, gửi STOP lần cuối...")
            try:
                send_command(sock, "stop")
            except Exception:
                pass
            break
        else:
            print("Lựa chọn không hợp lệ, hãy nhập 1, 2, hoặc q.")


if __name__ == "__main__":
    main()
