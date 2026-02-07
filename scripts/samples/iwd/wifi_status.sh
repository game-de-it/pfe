#!/bin/sh
# WiFi status script using iwctl (iwd)
# iwdを使用したWiFi状態取得スクリプト
#
# 出力: "enabled" または "disabled"
#

INTERFACE="${WIFI_INTERFACE:-wlan0}"

# Check adapter power state
POWERED=$(iwctl adapter "$INTERFACE" show 2>/dev/null | grep "Powered" | awk '{print $2}')

if [ "$POWERED" = "on" ]; then
    echo "enabled"
else
    echo "disabled"
fi

exit 0
