# PFE (Pyxel Frontend) アーキテクチャドキュメント

## 1. 概要

PFEは、Pyxel（レトロゲームエンジン）をベースにしたROMランチャーです。主にAnbernicなどの携帯型ゲーム機向けに設計されており、複数のエミュレーションシステムにわたるROMファイルの閲覧、検索、起動のための機能豊富なUIを提供します。

### 主な特徴
- 日本語テキストサポート
- 複数テーマ対応（ダーク、ライト、レトロ、ネオン）
- BGM再生機能（プレイリスト対応）
- スクリーンショット表示
- お気に入り・履歴管理
- セッション復元機能
- カスタムキー設定

### 技術スタック
- **Python 3.x**
- **Pyxel 2.2.7**: グラフィック描画エンジン
- **Pillow**: 画像処理
- **pygame**: BGM再生（遅延読み込み）
- **pyxel-universal-font**: 日本語フォント

---

## 2. ディレクトリ構造

```
pd/
├── main.py                    # エントリーポイント・メインアプリケーション
├── launcher.py                # ROM起動システム
├── config.py                  # 設定ファイルパーサー（pfe.cfg）
├── state_manager.py           # UI状態管理（ステートマシン）
├── input_handler.py           # 入力処理（キーボード・ゲームパッド）
├── persistence.py             # データ永続化（JSON）
├── rom_manager.py             # ROMファイルスキャン・フィルタリング
├── theme_manager.py           # カラーテーマ管理
├── bgm_manager.py             # BGM再生管理
├── system_monitor.py          # システム状態監視（バッテリー・ネットワーク）
├── brightness_manager.py      # 画面輝度制御
├── japanese_text.py           # 日本語テキスト描画
├── screenshot_loader.py       # スクリーンショット読み込み
├── music_mode.py              # 音楽再生モード
├── debug.py                   # デバッグログユーティリティ
├── version.py                 # バージョン情報
│
├── ui/                        # UIコンポーネント
│   ├── base.py                # 基底クラス（UIScreen, ScrollableList）
│   ├── components.py          # 再利用可能UIコンポーネント
│   ├── window.py              # DQ風ウィンドウ描画
│   ├── soft_keyboard.py       # ソフトキーボード（クイックジャンプ用）
│   ├── software_keyboard.py   # ソフトウェアキーボード（テキスト入力）
│   ├── main_menu.py           # カテゴリ選択画面
│   ├── file_list.py           # ROMファイルブラウザ
│   ├── core_select.py         # コア/エミュレータ選択
│   ├── splash.py              # スプラッシュ画面
│   ├── favorites.py           # お気に入り画面
│   ├── recent.py              # 最近プレイしたROM
│   ├── search.py              # ROM検索
│   ├── settings.py            # 設定メニュー
│   ├── wifi_settings.py       # WiFi設定
│   ├── key_config_menu.py     # キー設定メニュー
│   ├── key_config.py          # キーマッピング画面
│   ├── bgm_config.py          # BGM設定
│   ├── datetime_settings.py   # 日付・時刻設定
│   ├── statistics.py          # プレイ統計
│   ├── about.py               # About画面
│   └── quit_menu.py           # 終了ダイアログ
│
├── data/                      # 設定・データファイル
│   ├── pfe.cfg                # メイン設定ファイル
│   ├── session.json           # セッション状態（実行時生成）
│   ├── settings.json          # ユーザー設定（実行時生成）
│   ├── favorites.json         # お気に入りリスト
│   ├── history.json           # プレイ履歴
│   ├── core_history.json      # コア選択履歴
│   └── keyconfig.json         # カスタムキー設定
│
├── assets/                    # アセット
│   ├── screenshots/           # ROMスクリーンショット
│   ├── bgm/                   # BGMファイル（mp3/wav）
│   ├── themes/                # カラーテーマ
│   └── title/                 # カテゴリタイトル画像
│
├── scripts/                   # システム統合スクリプト
│   ├── get_battery.sh         # バッテリー状態取得
│   ├── get_network.sh         # ネットワーク状態取得
│   ├── wifi_scan.sh           # WiFiスキャン
│   ├── wifi_connect.sh        # WiFi接続
│   ├── set_datetime.sh        # 日付・時刻設定
│   └── ...                    # その他システムスクリプト
│
├── bin/                       # 外部バイナリ
│   └── retroarch.sh           # RetroArchランチャー
│
└── docs/                      # ドキュメント
    └── ARCHITECTURE.md        # このファイル
```

---

## 3. コアコンポーネント

### 3.1 アプリケーションライフサイクル

```
launcher.sh（シェルラッパー）
    ↓
main.py → ROMApp クラス
    ├── 解像度設定読み込み（settings.json）
    ├── Pyxel初期化（160x160 または 214x160）
    ├── Config読み込み（pfe.cfg）
    ├── マネージャー初期化:
    │   ├── PersistenceManager（データ永続化）
    │   ├── StateManager（状態管理）
    │   ├── InputHandler（入力処理）
    │   ├── ROMManager（ROM管理）
    │   ├── Launcher（ROM起動）
    │   ├── ThemeManager（テーマ）
    │   ├── SystemMonitor（システム監視）
    │   └── BGMManager（BGM、遅延初期化）
    ├── セッション復元
    ├── 初期状態: SPLASH
    └── pyxel.run(update, draw) 実行
```

### 3.2 フレームループ（30 FPS）

```python
def update():
    # 1. BGM遅延初期化（スプラッシュ後）
    # 2. BGM曲終了チェック（次の曲へ）
    # 3. 入力チェック（再描画判定用）
    # 4. 定期的強制再描画（時計更新用、30フレームごと）
    # 5. ROM起動リクエスト処理
    # 6. アクティブ画面のupdate()呼び出し
    # 7. トースト通知更新

def draw():
    # 再描画が必要な場合のみ実行
    if not self._needs_redraw:
        return
    # 1. 画面クリア
    # 2. アクティブ画面のdraw()呼び出し
    # 3. トースト通知描画
```

---

## 4. 状態管理（StateManager）

### 4.1 アプリケーション状態（AppState）

```python
class AppState(Enum):
    SPLASH          = "splash"           # スプラッシュ画面
    MAIN_MENU       = "main_menu"        # カテゴリ選択
    FILE_LIST       = "file_list"        # ROMブラウザ（メイン画面）
    CORE_SELECT     = "core_select"      # コア選択
    FAVORITES       = "favorites"        # お気に入り
    RECENT          = "recent"           # 最近プレイ
    SEARCH          = "search"           # 検索
    SETTINGS        = "settings"         # 設定
    WIFI_SETTINGS   = "wifi_settings"    # WiFi設定
    KEY_CONFIG_MENU = "key_config_menu"  # キー設定メニュー
    KEY_CONFIG      = "key_config"       # キーマッピング
    BGM_CONFIG      = "bgm_config"       # BGM設定
    DATETIME_SETTINGS = "datetime_settings" # 日付・時刻設定
    STATISTICS      = "statistics"       # 統計
    ABOUT           = "about"            # About
    QUIT_MENU       = "quit_menu"        # 終了確認
```

### 4.2 状態遷移

```
StateManager:
├── current_state: AppState          # 現在の状態
├── state_history: List[AppState]    # 履歴スタック（最大10）
├── state_data: Dict                 # 画面間データ受け渡し
│
├── change_state(new_state)          # 状態変更（履歴にプッシュ）
├── go_back()                        # 前の状態に戻る
├── set_data(key, value)             # データ設定
└── get_data(key)                    # データ取得
```

### 4.3 カテゴリ位置トラッキング

各カテゴリのカーソル位置とスクロールオフセットを記憶：

```python
category_positions = {
    "Nintendo Entertainment System": {"index": 5, "scroll": 2},
    "MAME": {"index": 10, "scroll": 5},
    ...
}
```

---

## 5. 設定システム（Config）

### 5.1 pfe.cfg フォーマット

```ini
; コメント行（セミコロン開始）

; ========================================
; グローバル変数
; ========================================
ROM_BASE=/roms                              ; ROMベースディレクトリ
TYPE_RA=./bin/retroarch.sh                  ; RetroArchランチャー
TYPE_SA_PPSSPP=/usr/local/bin/ppsspp        ; スタンドアロンエミュレータ
CORE_PATH=/home/ark/.config/retroarch/cores ; コアライブラリパス
DEBUG=true                                  ; デバッグモード

; アセットディレクトリ
SCREENSHOT_DIR=assets/screenshots           ; スクリーンショット
BGM_DIR=assets/bgm                          ; BGMファイル

; システムスクリプト
BATTERY_SCRIPT=./scripts/get_battery.sh
NETWORK_SCRIPT=./scripts/get_network.sh

; ========================================
; カテゴリ定義
; ========================================
-TITLE=Nintendo Entertainment System        ; 表示名
-TITLE_IMG=./assets/title/Fc_2.png          ; タイトル画像
-DIR=nes                                    ; ROMディレクトリ（相対/絶対）
-EXT=nes,NES,zip,ZIP                        ; 対応拡張子
-CORE=nestopia,fceumm,quicknes              ; 利用可能コア
```

### 5.2 ディレクトリパス解決

```
-DIR=nes           → ROM_BASE/nes (例: /roms/nes)
-DIR=/roms/nes     → /roms/nes（絶対パス）
```

### 5.3 コアパス解決

```
-CORE=nestopia           → CORE_PATH/nestopia_libretro.so
-CORE=/full/path/core.so → /full/path/core.so（絶対パス）
```

---

## 6. ROM管理（ROMManager）

### 6.1 ROMFileクラス

```python
class ROMFile:
    path: str           # フルパス
    name: str           # 表示名
    extension: str      # 拡張子
    is_directory: bool  # ディレクトリフラグ
    size: int           # ファイルサイズ（バイト）
```

### 6.2 主要メソッド

```python
class ROMManager:
    def scan_category(category, subdirectory=""):
        """カテゴリ内のROMをスキャン
        - ディレクトリとファイルをソートして返す
        - サブディレクトリ対応
        """

    def search_roms(query, category):
        """ROM検索（大文字小文字区別なし）"""

    def get_rom_display_name(name, max_width):
        """幅に合わせた表示名（省略記号付き）"""

    def format_file_size(size):
        """人間が読めるサイズ（KB/MB/GB）"""
```

---

## 7. 起動システム（Launcher）

### 7.1 起動フロー

```
Launcher.launch_rom(rom_file, category, core)
    │
    ├── 1. ROMファイル存在確認
    ├── 2. BGM停止
    ├── 3. コア選択ロジック:
    │   ├── ユーザー指定 > 前回使用 > デフォルト
    │   └── コア名正規化（_libretro.so サフィックス追加）
    │
    ├── 4. エミュレータタイプに応じた起動:
    │   ├── RA (RetroArch):
    │   │   └── script core_path rom_path
    │   │
    │   ├── SA_* (Standalone):
    │   │   └── script rom_path
    │   │
    │   └── Custom:
    │       └── TYPE_* 設定値を使用
    │
    ├── 5. 起動成功時:
    │   ├── 履歴に追加
    │   ├── コア選択を保存
    │   ├── セッション保存
    │   └── PFE終了（launcher.shが再起動）
    │
    └── 6. 起動失敗時:
        ├── エラートースト表示
        └── BGM再開
```

### 7.2 エミュレータタイプ

| タイプ | 説明 | 起動コマンド |
|--------|------|--------------|
| `RA` | RetroArch | `TYPE_RA core_path rom_path` |
| `SA_PPSSPP` | PPSSPP | `TYPE_SA_PPSSPP rom_path` |
| `SA:pyxel` | Pyxelアプリ | `python rom_path` |
| カスタム | 設定による | `TYPE_* rom_path` |

---

## 8. 入力処理（InputHandler）

### 8.1 アクション定義

```python
class Action(Enum):
    UP, DOWN, LEFT, RIGHT   # 方向キー
    A, B, X, Y              # フェイスボタン
    L, R, L2, R2            # ショルダーボタン
    START, SELECT           # 特殊ボタン
```

### 8.2 ボタンレイアウト

| レイアウト | 決定 | キャンセル |
|------------|------|------------|
| Nintendo | A | B |
| Xbox | B | A |

### 8.3 主要機能

```python
class InputHandler:
    def is_pressed(action)     # 今フレームで押された
    def is_held(action)        # 押し続けている
    def is_repeated(action)    # リピート入力（長押し対応）

    # キーリピート設定
    key_repeat_delay = 8       # 約0.27秒
    key_repeat_interval = 2    # 約0.07秒
```

---

## 9. データ永続化（PersistenceManager）

### 9.1 保存ファイル

| ファイル | 内容 |
|----------|------|
| `session.json` | 画面状態、カテゴリ、カーソル位置 |
| `settings.json` | ユーザー設定（輝度、音量、テーマ等） |
| `favorites.json` | お気に入りROMリスト |
| `history.json` | プレイ履歴（最大50件） |
| `core_history.json` | ROM毎の最後に使用したコア |
| `keyconfig.json` | カスタムキー設定 |

### 9.2 settings.json 構造

```json
{
  "version": "1.0",
  "settings": {
    "brightness": "5",
    "show_screenshots": "On",
    "sort_mode": "Name",
    "view_mode": "list",
    "button_layout": "NINTENDO",
    "resolution": "1:1",
    "theme": "dark",
    "bgm_enabled": "On",
    "bgm_volume": "5",
    "bgm_mode": "Normal"
  }
}
```

### 9.3 お気に入りキャッシュ

高速検索のためセット型でキャッシュ：

```python
_favorites_cache = set(rom_paths)  # O(1) ルックアップ
```

---

## 10. UIコンポーネント階層

### 10.1 基底クラス

```python
class UIScreen(ABC):
    """UI画面の基底クラス"""
    active: bool

    def update()      # 毎フレーム呼び出し
    def draw()        # 毎フレーム呼び出し
    def activate()    # 画面アクティブ時
    def deactivate()  # 画面非アクティブ時

class ScrollableList(UIScreen):
    """スクロール可能リストの基底クラス"""
    items: list
    selected_index: int
    scroll_offset: int
    items_per_page: int

    def scroll_up/down()
    def page_up/down()
    def jump_to_start/end()
    def get_selected_item()
```

### 10.2 再利用可能コンポーネント（ui/components.py）

| コンポーネント | 用途 |
|----------------|------|
| `StatusBar` | 上部/下部ステータス表示 |
| `Breadcrumb` | パスナビゲーション |
| `CategoryTitle` | カテゴリ名（日本語対応） |
| `Toast` | 一時的通知 |
| `Counter` | アイテムカウンター（X/Y形式） |
| `LoadingSpinner` | ローディングアニメーション |
| `ProgressBar` | 進捗バー |
| `HelpText` | 操作ヒント |
| `Icon` | スター/フォルダ/ファイルアイコン |
| `SystemStatus` | 時刻/バッテリー/ネットワーク表示 |

### 10.3 画面実装

| 画面 | クラス | 説明 |
|------|--------|------|
| スプラッシュ | `Splash` | 起動画面 |
| メインメニュー | `MainMenu` | カテゴリ選択 |
| ファイルリスト | `FileList` | ROMブラウザ（リスト/ギャラリー/スライドショー） |
| コア選択 | `CoreSelect` | エミュレータコア選択 |
| お気に入り | `Favorites` | お気に入りROM一覧 |
| 履歴 | `Recent` | 最近プレイしたROM |
| 検索 | `Search` | ROM検索 |
| 設定 | `Settings` | 各種設定 |
| WiFi設定 | `WiFiSettings` | ネットワーク設定 |
| キー設定 | `KeyConfig` | ボタンリマップ |
| BGM設定 | `BGMConfig` | 音楽設定 |
| 日付・時刻設定 | `DateTimeSettings` | システム日付・時刻設定 |
| 統計 | `Statistics` | プレイ統計 |
| About | `About` | バージョン情報 |
| 終了 | `QuitMenu` | 終了確認 |

---

## 11. BGM管理（BGMManager）

### 11.1 遅延初期化

起動時間短縮のため、pygame.mixerは最初のBGM操作時に読み込み：

```python
def _get_mixer():
    """遅延読み込み"""
    if not _mixer_import_attempted:
        import pygame.mixer as mixer
        mixer.init(frequency=44100, size=-16, channels=2, buffer=8192)
```

### 11.2 プレイリスト機能

```python
class BGMManager:
    playlist: list          # 選択されたトラックリスト
    play_order: list        # 再生順序（シャッフル時はランダム化）
    current_index: int      # 現在のトラックインデックス
    play_mode: str          # "Normal" or "Shuffle"
    max_playlist_size: int  # 最大300トラック

    def build_playlist()    # BGMディレクトリをスキャン
    def play_next()         # 次のトラックを再生
    def check_music_end()   # 曲終了チェック（30フレームごと）
```

---

## 12. システム監視（SystemMonitor）

### 12.1 監視項目

| 項目 | スクリプト | 更新間隔 |
|------|------------|----------|
| バッテリー | `get_battery.sh` | 60フレーム（約2秒） |
| ネットワーク | `get_network.sh` | 30フレーム（約1秒） |
| 時刻 | Python内部 | 30フレーム（約1秒） |

### 12.2 日付・時刻設定（DateTimeSettings）

Settings画面のサブメニューから遷移する日付・時刻設定画面。

```
Settings画面 → "Date/Time" 選択 → DateTimeSettings画面
    ├── 現在のシステム日時を読み込み（activate時）
    ├── 各フィールドを上下で選択、左右で値変更
    │   ├── Year   (2020-2099)
    │   ├── Month  (1-12)
    │   ├── Day    (1-28/29/30/31、月・閏年に応じて動的変更)
    │   ├── Hour   (0-23)
    │   └── Minute (0-59)
    ├── "Apply" ボタンでシステム日時を適用
    │   └── system_monitor.set_datetime() → scripts/set_datetime.sh
    └── Bボタンで Settings に戻る
```

**主要メソッド（SystemMonitor）:**

```python
def get_current_datetime(self) -> tuple:
    """現在のシステム日時を取得 → (year, month, day, hour, minute)"""

def set_datetime(self, year, month, day, hour, minute) -> bool:
    """外部スクリプト経由でシステム日時を設定"""
```

### 12.3 キャッシュ戦略

```python
class SystemMonitor:
    _battery_cache: str
    _battery_cache_time: int
    _network_cache: str
    _network_cache_time: int

    # キャッシュが有効な間はスクリプト実行をスキップ
```

---

## 13. テーマシステム（ThemeManager）

### 13.1 組み込みテーマ

| テーマ | 説明 |
|--------|------|
| `dark` | ダークテーマ（デフォルト） |
| `light` | ライトテーマ |
| `retro` | ゲームボーイ風 |
| `neon` | ネオンカラー |

### 13.2 カラーキー

```python
color_keys = [
    "background",      # 背景
    "text",            # 通常テキスト
    "text_selected",   # 選択テキスト
    "border",          # 枠線
    "border_accent",   # アクセント枠線
    "scrollbar",       # スクロールバー
    "status_bg",       # ステータスバー背景
    "help_bg",         # ヘルプ背景
    "error",           # エラー
    "success",         # 成功
    "info"             # 情報
]
```

---

## 14. 最適化技術

### 14.1 遅延読み込み

- pygame/mixer: BGM必要時のみ
- PyxelUniversalFont: 初回使用時
- UI画面: アクセス時に初期化

### 14.2 キャッシュ

- お気に入り: セット型（O(1)ルックアップ）
- テーマカラー: 事前読み込み
- カラールックアップテーブル: 画像ディザリング用
- バッテリー/ネットワーク: 1-2秒間隔で更新

### 14.3 描画最適化

```python
def update():
    # 入力がある場合のみ再描画フラグを立てる
    if has_input:
        self._needs_redraw = True

    # 時計更新用に30フレームごとに強制再描画
    if self._redraw_counter >= 30:
        self._needs_redraw = True

def draw():
    # 再描画不要なら何もしない（CPU節約）
    if not self._needs_redraw:
        return
```

---

## 15. データフロー図

```
ユーザー入力
    ↓
InputHandler.is_pressed/is_held()
    ↓
アクティブ画面.update()
    ├── ユーザーアクション処理
    ├── state_manager更新
    └── ROM起動リクエスト（オプション）
         ↓
    ROM起動
         ├── Launcher.launch_rom()
         │   ├── BGM停止
         │   ├── エミュレータ実行
         │   └── 失敗時: BGM再開
         ├── Persistence: 履歴/コア選択保存
         ├── セッション保存
         └── PFE終了 → launcher.sh再起動
                              ↓
                         セッション復元
                              ↓
                         前回の状態で再開

状態変更
    ↓
StateManager.change_state()
    ├── 現在の状態を履歴にプッシュ
    └── current_state更新
         ↓
ROMApp.update()
    ├── current_stateチェック
    ├── 旧画面deactivate()
    ├── 新画面activate()
    └── 画面.update()呼び出し
         ↓
ROMApp.draw()
    ├── 再描画必要かチェック
    └── 画面.draw()呼び出し
         ↓
画面に描画
```

---

## 16. 外部システム連携

### 16.1 シェルスクリプト

| スクリプト | 用途 |
|------------|------|
| `get_battery.sh` | バッテリー状態取得 |
| `get_network.sh` | ネットワーク接続確認 |
| `wifi_scan.sh` | 利用可能WiFiスキャン |
| `wifi_connect.sh` | WiFi接続 |
| `get_cpu_governor.sh` | CPUガバナー取得 |
| `set_cpu_governor.sh` | CPUガバナー設定 |
| `set_datetime.sh` | システム日付・時刻設定 |
| `system_reboot.sh` | システム再起動 |
| `system_shutdown.sh` | システムシャットダウン |

### 16.2 エミュレータ連携

- **RetroArch**: シェルスクリプト経由でコア+ROMパスを渡す
- **スタンドアロン**: 直接実行ファイルにROMパスを渡す
- **カスタム**: 設定可能なランチャー

---

## 17. 画面解像度

| 設定 | 解像度 | 用途 |
|------|--------|------|
| `1:1` | 160x160 | 正方形（デフォルト） |
| `4:3` | 214x160 | 4:3アスペクト比 |

---

## 18. エラーハンドリング

### 18.1 ROM起動エラー

```python
try:
    launch_result = subprocess.run(...)
except Exception as e:
    self.last_error = str(e)
    # BGM再開
    # エラートースト表示
```

### 18.2 設定ファイルエラー

```python
try:
    with open(config_path) as f:
        ...
except Exception as e:
    print(f"Warning: Config file not found: {config_path}")
    # デフォルト値を使用
```

---

## 19. デバッグ機能

### 19.1 デバッグモード有効化

```ini
; pfe.cfg
DEBUG=true
```

### 19.2 デバッグログ

```python
from debug import debug_print

debug_print("[BGM] Track ended, playing next")
# DEBUGがtrueの場合のみ出力
```

---

## 20. 拡張ポイント

### 20.1 新しいエミュレータタイプの追加

1. `pfe.cfg`に`TYPE_SA_*`変数を追加
2. カテゴリ定義で`-CORE=SA:*`を使用

### 20.2 新しいテーマの追加

1. `theme_manager.py`の`THEMES`辞書に追加
2. 全カラーキーを定義

### 20.3 新しいUI画面の追加

1. `ui/`に新しいファイル作成
2. `UIScreen`または`ScrollableList`を継承
3. `state_manager.py`の`AppState`に追加
4. `main.py`に遅延初期化プロパティを追加

---

## 21. ライセンス・謝辞

The source code and original background music (BGM) files of this project
are licensed under the MIT License.

However, **the icon assets included in this repository are NOT covered by the MIT License**.


PFEは以下のオープンソースプロジェクト、素材を使用しています：

- [**Pyxel**: レトロゲームエンジン](https://github.com/kitao/pyxel)
- [**Pillow**: Python画像処理ライブラリ](https://pillow.readthedocs.io/en/stable/#)
- [**pygame**: マルチメディアライブラリ](https://www.pygame.org/news)
- [**pyxel-universal-font**: Unicode フォントサポート](https://pypi.org/project/pyxel-universal-font/)
- [**よしくんのアイコン格納庫**: 各種アイコン](https://yspixel.jpn.org/)
- [**Retro game console icons**: 各種アイコン](https://github.com/KyleBing/retro-game-console-icons)

### Icon Assets

The icon assets included in this project are the property of their respective creators.

- These assets are **NOT licensed under the MIT License**
- Use, modification, or redistribution of the icon assets may require
  permission from the original creators
- Please check the license or obtain permission before using these assets
  outside of this project


---

*このドキュメントは自動生成されました。最終更新: 2026-02-07*
