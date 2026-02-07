#!/bin/sh
# Get current CPU governor
#
# Output: "ondemand", "performance", "powersave", etc.
# If unable to retrieve, nothing is output
#

# Common governor paths
GOVERNOR_PATHS="
/sys/devices/system/cpu/cpufreq/policy0/scaling_governor
/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
"

# Find governor file
for path in $GOVERNOR_PATHS; do
    if [ -f "$path" ]; then
        cat "$path" 2>/dev/null
        exit 0
    fi
done

exit 0
