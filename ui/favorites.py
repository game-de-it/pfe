"""
Favorites screen for viewing favorite ROMs.
"""
from theme_manager import get_theme_manager

import pyxel
from ui.base import ScrollableList
from ui.components import StatusBar, HelpText, Breadcrumb
from ui.window import DQWindow
from rom_manager import ROMFile
from japanese_text import draw_japanese_text
import os


class Favorites(ScrollableList):
    """Favorites screen for viewing favorite ROMs."""

    def __init__(self, input_handler, state_manager, config, persistence):
        super().__init__(items_per_page=8)  # Adjusted to 8 so the bottom row doesn't overlap with the frame
        self.input_handler = input_handler
        self.state_manager = state_manager
        self.config = config
        self.persistence = persistence
        self.status_bar = StatusBar(138, 160)
        self.help_text = HelpText(146, 160)
        self.breadcrumb = Breadcrumb(2, 2)

        self.favorites = []

    def activate(self):
        """Called when screen becomes active."""
        super().activate()

        # Load favorites
        self._load_favorites()

        # Set help text
        self.help_text.set_controls([
            ("Up/Down", "Select"),
            ("A", "Launch"),
            ("START", "Remove"),
            ("B", "Back")
        ])

        # Set breadcrumb
        self.breadcrumb.set_path(["Favorites"])

    def _load_favorites(self):
        """Load favorites from persistence."""
        fav_data = self.persistence.get_favorites()

        # Convert to displayable format
        self.favorites = []
        for fav in fav_data:
            rom_path = fav.get("rom_path", "")
            category = fav.get("category", "")

            if os.path.exists(rom_path):
                # Create ROM file object
                filename = os.path.basename(rom_path)
                name, ext = os.path.splitext(filename)
                ext = ext.lstrip('.')
                rom_file = ROMFile(rom_path, name, ext)
                self.favorites.append({
                    'rom': rom_file,
                    'category': category
                })

        self.set_items(self.favorites)

    def update(self):
        """Update favorites screen logic."""
        if not self.active:
            return

        from input_handler import Action
        from state_manager import AppState

        # Navigation
        if self.input_handler.is_pressed_with_repeat(Action.UP):
            self.scroll_up()
        elif self.input_handler.is_pressed_with_repeat(Action.DOWN):
            self.scroll_down()
        elif self.input_handler.is_pressed(Action.L):
            self.jump_to_start()
        elif self.input_handler.is_pressed(Action.R):
            self.jump_to_end()

        # Launch ROM
        if self.input_handler.is_pressed(Action.A):
            selected = self.get_selected_item()
            if selected:
                rom_file = selected['rom']
                category_name = selected['category']

                # Get category
                category = self.config.get_category(category_name)
                if category:
                    # Set data for launcher
                    self.state_manager.set_data('rom_to_launch', rom_file)
                    self.state_manager.set_data('launch_category', category)

        # Remove from favorites
        if self.input_handler.is_pressed(Action.START):
            selected = self.get_selected_item()
            if selected:
                rom_file = selected['rom']
                self.persistence.remove_from_favorites(rom_file.path)
                # Reload favorites
                self._load_favorites()

        # Back to main menu
        if self.input_handler.is_pressed(Action.B):
            # Clear history and go directly to main menu
            from state_manager import AppState
            self.state_manager.current_state = AppState.MAIN_MENU
            self.state_manager.state_history.clear()

    def draw(self):
        """Draw favorites screen."""
        if not self.active:
            return

        # Clear screen
        pyxel.cls(0)

        # Draw breadcrumb
        self.breadcrumb.draw()

        # Draw window frame (reserve space for 1 breadcrumb line + 2 help lines at bottom)
        window_width = pyxel.width - 8
        DQWindow.draw(2, 18, window_width, 120, bg_color=0, border_color=7)

        # Draw favorites list
        start_y = 26
        line_height = 13
        visible = self.get_visible_items()
        visible_start, _ = self.get_visible_range()

        if not self.favorites:
            # Empty state (centered on screen)
            msg1 = "No favorites"
            msg2 = "Press START to add"
            center_x = pyxel.width // 2
            pyxel.text(center_x - len(msg1) * 2, 70, msg1, 7)
            pyxel.text(center_x - len(msg2) * 2, 80, msg2, 6)
        else:
            for i, fav in enumerate(visible):
                y = start_y + i * line_height
                index = visible_start + i

                rom_file = fav['rom']
                category = fav['category']

                # Display name (up to 33 half-width characters)
                display_name = f"{rom_file.name}"
                if len(display_name) > 33:
                    display_name = display_name[:30] + "..."

                color = 10 if index == self.selected_index else 7
                draw_japanese_text(6, y, display_name, color)

            # Draw scrollbar if needed
            if len(self.favorites) > self.items_per_page:
                from ui.base import draw_scrollbar
                scrollbar_x = pyxel.width - 4
                draw_scrollbar(scrollbar_x, start_y, self.items_per_page * line_height,
                              len(self.favorites), self.items_per_page, self.scroll_offset, 11)

        # Status bar
        self.status_bar.set_text(
            left=f"Favorites: {len(self.favorites)}",
            center="",
            right=f"{self.selected_index + 1}/{len(self.favorites)}" if self.favorites else ""
        )
        self.status_bar.draw()

        # Help text
        self.help_text.draw()
