#!/bin/sh
# WiFi scan script using iwctl (iwd)
# iwdを使用したWiFiスキャンスクリプト
#
# 前提条件:
# - iwd (iNet Wireless Daemon) がインストール・起動していること
# - systemctl enable --now iwd
#

INTERFACE="${WIFI_INTERFACE:-wlan0}"

# Trigger scan
iwctl station "$INTERFACE" scan 2>/dev/null
sleep 3

# Get networks
# iwctl station wlan0 get-networks outputs formatted table
# Parse to extract network names
iwctl station "$INTERFACE" get-networks 2>/dev/null | \
    tail -n +5 | \
    sed 's/^[[:space:]]*//' | \
    awk -F'[[:space:]]{2,}' 'NF >= 1 && $1 != "" && $1 !~ /^-/ { print $1 }' | \
    sed 's/^>//' | \
    sed 's/^[[:space:]]*//' | \
    awk 'NF && !seen[$0]++'

exit 0
