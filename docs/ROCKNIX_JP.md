# ROCKNIX 導入ガイド

この文書は、ROCKNIX上でPFEとPyxelゲーム実行環境を使うための利用者向けガイドです。

Linuxに詳しくない利用者でもEmulationStationのPortsから作業できるように、通常は `tools/rocknix/ports/` の中身だけを `/roms/ports/` にコピーして使います。

## できること

- ROCKNIX上にPyxel実行環境をセットアップする
- EmulationStationにPyxelゲーム用システムを追加する
- PFEをsystemdサービスとして登録する
- EmulationStationとPFEを切り替える
- OS再起動後も最後に選んだフロントエンドを維持する
- RetroArchで撮影したスクリーンショットをPFEのギャラリーに表示しやすくする

## 前提

- ROCKNIXが起動していること
- PFE本体を `/roms/pfe` に配置していること
- `tools/rocknix/ports/` の中身を `/roms/ports/` にコピーしていること
- 通常操作はEmulationStationのPortsから行うこと

PFE本体は、次のようなディレクトリを含む形で丸ごと `/roms/pfe` に置きます。

```txt
/roms/pfe/
  main.py
  launcher.sh
  pfe_app/
  ui/
  data/
  bin/
  scripts/
  assets/
```

`pfe_app/` はPFEの内部モジュールです。これをコピーし忘れるとPFEは起動できません。

## Portsにコピーするファイル

利用者が直接実行するファイルは、標準ではこの3つです。

```txt
/roms/ports/
  01_install_pyxel.sh
  02_install_pfe.sh
  Switch_to_PFE.sh
```

元ファイルはリポジトリ内のここにあります。

```txt
tools/rocknix/ports/
  01_install_pyxel.sh
  02_install_pfe.sh
  Switch_to_PFE.sh
```

`tools/rocknix/` 直下のスクリプトは、互換用、個別再実行用、開発者向けの部品です。通常の利用者には `ports/` の中身だけを案内してください。

## 基本の導入手順

EmulationStationのPortsから、次の順に実行します。

1. `01_install_pyxel.sh`
2. `02_install_pfe.sh`
3. `Switch_to_PFE.sh`

### 1. Pyxel環境をインストール

`01_install_pyxel.sh` は、Pyxel実行環境をROCKNIXへセットアップします。

主な処理:

- Pyxelを `/storage/.local` にインストール
- Pyxelゲーム起動ランナーを `/storage/.config/rocknix-pyxel/rocknix_pyxel_run.sh` に配置
- EmulationStationに `pyxel` システムを追加または更新
- `/storage/roms/pyxel` を作成

対応するPyxelゲーム形式:

```txt
.py     -> python3 -m pyxel run
.pyxapp -> python3 -m pyxel play
.edit   -> python3 -m pyxel edit
```

`01_install_pyxel.sh` は `/storage/.config/emulationstation/es_systems.cfg` をバックアップしてから更新します。既存の `nes` や `ports` などのシステムを消さないように、更新後のシステム数チェックも行います。

### 2. PFEサービスを登録

`02_install_pfe.sh` は、PFEをROCKNIXのsystemdサービスとして登録します。

主な処理:

- PFE本体の `requirements.txt` を `/storage/.local` へ `pip --user --no-compile` でインストール
- `pyxel`、`Pillow`、`pygame`、`pyxel-universal-font` のimportチェック
- `/storage/.config/system.d/pfe.service` を作成
- `WorkingDirectory=/roms/pfe` を設定
- `ExecStart=/bin/bash /roms/pfe/launcher.sh` を設定
- PFE本体の権限を補正
- RetroArchのスクリーンショット設定をPFE向けに補正

依存関係のインストールやimportチェックに失敗した場合、`02_install_pfe.sh` はそこで停止します。この状態ではPFEへの切り替えは行わず、EmulationStation側に残れるようにしています。

この段階では、OS起動時のフロントエンドはまだ切り替えません。PFEへ切り替えるには次の `Switch_to_PFE.sh` を実行します。

### 3. ESからPFEへ切り替え

`Switch_to_PFE.sh` は、現在のフロントエンドをEmulationStationからPFEへ切り替えます。

主な処理:

- `pfe.service` が登録済みか確認
- `pfe.service` を起動し、activeになることを確認
- 起動できた場合だけ、次回OS起動時もPFEが選ばれるように状態を保存
- `essway.service` を停止

PFEが起動できない場合は、起動対象をPFEへ保存せずにエラーで停止します。これにより、依存関係不足などでPFEが落ちる状態のままESへ戻れなくなる事故を避けます。

切り替え状態は主に次のファイルに保存されます。

```txt
/storage/.config/pfe/frontend.conf
/storage/.config/profile.d/090-ui_service
/storage/.config/autostart/99-pfe-frontend
```

PFEを選んだ状態では、OS再起動後もPFEが起動します。

## PFEからESへ戻る

PFE側からEmulationStationへ戻る場合は、PFEのメニューから実行します。

```txt
Settings > Quit > Switch to ES
```

この操作で `essway.service` が起動し、次回OS起動時もEmulationStationが選ばれる状態になります。

## Pyxelゲームの追加

Pyxelゲームは次の場所に置きます。

```txt
/storage/roms/pyxel
```

対応拡張子:

```txt
.py
.pyxapp
.edit
```

ゲームが追加でPythonモジュールを必要とする場合は、`requirements.txt` を `/roms/ports/` に置いてから `01_install_pyxel.sh` を再実行します。

```txt
/roms/ports/
  01_install_pyxel.sh
  requirements.txt
```

`requirements.txt` の例:

```txt
Pillow>=10.0.0
requests>=2.31.0
```

ROCKNIXのPython環境では `.pyc` 生成まわりに相性問題があるため、スクリプトは `pip --user --no-compile` を使います。

## PFEゲームとスクリーンショット

PFEのROM一覧やギャラリーにスクリーンショットを表示するには、基本的に次の配置を使います。

```txt
/roms/screenshots/<system>/<ROMファイル名>.png
```

例:

```txt
/roms/screenshots/nes/Akumajou Densetsu.png
```

RetroArchで撮影したスクリーンショットをPFEで拾いやすくするため、`02_install_pfe.sh` は次の設定を `/storage/.config/retroarch/retroarch.cfg` に書き込みます。

```ini
auto_screenshot_filename = "false"
screenshots_in_content_dir = "false"
sort_screenshots_by_content_enable = "true"
```

この補正を行いたくない場合は、SSHなどから `02_install_pfe.sh --no-ra-screenshot` を実行します。

## Ports実行時の画面表示

`01_install_pyxel.sh` と `02_install_pfe.sh` は、EmulationStationのPortsから実行された場合、ROCKNIX上の `foot` ターミナルを開いて作業ログを表示します。

RGB30のような720x720端末でも読めるよう、標準の文字サイズは大きめにしています。文字サイズを変えたい場合は、SSHなどから環境変数を指定して実行できます。

```sh
PFE_PORT_TERMINAL_FONT_SIZE=20 ./01_install_pyxel.sh
```

ターミナル表示を無効化したい場合:

```sh
PFE_PORT_TERMINAL=false ./01_install_pyxel.sh
```

通常の利用者には、標準設定のままPortsから実行してもらう想定です。

## systemdサービス

PFEのサービスファイルは次の場所に作成されます。

```txt
/storage/.config/system.d/pfe.service
```

重要な設定:

```ini
WorkingDirectory=/roms/pfe
ExecStart=/bin/bash /roms/pfe/launcher.sh
Environment=PFE_APP_DIR=/roms/pfe
Environment=PFE_PYTHON=/usr/bin/python3
```

`launcher.sh` は `/roms/pfe/main.py` を起動します。`main.py` は `pfe_app/` 内のモジュールを読み込むため、`pfe_app/` を含めたPFE本体一式が必要です。

## トラブルシュート

### ESにPyxelしか表示されない

`/storage/.config/emulationstation/es_systems.cfg` がPyxelだけの内容になっている可能性があります。

まず現在の登録数を確認します。

```sh
grep -c '<system>' /storage/.config/emulationstation/es_systems.cfg
grep -n '<name>pyxel</name>\|<name>nes</name>\|<name>ports</name>' /storage/.config/emulationstation/es_systems.cfg
```

バックアップ一覧を確認します。

```sh
ls -lh /storage/.config/emulationstation/es_systems.cfg.bak.*
```

`nes`、`ports`、`pyxel` が含まれていて、システム数が多いバックアップを復元します。

```sh
cp /storage/.config/emulationstation/es_systems.cfg /storage/.config/emulationstation/es_systems.cfg.bak.before-restore
cp /storage/.config/emulationstation/es_systems.cfg.bak.YYYYMMDD-HHMMSS /storage/.config/emulationstation/es_systems.cfg
systemctl restart essway.service
```

修正版の `01_install_pyxel.sh` と `rocknix_pyxel_es_install.sh` では、既存システム数が不自然に減る場合は書き込みを拒否します。

### PFEが起動しない

PFE本体のコピー漏れを確認します。

```sh
ls -la /roms/pfe/main.py
ls -la /roms/pfe/launcher.sh
ls -la /roms/pfe/pfe_app
```

サービス状態を確認します。

```sh
systemctl status pfe.service --no-pager
tail -n 80 /roms/pfe/data/debug.log
```

`pfe_app directory not found` のような表示がある場合は、PFE本体を `/roms/pfe` へ丸ごとコピーし直してください。

### PFEではなくESが起動する

現在のフロントエンド状態を確認します。

```sh
cat /storage/.config/pfe/frontend.conf
cat /storage/.config/profile.d/090-ui_service
```

PFEを起動時のフロントエンドにしたい場合は、EmulationStationのPortsから `Switch_to_PFE.sh` を実行します。

`Switch_to_PFE.sh` は `pfe.service` の起動確認に成功した場合だけ、起動対象をPFEへ保存します。PFEが起動できない場合はES側の選択状態を維持します。

### OS起動直後の音量が大きい

PFEの `launcher.sh` は、ROCKNIX側に保存されたシステム音量を起動時に適用します。

関連スクリプト:

```txt
/roms/pfe/scripts/rocknix_apply_volume.sh
```

音量補正を無効化したい場合は、環境ファイルで指定します。

```sh
mkdir -p /storage/.config/pfe
echo 'PFE_APPLY_SYSTEM_VOLUME=false' >> /storage/.config/pfe/pfe.env
```

### PyxelゲームがPFE画面の横に出る

PFEからPyxelゲームを起動する場合、PFEはPyxel側へ画面を譲るためにhandoff起動を使います。

関連設定:

```ini
PYXEL_LAUNCH_MODE=handoff
```

PFEの設定や起動スクリプトを古い状態から更新した場合は、`/roms/pfe` の `main.py`、`pfe_app/`、`bin/` を新しいものに揃えてください。

### RetroArchのスクリーンショットがPFEに出ない

次の順に確認します。

```sh
grep -n 'auto_screenshot_filename\|screenshots_in_content_dir\|sort_screenshots_by_content_enable' /storage/.config/retroarch/retroarch.cfg
ls -la /roms/screenshots/nes
```

スクリーンショット名は、ROMファイル名と同じ名前にします。

```txt
ROM:        /roms/nes/Akumajou Densetsu.nes
Screenshot: /roms/screenshots/nes/Akumajou Densetsu.png
```

## 開発者向け補足

ROCKNIXのEmulationStation設定からPFEの `data/pfe.cfg` を同期する補助ツールがあります。

```txt
tools/rocknix/sync_pfe_from_es_systems.py
```

このツールは開発者向けです。通常の利用者には案内しません。

`tools/rocknix/` 直下の個別スクリプトは、`ports/` 版の元ファイルや互換用として残しています。配布時に利用者へ案内するのは、原則として `tools/rocknix/ports/` の中身だけです。
