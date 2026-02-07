#!/bin/sh
# WiFi scan script using connmanctl (ConnMan)
# ConnManを使用したWiFiスキャンスクリプト
#
# 前提条件:
# - ConnManがインストール・起動していること
# - systemctl enable --now connman
#

# Enable WiFi if not enabled
connmanctl enable wifi 2>/dev/null
sleep 1

# Trigger scan
connmanctl scan wifi 2>/dev/null
sleep 3

# Get services and extract WiFi SSIDs
# connmanctl services format: *AO Name                wifi_xxx_managed_psk
connmanctl services 2>/dev/null | \
    grep "wifi_" | \
    sed 's/^[*A-Z ]*//;s/  *wifi_.*$//' | \
    awk 'NF && !seen[$0]++'

exit 0
