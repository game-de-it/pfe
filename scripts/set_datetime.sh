#!/bin/bash
# Set system date and time
# Usage: set_datetime.sh YYYY MM DD HH MM
# Example: set_datetime.sh 2024 12 25 14 30

YEAR=$1
MONTH=$2
DAY=$3
HOUR=$4
MINUTE=$5

if [ -z "$YEAR" ] || [ -z "$MONTH" ] || [ -z "$DAY" ] || [ -z "$HOUR" ] || [ -z "$MINUTE" ]; then
    echo "Usage: $0 YYYY MM DD HH MM"
    exit 1
fi

# Format: YYYY-MM-DD HH:MM:00
DATETIME="${YEAR}-${MONTH}-${DAY} ${HOUR}:${MINUTE}:00"

# Try to set the date (requires root or sudo privileges)
if command -v sudo &> /dev/null; then
    sudo date -s "$DATETIME" 2>/dev/null || date -s "$DATETIME" 2>/dev/null
else
    date -s "$DATETIME" 2>/dev/null
fi

# Sync hardware clock if available
if command -v hwclock &> /dev/null; then
    if command -v sudo &> /dev/null; then
        sudo hwclock -w 2>/dev/null || hwclock -w 2>/dev/null
    else
        hwclock -w 2>/dev/null
    fi
fi

echo "Date set to: $DATETIME"
exit 0
