#!/usr/bin/env python3
"""
Client Configuration Module

Loads configuration from environment variables (.env file).
Provides centralized access to all client settings including:
    - Network addresses (RPi IP, ZMQ ports)
    - Movement parameters (duration, cooldowns)
    - Controller settings (repeat intervals)

All values have sensible defaults for easy setup.

Author: Auto-Bot Team
"""
import os
from dotenv import load_dotenv

# Load .env from current directory
load_dotenv()

# ============================================================
# Network Configuration
# ============================================================

# RPi server address
RPI_IP = os.getenv("RPI_IP", "192.168.10.200")

# ZMQ ports
ZMQ_PORT = int(os.getenv("ZMQ_PORT", "5555"))              # Server -> RPi command port
HEARTBEAT_PORT = int(os.getenv("HEARTBEAT_PORT", "5556"))  # RPi -> Server heartbeat port
SERVER_PORT = int(os.getenv("SERVER_PORT", "5557"))  # Jetson -> Server command port

# Build connection addresses
ADDR = f"tcp://{RPI_IP}:{ZMQ_PORT}"          # Address for sending commands to RPi
HB_ADDR = f"tcp://{RPI_IP}:{HEARTBEAT_PORT}"  # Address for receiving heartbeat from RPi

# ============================================================
# Movement Parameters
# ============================================================

# Default movement durations (in seconds)
DUR_FORWARD = float(os.getenv("DUR_FORWARD", "0.5"))   # Forward movement duration
DUR_BACKWARD = float(os.getenv("DUR_BACKWARD", "0.5"))  # Backward movement duration
DUR_TURN = float(os.getenv("DUR_TURN", "0.3"))          # Turn duration (left/right)

# ============================================================
# Control Parameters
# ============================================================

# Rate limiting
SEND_COOLDOWN = float(os.getenv("SEND_COOLDOWN", "0.05"))  # Minimum interval between commands

# Controller settings
REPEAT_HOLD_INTERVAL = float(os.getenv("REPEAT_HOLD_INTERVAL", "0.15"))  # Hold-to-repeat interval for D-pad
