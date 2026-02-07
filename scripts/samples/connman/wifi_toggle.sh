#!/bin/sh
# WiFi toggle script using connmanctl (ConnMan)
# ConnManを使用したWiFi電源切り替えスクリプト
#
# 引数:
#   $1: "on" または "off"
#

ACTION="$1"

if [ -z "$ACTION" ]; then
    echo "Usage: $0 <on|off>"
    exit 1
fi

case "$ACTION" in
    on)
        connmanctl enable wifi 2>/dev/null
        echo "WiFi enabled"
        ;;
    off)
        connmanctl disable wifi 2>/dev/null
        echo "WiFi disabled"
        ;;
    *)
        echo "Usage: $0 <on|off>"
        exit 1
        ;;
esac

exit 0
