"""
Help screen showing gamepad and keyboard controls.
"""

import pyxel
from ui.base import ScrollableList
from ui.components import StatusBar, HelpText
from ui.window import DQWindow
from pfe_app.theme_manager import get_theme_manager


class HelpScreen(ScrollableList):
    """Full control reference for handheld gamepad and keyboard use."""

    def __init__(self, input_handler, state_manager):
        super().__init__(items_per_page=14)
        self.input_handler = input_handler
        self.state_manager = state_manager
        self.status_bar = StatusBar(138, 160)
        self.help_text = HelpText(146, 160)
        self.lines = []
        self.content_y = 24
        self.content_height = 112
        self.line_height = 8

    def activate(self):
        """Called when screen becomes active."""
        super().activate()
        self.lines = self._build_lines()
        self.items_per_page = self._visible_line_count()
        self.set_items(self.lines)
        self.selected_index = 0
        self.scroll_offset = 0
        self.help_text.set_controls([
            ("Up/Down", "Scroll"),
            ("B", "Back"),
        ])

    def deactivate(self):
        """Called when screen becomes inactive."""
        super().deactivate()

    def _visible_line_count(self) -> int:
        return max(1, self.content_height // self.line_height)

    def _max_scroll_offset(self) -> int:
        return max(0, len(self.lines) - self.items_per_page)

    def _scroll_content(self, delta: int):
        self.scroll_offset = max(0, min(self._max_scroll_offset(), self.scroll_offset + delta))

    def _build_lines(self) -> list[str]:
        return [
            "Controls",
            "",
            "Basic",
            "  Move",
            "    Pad: D-Pad",
            "    Key: Arrow keys",
            "  Select / Open",
            "    Pad: A",
            "    Key: Z or Enter",
            "  Back / Cancel",
            "    Pad: B",
            "    Key: X or Esc",
            "",
            "Main Menu",
            "  Toggle view",
            "    Pad: X",
            "    Key: A",
            "  Favorites",
            "    Pad: R",
            "    Key: W",
            "  Recent",
            "    Pad: Y",
            "    Key: S",
            "  Settings",
            "    Pad: Select",
            "    Key: Shift",
            "",
            "Game List",
            "  Launch / Folder",
            "    Pad: A",
            "    Key: Z or Enter",
            "  Back",
            "    Pad: B",
            "    Key: X or Esc",
            "  Toggle Gallery",
            "    Pad: X",
            "    Key: A",
            "  Screenshot On/Off",
            "    Pad: Y",
            "    Key: S",
            "  Favorite",
            "    Pad: Start",
            "    Key: Enter",
            "  Core Select",
            "    Pad: Select",
            "    Key: Shift",
            "  Page / Jump",
            "    Pad: L / R",
            "    Key: Q / W",
            "",
            "Gallery",
            "  Prev / Next",
            "    Pad: Left / Right",
            "    Key: Left / Right",
            "  Jump 5 items",
            "    Pad: Up / Down",
            "    Key: Up / Down",
            "  Slideshow",
            "    Pad: Start",
            "    Key: Enter",
            "",
            "Settings",
            "  Change value",
            "    Pad: Left / Right",
            "    Key: Left / Right",
            "  Open submenu",
            "    Pad: A",
            "    Key: Z or Enter",
            "",
            "Key Names",
            "  Gamepad buttons can",
            "  be changed in",
            "  Key Mapping Wizard.",
            "  Default keyboard:",
            "    A=Z  B=X",
            "    X=A  Y=S",
            "    L=Q  R=W",
            "    Select=Shift",
            "    Start=Enter",
        ]

    def update(self):
        """Update help screen logic."""
        if not self.active:
            return

        from pfe_app.input_handler import Action

        if self.input_handler.is_pressed_with_repeat(Action.UP):
            self._scroll_content(-1)
        elif self.input_handler.is_pressed_with_repeat(Action.DOWN):
            self._scroll_content(1)

        if self.input_handler.is_pressed(Action.B):
            self.state_manager.go_back()

    def draw(self):
        """Draw help screen."""
        if not self.active:
            return

        theme = get_theme_manager()
        bg_color = theme.get_color("background")
        text_color = theme.get_color("text")
        text_selected_color = theme.get_color("text_selected")
        border_color = theme.get_color("border")
        scrollbar_color = theme.get_color("scrollbar")

        pyxel.cls(bg_color)
        pyxel.text(2, 2, "Help", text_selected_color)

        window_width = pyxel.width - 8
        DQWindow.draw(2, 18, window_width, 120, bg_color=bg_color, border_color=border_color)

        self.items_per_page = self._visible_line_count()
        visible_start = self.scroll_offset
        visible_end = min(len(self.lines), visible_start + self.items_per_page)
        visible = self.lines[visible_start:visible_end]

        for i, line in enumerate(visible):
            y = self.content_y + i * self.line_height
            color = text_selected_color if line and not line.startswith(" ") else text_color
            pyxel.text(6, y, line, color)

        if len(self.lines) > self.items_per_page:
            from ui.base import draw_scrollbar
            scrollbar_x = pyxel.width - 4
            draw_scrollbar(scrollbar_x, self.content_y, self.items_per_page * self.line_height,
                           len(self.lines), self.items_per_page, self.scroll_offset, scrollbar_color)

        visible_end = min(len(self.lines), self.scroll_offset + self.items_per_page)
        self.status_bar.set_text(
            left="Help",
            center="",
            right=f"{self.scroll_offset + 1}-{visible_end}/{len(self.lines)}",
        )
        self.status_bar.draw()
        self.help_text.draw()
