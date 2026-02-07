#!/bin/sh
# WiFi status script using connmanctl (ConnMan)
# ConnManを使用したWiFi状態取得スクリプト
#
# 出力: "enabled" または "disabled"
#

# Check WiFi technology state
STATE=$(connmanctl technologies 2>/dev/null | grep -A5 "Type = wifi" | grep "Powered" | awk '{print $3}')

if [ "$STATE" = "True" ]; then
    echo "enabled"
else
    echo "disabled"
fi

exit 0
