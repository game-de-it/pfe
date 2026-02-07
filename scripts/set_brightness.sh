#!/bin/sh
# Set brightness level (0-10)
# Customize this script for your hardware
#
# Usage: set_brightness.sh <level>
# where level is 0-10 (0 = off, 10 = max)
#
# Example implementations:
#
# For /sys/class/backlight (common on Linux):
#   BACKLIGHT_PATH="/sys/class/backlight/backlight"
#   MAX=$(cat "$BACKLIGHT_PATH/max_brightness")
#   VALUE=$(( LEVEL * MAX / 10 ))
#   echo "$VALUE" > "$BACKLIGHT_PATH/brightness"

LEVEL="$1"

if [ -z "$LEVEL" ]; then
    echo "Usage: $0 <level>" >&2
    exit 1
fi

BACKLIGHT_PATH="/sys/class/backlight/backlight"

if [ -f "$BACKLIGHT_PATH/brightness" ] && [ -f "$BACKLIGHT_PATH/max_brightness" ]; then
    MAX=$(cat "$BACKLIGHT_PATH/max_brightness")
    if [ "$MAX" -gt 0 ]; then
        # Convert from 0-10 scale to hardware scale
        VALUE=$(( LEVEL * MAX / 10 ))
        echo "$VALUE" > "$BACKLIGHT_PATH/brightness" 2>/dev/null
        if [ $? -eq 0 ]; then
            exit 0
        fi
    fi
fi

# Fallback: do nothing but report success
# (for testing on systems without backlight control)
exit 0
