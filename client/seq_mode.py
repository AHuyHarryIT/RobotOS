# seq_mode.py
from zmq_client import send_command


def seq_console_loop(sock):
    """
    REPL console để nhập seq / single command:
      - 'forward 2'
      - 'seq forward 2; right 1; stop'
      - 'stop' (emergency stop)
      - 'back' / 'menu' để quay lại màn hình chọn mode
      - 'exit' / 'quit' / 'q' để thoát chương trình
    """
    print("\n===== SEQUENCE MODE =====")
    print("Nhập lệnh:")
    print("  - Single: forward / backward / left / right / lock / unlock / stop / sleep 1.0")
    print("  - Sequence: seq forward 2; right 1; lock 0.5; stop")
    print("  - back / menu: quay lại màn hình chọn mode")
    print("  - exit / quit / q: thoát chương trình client\n")

    while True:
        try:
            line = input("seq> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[SEQ] KeyboardInterrupt -> gửi STOP và thoát mode.")
            try:
                send_command(sock, "stop")
            except Exception:
                pass
            return

        if not line:
            continue

        low = line.lower()
        if low in ("back", "menu"):
            print("[SEQ] Quay lại màn hình chọn mode.")
            return
        if low in ("exit", "quit", "q"):
            print("[SEQ] Thoát toàn bộ client.")
            raise SystemExit(0)

        send_command(sock, line)
