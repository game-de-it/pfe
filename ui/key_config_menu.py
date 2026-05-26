"""
Key Config Menu - submenu for key mapping settings.
"""

import pyxel
from ui.base import ScrollableList
from ui.components import StatusBar, HelpText
from ui.window import DQWindow
from pfe_app.japanese_text import draw_japanese_text
from pfe_app.theme_manager import get_theme_manager


class KeyConfigMenu(ScrollableList):
    """Key Config submenu containing the key mapping wizard."""

    def __init__(self, input_handler, state_manager, persistence):
        super().__init__(items_per_page=8)
        self.input_handler = input_handler
        self.state_manager = state_manager
        self.persistence = persistence
        self.status_bar = StatusBar(138, 160)
        self.help_text = HelpText(146, 160)

        # Menu items
        self.menu_items = [
            {"name": "Key Mapping Wizard", "type": "submenu", "key": "key_mapping"},
        ]

        self.set_items(self.menu_items)

    def activate(self):
        """Called when screen becomes active."""
        super().activate()

        # Set help text
        self.help_text.set_controls([
            ("A", "Select"),
            ("B", "Back")
        ])

    def deactivate(self):
        """Called when screen becomes inactive."""
        super().deactivate()

    def update(self):
        """Update key config menu logic."""
        if not self.active:
            return

        from pfe_app.input_handler import Action

        # Navigation
        if self.input_handler.is_pressed_with_repeat(Action.UP):
            self.scroll_up()
        elif self.input_handler.is_pressed_with_repeat(Action.DOWN):
            self.scroll_down()

        selected = self.get_selected_item()

        # Enter submenu
        if self.input_handler.is_pressed(Action.A):
            if selected and selected["key"] == "key_mapping":
                from pfe_app.state_manager import AppState
                self.state_manager.change_state(AppState.KEY_CONFIG)

        # Back
        if self.input_handler.is_pressed(Action.B):
            self.state_manager.go_back()

    def draw(self):
        """Draw key config menu screen."""
        if not self.active:
            return

        # Get theme colors
        theme = get_theme_manager()
        bg_color = theme.get_color("background")
        text_color = theme.get_color("text")
        text_selected_color = theme.get_color("text_selected")
        border_color = theme.get_color("border")

        # Clear screen
        pyxel.cls(bg_color)

        # Draw title
        title = "KEY CONFIG"
        pyxel.text(2, 2, title, text_selected_color)

        # Draw subtitle
        subtitle = "Button Mapping"
        subtitle_x = pyxel.width // 2 - len(subtitle) * 2
        pyxel.text(subtitle_x, 10, subtitle, text_color)

        # Draw main window frame
        window_width = pyxel.width - 8
        DQWindow.draw(2, 18, window_width, 120, bg_color=bg_color, border_color=border_color)

        # Draw menu items
        start_y = 26
        line_height = 13
        visible = self.get_visible_items()
        visible_start, _ = self.get_visible_range()

        for i, item in enumerate(visible):
            y = start_y + i * line_height
            index = visible_start + i

            # Draw item name
            color = text_selected_color if index == self.selected_index else text_color
            draw_japanese_text(6, y, item["name"], color)

            if item["type"] == "submenu":
                submenu_x = pyxel.width - 30
                draw_japanese_text(submenu_x, y, ">", color)

        # Status bar
        self.status_bar.set_text(
            left="Key Config",
            center="",
            right=f"{self.selected_index + 1}/{len(self.menu_items)}"
        )
        self.status_bar.draw()

        # Help text
        self.help_text.draw()
