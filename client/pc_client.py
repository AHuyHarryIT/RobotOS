#!/usr/bin/env python3
import zmq
import json
import time

RPI_IP = "172.29.117.141"
PORT = 5555
ADDR = f"tcp://{RPI_IP}:{PORT}"

def send(sock, msg: str):
    print(f"[CLIENT] -> {msg!r}")
    sock.send_string(msg)
    reply = sock.recv().decode("utf-8")
    print(f"[CLIENT] <- {reply}")

def main():
    ctx = zmq.Context.instance()
    sock = ctx.socket(zmq.REQ)
    sock.connect(ADDR)
    print(f"[CLIENT] Connected to {ADDR}")

    # B1: cho xe chạy seq dài
    # send(sock, "seq forward 5; right 5; forward 5; left 5")

    # (hoặc async: bạn có thể sửa client để gửi lệnh mà không chờ xong, nhưng
    #  với REQ/REP thì cần chờ response. Quan trọng là server đã chạy trong thread riêng,
    #  nên sau khi reply xong, nó vẫn tiếp tục chạy motion.)

    # Ví dụ thực tế hơn: bạn gửi lệnh rồi đợi một lúc mới STOP
    send(sock, "seq forward 5; right 5; forward 5")
    time.sleep(7)
    send(sock, "stop")  # EMERGENCY STOP

if __name__ == "__main__":
    main()
