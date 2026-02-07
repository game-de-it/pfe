#!/bin/sh
# Get battery level and status
#
# Output format: <capacity> <status>
# Example: "85 Charging" or "100 Full" or "50 Discharging"
# If no battery is found, nothing is output
#

# Common battery paths
BATTERY_PATHS="
/sys/class/power_supply/axp20x-battery
/sys/class/power_supply/BAT0
/sys/class/power_supply/BAT1
/sys/class/power_supply/battery
"

# Find battery
BATTERY_PATH=""
for path in $BATTERY_PATHS; do
    if [ -f "${path}/capacity" ]; then
        BATTERY_PATH="$path"
        break
    fi
done

# No battery found
if [ -z "$BATTERY_PATH" ]; then
    exit 0
fi

# Read capacity
CAPACITY=""
if [ -f "${BATTERY_PATH}/capacity" ]; then
    CAPACITY=$(cat "${BATTERY_PATH}/capacity" 2>/dev/null)
fi

# Read status
STATUS=""
if [ -f "${BATTERY_PATH}/status" ]; then
    STATUS=$(cat "${BATTERY_PATH}/status" 2>/dev/null)
fi

# Output
if [ -n "$CAPACITY" ]; then
    echo "${CAPACITY} ${STATUS:-Unknown}"
fi

exit 0
