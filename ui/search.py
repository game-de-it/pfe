"""
Search screen for finding ROMs by name.
"""
from theme_manager import get_theme_manager

import pyxel
from ui.base import ScrollableList
from ui.components import StatusBar, HelpText
from ui.window import DQWindow
from rom_manager import ROMFile
from japanese_text import draw_japanese_text
from typing import List


class Search(ScrollableList):
    """Search screen for finding ROMs."""

    def __init__(self, input_handler, state_manager, config, rom_manager, persistence):
        super().__init__(items_per_page=7)  # 7 rows to account for search box
        self.input_handler = input_handler
        self.state_manager = state_manager
        self.config = config
        self.rom_manager = rom_manager
        self.persistence = persistence
        self.status_bar = StatusBar(138, 160)
        self.help_text = HelpText(146, 160)

        self.search_query = ""
        self.search_results: List[ROMFile] = []
        self.all_roms: List[ROMFile] = []
        self.input_mode = False  # Text input mode

        # For software keyboard
        self.keyboard_chars = "abcdefghijklmnopqrstuvwxyz0123456789 "
        self.keyboard_index = 0

    def activate(self):
        """Called when screen becomes active."""
        super().activate()

        # Collect ROMs from all categories
        self._load_all_roms()

        # Set help text
        self._update_help_text()

    def _load_all_roms(self):
        """Load ROMs from all categories."""
        self.all_roms = []
        categories = self.config.get_categories()

        for category in categories:
            roms = self.rom_manager.scan_category(category)
            # Exclude directories
            for rom in roms:
                if not rom.is_directory:
                    self.all_roms.append(rom)

        # Initial display shows all ROMs
        self.search_results = self.all_roms.copy()
        self.set_items(self.search_results)

    def _update_help_text(self):
        """Update help text."""
        if self.input_mode:
            self.help_text.set_controls([
                ("Up/Down", "Chr"),
                ("A", "Add"),
                ("B", "Del"),
                ("START", "Done")
            ])
        else:
            self.help_text.set_controls([
                ("Up/Down", "Sel"),
                ("A", "Lnch"),
                ("X", "Srch"),
                ("B", "Back")
            ])

    def update(self):
        """Update search screen logic."""
        if not self.active:
            return

        from input_handler import Action
        from state_manager import AppState

        if self.input_mode:
            # Text input mode
            self._update_text_input()
        else:
            # Normal mode (list selection)
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
                    # Identify category and launch ROM
                    self._launch_rom(selected)

            # Start search mode
            if self.input_handler.is_pressed(Action.X):
                self.input_mode = True
                self._update_help_text()

            # Back
            if self.input_handler.is_pressed(Action.B):
                self.state_manager.go_back()

    def _update_text_input(self):
        """Update text input (software keyboard)."""
        from input_handler import Action

        # Character selection
        if self.input_handler.is_pressed_with_repeat(Action.UP):
            self.keyboard_index = (self.keyboard_index - 1) % len(self.keyboard_chars)
        elif self.input_handler.is_pressed_with_repeat(Action.DOWN):
            self.keyboard_index = (self.keyboard_index + 1) % len(self.keyboard_chars)

        # Add character
        if self.input_handler.is_pressed(Action.A):
            if len(self.search_query) < 20:  # Maximum 20 characters
                self.search_query += self.keyboard_chars[self.keyboard_index]
                self._perform_search()

        # Delete character (backspace)
        if self.input_handler.is_pressed(Action.B):
            if self.search_query:
                self.search_query = self.search_query[:-1]
                self._perform_search()

        # Search complete
        if self.input_handler.is_pressed(Action.START):
            self.input_mode = False
            self._update_help_text()

    def _perform_search(self):
        """Execute search."""
        if not self.search_query:
            # Show all ROMs if query is empty
            self.search_results = self.all_roms.copy()
        else:
            # Search for ROMs matching query
            query = self.search_query.lower()
            self.search_results = []
            for rom in self.all_roms:
                if query in rom.name.lower():
                    self.search_results.append(rom)

        self.set_items(self.search_results)
        self.selected_index = 0
        self.scroll_offset = 0
        self._update_scroll()

    def _launch_rom(self, rom_file: ROMFile):
        """Launch ROM."""
        # Identify category
        categories = self.config.get_categories()
        for category in categories:
            # Check if ROM path is under category directory
            import os
            if rom_file.path.startswith(category.directory):
                # Set data for launcher
                self.state_manager.set_data('rom_to_launch', rom_file)
                self.state_manager.set_data('launch_category', category)
                return

    def draw(self):
        """Draw search screen."""
        if not self.active:
            return

        # Clear screen
        pyxel.cls(0)

        # Draw title (left-aligned to avoid overlap with system status)
        title = "Search ROMs"
        pyxel.text(2, 2, title, 10)

        # Draw search box
        search_box_width = pyxel.width - 20
        DQWindow.draw(10, 12, search_box_width, 16, bg_color=1, border_color=7)
        search_display = f"> {self.search_query}_" if self.input_mode else f"> {self.search_query}"
        draw_japanese_text(14, 18, search_display, 7)

        # Draw main window
        window_width = pyxel.width - 8
        DQWindow.draw(2, 30, window_width, 106, bg_color=0, border_color=7)

        # Draw results list
        start_y = 38
        line_height = 13
        visible = self.get_visible_items()
        visible_start, _ = self.get_visible_range()

        if not self.search_results:
            msg = "No results"
            center_x = pyxel.width // 2
            pyxel.text(center_x - len(msg) * 2, 70, msg, 7)
        else:
            for i, rom_file in enumerate(visible):
                y = start_y + i * line_height
                index = visible_start + i

                # Display name
                display_name = self.rom_manager.get_rom_display_name(rom_file, max_length=33, max_width=145)
                color = 10 if index == self.selected_index else 7
                draw_japanese_text(6, y, display_name, color)

            # Draw scrollbar if needed
            if len(self.search_results) > self.items_per_page:
                from ui.base import draw_scrollbar
                scrollbar_x = pyxel.width - 4
                draw_scrollbar(scrollbar_x, start_y, self.items_per_page * line_height,
                              len(self.search_results), self.items_per_page, self.scroll_offset, 11)

        # Display software keyboard (in input mode)
        if self.input_mode:
            # Display current character
            current_char = self.keyboard_chars[self.keyboard_index]
            char_display = f"[{current_char}]"
            pyxel.text(70, 18, char_display, 11)

        # Status bar
        self.status_bar.set_text(
            left=f"Results: {len(self.search_results)}",
            center="",
            right=f"{self.selected_index + 1}/{len(self.search_results)}" if self.search_results else ""
        )
        self.status_bar.draw()

        # Help text
        self.help_text.draw()
