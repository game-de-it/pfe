#!/bin/sh
# Connect to a WiFi network using nmcli
#
# Usage: wifi_connect.sh <SSID> <PASSWORD>
#
# Arguments:
#   $1 - SSID (network name)
#   $2 - Password
#
# Exit codes:
#   0 - Connection successful
#   1 - Connection failed

SSID="$1"
PASSWORD="$2"

# Validate arguments
if [ -z "$SSID" ]; then
    echo "Error: SSID is required" >&2
    exit 1
fi

if [ -z "$PASSWORD" ]; then
    echo "Error: Password is required" >&2
    exit 1
fi

# Ensure PATH includes common locations for nmcli
export PATH="/usr/bin:/usr/sbin:/bin:/sbin:$PATH"

# For systemd service environment: use system D-Bus
export DBUS_SYSTEM_BUS_ADDRESS="unix:path=/run/dbus/system_bus_socket"

# Debug: Show environment info
echo "[wifi_connect] Running as user: $(whoami)"
echo "[wifi_connect] DBUS_SESSION_BUS_ADDRESS: ${DBUS_SESSION_BUS_ADDRESS:-not set}"
echo "[wifi_connect] nmcli path: $(which nmcli)"

# Debug: Show existing connections for this SSID
echo "[wifi_connect] Checking existing connections for: $SSID"
nmcli -t -f NAME,TYPE connection show 2>&1 | grep -i "$SSID" || echo "[wifi_connect] No existing connection found"

# Delete existing connection profile to avoid key-mgmt errors
# Requires sudo for privilege elevation
echo "[wifi_connect] Deleting existing connection..."
DELETE_OUTPUT=$(sudo nmcli connection delete "$SSID" 2>&1)
DELETE_EXIT=$?
echo "[wifi_connect] Delete exit code: $DELETE_EXIT"
echo "[wifi_connect] Delete output: $DELETE_OUTPUT"

# Small delay to ensure deletion is complete
sleep 1

# Attempt to connect with 30 second timeout
echo "[wifi_connect] Connecting to $SSID..."
sudo nmcli --wait 30 device wifi connect "$SSID" password "$PASSWORD"

exit $?
