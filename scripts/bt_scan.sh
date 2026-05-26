#!/bin/bash
# Bluetooth device scan script
# Output format: MAC_ADDRESS\tDeviceName (one device per line)

# Start scanning (background, with timeout)
timeout 8 bluetoothctl scan on &>/dev/null &
SCAN_PID=$!

# Wait for scan to complete
sleep 8
kill $SCAN_PID 2>/dev/null
wait $SCAN_PID 2>/dev/null

# Get discovered devices
bluetoothctl devices | while read -r line; do
    # Format: "Device AA:BB:CC:DD:EE:FF DeviceName"
    MAC=$(echo "$line" | awk '{print $2}')
    NAME=$(echo "$line" | cut -d ' ' -f 3-)
    if [ -n "$MAC" ] && [ -n "$NAME" ]; then
        echo -e "${MAC}\t${NAME}"
    fi
done
