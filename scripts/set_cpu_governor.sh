#!/bin/sh
# Set CPU governor
#
# Arguments: $1 = governor name (ondemand, performance, powersave, etc.)
#

GOVERNOR="$1"

if [ -z "$GOVERNOR" ]; then
    echo "Usage: $0 <governor>"
    exit 1
fi

# Common governor paths
GOVERNOR_PATHS="
/sys/devices/system/cpu/cpufreq/policy0/scaling_governor
/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
"

# Find governor file and set
for path in $GOVERNOR_PATHS; do
    if [ -f "$path" ]; then
        # Try direct write first
        if echo "$GOVERNOR" > "$path" 2>/dev/null; then
            exit 0
        fi
        # Try with sudo if direct write fails
        if sudo sh -c "echo '$GOVERNOR' > '$path'" 2>/dev/null; then
            exit 0
        fi
        exit 1
    fi
done

exit 1
