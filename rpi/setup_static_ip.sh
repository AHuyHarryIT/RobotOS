#!/usr/bin/env bash
set -euo pipefail

IFACE="eth0"
IP="192.168.10.210/24"
GATEWAY="192.168.10.1"
DNS="8.8.8.8"

echo "[INFO] Configuring static IPv4 for Jetson Nano..."

# Find existing connection for eth0
CON_NAME=$(nmcli -t -f NAME,DEVICE connection show | awk -F: -v IFACE="$IFACE" '$2==IFACE {print $1; exit}')

# If no connection exists, create one
if [[ -z "$CON_NAME" ]]; then
  echo "[INFO] No existing connection found. Creating new one..."
  CON_NAME="$IFACE"
  nmcli connection add type ethernet ifname "$IFACE" con-name "$CON_NAME" autoconnect yes
fi

echo "[INFO] Using connection name: $CON_NAME"

# Apply static configuration
nmcli connection modify "$CON_NAME" \
  ipv4.addresses "$IP" \
  ipv4.gateway "$GATEWAY" \
  ipv4.dns "$DNS" \
  ipv4.method manual \
  ipv6.method ignore

# Restart the connection
nmcli connection down "$CON_NAME" || true
nmcli connection up "$CON_NAME"

echo "[OK] Static IP set to 192.168.10.210"
EOF