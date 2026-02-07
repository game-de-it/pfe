#!/bin/sh
# WiFi toggle script using iwctl (iwd)
# iwdを使用したWiFi電源切り替えスクリプト
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
        iwctl adapter "$INTERFACE" set-property Powered on 2>/dev/null
        iwctl device "$INTERFACE" set-property Powered on 2>/dev/null
        echo "WiFi enabled"
        ;;
    off)
        iwctl device "$INTERFACE" set-property Powered off 2>/dev/null
        iwctl adapter "$INTERFACE" set-property Powered off 2>/dev/null
        echo "WiFi disabled"
        ;;
    *)
        echo "Usage: $0 <on|off>"
        exit 1
        ;;
esac

exit 0
