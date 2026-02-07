#!/bin/sh
# WiFi status script using wpa_supplicant / rfkill
# wpa_supplicantを使用したWiFi状態取得スクリプト
#
# 出力: "enabled" または "disabled"
#

INTERFACE="${WIFI_INTERFACE:-wlan0}"

# Check if interface exists and is up
if [ -d "/sys/class/net/$INTERFACE" ]; then
    # Check rfkill status
    if command -v rfkill >/dev/null 2>&1; then
        BLOCKED=$(rfkill list wifi 2>/dev/null | grep -i "Soft blocked: yes")
        if [ -n "$BLOCKED" ]; then
            echo "disabled"
            exit 0
        fi
    fi

    # Check interface operstate
    OPERSTATE=$(cat "/sys/class/net/$INTERFACE/operstate" 2>/dev/null)
    if [ "$OPERSTATE" = "down" ]; then
        echo "disabled"
    else
        echo "enabled"
    fi
else
    echo "disabled"
fi

exit 0
