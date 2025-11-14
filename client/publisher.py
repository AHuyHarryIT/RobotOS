import zmq, time, msgpack

ctx = zmq.Context()
pub = ctx.socket(zmq.PUB)
pub.bind("tcp://*:5556")  # mở port 5556 để Raspberry Pi connect

print("[PUB] Bound to tcp://*:5556")
time.sleep(0.5)  # đợi subscriber sẵn sàng

seq = 0
while True:
    data = {"seq": seq, "msg": f"Hello from Mini-PC #{seq}", "ts": time.time()}
    pub.send_multipart([b"test/topic", msgpack.packb(data, use_bin_type=True)])
    print(f"[PUB] Sent: {data}")
    seq += 1
    time.sleep(1)
