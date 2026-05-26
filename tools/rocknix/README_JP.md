# ROCKNIX Pyxel 環境構築スクリプト

`01_install_pyxel.sh` は、ROCKNIX の `/usr/bin/python3` で Pyxel アプリを動かすための統合セットアップスクリプトです。Pyxel本体のインストール、Pyxel起動ランナーの配置、EmulationStationへのPyxelシステム登録までをまとめて実行します。PFE専用ではなく、ユーザーが用意した Pyxel プログラムや `.pyxapp` の実行環境として使えます。

PFEをROCKNIXへ導入する利用者向けの通し手順は [ROCKNIX導入ガイド](../../docs/ROCKNIX_JP.md) にまとめています。配布ZIPの作成と実機確認は [配布チェックリスト](../../docs/RELEASE_JP.md) を参照してください。このファイルは、`tools/rocknix` 配下のスクリプトの役割と個別仕様を確認するための補足資料です。

## 使い方

1. `tools/rocknix/ports/` の中身を `/roms/ports/` にコピーします。
2. 必要に応じて `requirements.txt` も `/roms/ports/` に置きます。
3. EmulationStation の Ports から `01_install_pyxel.sh` を実行します。

`ports/` には、ユーザーがEmulationStationから直接実行するファイルだけを置いています。

```txt
01_install_pyxel.sh
02_install_pfe.sh
Switch_to_PFE.sh
```

## スクリプトの配置方針

`tools/rocknix/ports/` は、利用者がそのまま `/roms/ports/` にコピーしてEmulationStationから実行するためのディレクトリです。ここには、利用者が直接選ぶ想定のスクリプトだけを置きます。

```txt
tools/rocknix/ports/
  01_install_pyxel.sh
  02_install_pfe.sh
  Switch_to_PFE.sh
```

`01_install_pyxel.sh` と `02_install_pfe.sh` は、EmulationStationのPortsから実行されたときに、ROCKNIX上の `foot` ターミナルを開いて作業ログを表示します。SSHから実行した場合は通常の標準出力に表示します。ターミナル表示を無効化したい場合は、環境変数 `PFE_PORT_TERMINAL=false` を指定します。文字サイズは標準で `18` にしてあります。機種に合わせて変えたい場合は `PFE_PORT_TERMINAL_FONT_SIZE=20` のように指定できます。

一方、`tools/rocknix/` 直下のスクリプトは、部品、互換用、個別再実行用、開発者向けツールとして扱います。通常の利用者には案内せず、基本的には `ports/` の中身だけを使ってもらいます。

```txt
rocknix_pyxel_setup.sh          Pyxel環境構築の個別実行用。01_install_pyxel.sh に統合済み
rocknix_pyxel_es_install.sh     ESへのPyxel登録の個別実行用。01_install_pyxel.sh に統合済み
rocknix_pyxel_run.sh            Pyxelランナー本体の元ファイル/参考。通常は01_install_pyxel.shが配置する
rocknix_pfe_service_install.sh  PFEサービス登録の元スクリプト/互換用。ports/02_install_pfe.sh と同等
rocknix_switch_to_pfe.sh        PFE切り替えの元スクリプト/互換用。ports/Switch_to_PFE.sh と同等
sync_pfe_from_es_systems.py     ROCKNIXのes_systems.cfgからPFE設定を同期する開発者向けツール
es_systems_pyxel_snippet.cfg    Pyxelシステム定義の参考スニペット
requirements.txt.example        requirements.txt の参考テンプレート
```

SSHから実行する場合:

```sh
cd /roms/ports
chmod +x 01_install_pyxel.sh
./01_install_pyxel.sh
```

## requirements.txt

スクリプトは Pyxel 本体を標準でインストールします。追加モジュールが必要な場合だけ、同じディレクトリに `requirements.txt` を置きます。

例:

```txt
pyxel>=2.9.5
Pillow>=10.0.0
pyxel-universal-font>=0.2.0
```

## インストール先

標準では `/storage/.local` に `pip --user --no-compile` でインストールします。ROCKNIX の Python は bytecode 生成まわりに相性問題があるため、`.pyc` を作らないようにしています。

ログはここに保存されます:

```txt
/storage/.config/rocknix-pyxel/install.log
```

起動スクリプトで読み込める環境ファイルも作成します:

```txt
/storage/.config/rocknix-pyxel/env.sh
```

Pyxelアプリの起動スクリプト側では、必要に応じて次のように読み込みます。

```sh
. /storage/.config/rocknix-pyxel/env.sh
/usr/bin/python3 /path/to/app.py
```

## オプション

```sh
./01_install_pyxel.sh --check
./01_install_pyxel.sh --requirements /path/to/requirements.txt
./01_install_pyxel.sh --no-base
./01_install_pyxel.sh --offline
./01_install_pyxel.sh --no-es
```

`--offline` を使う場合は、スクリプトと同じディレクトリに `wheelhouse/` を置き、必要な `.whl` を入れてください。

## EmulationStation連携

`01_install_pyxel.sh` は、Pyxelランナーを `/storage/.config/rocknix-pyxel/rocknix_pyxel_run.sh` に配置し、EmulationStationのPyxelシステム定義を追加または更新します。`rocknix_pyxel_run.sh` は拡張子ごとに起動方法を切り替えます。

```txt
.py     -> python3 -m pyxel run
.pyxapp -> python3 -m pyxel play
.edit   -> python3 -m pyxel edit
```

内部的には `/storage/.config/emulationstation/es_systems.cfg` をバックアップしてから、次のPyxelシステム定義を追加または更新します。

```xml
<system>
        <name>pyxel</name>
        <fullname>Pyxel</fullname>
        <path>/storage/roms/pyxel</path>
        <extension>.py .pyxapp .edit</extension>
        <command>/storage/.config/rocknix-pyxel/rocknix_pyxel_run.sh "%ROM%"</command>
        <platform>pyxel</platform>
        <theme>pyxel</theme>
</system>
```

オーバーレイFSで設定が保持されるかは、編集後にOS再起動して確認します。

個別に再実行したい場合だけ、上級者向けに `rocknix_pyxel_setup.sh` と `rocknix_pyxel_es_install.sh` も利用できます。

## PFE と ES の切り替え

PFEをsystemdサービスとして登録するには、PFE本体を `/roms/pfe` に置いた状態で次を実行します。現在のPFEは、直下の `main.py` と `launcher.sh` に加えて `pfe_app/`、`ui/`、`data/`、`bin/` などのディレクトリをそのまま含む構成です。

```sh
cd /roms/ports
chmod +x 02_install_pfe.sh Switch_to_PFE.sh
./02_install_pfe.sh
```

この状態ではサービス登録だけ行い、起動時のフロントエンドは変更しません。ESからPFEへ切り替えるには、`Switch_to_PFE.sh` をPortsから起動します。

`02_install_pfe.sh` は、サービス登録の前に `/roms/pfe/requirements.txt` を `/storage/.local` へインストールし、PFEに必要な `pyxel`、`Pillow`、`pygame`、`pyxel-universal-font` がimportできるか確認します。失敗した場合はサービス登録や切り替えへ進まずに停止します。依存関係のインストールを明示的に省略したい上級者向けには `--no-deps` があります。

`02_install_pfe.sh` とPFEの `launcher.sh` は、`/roms/pfe` や `/storage/pfe` などの実機配置先では起動時に `chmod -R 755` を実行します。ZIP展開やコピー直後に実行権限が落ちていても、WiFi、Bluetooth、電源操作などの同梱スクリプトが実行できる状態へ補正します。無効化したい場合は、`/storage/.config/pfe/pfe.env` などで `PFE_FIX_PERMISSIONS=false` を指定します。

インストール時にはRetroArchの設定もPFE向けに補正します。`/storage/.config/retroarch/retroarch.cfg` の `auto_screenshot_filename`、`screenshots_in_content_dir`、`sort_screenshots_by_content_enable` を更新し、RetroArchで撮ったスクリーンショットがPFEのギャラリーで拾いやすい命名にします。さらに、小型画面でもRetroArchメニューを読みやすくするため `menu_driver = "rgui"` も設定します。スクリーンショット設定の補正をスキップしたい場合は `--no-ra-screenshot` を指定します。

PFEを起動時のフロントエンドにしたい場合:

```sh
./02_install_pfe.sh --enable
```

ROCKNIXの起動対象は `/storage/.config/profile.d/090-ui_service` の `UI_SERVICE` で管理されます。ただし標準の起動処理がこのファイルを毎回初期値に戻すため、PFEの切り替えスクリプトは `/storage/.config/pfe/frontend.conf` に選択状態を保存し、`/storage/.config/autostart/99-pfe-frontend` で起動時に再適用します。

`Switch_to_PFE.sh` は、`pfe.service` が起動してactiveになることを確認できた場合だけ、選択状態を `sway.service pfe.service` に保存します。PFEが起動できない場合は保存せずに停止するため、ESへ戻れない状態を避けます。PFE側の `Settings > Quit > Switch to ES` は `sway.service essway.service` に更新します。つまり、最後に正常に切り替えたフロントエンドが次回のOS起動時にも選ばれます。

PFE側からESへ戻る場合は、PFEの `Settings > Quit > Switch to ES` を使います。この項目はPFE同梱の `scripts/switch_to_es.sh` を呼び出し、PFEの自動再起動を止めてから `essway.service` を起動します。
