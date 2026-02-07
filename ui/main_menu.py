"""
Main menu screen for category selection.
"""

import os
import pyxel
from PIL import Image
from ui.base import ScrollableList, draw_box
from ui.components import StatusBar, HelpText, Icon, SystemStatus
from ui.window import DQWindow
from typing import List, Dict
from config import Category
from japanese_text import draw_japanese_text, get_japanese_text_width
from theme_manager import get_theme_manager


class MainMenu(ScrollableList):
    """Main menu screen for selecting ROM categories."""

    def __init__(self, input_handler, state_manager, config, persistence=None):
        super().__init__(items_per_page=8)  # 一番下の行が枠にかぶらないように8に調整
        self.input_handler = input_handler
        self.state_manager = state_manager
        self.config = config
        self.persistence = persistence
        self.status_bar = StatusBar(138, 160)  # ステータスバー位置調整
        self.help_text = HelpText(146, 160)  # ヘルプテキスト位置調整（2行分のスペース確保）
        self.system_status = SystemStatus()  # システムステータス（右上）

        # ギャラリーモード設定（settings.jsonから読み込み）
        self.view_mode = self._load_view_mode()
        self.gallery_cols = 3  # 横方向のセル数
        self.gallery_rows = 3  # 縦方向のセル数
        self.gallery_cell_size = 32  # 各セルのサイズ
        self.gallery_page_offset = 0  # ページオフセット（ページ単位でスクロール）

        # 画像キャッシュ
        self.image_cache: Dict[str, bool] = {}  # パス -> ロード済みフラグ
        self.image_bank = 0  # イメージバンク0を使用（Pyxelは0,1,2の3つのみ）
        self.image_cache_positions: Dict[str, tuple] = {}  # パス -> (x, y) イメージバンク内の位置
        self._init_color_lookup_table()

        # Load categories from config
        self._load_categories()

    def _init_color_lookup_table(self):
        """RGB→Pyxelカラー変換用LUTを初期化"""
        palette = [
            (0, 0, 0), (43, 51, 95), (126, 32, 114), (25, 149, 156),
            (139, 72, 82), (57, 92, 152), (169, 193, 255), (238, 238, 238),
            (212, 24, 108), (211, 132, 65), (233, 195, 91), (112, 198, 169),
            (118, 150, 222), (163, 163, 163), (255, 151, 152), (237, 199, 176),
        ]
        self.color_lut = {}
        for r5 in range(32):
            for g5 in range(32):
                for b5 in range(32):
                    r = (r5 * 255) // 31
                    g = (g5 * 255) // 31
                    b = (b5 * 255) // 31
                    min_distance = float('inf')
                    nearest_color = 0
                    for i, (pr, pg, pb) in enumerate(palette):
                        distance = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
                        if distance < min_distance:
                            min_distance = distance
                            nearest_color = i
                    self.color_lut[(r5, g5, b5)] = nearest_color

    def _rgb_to_pyxel_color(self, r: int, g: int, b: int) -> int:
        """RGBをPyxelカラーに変換"""
        r5 = (r * 31) // 255
        g5 = (g * 31) // 255
        b5 = (b * 31) // 255
        return self.color_lut.get((r5, g5, b5), 0)

    def _load_view_mode(self) -> str:
        """settings.jsonからview_modeを読み込み"""
        if self.persistence:
            settings = self.persistence.load_settings()
            return settings.get("main_menu_view_mode", "list")
        return "list"

    def _save_view_mode(self):
        """view_modeをsettings.jsonに保存"""
        if self.persistence:
            settings = self.persistence.load_settings()
            settings["main_menu_view_mode"] = self.view_mode
            self.persistence.save_settings(settings)

    def _load_categories(self):
        """Load categories from config."""
        categories = self.config.get_categories()
        self.set_items(categories)

    def _update_help_text(self):
        """ヘルプテキストを更新（view_modeに応じて）"""
        if self.view_mode == "gallery":
            self.help_text.set_controls([
                ("D-Pad", "Sel"),
                ("A", "Ent"),
                ("X", "List"),
                ("R", "Fav")
            ])
        else:
            self.help_text.set_controls([
                ("Up/Down", "Sel"),
                ("A", "Ent"),
                ("X", "Gallery"),
                ("R", "Fav"),
                ("Y", "Rec")
            ])

    def activate(self):
        """Called when screen becomes active."""
        super().activate()
        # Restore scroll position if needed
        self._load_categories()

        # view_modeを復元（settings.jsonから）
        self.view_mode = self._load_view_mode()

        self._update_help_text()
        # ギャラリー用画像をプリロード
        if self.view_mode == "gallery":
            self._preload_gallery_images()
            self._update_gallery_page()

    def update(self):
        """Update main menu logic."""
        if not self.active:
            return

        from input_handler import Action

        # View mode toggle (X button)
        if self.input_handler.is_pressed(Action.X):
            if self.view_mode == "list":
                self.view_mode = "gallery"
                self._preload_gallery_images()
                # ギャラリー用にページオフセットを計算
                self._update_gallery_page()
            else:
                self.view_mode = "list"
            # view_modeを保存（settings.json）
            self._save_view_mode()
            self._update_help_text()
            return

        # Favorites (R button)
        if self.input_handler.is_pressed(Action.R):
            from state_manager import AppState
            self.state_manager.change_state(AppState.FAVORITES)
            return

        if self.view_mode == "gallery":
            # ギャラリーモードのナビゲーション
            self._update_gallery_navigation()
        else:
            # リストモードのナビゲーション
            # Navigation (with key repeat for up/down)
            if self.input_handler.is_pressed_with_repeat(Action.UP):
                self.scroll_up()
            elif self.input_handler.is_pressed_with_repeat(Action.DOWN):
                self.scroll_down()
            elif self.input_handler.is_pressed(Action.L):
                self.jump_to_start()

            # Page navigation (left/right arrows)
            if self.input_handler.is_pressed(Action.LEFT):
                self.page_up()
            elif self.input_handler.is_pressed(Action.RIGHT):
                self.page_down()

        # Selection
        if self.input_handler.is_pressed(Action.A):
            selected = self.get_selected_item()
            if selected:
                from state_manager import AppState
                self.state_manager.set_selected_category(selected.name)
                self.state_manager.change_state(AppState.FILE_LIST)

        # Recent
        if self.input_handler.is_pressed(Action.Y):
            from state_manager import AppState
            self.state_manager.change_state(AppState.RECENT)

        # Settings
        if self.input_handler.is_pressed(Action.SELECT):
            from state_manager import AppState
            self.state_manager.change_state(AppState.SETTINGS)

        # TOPメニューではBボタンを無効化（終了させない）
        # if self.input_handler.is_pressed(Action.B):
        #     pass  # 何もしない

    def _update_gallery_navigation(self):
        """ギャラリーモードのナビゲーション処理（行優先：右→右、下→下）"""
        from input_handler import Action

        if not self.items:
            return

        old_index = self.selected_index
        total_items = len(self.items)
        items_per_page = self.gallery_cols * self.gallery_rows

        # 現在のページ内での位置を計算
        page_start = self.gallery_page_offset * items_per_page
        local_index = self.selected_index - page_start
        current_row = local_index // self.gallery_cols
        current_col = local_index % self.gallery_cols

        # 上下左右でカーソル移動（行優先）
        if self.input_handler.is_pressed_with_repeat(Action.UP):
            if current_row > 0:
                # 上の行に移動
                self.selected_index -= self.gallery_cols
            elif self.gallery_page_offset > 0:
                # 前のページの最下行へ
                self.gallery_page_offset -= 1
                new_page_start = self.gallery_page_offset * items_per_page
                # 同じ列の最下行
                self.selected_index = new_page_start + (self.gallery_rows - 1) * self.gallery_cols + current_col
                if self.selected_index >= total_items:
                    self.selected_index = total_items - 1

        elif self.input_handler.is_pressed_with_repeat(Action.DOWN):
            if current_row < self.gallery_rows - 1:
                # 下の行に移動
                new_index = self.selected_index + self.gallery_cols
                if new_index < total_items:
                    self.selected_index = new_index
                elif (self.gallery_page_offset + 1) * items_per_page < total_items:
                    # 次のページへ
                    self.gallery_page_offset += 1
                    new_page_start = self.gallery_page_offset * items_per_page
                    self.selected_index = new_page_start + current_col
                    if self.selected_index >= total_items:
                        self.selected_index = total_items - 1
            elif (self.gallery_page_offset + 1) * items_per_page < total_items:
                # 次のページの最上行へ
                self.gallery_page_offset += 1
                new_page_start = self.gallery_page_offset * items_per_page
                self.selected_index = new_page_start + current_col
                if self.selected_index >= total_items:
                    self.selected_index = total_items - 1

        elif self.input_handler.is_pressed_with_repeat(Action.LEFT):
            if current_col > 0:
                # 左に移動
                self.selected_index -= 1
            elif self.selected_index > 0:
                # 前の行の右端へ
                self.selected_index -= 1
                self._update_gallery_page()

        elif self.input_handler.is_pressed_with_repeat(Action.RIGHT):
            if current_col < self.gallery_cols - 1 and self.selected_index + 1 < total_items:
                # 右に移動
                self.selected_index += 1
            elif self.selected_index + 1 < total_items:
                # 次の行の左端へ
                self.selected_index += 1
                self._update_gallery_page()

        # インデックスが変わったらページを更新
        if old_index != self.selected_index:
            self._update_gallery_page()

    def _update_gallery_page(self):
        """ギャラリーのページオフセットを更新"""
        if not self.items:
            return

        items_per_page = self.gallery_cols * self.gallery_rows

        # 現在選択中のアイテムが表示範囲内になるようにページを調整
        current_page = self.selected_index // items_per_page
        self.gallery_page_offset = current_page

    def draw(self):
        """Draw main menu screen."""
        if not self.active:
            return

        # Get theme colors
        theme = get_theme_manager()
        bg_color = theme.get_color("background")
        text_color = theme.get_color("text")
        text_selected_color = theme.get_color("text_selected")
        border_color = theme.get_color("border")
        scrollbar_color = theme.get_color("scrollbar")

        # Clear screen
        pyxel.cls(bg_color)

        # Draw title (上部1行目、左詰めでシステムステータスと重ならないように)
        title = "ROM LAUNCHER"
        pyxel.text(2, 2, title, text_selected_color)

        # Draw system status (右上)
        self.system_status.draw()

        # Draw subtitle (上部2行目)
        subtitle = "Select Category"
        subtitle_x = pyxel.width // 2 - len(subtitle) * 2
        pyxel.text(subtitle_x, 10, subtitle, text_color)

        if self.view_mode == "gallery":
            self._draw_gallery_view()
        else:
            self._draw_list_view()

        # Status bar
        if self.view_mode == "gallery":
            # ギャラリーモードでは選択中のカテゴリ名を中央に表示（日本語対応）
            selected = self.get_selected_item()
            category_name = selected.name if selected else ""

            # ステータスバーの背景を描画
            self.status_bar.set_text(
                left="",
                center="",
                right=f"{self.selected_index + 1}/{len(self.items)}"
            )
            self.status_bar.draw()

            # カテゴリ名を日本語対応で中央に描画
            if category_name:
                # 長すぎる場合は切り詰め
                max_width = pyxel.width - 80
                try:
                    while get_japanese_text_width(category_name) > max_width and len(category_name) > 0:
                        category_name = category_name[:-1]
                    if get_japanese_text_width(category_name) > max_width:
                        category_name = category_name[:-2] + ".."
                except:
                    if len(category_name) > 20:
                        category_name = category_name[:18] + ".."

                # 中央揃えで描画
                try:
                    name_width = get_japanese_text_width(category_name)
                except:
                    name_width = len(category_name) * 4
                name_x = (pyxel.width - name_width) // 2
                draw_japanese_text(name_x, 139, category_name, text_selected_color)
        else:
            self.status_bar.set_text(
                left=f"Categories: {len(self.items)}",
                center="",
                right=f"{self.selected_index + 1}/{len(self.items)}"
            )
            self.status_bar.draw()

        # Help text
        self.help_text.draw()

    def _draw_list_view(self):
        """リストビューを描画"""
        theme = get_theme_manager()
        bg_color = theme.get_color("background")
        text_color = theme.get_color("text")
        text_selected_color = theme.get_color("text_selected")
        border_color = theme.get_color("border")
        scrollbar_color = theme.get_color("scrollbar")

        # Draw main window frame (タイトル2行分+下部ヘルプ2行分のスペース確保)
        window_width = pyxel.width - 8
        DQWindow.draw(2, 18, window_width, 120, bg_color=bg_color, border_color=border_color)

        # Draw categories list
        start_y = 26  # ウィンドウ内に収める
        line_height = 13
        visible = self.get_visible_items()
        visible_start, _ = self.get_visible_range()

        for i, category in enumerate(visible):
            y = start_y + i * line_height
            index = visible_start + i

            # Draw category name (半角33文字まで表示)
            category_name = category.name
            max_width = pyxel.width - 15
            try:
                if get_japanese_text_width(category_name) > max_width:
                    while len(category_name) > 0:
                        category_name = category_name[:-1]
                        test_text = category_name + "..."
                        if get_japanese_text_width(test_text) <= max_width:
                            category_name = test_text
                            break
            except:
                max_chars = (pyxel.width - 15) // 4
                if len(category_name) > max_chars:
                    category_name = category_name[:max_chars - 3] + "..."

            color = text_selected_color if index == self.selected_index else text_color
            draw_japanese_text(6, y, category_name, color)

        # Draw scrollbar if needed
        if len(self.items) > self.items_per_page:
            from ui.base import draw_scrollbar
            scrollbar_x = pyxel.width - 4
            draw_scrollbar(scrollbar_x, start_y, self.items_per_page * line_height,
                          len(self.items), self.items_per_page, self.scroll_offset, scrollbar_color)

    def _draw_gallery_view(self):
        """ギャラリービューを描画（3x3グリッド、行優先）"""
        theme = get_theme_manager()
        bg_color = theme.get_color("background")
        text_color = theme.get_color("text")
        text_selected_color = theme.get_color("text_selected")
        border_color = theme.get_color("border")

        if not self.items:
            # Empty state
            msg = "No categories"
            center_x = pyxel.width // 2
            pyxel.text(center_x - len(msg) * 2, 70, msg, text_color)
            return

        # グリッドの配置計算
        cell_size = self.gallery_cell_size
        cell_margin = 4  # セル間のマージン
        grid_width = self.gallery_cols * cell_size + (self.gallery_cols - 1) * cell_margin
        grid_height = self.gallery_rows * cell_size + (self.gallery_rows - 1) * cell_margin

        # グリッドを画面中央に配置
        grid_start_x = (pyxel.width - grid_width) // 2
        grid_start_y = 24  # タイトルの下

        # 表示範囲のアイテムインデックスを計算（行優先）
        items_per_page = self.gallery_cols * self.gallery_rows
        page_start = self.gallery_page_offset * items_per_page

        # グリッドを描画（行優先：左から右、上から下）
        for row in range(self.gallery_rows):
            for col in range(self.gallery_cols):
                # アイテムインデックス（行優先）
                local_index = row * self.gallery_cols + col
                item_index = page_start + local_index

                if item_index >= len(self.items):
                    continue

                category = self.items[item_index]

                # セルの位置
                cell_x = grid_start_x + col * (cell_size + cell_margin)
                cell_y = grid_start_y + row * (cell_size + cell_margin)

                # 選択中のセルはハイライト
                is_selected = (item_index == self.selected_index)

                # セル背景
                if is_selected:
                    # 選択枠を描画
                    pyxel.rectb(cell_x - 1, cell_y - 1, cell_size + 2, cell_size + 2, text_selected_color)
                    pyxel.rectb(cell_x - 2, cell_y - 2, cell_size + 4, cell_size + 4, text_selected_color)

                # 画像またはプレースホルダーを描画
                self._draw_gallery_cell(category, cell_x, cell_y, cell_size, is_selected)

        # ページインジケータ
        total_pages = (len(self.items) + items_per_page - 1) // items_per_page
        if total_pages > 1:
            indicator_y = grid_start_y + grid_height + 4
            indicator_text = f"{self.gallery_page_offset + 1}/{total_pages}"
            indicator_x = pyxel.width // 2 - len(indicator_text) * 2
            pyxel.text(indicator_x, indicator_y, indicator_text, text_color)

    def _draw_gallery_cell(self, category: Category, x: int, y: int, size: int, is_selected: bool):
        """ギャラリーの1セルを描画"""
        theme = get_theme_manager()
        bg_color = theme.get_color("background")
        text_color = theme.get_color("text")
        border_color = theme.get_color("border")

        # 画像がある場合は画像を表示
        if category.title_img and self._is_image_loaded(category.title_img):
            self._draw_cached_image(category.title_img, x, y, size)
        else:
            # 画像がない場合はプレースホルダー（グレーの四角）
            pyxel.rect(x, y, size, size, 5)  # グレー背景
            pyxel.rectb(x, y, size, size, border_color)  # 枠線

            # 「?」マークを中央に表示
            mark = "?"
            mark_x = x + (size - 4) // 2
            mark_y = y + (size - 6) // 2
            pyxel.text(mark_x, mark_y, mark, text_color)

    def _preload_gallery_images(self):
        """ギャラリー用の画像をプリロード"""
        from debug import debug_print

        if not self.items:
            return

        # 各カテゴリの画像をロード
        cache_x = 0
        cache_y = 0
        cell_size = self.gallery_cell_size

        for category in self.items:
            if not category.title_img:
                continue

            if category.title_img in self.image_cache:
                continue

            debug_print(f"[MainMenu] Loading image: {category.title_img}")

            # 画像をロード
            if self._load_image_to_cache(category.title_img, cache_x, cache_y, cell_size):
                self.image_cache_positions[category.title_img] = (cache_x, cache_y)
                self.image_cache[category.title_img] = True
                debug_print(f"[MainMenu] Image loaded at ({cache_x}, {cache_y})")

                # 次のキャッシュ位置
                cache_x += cell_size
                if cache_x + cell_size > 256:  # イメージバンクの幅
                    cache_x = 0
                    cache_y += cell_size
                    if cache_y + cell_size > 256:  # イメージバンクの高さ
                        debug_print("[MainMenu] Image cache full")
                        break  # キャッシュがいっぱい
            else:
                debug_print(f"[MainMenu] Failed to load image: {category.title_img}")

    def _load_image_to_cache(self, img_path: str, cache_x: int, cache_y: int, size: int) -> bool:
        """画像をイメージバンクにロード"""
        from debug import debug_print

        try:
            # パスの正規化（相対パス対応）
            if not os.path.isabs(img_path):
                # 相対パスの場合、現在の作業ディレクトリからの相対パスとして扱う
                full_path = os.path.abspath(img_path)
            else:
                full_path = img_path

            debug_print(f"[MainMenu] Checking path: {full_path}")

            if not os.path.exists(full_path):
                debug_print(f"[MainMenu] File not found: {full_path}")
                return False

            img = Image.open(full_path)
            orig_width, orig_height = img.size

            # アスペクト比を維持してフィット
            scale = min(size / orig_width, size / orig_height)
            new_width = int(orig_width * scale)
            new_height = int(orig_height * scale)

            img = img.resize((new_width, new_height), Image.Resampling.BILINEAR)
            img = img.convert('RGB')
            pixels = img.load()

            # オフセット（中央配置）
            offset_x = (size - new_width) // 2
            offset_y = (size - new_height) // 2

            # Pyxelイメージバンクに書き込み
            pyxel_img = pyxel.image(self.image_bank)

            # まず背景をクリア（透明色として0を使用）
            for py in range(size):
                for px in range(size):
                    pyxel_img.pset(cache_x + px, cache_y + py, 0)

            # 画像を書き込み
            for py in range(new_height):
                for px in range(new_width):
                    r, g, b = pixels[px, py]
                    color = self._rgb_to_pyxel_color(r, g, b)
                    pyxel_img.pset(cache_x + offset_x + px, cache_y + offset_y + py, color)

            return True
        except Exception as e:
            debug_print(f"[MainMenu] Error loading image: {e}")
            return False

    def _is_image_loaded(self, img_path: str) -> bool:
        """画像がキャッシュにロード済みか確認"""
        return img_path in self.image_cache and self.image_cache[img_path]

    def _draw_cached_image(self, img_path: str, x: int, y: int, size: int):
        """キャッシュされた画像を描画"""
        if img_path not in self.image_cache_positions:
            return

        cache_x, cache_y = self.image_cache_positions[img_path]
        # 透明色を指定しない（-1は無効な値として扱われ透明処理をスキップ）
        pyxel.blt(x, y, self.image_bank, cache_x, cache_y, size, size)
