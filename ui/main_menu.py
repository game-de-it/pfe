"""
Main menu screen for category selection.
"""

import pyxel
from ui.base import ScrollableList, draw_box
from ui.components import StatusBar, HelpText, Icon, SystemStatus
from ui.window import DQWindow
from pfe_app.config import Category
from pfe_app.japanese_text import draw_japanese_text, get_japanese_text_width
from pfe_app.theme_manager import get_theme_manager
from pfe_app.image_cache import ImageCache


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
        self._update_gallery_layout()

        # 画像キャッシュ（PVNM方式: 256色パレット化してpyxel.Imageへ一括転送）
        self.image_cache = ImageCache(memory_limit=128)

        # Load categories from config
        self._load_categories()

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

    def _update_gallery_layout(self):
        """Use a wider grid when the 4:3 layout gives us room."""
        self.gallery_cols = 5 if pyxel.width >= 200 else 3
        self.gallery_rows = 3

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
        self._update_gallery_layout()

        self._update_help_text()
        # ギャラリー用画像をプリロード
        if self.view_mode == "gallery":
            self._preload_gallery_images()
            self._update_gallery_page()

    def update(self):
        """Update main menu logic."""
        if not self.active:
            return

        from pfe_app.input_handler import Action

        # View mode toggle (X button)
        if self.input_handler.is_pressed(Action.X):
            if self.view_mode == "list":
                self.view_mode = "gallery"
                self._update_gallery_layout()
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
            from pfe_app.state_manager import AppState
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
                from pfe_app.state_manager import AppState
                self.state_manager.set_selected_category(selected.name)
                self.state_manager.change_state(AppState.FILE_LIST)

        # Recent
        if self.input_handler.is_pressed(Action.Y):
            from pfe_app.state_manager import AppState
            self.state_manager.change_state(AppState.RECENT)

        # Settings
        if self.input_handler.is_pressed(Action.SELECT):
            from pfe_app.state_manager import AppState
            selected = self.get_selected_item()
            if selected:
                self.state_manager.set_selected_category(selected.name)
            self.state_manager.change_state(AppState.SETTINGS)

        # TOPメニューではBボタンを無効化（終了させない）
        # if self.input_handler.is_pressed(Action.B):
        #     pass  # 何もしない

    def _update_gallery_navigation(self):
        """ギャラリーモードのナビゲーション処理（行優先：右→右、下→下）"""
        from pfe_app.input_handler import Action

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

        # Draw system status (右上)
        self.system_status.draw()

        # Draw subtitle (上部2行目)
        subtitle = "Select Category"
        subtitle_x = pyxel.width // 2 - len(subtitle) * 2
        pyxel.text(subtitle_x, 10, subtitle, text_color)

        if self.view_mode == "gallery":
            self._update_gallery_layout()
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
                center=category_name,
                right=f"{self.selected_index + 1}/{len(self.items)}",
                center_highlight=True,
            )
            self.status_bar.draw()
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
        cursor_color = theme.get_color("gallery_cursor")

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
                    pyxel.rectb(cell_x - 1, cell_y - 1, cell_size + 2, cell_size + 2, cursor_color)
                    pyxel.rectb(cell_x - 2, cell_y - 2, cell_size + 4, cell_size + 4, cursor_color)

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
        if category.title_img and self._draw_cached_image(category.title_img, x, y, size):
            return

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
        from pfe_app.debug import debug_print

        if not self.items:
            return

        cell_size = self.gallery_cell_size

        for category in self.items:
            if not category.title_img:
                continue

            debug_print(f"[MainMenu] Loading image: {category.title_img}")
            if not self.image_cache.get_fit(category.title_img, cell_size, cell_size, upscale=True):
                debug_print(f"[MainMenu] Failed to load image: {category.title_img}")

    def _is_image_loaded(self, img_path: str) -> bool:
        """画像がキャッシュにロード可能か確認"""
        return self.image_cache.get_fit(img_path, self.gallery_cell_size, self.gallery_cell_size, upscale=True) is not None

    def _draw_cached_image(self, img_path: str, x: int, y: int, size: int) -> bool:
        """キャッシュされた画像を描画"""
        from pfe_app.debug import debug_print

        try:
            image = self.image_cache.get_fit(img_path, size, size, upscale=True)
            if image is None:
                return False
            theme = get_theme_manager()
            pyxel.rect(x, y, size, size, theme.get_color("background"))
            draw_x = x + (size - image.width) // 2
            draw_y = y + (size - image.height) // 2
            pyxel.blt(draw_x, draw_y, image.image, 0, 0, image.width, image.height)
            return True
        except Exception as e:
            debug_print(f"[MainMenu] Error drawing image: {e}")
            return False
