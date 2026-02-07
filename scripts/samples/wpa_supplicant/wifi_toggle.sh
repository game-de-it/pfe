#!/bin/sh
# WiFi toggle script using rfkill / ip
# WiFi電源切り替えスクリプト
#
# 引数:
#   $1: "on" または "off"
#

ACTION="$1"
INTERFACE="${WIFI_INTERFACE:-wlan0}"

if [ -z "$ACTION" ]; then
    echo "Usage: $0 <on|off>"
    exit 1
fi

case "$ACTION" in
    on)
        # Unblock WiFi via rfkill
        if command -v rfkill >/dev/null 2>&1; then
            sudo rfkill unblock wifi
        fi
        # Bring interface up
        sudo ip link set "$INTERFACE" up 2>/dev/null
        echo "WiFi enabled"
        ;;
    off)
        # Bring interface down
        sudo ip link set "$INTERFACE" down 2>/dev/null
        # Block WiFi via rfkill
        if command -v rfkill >/dev/null 2>&1; then
            sudo rfkill block wifi
        fi
        echo "WiFi disabled"
        ;;
    *)
        echo "Usage: $0 <on|off>"
        exit 1
        ;;
esac

exit 0
