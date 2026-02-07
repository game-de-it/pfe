# WiFi Sample Scripts

nmcli (NetworkManager) 以外のWiFi接続方法のサンプルスクリプト集です。

## ディレクトリ構成

```
samples/
├── wpa_supplicant/  # wpa_supplicant / wpa_cli
├── iwd/             # iwctl (iNet Wireless Daemon)
├── connman/         # connmanctl (Connection Manager)
└── netctl/          # netctl (Arch Linux)
```

## 使用方法

1. 使用したいスクリプトを `scripts/` ディレクトリにコピー
2. 実行権限を付与: `chmod +x scripts/wifi_*.sh`
3. `data/pfe.cfg` でスクリプトパスを設定

```ini
WIFI_SCAN_SCRIPT=./scripts/wifi_scan.sh
WIFI_CONNECT_SCRIPT=./scripts/wifi_connect.sh
WIFI_STATUS_SCRIPT=./scripts/wifi_status.sh
WIFI_TOGGLE_SCRIPT=./scripts/wifi_toggle.sh
```

## 各ツールの特徴

### wpa_supplicant / wpa_cli

- 最も低レベルなWiFi管理ツール
- 多くのLinuxディストリビューションで利用可能
- DHCPクライアント（dhclient, dhcpcd）が別途必要
- 設定: `/etc/wpa_supplicant/wpa_supplicant.conf`

**前提条件:**
```bash
# wpa_supplicant を起動
sudo wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant.conf
```

### iwd (iNet Wireless Daemon)

- Intel開発の新しいWiFiデーモン
- 軽量で高速
- 組み込みDHCPクライアント（オプション）
- Arch Linux、Fedora等で利用可能

**前提条件:**
```bash
# iwdをインストール・起動
sudo pacman -S iwd  # Arch Linux
sudo systemctl enable --now iwd
```

### ConnMan (Connection Manager)

- Intel開発のネットワーク管理デーモン
- 組み込みシステムで人気
- 複数の接続タイプ（WiFi、イーサネット、VPN等）をサポート

**前提条件:**
```bash
# ConnManをインストール・起動
sudo pacman -S connman  # Arch Linux
sudo systemctl enable --now connman
```

### netctl (Arch Linux)

- Arch Linux固有のプロファイルベースネットワーク管理
- シンプルなプロファイル形式
- systemdと統合

**前提条件:**
```bash
# netctlをインストール
sudo pacman -S netctl wpa_supplicant dhcpcd
```

## 環境変数

すべてのスクリプトは以下の環境変数をサポート:

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `WIFI_INTERFACE` | `wlan0` | WiFiインターフェース名 |

使用例:
```bash
export WIFI_INTERFACE=wlp2s0
./wifi_scan.sh
```

## 権限

多くのスクリプトはroot権限が必要です。sudoを使用するか、sudoersで設定してください:

```bash
# sudoers設定例
echo "username ALL=(ALL) NOPASSWD: /usr/sbin/wpa_supplicant, /usr/sbin/wpa_cli, /sbin/ip, /usr/bin/rfkill" | \
    sudo tee /etc/sudoers.d/wifi
sudo chmod 440 /etc/sudoers.d/wifi
```

## 注意事項

1. **NetworkManagerとの競合**: これらのツールを使用する場合、NetworkManagerを無効化する必要があります
   ```bash
   sudo systemctl disable --now NetworkManager
   ```

2. **インターフェース名**: システムによってインターフェース名が異なります（wlan0, wlp2s0等）

3. **セキュリティ**: パスワードがスクリプトやプロファイルファイルに保存されるため、ファイルパーミッションに注意

4. **DHCP**: wpa_supplicantを直接使用する場合、別途DHCPクライアントを起動する必要があります

## トラブルシューティング

### スキャン結果が空

1. インターフェースがupか確認: `ip link show wlan0`
2. rfkillでブロックされていないか確認: `rfkill list`
3. 正しいデーモンが起動しているか確認

### 接続失敗

1. デバッグログを確認（PFE: `data/debug.log`）
2. システムログを確認: `journalctl -u wpa_supplicant` 等
3. パスワードが正しいか確認
4. セキュリティタイプ（WPA2、WPA3等）が対応しているか確認
