"""
Software keyboard for text input.
"""

import pyxel


class SoftwareKeyboard:
    """Software keyboard for text input on screen."""

    def __init__(self, x: int = 4, y: int = 80):
        self.x = x
        self.y = y
        self.text = ""
        self.cursor_pos = 0
        self.active = False

        # キーボードレイアウト（コンパクト3行）
        self.layout = [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '_'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', '@', '.'],
            ['z', 'x', 'c', 'v', 'b', 'n', 'm', 'SP', 'BS', 'OK']
        ]

        self.selected_row = 0
        self.selected_col = 0

        # 大文字モード
        self.shift = False

    def set_text(self, text: str):
        """Set initial text."""
        self.text = text
        self.cursor_pos = len(text)

    def get_text(self) -> str:
        """Get current text."""
        return self.text

    def clear(self):
        """Clear text."""
        self.text = ""
        self.cursor_pos = 0

    def activate(self):
        """Activate keyboard."""
        self.active = True

    def deactivate(self):
        """Deactivate keyboard."""
        self.active = False

    def move_up(self):
        """Move selection up."""
        self.selected_row = (self.selected_row - 1) % len(self.layout)
        # 行が変わったら列を調整
        if self.selected_col >= len(self.layout[self.selected_row]):
            self.selected_col = len(self.layout[self.selected_row]) - 1

    def move_down(self):
        """Move selection down."""
        self.selected_row = (self.selected_row + 1) % len(self.layout)
        # 行が変わったら列を調整
        if self.selected_col >= len(self.layout[self.selected_row]):
            self.selected_col = len(self.layout[self.selected_row]) - 1

    def move_left(self):
        """Move selection left."""
        self.selected_col = (self.selected_col - 1) % len(self.layout[self.selected_row])

    def move_right(self):
        """Move selection right."""
        self.selected_col = (self.selected_col + 1) % len(self.layout[self.selected_row])

    def input_char(self):
        """Input selected character."""
        char = self.layout[self.selected_row][self.selected_col]

        if char == 'SP':
            # Space
            self.text = self.text[:self.cursor_pos] + ' ' + self.text[self.cursor_pos:]
            self.cursor_pos += 1
        elif char == 'BS':
            # Backspace
            if self.cursor_pos > 0:
                self.text = self.text[:self.cursor_pos-1] + self.text[self.cursor_pos:]
                self.cursor_pos -= 1
        elif char == 'OK':
            # Done
            return True
        else:
            # Regular character
            if self.shift and char.isalpha():
                char = char.upper()
            self.text = self.text[:self.cursor_pos] + char + self.text[self.cursor_pos:]
            self.cursor_pos += 1

        return False

    def toggle_shift(self):
        """Toggle shift (uppercase) mode."""
        self.shift = not self.shift

    def draw(self):
        """Draw software keyboard."""
        if not self.active:
            return

        from theme_manager import get_theme_manager
        theme = get_theme_manager()
        bg_color = theme.get_color("background")
        border_color = theme.get_color("border")
        text_selected_color = theme.get_color("text_selected")
        text_color = theme.get_color("text")

        # Draw background
        pyxel.rect(self.x - 2, self.y - 10, 152, 70, bg_color)
        pyxel.rectb(self.x - 2, self.y - 10, 152, 70, border_color)

        # Draw input text field
        text_display = self.text if len(self.text) <= 25 else "..." + self.text[-22:]
        pyxel.text(self.x, self.y - 7, text_display, text_selected_color)

        # Draw cursor
        cursor_x = self.x + len(text_display) * 4
        if pyxel.frame_count % 30 < 15:
            pyxel.text(cursor_x, self.y - 7, "_", text_selected_color)

        # Draw keyboard
        key_y = self.y
        for row_idx, row in enumerate(self.layout):
            key_x = self.x
            for col_idx, key in enumerate(row):
                # Key background
                if row_idx == self.selected_row and col_idx == self.selected_col:
                    color = text_selected_color  # Selected
                else:
                    color = text_color   # Normal

                # Draw key
                display_key = key
                if self.shift and key.isalpha():
                    display_key = key.upper()

                # 特殊キーの幅調整
                if key in ['SP', 'BS', 'OK']:
                    pyxel.text(key_x, key_y, display_key, color)
                    key_x += len(display_key) * 4 + 2
                else:
                    pyxel.text(key_x, key_y, display_key, color)
                    key_x += 4 * 2  # 2文字分のスペース

            key_y += 8

        # Draw shift indicator
        if self.shift:
            pyxel.text(self.x, key_y + 4, "SHIFT:ON", text_selected_color)
