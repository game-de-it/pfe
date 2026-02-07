#!/bin/sh
# WiFi connect script using wpa_supplicant / wpa_cli
# wpa_supplicantを使用したWiFi接続スクリプト
#
# 前提条件:
# - wpa_supplicantが起動していること
# - wpa_supplicant.confでctrl_interfaceが設定されていること
#
# 引数:
#   $1: SSID
#   $2: パスワード
#

SSID="$1"
PASSWORD="$2"
INTERFACE="${WIFI_INTERFACE:-wlan0}"

if [ -z "$SSID" ] || [ -z "$PASSWORD" ]; then
    echo "Usage: $0 <SSID> <PASSWORD>"
    exit 1
fi

# Remove existing network with same SSID
EXISTING_ID=$(wpa_cli -i "$INTERFACE" list_networks 2>/dev/null | \
    grep -F "$SSID" | awk '{print $1}' | head -1)

if [ -n "$EXISTING_ID" ]; then
    wpa_cli -i "$INTERFACE" remove_network "$EXISTING_ID" >/dev/null 2>&1
fi

# Add new network
NETWORK_ID=$(wpa_cli -i "$INTERFACE" add_network 2>/dev/null | tail -1)

if [ -z "$NETWORK_ID" ] || [ "$NETWORK_ID" = "FAIL" ]; then
    echo "Failed to add network"
    exit 1
fi

# Configure network
wpa_cli -i "$INTERFACE" set_network "$NETWORK_ID" ssid "\"$SSID\"" >/dev/null 2>&1
wpa_cli -i "$INTERFACE" set_network "$NETWORK_ID" psk "\"$PASSWORD\"" >/dev/null 2>&1
wpa_cli -i "$INTERFACE" set_network "$NETWORK_ID" key_mgmt WPA-PSK >/dev/null 2>&1

# Enable and connect
wpa_cli -i "$INTERFACE" enable_network "$NETWORK_ID" >/dev/null 2>&1
wpa_cli -i "$INTERFACE" select_network "$NETWORK_ID" >/dev/null 2>&1

# Wait for connection
TIMEOUT=30
COUNT=0
while [ $COUNT -lt $TIMEOUT ]; do
    STATUS=$(wpa_cli -i "$INTERFACE" status 2>/dev/null | grep "wpa_state=" | cut -d= -f2)
    if [ "$STATUS" = "COMPLETED" ]; then
        # Save configuration
        wpa_cli -i "$INTERFACE" save_config >/dev/null 2>&1
        echo "Connected to $SSID"

        # Request DHCP (if dhclient is available)
        if command -v dhclient >/dev/null 2>&1; then
            dhclient "$INTERFACE" 2>/dev/null
        elif command -v dhcpcd >/dev/null 2>&1; then
            dhcpcd "$INTERFACE" 2>/dev/null
        fi

        exit 0
    fi
    sleep 1
    COUNT=$((COUNT + 1))
done

echo "Connection timeout"
exit 1
