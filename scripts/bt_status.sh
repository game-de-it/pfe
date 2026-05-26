#!/bin/bash
# Bluetooth power status script
# Output: "enabled" or "disabled"

STATUS=$(bluetoothctl show 2>/dev/null | grep "Powered:" | awk '{print $2}')

if [ "$STATUS" = "yes" ]; then
    echo "enabled"
else
    echo "disabled"
fi
