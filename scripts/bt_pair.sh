#!/bin/bash
# Bluetooth pairing script
# Arguments: $1=MAC address, $2=PIN (optional)

MAC="$1"
PIN="$2"

if [ -z "$MAC" ]; then
    echo "Usage: $0 <MAC_ADDRESS> [PIN]"
    exit 1
fi

# Trust the device
bluetoothctl trust "$MAC" 2>/dev/null

# If PIN is provided, set up agent with PIN
if [ -n "$PIN" ]; then
    # Use expect-like approach with bluetoothctl
    (
        echo "agent off"
        echo "agent on"
        echo "default-agent"
        sleep 1
        echo "pair $MAC"
        sleep 3
        echo "$PIN"
        sleep 2
        echo "connect $MAC"
        sleep 3
        echo "quit"
    ) | bluetoothctl 2>/dev/null
else
    # No PIN pairing
    bluetoothctl pair "$MAC" 2>/dev/null
    sleep 3
    bluetoothctl connect "$MAC" 2>/dev/null
fi

# Check connection status
if bluetoothctl info "$MAC" 2>/dev/null | grep -q "Connected: yes"; then
    echo "connected"
    exit 0
else
    echo "failed"
    exit 1
fi
