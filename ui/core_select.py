"""
Core selection screen for choosing emulator cores/launchers.
"""

import pyxel
from ui.base import ScrollableList
from ui.components import StatusBar, HelpText
from ui.window import DQWindow
from japanese_text import draw_japanese_text
from theme_manager import get_theme_manager


class CoreSelect(ScrollableList):
    """Core selection screen for choosing which core/launcher to use."""

    def __init__(self, input_handler, state_manager, persistence):
        super().__init__(items_per_page=7)  # Adjusted for 160x160 display
        self.input_handler = input_handler
        self.state_manager = state_manager
        self.persistence = persistence
        self.status_bar = StatusBar(138, 160)
        self.help_text = HelpText(146, 160)

        self.available_cores = []
        self.display_names = []  # Display names with (RA)/(SA) suffix
        self.rom_path = None
        self.last_used_core = None

    def _parse_core_display_name(self, core_spec: str) -> str:
        """
        Parse core specification and return display name with type suffix.

        Args:
            core_spec: Core specification (e.g., "nestopia", "SA:YABASANSHIRO")

        Returns:
            Display name (e.g., "nestopia (RA)", "YABASANSHIRO (SA)")
        """
        if ':' in core_spec:
            parts = core_spec.split(':', 1)
            prefix = parts[0].upper()
            name = parts[1]
            return f"{name} ({prefix})"
        else:
            # No prefix - assume RA (RetroArch)
            return f"{core_spec} (RA)"

    def activate(self):
        """Called when screen becomes active."""
        super().activate()

        # Get available cores for current category
        self.available_cores = self.state_manager.get_available_cores()
        self.rom_path = self.state_manager.get_selected_file()

        # Generate display names with (RA)/(SA) suffix
        self.display_names = [self._parse_core_display_name(core) for core in self.available_cores]

        # Get last used core for this ROM
        if self.rom_path:
            self.last_used_core = self.persistence.get_last_core(self.rom_path)

            # Pre-select last used core
            if self.last_used_core and self.last_used_core in self.available_cores:
                self.selected_index = self.available_cores.index(self.last_used_core)

        self.set_items(self.available_cores)

        # Set help text
        self.help_text.set_controls([
            ("Up/Down", "Select"),
            ("A", "Confirm"),
            ("B", "Cancel")
        ])

    def update(self):
        """Update core selection logic."""
        if not self.active:
            return

        from input_handler import Action

        # Navigation
        if self.input_handler.is_pressed_with_repeat(Action.UP):
            self.scroll_up()
        elif self.input_handler.is_pressed_with_repeat(Action.DOWN):
            self.scroll_down()
        elif self.input_handler.is_pressed(Action.L):
            self.jump_to_start()
        elif self.input_handler.is_pressed(Action.R):
            self.jump_to_end()

        # Confirm selection
        if self.input_handler.is_pressed(Action.A):
            selected_core = self.get_selected_item()
            if selected_core:
                # Set temporary core override for this launch
                self.state_manager.set_temp_core_override(selected_core)

                # Save to history
                if self.rom_path:
                    self.persistence.save_core_choice(self.rom_path, selected_core)

                # Go back to file list
                self.state_manager.go_back()

        # Cancel
        if self.input_handler.is_pressed(Action.B):
            self.state_manager.go_back()

    def draw(self):
        """Draw core selection screen."""
        if not self.active:
            return

        # Clear screen
        pyxel.cls(0)

        # Get theme colors
        theme = get_theme_manager()
        bg_color = theme.get_color("background")
        border_color = theme.get_color("border")
        text_color = theme.get_color("text")
        text_selected_color = theme.get_color("text_selected")

        # Draw title
        center_x = pyxel.width // 2
        title = "Select Core"
        title_x = center_x - len(title) * 2
        pyxel.text(title_x, 20, title, text_selected_color)

        # Draw window frame (centered)
        window_width = min(120, pyxel.width - 40)
        window_x = center_x - window_width // 2
        DQWindow.draw(window_x, 30, window_width, 100, bg_color=bg_color, border_color=border_color)

        # Draw core list
        start_y = 42
        line_height = 13
        visible = self.get_visible_items()
        visible_start, _ = self.get_visible_range()
        list_x = window_x + 4

        if not self.available_cores:
            msg = "No cores available"
            pyxel.text(center_x - len(msg) * 2, 70, msg, text_color)
        else:
            for i, core in enumerate(visible):
                y = start_y + i * line_height
                index = visible_start + i

                # Get display name with (RA)/(SA) suffix
                display_name = self.display_names[index] if index < len(self.display_names) else core

                # Truncate if too long
                if len(display_name) > 25:
                    display_name = display_name[:22] + "..."

                # Highlight selected and last used
                if index == self.selected_index:
                    color = text_selected_color  # Selected
                    draw_japanese_text(list_x, y, f"> {display_name}", color)
                elif core == self.last_used_core:
                    color = theme.get_color("success")  # Last used
                    draw_japanese_text(list_x, y, f"  {display_name} *", color)
                else:
                    color = text_color
                    draw_japanese_text(list_x, y, f"  {display_name}", color)

        # Status bar
        self.status_bar.set_text(
            left=f"Cores: {len(self.available_cores)}",
            center="",
            right=f"{self.selected_index + 1}/{len(self.available_cores)}" if self.available_cores else ""
        )
        self.status_bar.draw()

        # Help text
        self.help_text.draw()
