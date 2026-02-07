# インストール手順

## 必要なもの

- Python 3.8以降
- pip
- RetroArch（またはPPSSPP等のエミュレータ）

## 手順

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

または個別にインストール:

```bash
pip install pyxel>=2.2.7
pip install Pillow>=10.0.0
pip install pyxel-universal-font>=0.2.0
pip install pygame>=2.0.0  # BGM再生用
```

### 2. 設定ファイルの準備

サンプル設定ファイルをコピー:

```bash
cp data/pfe.cfg.example data/pfe.cfg
```

`data/pfe.cfg` を編集してROMディレクトリとエミュレータパスを設定:

```ini
; グローバル設定
ROM_BASE=/path/to/your/roms

; エミュレータ設定
; TYPE_RA: RetroArchランチャースクリプト（<core_filename> <rom_path>を受け取る）
TYPE_RA=./bin/retroarch.sh

; TYPE_SA_*: スタンドアローンエミュレータ（<rom_path>のみ受け取る）
;TYPE_SA_PPSSPP=/usr/local/bin/ppsspp.sh

; デバッグ（問題がある場合はtrueに）
DEBUG=false

; カテゴリ定義
-TITLE=ファミコン
-DIR=nes
-EXT=nes,fds
-CORE=nestopia,fceumm

-TITLE=スーファミ
-DIR=snes
-EXT=sfc,smc
-CORE=snes9x

; スタンドアローンエミュレータの例
;-TITLE=PSP
;-DIR=psp
;-EXT=iso,cso,pbp
;-CORE=SA:PPSSPP
```

詳細な設定オプションは `data/pfe.cfg.example` を参照してください。

### 2.5. ランチャースクリプトの準備

PFEは外部スクリプトを通じてエミュレータを起動します。

#### RetroArch用スクリプト例 (`bin/retroarch.sh`)

```bash
#!/bin/bash
# 引数: $1=コアファイル名, $2=ROMパス
CORE_PATH="/path/to/retroarch/cores"
retroarch -L "${CORE_PATH}/$1" "$2"
```

#### スタンドアローンエミュレータ用スクリプト例

```bash
#!/bin/bash
# 引数: $1=ROMパス
/usr/local/bin/ppsspp "$1"
```

スクリプトに実行権限を付与:
```bash
chmod +x bin/retroarch.sh
```

#### WiFi/システム用スクリプト

PFEには以下のスクリプトが同梱されています:

```
scripts/
├── wifi_scan.sh        # WiFiネットワークスキャン
├── wifi_connect.sh     # WiFi接続
├── wifi_status.sh      # WiFi電源状態取得
├── wifi_toggle.sh      # WiFi電源ON/OFF
├── get_brightness.sh   # 画面輝度取得
└── set_brightness.sh   # 画面輝度設定
```

これらのスクリプトは`data/pfe.cfg`で設定されています:

```ini
WIFI_SCAN_SCRIPT=./scripts/wifi_scan.sh
WIFI_CONNECT_SCRIPT=./scripts/wifi_connect.sh
WIFI_STATUS_SCRIPT=./scripts/wifi_status.sh
WIFI_TOGGLE_SCRIPT=./scripts/wifi_toggle.sh
```

環境に合わせてスクリプトをカスタマイズすることも可能です。

### 3. アセットの準備（オプション）

#### スプラッシュ画像
`assets/splash.png` または `assets/splash.jpg` を配置すると起動時に表示されます。

#### BGM
`assets/bgm.mp3` を配置するとBGMが再生されます。Settings画面でON/OFF切替可能です。

#### スクリーンショット
ROM選択画面でスクリーンショットを表示するには:
```
assets/screenshots/
├── nes/
│   ├── Game Name.png  # ROMファイル名と同じ名前
│   └── ...
├── snes/
│   └── ...
```

#### カスタムフォント
日本語フォントを使用する場合:
- フォントファイルを `assets/fonts/` に配置
- `data/pfe.cfg` に追加: `FONT_PATH=assets/fonts/your-font.ttf`

推奨フォント:
- 美咲フォント (8x8): http://littlelimit.net/misaki.htm
- Noto Sans CJK: https://fonts.google.com/noto/specimen/Noto+Sans+JP

### 4. 起動

#### 推奨: 自動再起動スクリプト

```bash
chmod +x launcher.sh
./launcher.sh
```

ゲーム終了後に自動的にランチャーに戻ります。

#### 直接起動（手動再起動が必要）

```bash
python3 main.py
```

## Linux（組み込み機器）向け設定

### launcher.shの設定

ALSAオーディオを使用する場合、`launcher.sh`で環境変数を設定:

```bash
export SDL_AUDIODRIVER=alsa
export SDL_GAMECONTROLLERCONFIG="..."  # コントローラー設定
```

### 自動起動設定

システム起動時に自動的にランチャーを起動するには:

```bash
# ~/.bashrc または /etc/rc.local に追加
cd /path/to/pd && ./launcher.sh
```

### CPU Governor

CPUガバナーを変更するには、ファイルへの書き込み権限が必要です:

```bash
# 権限確認
ls -la /sys/devices/system/cpu/cpufreq/policy0/scaling_governor

# 必要に応じてudevルールを追加
```

### WiFi設定の権限

一般ユーザーでWiFi接続を行うには、nmcliのsudo権限が必要です:

```bash
echo "ark ALL=(ALL) NOPASSWD: /usr/bin/nmcli" | sudo tee /etc/sudoers.d/wifi
sudo chmod 440 /etc/sudoers.d/wifi
```

### 再起動/シャットダウンの権限

一般ユーザーでシステムの再起動/シャットダウンを行うには:

```bash
echo "ark ALL=(ALL) NOPASSWD: /usr/bin/systemctl reboot, /usr/bin/systemctl poweroff, /sbin/reboot, /sbin/poweroff" | sudo tee /etc/sudoers.d/power
sudo chmod 440 /etc/sudoers.d/power
```

**注意**: `ark`を実際のユーザー名に置き換えてください。

## トラブルシューティング

### pyxel-universal-fontがインストールできない

```bash
pip install --upgrade pip
pip install pyxel-universal-font
```

### BGMが再生されない

1. pygameがインストールされているか確認:
   ```bash
   pip install pygame
   ```

2. `launcher.sh`で`SDL_AUDIODRIVER`がexportされているか確認:
   ```bash
   export SDL_AUDIODRIVER=alsa
   ```

3. `assets/bgm.mp3`が存在するか確認

4. Settings画面でBGMがOnになっているか確認

### フォントが表示されない

1. フォントパスが正しいか確認
2. フォントファイルが存在するか確認
3. `DEBUG=true`にして起動時のログを確認

### 画面が表示されない

1. Pyxelが正しくインストールされているか確認
2. グラフィックドライバが最新か確認
3. SDLの環境変数を確認

### ゲーム起動後に前の画面に戻らない

1. `launcher.sh`を使用しているか確認
2. セッションファイル（`data/session.json`）の権限を確認

### CPU Governorが変更できない

1. パスが正しいか確認:
   ```bash
   cat /sys/devices/system/cpu/cpufreq/policy0/scaling_governor
   ```

2. `pfe.cfg`で`CPU_GOVERNOR_PATH`を設定:
   ```ini
   CPU_GOVERNOR_PATH=/sys/devices/system/cpu/cpufreq/policy0/scaling_governor
   ```

3. ファイルへの書き込み権限を確認

### WiFi接続に失敗する

1. デバッグログを確認:
   ```bash
   cat data/debug.log
   ```

2. nmcliが動作するか確認:
   ```bash
   nmcli device wifi list
   ```

3. 権限エラーの場合、sudoers設定を追加（上記「WiFi設定の権限」参照）

4. `Insufficient privileges`エラーが出る場合:
   - systemdサービス経由で実行している場合に発生
   - sudoers設定が必要

### 再起動/シャットダウンが動作しない

1. デバッグログを確認:
   ```bash
   tail -20 data/debug.log
   ```

2. 権限エラーの場合、sudoers設定を追加（上記「再起動/シャットダウンの権限」参照）

### デバッグログの確認

`DEBUG=true`を設定すると、`data/debug.log`にログが出力されます:

```bash
# リアルタイムでログを確認
tail -f data/debug.log

# 最新のログを確認
cat data/debug.log
```

systemdサービスとして実行している場合、コンソールにログが表示されないため、
ファイルログが問題の診断に役立ちます。
