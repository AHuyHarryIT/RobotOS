#!/usr/bin/env bash
set -euo pipefail

# ================================
# Ethernet static IP setup for Raspberry Pi (Bookworm)
# (NO systemd-resolved required)
# ================================

IFACE="${1:-eth0}"
IP_CIDR="${2:-192.168.10.200/24}"
GATEWAY="${3:-192.168.10.1}"
DNS1="${4:-1.1.1.1}"
DNS2="${5:-8.8.8.8}"

NETWORK_DIR="/etc/systemd/network"
NET_FILE="${NETWORK_DIR}/20-wired-${IFACE}.network"

echo "=== Raspberry Pi Ethernet setup ==="
echo "Interface : ${IFACE}"
echo "IP/CIDR   : ${IP_CIDR}"
echo "Gateway   : ${GATEWAY}"
echo "DNS       : ${DNS1}, ${DNS2}"
echo

if [[ "$EUID" -ne 0 ]]; then
  echo "Run as root: sudo $0"
  exit 1
fi

# ---- Disable dhcpcd (if exists) ----
if systemctl list-unit-files | grep -q "^dhcpcd.service"; then
  echo "[INFO] Disabling dhcpcd.service..."
  systemctl disable dhcpcd --now || true
fi

# ---- Enable systemd-networkd only ----
echo "[INFO] Enabling systemd-networkd..."
systemctl enable systemd-networkd --now

# ---- Create network configuration ----
echo "[INFO] Writing ${NET_FILE} ..."
mkdir -p "${NETWORK_DIR}"

cat > "${NET_FILE}" <<EOF
[Match]
Name=${IFACE}

[Network]
DHCP=no
Address=${IP_CIDR}
Gateway=${GATEWAY}
DNS=${DNS1}
DNS=${DNS2}
EOF

# ---- Restart service ----
echo "[INFO] Restarting systemd-networkd..."
systemctl restart systemd-networkd

sleep 2

echo
echo "=== IPv4 Address ==="
ip -4 addr show "${IFACE}" || true

echo
echo "=== Routes ==="
ip route || true

echo
echo "[DONE] Static Ethernet configured."
