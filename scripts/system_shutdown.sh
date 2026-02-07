#!/bin/sh
# System shutdown script
#

# Check if running as root
if [ "$(id -u)" -eq 0 ]; then
    # Running as root
    if command -v systemctl >/dev/null 2>&1; then
        systemctl poweroff
    else
        poweroff
    fi
else
    # Not root, use sudo
    if command -v systemctl >/dev/null 2>&1; then
        sudo systemctl poweroff
    else
        sudo poweroff
    fi
fi

exit $?
