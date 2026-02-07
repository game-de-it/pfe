#!/bin/sh
# WiFi connect script using iwctl (iwd)
# iwdを使用したWiFi接続スクリプト
#
# 前提条件:
# - iwd (iNet Wireless Daemon) がインストール・起動していること
#
# 引数:
#   $1: SSID
#   $2: パスワード
#
# 注意:
# - iwctlはインタラクティブなパスワード入力を想定しているため、
#   expect または iwctl --passphrase オプション（iwd 1.9+）を使用
#

SSID="$1"
PASSWORD="$2"
INTERFACE="${WIFI_INTERFACE:-wlan0}"

if [ -z "$SSID" ] || [ -z "$PASSWORD" ]; then
    echo "Usage: $0 <SSID> <PASSWORD>"
    exit 1
fi

# Method 1: Using --passphrase option (iwd 1.9+)
# This is the preferred method if your iwd version supports it
iwctl --passphrase "$PASSWORD" station "$INTERFACE" connect "$SSID" 2>/dev/null

RESULT=$?

if [ $RESULT -eq 0 ]; then
    # Wait for connection to establish
    TIMEOUT=30
    COUNT=0
    while [ $COUNT -lt $TIMEOUT ]; do
        STATE=$(iwctl station "$INTERFACE" show 2>/dev/null | grep "State" | awk '{print $2}')
        if [ "$STATE" = "connected" ]; then
            echo "Connected to $SSID"
            exit 0
        fi
        sleep 1
        COUNT=$((COUNT + 1))
    done
fi

# Method 2: If --passphrase is not supported, use expect
# Uncomment the following if you need expect-based approach:
#
# if command -v expect >/dev/null 2>&1; then
#     expect << EOF
# spawn iwctl station $INTERFACE connect "$SSID"
# expect "Passphrase:"
# send "$PASSWORD\r"
# expect eof
# EOF
# fi

echo "Connection failed or timeout"
exit 1
