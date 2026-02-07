#!/bin/sh
# Toggle WiFi radio ON or OFF
#
# Usage: wifi_toggle.sh <on|off>
#
# Arguments:
#   $1 - "on" to enable WiFi, "off" to disable WiFi
#
# Exit codes:
#   0 - Success
#   1 - Error

ACTION="$1"

# Validate argument
if [ "$ACTION" != "on" ] && [ "$ACTION" != "off" ]; then
    echo "Usage: wifi_toggle.sh <on|off>" >&2
    exit 1
fi

# Ensure PATH includes common locations for nmcli
export PATH="/usr/bin:/usr/sbin:/bin:/sbin:$PATH"

echo "[wifi_toggle] Setting WiFi radio to: $ACTION"

# Use sudo for privilege elevation
sudo nmcli radio wifi "$ACTION"
EXIT_CODE=$?

echo "[wifi_toggle] Exit code: $EXIT_CODE"

exit $EXIT_CODE
