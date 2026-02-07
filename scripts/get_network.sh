#!/bin/sh
# Get network connectivity status
#
# Output: "connected" or "disconnected"
#

# Get default gateway
GATEWAY=$(ip route 2>/dev/null | grep default | awk '{print $3}' | head -1)

if [ -z "$GATEWAY" ]; then
    echo "disconnected"
    exit 0
fi

# Ping gateway with 1 second timeout
if ping -c 1 -W 1 "$GATEWAY" >/dev/null 2>&1; then
    echo "connected"
else
    echo "disconnected"
fi

exit 0
