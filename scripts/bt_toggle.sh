#!/bin/bash
# Bluetooth power toggle script
# Arguments: "on" or "off"

ACTION="$1"

if [ -z "$ACTION" ]; then
    echo "Usage: $0 <on|off>"
    exit 1
fi

if [ "$ACTION" = "on" ]; then
    rfkill unblock bluetooth 2>/dev/null
    bluetoothctl power on 2>/dev/null
else
    bluetoothctl power off 2>/dev/null
fi
