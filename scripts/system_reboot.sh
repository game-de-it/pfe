#!/bin/sh
# System reboot script
#

# Check if running as root
if [ "$(id -u)" -eq 0 ]; then
    # Running as root
    if command -v systemctl >/dev/null 2>&1; then
        systemctl reboot
    else
        reboot
    fi
else
    # Not root, use sudo
    if command -v systemctl >/dev/null 2>&1; then
        sudo systemctl reboot
    else
        sudo reboot
    fi
fi

exit $?
