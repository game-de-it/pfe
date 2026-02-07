#!/bin/sh
# WiFi scan script using wpa_supplicant / wpa_cli
# wpa_supplicantを使用したWiFiスキャンスクリプト
#
# 前提条件:
# - wpa_supplicantが起動していること
# - wpa_supplicant.confでctrl_interfaceが設定されていること
#
# 使用例:
#   sudo wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant.conf
#

INTERFACE="${WIFI_INTERFACE:-wlan0}"

# Trigger scan
wpa_cli -i "$INTERFACE" scan >/dev/null 2>&1
sleep 3

# Get scan results and extract SSIDs
# wpa_cli scan_results format: bssid / frequency / signal level / flags / ssid
wpa_cli -i "$INTERFACE" scan_results 2>/dev/null | \
    tail -n +2 | \
    awk -F'\t' 'NF >= 5 && $5 != "" { print $5 }' | \
    awk '!seen[$0]++'

exit 0
