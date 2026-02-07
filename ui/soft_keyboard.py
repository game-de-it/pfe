"""
Software keyboard for character input.
"""

import pyxel
from theme_manager import get_theme_manager


class SoftKeyboard:
    """Software keyboard for quick jump and text input."""

    def __init__(self):
        # キーボードレイアウト
        self.keys = [
            ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'],
            ['K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T'],
            ['U', 'V', 'W', 'X', 'Y', 'Z', '0', '1', '2', '3'],
            ['4', '5', '6', '7', '8', '9', '-', '_', '.', ' ']
        ]

        # カーソル位置
        self.cursor_x = 0
        self.cursor_y = 0

        # 選択された文字
        self.selected_char = None

        # 表示位置とサイズ
        self.x = 10
        self.y = 40
        self.cell_width = 14
        self.cell_height = 12

        # アクティブフラグ
        self.active = False

    def activate(self):
        """キーボードを有効化"""
        self.active = True
        self.cursor_x = 0
        self.cursor_y = 0
        self.selected_char = None

    def deactivate(self):
        """キーボードを無効化"""
        self.active = False
        self.selected_char = None

    def is_active(self) -> bool:
        """アクティブ状態を取得"""
        return self.active

    def move_cursor(self, dx: int, dy: int):
        """カーソルを移動"""
        self.cursor_x = (self.cursor_x + dx) % len(self.keys[0])
        self.cursor_y = (self.cursor_y + dy) % len(self.keys)

    def get_current_char(self) -> str:
        """現在のカーソル位置の文字を取得"""
        return self.keys[self.cursor_y][self.cursor_x]

    def select_current_char(self):
        """現在の文字を選択"""
        self.selected_char = self.get_current_char()

    def get_selected_char(self) -> str:
        """選択された文字を取得"""
        return self.selected_char

    def clear_selection(self):
        """選択をクリア"""
        self.selected_char = None

    def draw(self):
        """キーボードを描画"""
        if not self.active:
            return

        # Get theme colors
        theme = get_theme_manager()
        bg_color = theme.get_color("background")
        text_color = theme.get_color("text")
        text_selected_color = theme.get_color("text_selected")
        border_color = theme.get_color("border")

        # 背景
        keyboard_width = len(self.keys[0]) * self.cell_width + 4
        keyboard_height = len(self.keys) * self.cell_height + 4
        pyxel.rect(self.x - 2, self.y - 2, keyboard_width, keyboard_height, bg_color)

        # 枠線
        pyxel.rectb(self.x - 2, self.y - 2, keyboard_width, keyboard_height, border_color)

        # タイトル
        title = "Quick Jump - Select Character"
        title_x = self.x + (keyboard_width // 2) - (len(title) * 2)
        pyxel.text(title_x, self.y - 12, title, text_selected_color)

        # キーを描画
        for row_idx, row in enumerate(self.keys):
            for col_idx, char in enumerate(row):
                x = self.x + col_idx * self.cell_width
                y = self.y + row_idx * self.cell_height

                # カーソル位置の背景
                if row_idx == self.cursor_y and col_idx == self.cursor_x:
                    pyxel.rect(x, y, self.cell_width - 2, self.cell_height - 2, text_selected_color)
                    char_color = bg_color
                else:
                    char_color = text_color

                # 文字を描画（中央揃え）
                char_x = x + (self.cell_width // 2) - 2
                char_y = y + (self.cell_height // 2) - 3
                pyxel.text(char_x, char_y, char, char_color)

        # ヘルプテキスト
        help_text = "Arrow: Move | A: Select | B: Cancel"
        help_x = self.x
        help_y = self.y + keyboard_height + 4
        pyxel.text(help_x, help_y, help_text, text_color)
