import zmq
ctx = zmq.Context()
req = ctx.socket(zmq.REQ)
req.connect("tcp://192.168.10.200:5557")
for i in range(3):
    req.send_json({"cmd": f"ping{i}"})
    print("[REQ] Reply:", req.recv_json())