"""
Splash screen displayed on startup.
"""

import os
import pyxel
from ui.base import UIScreen
from pfe_app.theme_manager import get_theme_manager
from pfe_app.image_cache import ImageCache


class Splash(UIScreen):
    """Splash screen with image display."""

    def __init__(self, input_handler, state_manager, config):
        super().__init__()
        self.input_handler = input_handler
        self.state_manager = state_manager
        self.config = config

        # スプラッシュ画像 (サイズは実行時に決定)
        self.splash_loaded = False
        self.splash_image = None
        self.splash_width = None  # activate時にpyxel.widthを使用
        self.splash_height = None  # activate時にpyxel.heightを使用
        self.image_cache = ImageCache(memory_limit=4)

        # 表示時間管理（pfe.cfgから取得、1-5秒）
        splash_time_seconds = self.config.get_splash_time()
        self.display_frames = 0
        self.auto_close_frames = splash_time_seconds * 30  # seconds * fps

    def activate(self):
        """Called when screen becomes active."""
        super().activate()

        # 画面サイズを取得
        self.splash_width = pyxel.width
        self.splash_height = pyxel.height

        # スプラッシュ画像をロード
        self._load_splash_image()
        self.display_frames = 0

    def deactivate(self):
        """Called when screen becomes inactive."""
        super().deactivate()

    def _load_splash_image(self):
        """スプラッシュ画像をロード"""
        # 複数のパスを試行
        splash_paths = [
            "assets/splash.png",
            "assets/splash.jpg",
            "assets/splash.jpeg",
            "assets/images/splash.png",
            "assets/images/splash.jpg",
        ]

        splash_path = None
        for path in splash_paths:
            if os.path.exists(path):
                splash_path = path
                break

        if not splash_path:
            print("Splash image not found, skipping splash screen")
            self.splash_loaded = False
            # スプラッシュがない場合は即座に次の画面へ（セッション復元を考慮）
            self._close_splash()
            return

        try:
            self.splash_image = self.image_cache.get(splash_path, self.splash_width, self.splash_height)
            self.splash_loaded = self.splash_image is not None
            print(f"Splash image loaded: {splash_path}")

        except Exception as e:
            print(f"Failed to load splash image: {e}")
            self.splash_loaded = False
            # エラー時は即座に次の画面へ（セッション復元を考慮）
            self._close_splash()

    def update(self):
        """Update splash screen logic."""
        if not self.active:
            return

        from pfe_app.input_handler import Action

        # フレームカウント
        self.display_frames += 1

        # 任意のキー入力で閉じる
        if (self.input_handler.is_pressed(Action.A) or
            self.input_handler.is_pressed(Action.B) or
            self.input_handler.is_pressed(Action.START) or
            self.input_handler.is_pressed(Action.SELECT)):
            self._close_splash()
            return

        # 自動的に閉じる（3秒後）
        if self.display_frames >= self.auto_close_frames:
            self._close_splash()

    def _close_splash(self):
        """スプラッシュ画面を閉じて次の画面へ"""
        from pfe_app.state_manager import AppState

        # セッション復元で保存された状態があればそれに遷移、なければMAIN_MENU
        post_splash_state = self.state_manager.get_data('post_splash_state')
        if post_splash_state:
            self.state_manager.change_state(post_splash_state, push_history=False)
            # 一度使ったらクリア
            self.state_manager.set_data('post_splash_state', None)
        else:
            self.state_manager.change_state(AppState.MAIN_MENU, push_history=False)

    def draw(self):
        """Draw splash screen."""
        if not self.active:
            return

        # Get theme colors
        theme = get_theme_manager()
        bg_color = theme.get_color("background")

        # Clear screen
        pyxel.cls(bg_color)

        # スプラッシュ画像を描画
        if self.splash_loaded and self.splash_image is not None:
            pyxel.blt(0, 0, self.splash_image.image, 0, 0, self.splash_image.width, self.splash_image.height)
        else:
            # 画像がない場合はデフォルトテキスト
            text = "PFE - ROM Launcher"
            text_x = pyxel.width // 2 - len(text) * 2
            pyxel.text(text_x, 75, text, 7)
