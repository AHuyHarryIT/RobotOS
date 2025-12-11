import os
from dotenv import load_dotenv

# Load .env trong cùng thư mục
load_dotenv()

# Network
RPI_IP = os.getenv("RPI_IP", os.getenv("RPI_HOST", "192.168.10.200"))
ZMQ_PORT = int(os.getenv("ZMQ_PORT", "5555"))
HEARTBEAT_PORT = int(os.getenv("HEARTBEAT_PORT", "5556"))
CLIENT_SERVER_PORT = int(os.getenv("CLIENT_SERVER_PORT", "5557")) 

ADDR = f"tcp://{RPI_IP}:{ZMQ_PORT}"
HB_ADDR = f"tcp://{RPI_IP}:{HEARTBEAT_PORT}"

# Movement params
DUR_FORWARD = float(os.getenv("DUR_FORWARD", "0.5"))
DUR_BACKWARD = float(os.getenv("DUR_BACKWARD", "0.5"))
DUR_TURN = float(os.getenv("DUR_TURN", "0.3"))
SEND_COOLDOWN = float(os.getenv("SEND_COOLDOWN", "0.05"))
REPEAT_HOLD_INTERVAL = float(os.getenv("REPEAT_HOLD_INTERVAL", "0.15"))
