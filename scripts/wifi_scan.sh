#!/bin/sh
# Scan for available WiFi networks and output SSIDs
# Outputs one SSID per line, with duplicates removed
#
# This script uses nmcli to scan for WiFi networks.
# Customize for your specific hardware/environment if needed.
#
# Exit codes:
#   0 - Success (SSIDs output to stdout)
#   1 - Error (error message to stderr)

# Ensure PATH includes common locations for nmcli
export PATH="/usr/bin:/usr/sbin:/bin:/sbin:$PATH"

# For systemd service environment: use system D-Bus
export DBUS_SYSTEM_BUS_ADDRESS="unix:path=/run/dbus/system_bus_socket"

# Trigger a WiFi rescan (ignore errors - device may be busy)
nmcli device wifi rescan 2>/dev/null

# Wait briefly for scan to complete
sleep 2

# Get list of SSIDs, remove empty lines and duplicates while preserving order
nmcli -t -f SSID device wifi list 2>/dev/null | \
    awk 'NF && !seen[$0]++ { print }'

exit 0
