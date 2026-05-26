# PFE ROCKNIX 配布チェックリスト

この文書は、PFEをROCKNIX向けに配布する前の確認、ZIP作成、GitHub Releases公開手順をまとめた開発者・配布担当向けメモです。通常の利用者向け手順は [ROCKNIX導入ガイド](ROCKNIX_JP.md) を参照してください。

## リリース方針

PFEの成果物は GitHub リポジトリ `game-de-it/pfe` にコミットし、配布ZIPは GitHub Releases のAssetsとして添付します。

- 既存の `PFE_demo` タグは、plumOSにPFEを導入済みのOSイメージ配布として扱います。
- PFE本体の正式リリースは `v1.0.0` から開始します。
- PFE本体のリリースタグは `v<version>` 形式にします。例: `v1.0.0`
- `dist/*.zip` はリポジトリへコミットしません。`.gitignore` で `dist/` を除外しています。
- GitHubが自動生成する `Source code.zip` はROCKNIX向け配置になっていないため、利用者には添付した `pfe-rocknix-v<version>-YYYYMMDD.zip` を案内します。

## 配布物の前提

ROCKNIX向け配布ZIPは、次の2つを同梱します。

```txt
pfe/      /roms/pfe に置くPFE本体
ports/    /roms/ports に置くEmulationStation実行用スクリプト
```

`ports/` 直下に入るのは、利用者がEmulationStationのPortsから直接実行するファイルだけです。

```txt
01_install_pyxel.sh
02_install_pfe.sh
Switch_to_PFE.sh
```

`pfe/tools/rocknix/` には、互換用・個別実行用・開発者向けの元スクリプトも含まれます。通常の利用者には、ZIPのトップレベルにある `ports/` を `/roms/ports` へコピーするよう案内します。

## 配布前チェック

配布前に、まず検証スクリプトを実行します。

```bash
python3 tools/check_distribution.py
```

このチェックでは主に次を確認します。

- `data/pfe.cfg` と `data/pfe.cfg.example` が読み込めること
- 設定ファイル内の参照画像、起動スクリプト、`TYPE_*` 定義が存在すること
- Pyxel 2.9.5への更新漏れがないこと
- Markdownのコードフェンスが壊れていないこと
- 旧root直下モジュールが残っていないこと
- ROCKNIXのPFEインストール/切り替えスクリプトに、依存関係チェックと起動確認が入っていること

チェックに失敗した状態ではZIPを作らず、エラーに出たファイルを修正します。

## ZIP作成

検証が通ったら、ROCKNIX向けZIPを作成します。

```bash
python3 tools/build_release.py
```

出力先は次の形式です。

```txt
dist/pfe-rocknix-v<version>-YYYYMMDD.zip
```

`<version>` は `pfe_app/version.py` の `VERSION` から取得されます。リリース番号を変える場合は、ZIP作成前にこの値を更新してください。

ZIPには実行時の状態ファイルを入れません。主な除外対象は次の通りです。

- `.DS_Store`
- `__pycache__/`
- `*.pyc`
- `*.log`
- `dist/`
- `data/session.json`
- `data/settings.json`
- `data/history.json`
- `data/core_history.json`
- `data/favorites.json`
- `data/image_cache/`
- `assets/screenshots/` 配下の画像ファイル
- `data/pfe.cfg_*` 形式の個別環境用設定
- `PFE_BGM_` で始まらない `assets/bgm/*.mp3`
- `bin/tooles.sh` などのローカル補助ファイル

## 最小確認

配布直前の最低限の確認は次の順番で行います。

```bash
python3 -m py_compile tools/check_distribution.py tools/build_release.py
python3 tools/check_distribution.py
python3 tools/build_release.py
```

ZIP内のトップレベルに `pfe/` と `ports/` があることも確認します。

```bash
python3 -c 'from pathlib import Path; import zipfile; p=max(Path("dist").glob("pfe-rocknix-v*.zip"), key=lambda x: x.stat().st_mtime); z=zipfile.ZipFile(p); print(p); print("\n".join(sorted({n.split("/")[0] for n in z.namelist()})))'
```

## GitHub Releases公開

リリースコミットをmainブランチへ取り込んだ後、タグを作成してGitHubへpushします。

```bash
git tag -a v1.0.0 -m "PFE v1.0.0"
git push origin v1.0.0
```

GitHubのReleaseページで `v1.0.0` から新しいReleaseを作成し、作成済みZIPをAssetsへ添付します。

```txt
dist/pfe-rocknix-v1.0.0-YYYYMMDD.zip
```

GitHub CLIを使う場合は、次のように作成できます。Release本文は `docs/releases/v1.0.0.md` を使います。

```bash
gh release create v1.0.0 dist/pfe-rocknix-v1.0.0-20260527.zip --title "PFE v1.0.0" --notes-file docs/releases/v1.0.0.md
```

Release本文には、GitHub自動生成のSource codeではなく、AssetsのROCKNIX向けZIPを使うよう明記します。`v1.0.0` では、日本語と英語を併記した `docs/releases/v1.0.0.md` を本文として使います。

## ROCKNIX実機確認

できれば配布前に、ROCKNIX実機で次を確認します。

1. ZIP内の `pfe/` を `/roms/pfe` に配置
2. ZIP内の `ports/` の中身を `/roms/ports` に配置
3. EmulationStationのPortsから `01_install_pyxel.sh` を実行
4. 続けて `02_install_pfe.sh` を実行
5. `Switch_to_PFE.sh` でPFEへ切り替え
6. PFEからROMを1本起動し、終了後にPFEへ戻ることを確認
7. PFEの `Settings > Quit > Switch to ES` でEmulationStationへ戻ることを確認
8. OS再起動後、最後に選んだフロントエンドが起動することを確認

`02_install_pfe.sh` は、サービス登録前に `/roms/pfe/requirements.txt` を `/storage/.local` へインストールし、`pyxel`、`Pillow`、`pygame`、`pyxel-universal-font` のimport確認を行います。ここで失敗した場合は、サービス登録や切り替えへ進みません。

`Switch_to_PFE.sh` は、`pfe.service` がactiveになったことを確認できた場合だけ、次回起動時のフロントエンドをPFEへ保存します。PFEが起動できない場合はEmulationStation側の選択状態を維持します。

## 復旧確認

インストール後にPFEが起動しない場合、まず次を確認します。

```sh
tail -n 120 /storage/.config/rocknix-pyxel/install.log
tail -n 120 /roms/pfe/data/debug.log
systemctl status pfe.service --no-pager
```

フロントエンド選択を手動でEmulationStationへ戻す場合は、SSHから次を実行します。

```sh
mkdir -p /storage/.config/pfe /storage/.config/profile.d
printf '%s\n' 'sway.service essway.service' > /storage/.config/pfe/frontend.conf
printf '%s\n' 'UI_SERVICE="sway.service essway.service"' > /storage/.config/profile.d/090-ui_service
systemctl start sway.service
systemctl start essway.service
systemctl stop pfe.service
systemctl reset-failed pfe.service
```

現在のスクリプトでは、通常この手動復旧が必要になる前に `02_install_pfe.sh` または `Switch_to_PFE.sh` が停止する想定です。配布前の実機確認では、依存関係不足時にPFEへ切り替わらないことも重要な確認ポイントです。

## 更新時の注意

- Pyxelの確認済みバージョンを変えた場合は、`requirements.txt`、`tools/rocknix/requirements.txt.example`、インストールスクリプト、ドキュメントの表記をそろえます。
- `tools/rocknix/ports/` のスクリプトを変更した場合は、互換用の `tools/rocknix/rocknix_*.sh` も同じ安全策を維持します。
- `pfe_app/` 配下へモジュールを追加した場合は、root直下に旧モジュールを残さないようにします。
- `data/pfe.cfg` はROCKNIX実運用向け、`data/pfe.cfg.example` は汎用サンプルとして扱います。
- 配布ZIPを作り直したら、`dist/` 内の最新ZIP名とサイズを確認してから共有します。
