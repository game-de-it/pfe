#!/bin/sh
# WiFi scan script using connmanctl (ConnMan)
# ConnManを使用したWiFiスキャンスクリプト
#
# 前提条件:
# - ConnManがインストール・起動していること
# - systemctl enable --now connman
#

WIFI_SCAN_WAIT_SECONDS="${WIFI_SCAN_WAIT_SECONDS:-6}"

# Enable WiFi if not enabled
connmanctl enable wifi >/dev/null 2>&1
sleep 1

# Trigger scan
connmanctl scan wifi >/dev/null 2>&1
sleep "$WIFI_SCAN_WAIT_SECONDS"

# Get services and extract WiFi SSIDs
# connmanctl services format: *AO Name                wifi_xxx_managed_psk
connmanctl services 2>/dev/null | \
    grep "wifi_" | \
    sed 's/^[*A-Z ]*//;s/  *wifi_.*$//' | \
    awk 'NF && !seen[$0]++'

exit 0
