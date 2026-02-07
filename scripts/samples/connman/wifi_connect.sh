#!/bin/sh
# WiFi connect script using connmanctl (ConnMan)
# ConnManを使用したWiFi接続スクリプト
#
# 前提条件:
# - ConnManがインストール・起動していること
#
# 引数:
#   $1: SSID
#   $2: パスワード
#
# 注意:
# - ConnManはservice IDでの接続を行うため、SSIDからservice IDを検索する必要がある
# - パスワードはagent経由またはプロビジョニングファイルで設定
#

SSID="$1"
PASSWORD="$2"

if [ -z "$SSID" ] || [ -z "$PASSWORD" ]; then
    echo "Usage: $0 <SSID> <PASSWORD>"
    exit 1
fi

# Find service ID for the SSID
SERVICE_ID=$(connmanctl services 2>/dev/null | grep -F "$SSID" | awk '{print $NF}')

if [ -z "$SERVICE_ID" ]; then
    echo "Network not found: $SSID"
    exit 1
fi

# Create provisioning file for the network
# ConnMan looks for files in /var/lib/connman/
PROVISION_DIR="/var/lib/connman"
PROVISION_FILE="${PROVISION_DIR}/${SSID}.config"

# Create provisioning file
sudo mkdir -p "$PROVISION_DIR"
sudo tee "$PROVISION_FILE" > /dev/null << EOF
[service_${SSID}]
Type = wifi
Name = ${SSID}
Passphrase = ${PASSWORD}
EOF

sudo chmod 600 "$PROVISION_FILE"

# Reload configuration
connmanctl disable wifi 2>/dev/null
sleep 1
connmanctl enable wifi 2>/dev/null
sleep 2

# Connect to the service
connmanctl connect "$SERVICE_ID" 2>/dev/null

RESULT=$?

# Wait for connection
TIMEOUT=30
COUNT=0
while [ $COUNT -lt $TIMEOUT ]; do
    STATE=$(connmanctl services "$SERVICE_ID" 2>/dev/null | grep "State" | awk '{print $3}')
    if [ "$STATE" = "online" ] || [ "$STATE" = "ready" ]; then
        echo "Connected to $SSID"
        exit 0
    fi
    sleep 1
    COUNT=$((COUNT + 1))
done

echo "Connection failed or timeout"
exit 1
