# インストール手順

この文書は、通常のLinux/PC環境でPFEを導入するための手順です。

ROCKNIXで導入する場合は、この汎用手順ではなく [ROCKNIX導入ガイド](docs/ROCKNIX_JP.md) を参照してください。ROCKNIXでは `tools/rocknix/ports/` を `/roms/ports/` にコピーし、EmulationStationのPortsから実行する前提で説明しています。

## 必要なもの

- Python 3.8以降
- pip
- RetroArch、PPSSPPなど利用したいエミュレータ
- ROMファイル

## 1. 依存関係のインストール

推奨:

```bash
./scripts/install_deps.sh
```

別のPythonを使う場合:

```bash
PFE_PYTHON=/path/to/python3 ./scripts/install_deps.sh
```

手動で入れる場合:

```bash
pip install "pyxel>=2.9.5"
pip install Pillow>=10.0.0
pip install pyxel-universal-font>=0.2.0
pip install pygame>=2.0.0
```

`scripts/install_deps.sh` はROCKNIX/plumOS系のPythonで起きるpipのbytecode問題も避けるため、通常環境でもこのスクリプト経由を推奨します。

## 2. 設定ファイルの準備

サンプルをコピーします。

```bash
cp data/pfe.cfg.example data/pfe.cfg
```

最低限、ROMの場所とエミュレータ起動スクリプトを確認します。

```ini
ROM_BASE=/path/to/your/roms

TYPE_RA=./bin/retroarch.sh

; 必要に応じてスタンドアロンエミュレータを指定
;TYPE_SA_PPSSPP=./bin/ppsspp.sh
;TYPE_SA_YABASANSHIRO=./bin/yabasanshiro.sh
```

カテゴリは `-TITLE`、`-DIR`、`-EXT`、`-CORE` で定義します。

```ini
-TITLE=ファミコン
-DIR=nes
-EXT=nes,fds
-CORE=nestopia,fceumm

-TITLE=PSP
-DIR=psp
-EXT=iso,cso,pbp
-CORE=SA:PPSSPP
```

`-DIR` が相対パスの場合は `ROM_BASE` から解決されます。`-CORE` に通常のコア名を書くとRetroArch、`SA:NAME` と書くと `TYPE_SA_NAME` のスクリプトを使います。

詳しい設定項目は `data/pfe.cfg.example` を参照してください。

## 3. エミュレータ起動スクリプト

PFEはエミュレータ本体を直接決め打ちせず、`bin/` や任意の外部スクリプトに起動を委譲します。

同梱スクリプト例:

```txt
bin/retroarch.sh
bin/ppsspp.sh
bin/yabasanshiro.sh
bin/drastic.sh
bin/pyxel.sh
```

実行権限を付けます。

```bash
chmod +x bin/*.sh scripts/*.sh
```

RetroArch用スクリプトは、PFEから次の引数を受け取ります。

```txt
bin/retroarch.sh <core_path_or_filename> <rom_path>
```

スタンドアロン用スクリプトは、基本的にROMパスだけを受け取ります。

```txt
bin/ppsspp.sh <rom_path>
```

環境に合わせて `bin/*.sh` を編集するか、`data/pfe.cfg` の `TYPE_RA` / `TYPE_SA_*` に別のスクリプトパスを指定してください。

## 4. アセットの準備

### BGM

標準では `assets/bgm/` がBGMディレクトリです。

```txt
assets/bgm/
  song1.mp3
  song2.ogg
```

変更する場合は `data/pfe.cfg` に `BGM_DIR` を指定します。

```ini
BGM_DIR=./assets/bgm
```

### スクリーンショット

標準では `assets/screenshots/` がスクリーンショットディレクトリです。`SCREENSHOT_DIR` を指定すると別の場所を使えます。

```ini
SCREENSHOT_DIR=assets/screenshots
```

基本の配置:

```txt
assets/screenshots/
  nes/
    Game Name.png
  snes/
    Another Game.png
```

画像名はROMファイル名から拡張子を除いた名前に合わせます。

### スプラッシュ画像

起動時に画像を表示したい場合は、次のどちらかを置きます。

```txt
assets/splash.png
assets/splash.jpg
```

### フォント

日本語表示のためのフォントを明示したい場合は、`FONT_PATH` や `BDF_FONT_PATH` を指定します。

```ini
FONT_PATH=assets/fonts/your-font.ttf
BDF_FONT_PATH=assets/fonts/umplus_j10r.bdf
```

未指定の場合、PFEは利用可能なフォントを自動検出します。

## 5. 起動

推奨:

```bash
./launcher.sh
```

`launcher.sh` はゲーム終了後にPFEへ戻るための自動再起動や、環境変数の設定を担当します。

直接起動:

```bash
python3 main.py
```

専用Pythonを使う場合:

```bash
PFE_PYTHON=/path/to/python3 ./launcher.sh
```

## 6. OS連携スクリプト

WiFi、明るさ、バッテリー、CPUガバナー、電源操作などは `scripts/` の外部スクリプトで処理します。

代表例:

```txt
scripts/wifi_scan.sh
scripts/wifi_connect.sh
scripts/get_battery.sh
scripts/get_brightness.sh
scripts/set_brightness.sh
scripts/get_cpu_governor.sh
scripts/set_cpu_governor.sh
scripts/system_reboot.sh
scripts/system_shutdown.sh
```

環境によって必要なコマンドや権限が異なるため、うまく動かない場合は `scripts/samples/` を参考にして置き換えてください。

一般ユーザーでWiFiや電源操作を行う場合は、必要に応じてsudoers設定が必要です。

```bash
echo "username ALL=(ALL) NOPASSWD: /usr/bin/nmcli" | sudo tee /etc/sudoers.d/pfe-wifi
sudo chmod 440 /etc/sudoers.d/pfe-wifi
```

## 7. 自動起動

systemdで起動する場合の最小例です。パスは実際の配置先に合わせてください。

```ini
[Unit]
Description=PFE Frontend

[Service]
Type=simple
WorkingDirectory=/path/to/pfe
ExecStart=/bin/bash /path/to/pfe/launcher.sh
Restart=on-failure

[Install]
WantedBy=default.target
```

ROCKNIXでは専用の `02_install_pfe.sh` を使うため、この例ではなく [ROCKNIX導入ガイド](docs/ROCKNIX_JP.md) を参照してください。

## トラブルシューティング

### 起動しない

```bash
./scripts/install_deps.sh
python3 -m compileall -q main.py pfe_app ui
tail -n 80 data/debug.log
```

`pfe_app` が見つからない場合は、PFE本体をディレクトリごと正しくコピーしてください。

### ROMが表示されない

- `ROM_BASE` と `-DIR` の組み合わせを確認
- `-EXT` にROMの拡張子が含まれているか確認
- ROMディレクトリが読み取り可能か確認

### ゲームが起動しない

- `TYPE_RA` や `TYPE_SA_*` のパスを確認
- スクリプトに実行権限があるか確認
- RetroArchコアの場所を確認
- `data/debug.log` のエラーを確認

### BGMが再生されない

- `BGM_DIR` の場所を確認
- 対応形式の音声ファイルがあるか確認
- Settings画面でBGMが有効か確認
- pygameがインストールされているか確認

### スクリーンショットが表示されない

- `SCREENSHOT_DIR` の場所を確認
- システム名のディレクトリが合っているか確認
- 画像ファイル名がROM名と合っているか確認

### WiFiや電源操作が動かない

- `scripts/*.sh` がその環境に合っているか確認
- 必要なコマンドがインストールされているか確認
- sudoersなどの権限設定を確認

### デバッグログ

`data/pfe.cfg` で `DEBUG=true` にすると詳細ログが増えます。

```bash
tail -f data/debug.log
```
