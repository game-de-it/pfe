#!/bin/sh
# WiFi connect script using netctl (Arch Linux)
# netctlを使用したWiFi接続スクリプト
#
# 前提条件:
# - netctl がインストールされていること
# - インターフェースが他のサービス（NetworkManager等）に使用されていないこと
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

# Sanitize SSID for profile name (replace spaces and special chars)
PROFILE_NAME=$(echo "$SSID" | tr ' /' '__' | tr -cd '[:alnum:]_-')
PROFILE_PATH="/etc/netctl/${PROFILE_NAME}"

# Stop any running profile on this interface
sudo netctl stop-all 2>/dev/null

# Create profile file
sudo tee "$PROFILE_PATH" > /dev/null << EOF
Description='Automatically generated profile for ${SSID}'
Interface=${INTERFACE}
Connection=wireless
Security=wpa
ESSID='${SSID}'
Key='${PASSWORD}'
IP=dhcp
EOF

sudo chmod 600 "$PROFILE_PATH"

# Start the profile
sudo netctl start "$PROFILE_NAME" 2>/dev/null

RESULT=$?

if [ $RESULT -eq 0 ]; then
    # Wait for connection
    TIMEOUT=30
    COUNT=0
    while [ $COUNT -lt $TIMEOUT ]; do
        # Check if interface has an IP
        IP=$(ip addr show "$INTERFACE" 2>/dev/null | grep "inet " | awk '{print $2}')
        if [ -n "$IP" ]; then
            echo "Connected to $SSID"
            # Enable profile for auto-start (optional)
            # sudo netctl enable "$PROFILE_NAME"
            exit 0
        fi
        sleep 1
        COUNT=$((COUNT + 1))
    done
fi

echo "Connection failed or timeout"
exit 1
