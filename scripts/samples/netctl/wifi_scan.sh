#!/bin/sh
# WiFi scan script using netctl / wifi-menu (Arch Linux)
# netctlを使用したWiFiスキャンスクリプト
#
# 前提条件:
# - netctl, wpa_supplicant がインストールされていること
# - wifi-menu が利用可能であること (netctl-auto パッケージ)
#

INTERFACE="${WIFI_INTERFACE:-wlan0}"

# Bring interface up for scanning
sudo ip link set "$INTERFACE" up 2>/dev/null
sleep 1

# Use wpa_supplicant for scanning (netctl doesn't have built-in scan)
# Create temporary wpa_supplicant configuration
TEMP_CONF=$(mktemp)
echo "ctrl_interface=/run/wpa_supplicant" > "$TEMP_CONF"
echo "update_config=1" >> "$TEMP_CONF"

# Start temporary wpa_supplicant for scan
sudo wpa_supplicant -B -i "$INTERFACE" -c "$TEMP_CONF" 2>/dev/null
sleep 1

# Trigger scan
sudo wpa_cli -i "$INTERFACE" scan >/dev/null 2>&1
sleep 3

# Get scan results
sudo wpa_cli -i "$INTERFACE" scan_results 2>/dev/null | \
    tail -n +2 | \
    awk -F'\t' 'NF >= 5 && $5 != "" { print $5 }' | \
    awk '!seen[$0]++'

# Stop temporary wpa_supplicant
sudo wpa_cli -i "$INTERFACE" terminate >/dev/null 2>&1
rm -f "$TEMP_CONF"

exit 0
