#!/bin/sh
# Get current brightness level (1-10)
# Customize this script for your hardware
#
# This script should output a number from 1 to 10 representing current brightness.
# Example implementations:
#
# For /sys/class/backlight (common on Linux):
#   BACKLIGHT_PATH="/sys/class/backlight/backlight"
#   MAX=$(cat "$BACKLIGHT_PATH/max_brightness")
#   CURRENT=$(cat "$BACKLIGHT_PATH/brightness")
#   echo $(( (CURRENT * 10 + MAX/2) / MAX ))
#
# For Anbernic devices:
#   BACKLIGHT_PATH="/sys/class/backlight/backlight"
#   ... (device-specific implementation)

# Default implementation (placeholder - returns 5)
# Replace with your hardware-specific implementation

BACKLIGHT_PATH="/sys/class/backlight/backlight"

if [ -f "$BACKLIGHT_PATH/brightness" ] && [ -f "$BACKLIGHT_PATH/max_brightness" ]; then
    MAX=$(cat "$BACKLIGHT_PATH/max_brightness")
    CURRENT=$(cat "$BACKLIGHT_PATH/brightness")
    if [ "$MAX" -gt 0 ]; then
        # Convert to 1-10 scale
        LEVEL=$(( (CURRENT * 10 + MAX/2) / MAX ))
        # Ensure minimum of 1 (unless actually 0)
        if [ "$LEVEL" -lt 1 ] && [ "$CURRENT" -gt 0 ]; then
            LEVEL=1
        fi
        echo "$LEVEL"
        exit 0
    fi
fi

# Fallback: return middle value
echo "5"
exit 0
