"""
Splash screen displayed on startup.
"""

import os
import pyxel
from PIL import Image
from ui.base import UIScreen
from theme_manager import get_theme_manager


class Splash(UIScreen):
    """Splash screen with image display."""

    def __init__(self, input_handler, state_manager, config):
        super().__init__()
        self.input_handler = input_handler
        self.state_manager = state_manager
        self.config = config

        # スプラッシュ画像 (サイズは実行時に決定)
        self.splash_loaded = False
        self.splash_image_bank = 2  # イメージバンク2を使用
        self.splash_width = None  # activate時にpyxel.widthを使用
        self.splash_height = None  # activate時にpyxel.heightを使用

        # RGB→Pyxelカラー変換用LUT
        self._init_color_lookup_table()

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

    def _init_color_lookup_table(self):
        """RGB→Pyxelカラー変換用LUT（高速化）"""
        # Pyxelカラーパレット
        palette = [
            (0, 0, 0), (43, 51, 95), (126, 32, 114), (25, 149, 156),
            (139, 72, 82), (57, 92, 152), (169, 193, 255), (238, 238, 238),
            (212, 24, 108), (211, 132, 65), (233, 195, 91), (112, 198, 169),
            (118, 150, 222), (163, 163, 163), (255, 151, 152), (237, 199, 176),
        ]

        # 32x32x32のLUT（RGBを8→5ビットに量子化）
        self.color_lut = {}
        for r5 in range(32):
            for g5 in range(32):
                for b5 in range(32):
                    # 5ビット値を8ビット値に変換
                    r = (r5 * 255) // 31
                    g = (g5 * 255) // 31
                    b = (b5 * 255) // 31

                    # 最も近いPyxelカラーを検索
                    min_distance = float('inf')
                    nearest_color = 0

                    for i, (pr, pg, pb) in enumerate(palette):
                        distance = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
                        if distance < min_distance:
                            min_distance = distance
                            nearest_color = i

                    self.color_lut[(r5, g5, b5)] = nearest_color

    def _rgb_to_pyxel_color(self, r: int, g: int, b: int) -> int:
        """RGBを最も近いPyxelカラーに変換"""
        # 8ビット→5ビットに量子化
        r5 = (r * 31) // 255
        g5 = (g * 31) // 255
        b5 = (b * 31) // 255

        return self.color_lut.get((r5, g5, b5), 0)

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
            # 画像を読み込んでリサイズ
            img = Image.open(splash_path)
            img = img.resize((self.splash_width, self.splash_height), Image.Resampling.BILINEAR)
            img = img.convert('RGB')
            pixels = img.load()

            # Pyxelイメージバンクに保存
            pyxel_img = pyxel.image(self.splash_image_bank)
            for y in range(self.splash_height):
                for x in range(self.splash_width):
                    r, g, b = pixels[x, y]
                    color = self._rgb_to_pyxel_color(r, g, b)
                    pyxel_img.pset(x, y, color)

            self.splash_loaded = True
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

        from input_handler import Action

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
        from state_manager import AppState

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
        if self.splash_loaded:
            pyxel.blt(0, 0, self.splash_image_bank, 0, 0, self.splash_width, self.splash_height)
        else:
            # 画像がない場合はデフォルトテキスト
            text = "PFE - ROM Launcher"
            text_x = pyxel.width // 2 - len(text) * 2
            pyxel.text(text_x, 75, text, 7)
