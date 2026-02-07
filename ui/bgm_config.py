"""
BGM Config Menu - submenu for BGM settings.
"""

import pyxel
from ui.base import ScrollableList
from ui.components import StatusBar, HelpText
from ui.window import DQWindow
from japanese_text import draw_japanese_text, get_japanese_text_width
from theme_manager import get_theme_manager
from debug import debug_print
from bgm_manager import get_bgm_manager
from music_mode import get_music_mode_manager
from brightness_manager import get_brightness_manager
from system_monitor import get_system_monitor


class BGMConfig(ScrollableList):
    """BGM Config submenu containing BGM ON/OFF, Volume, Mode, and Music Mode."""

    def __init__(self, input_handler, state_manager, persistence):
        super().__init__(items_per_page=8)
        self.input_handler = input_handler
        self.state_manager = state_manager
        self.persistence = persistence
        self.status_bar = StatusBar(138, 160)
        self.help_text = HelpText(146, 160)

        # Get managers
        self.bgm_manager = get_bgm_manager()
        self.music_mode_manager = get_music_mode_manager()
        self.brightness_manager = get_brightness_manager()
        self.system_monitor = get_system_monitor()

        # Load settings
        settings = self.persistence.load_settings()

        # BGM ON/OFF
        bgm_enabled_str = settings.get("bgm_enabled", "On")
        bgm_enabled = 1 if bgm_enabled_str == "On" else 0

        # BGM Volume (0-10)
        bgm_volume_str = settings.get("bgm_volume", "5")
        try:
            bgm_volume = int(bgm_volume_str)
        except:
            bgm_volume = 5

        # BGM Mode
        bgm_mode_values = ["Normal", "Shuffle"]
        bgm_mode_str = settings.get("bgm_mode", "Normal")
        bgm_mode_index = bgm_mode_values.index(bgm_mode_str) if bgm_mode_str in bgm_mode_values else 0

        # Menu items
        self.menu_items = [
            {"name": "BGM", "type": "toggle", "key": "bgm_enabled", "values": ["Off", "On"], "current": bgm_enabled},
            {"name": "BGM Volume", "type": "toggle", "key": "bgm_volume", "values": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"], "current": bgm_volume},
            {"name": "BGM Mode", "type": "toggle", "key": "bgm_mode", "values": bgm_mode_values, "current": bgm_mode_index},
            {"name": "Music Mode", "type": "toggle", "key": "music_mode", "values": ["Off", "On"], "current": 0},
        ]

        self.set_items(self.menu_items)

    def activate(self):
        """Called when screen becomes active."""
        super().activate()

        # Reload settings
        settings = self.persistence.load_settings()

        for item in self.menu_items:
            if item["key"] == "bgm_enabled":
                bgm_enabled_str = settings.get("bgm_enabled", "On")
                item["current"] = 1 if bgm_enabled_str == "On" else 0
            elif item["key"] == "bgm_volume":
                bgm_volume_str = settings.get("bgm_volume", "5")
                try:
                    item["current"] = int(bgm_volume_str)
                except:
                    item["current"] = 5
            elif item["key"] == "bgm_mode":
                bgm_mode_str = settings.get("bgm_mode", "Normal")
                if bgm_mode_str in item["values"]:
                    item["current"] = item["values"].index(bgm_mode_str)
            elif item["key"] == "music_mode":
                # Music Mode is always Off on activate
                item["current"] = 0

        # Set help text
        self.help_text.set_controls([
            ("Left/Right", "Change"),
            ("B", "Back")
        ])

    def deactivate(self):
        """Called when screen becomes inactive."""
        super().deactivate()

    def _save_settings(self):
        """Save settings to file."""
        settings = self.persistence.load_settings()
        for item in self.menu_items:
            if item["type"] == "toggle" and item["key"] != "music_mode":
                settings[item["key"]] = item["values"][item["current"]]
        self.persistence.save_settings(settings)

    def _activate_music_mode(self):
        """Activate Music Mode."""
        # Get current brightness and governor
        current_brightness = 5
        if self.brightness_manager.is_available():
            brightness = self.brightness_manager.get_brightness()
            if brightness >= 1:
                current_brightness = brightness

        current_governor = "ondemand"
        if self.system_monitor:
            governor = self.system_monitor.get_cpu_governor()
            if governor:
                current_governor = governor

        # Activate Music Mode
        self.music_mode_manager.activate(current_brightness, current_governor)
        debug_print("Music Mode activated from BGM Config")

    def _deactivate_music_mode(self):
        """Deactivate Music Mode and restore settings."""
        saved_brightness, saved_governor = self.music_mode_manager.deactivate()

        # Restore brightness
        if self.brightness_manager.is_available():
            self.brightness_manager.set_brightness(saved_brightness)
            debug_print(f"Brightness restored to: {saved_brightness}")

        # Restore governor
        if self.system_monitor:
            self.system_monitor.set_cpu_governor(saved_governor)
            debug_print(f"CPU governor restored to: {saved_governor}")

        # Update display
        for item in self.menu_items:
            if item["key"] == "music_mode":
                item["current"] = 0  # Off

    def update(self):
        """Update BGM config menu logic."""
        if not self.active:
            return

        from input_handler import Action

        # Check for Music Mode exit combo (X + Y)
        if self.music_mode_manager.is_active():
            if self.music_mode_manager.check_exit_combo(self.input_handler):
                self._deactivate_music_mode()
            # Ignore other input during Music Mode
            return

        # Navigation
        if self.input_handler.is_pressed_with_repeat(Action.UP):
            self.scroll_up()
        elif self.input_handler.is_pressed_with_repeat(Action.DOWN):
            self.scroll_down()

        # Change setting value
        selected = self.get_selected_item()
        if selected and selected["type"] == "toggle":
            changed = False
            if self.input_handler.is_pressed(Action.LEFT):
                selected["current"] = (selected["current"] - 1) % len(selected["values"])
                changed = True
                self._apply_setting(selected)

            elif self.input_handler.is_pressed(Action.RIGHT):
                selected["current"] = (selected["current"] + 1) % len(selected["values"])
                changed = True
                self._apply_setting(selected)

            if changed and selected["key"] != "music_mode":
                self._save_settings()

        # Back
        if self.input_handler.is_pressed(Action.B):
            self.state_manager.go_back()

    def _apply_setting(self, item):
        """Apply setting change immediately."""
        key = item["key"]
        value = item["values"][item["current"]]

        if key == "bgm_enabled":
            enabled = value == "On"
            debug_print(f"BGM setting changed to: {enabled}")
            self.bgm_manager.set_enabled(enabled)
            debug_print(f"BGM is now playing: {self.bgm_manager.is_bgm_playing()}")

        elif key == "bgm_volume":
            volume_level = int(value)
            volume = volume_level / 10.0  # 0-10 -> 0.0-1.0
            debug_print(f"Setting BGM volume to: {volume}")
            self.bgm_manager.set_volume(volume)

        elif key == "bgm_mode":
            debug_print(f"BGM mode changed to: {value}")
            self.bgm_manager.set_play_mode(value)

        elif key == "music_mode":
            enabled = value == "On"
            if enabled:
                self._activate_music_mode()

    def draw(self):
        """Draw BGM config menu screen."""
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
        title = "BGM CONFIG"
        pyxel.text(2, 2, title, text_selected_color)

        # Draw subtitle
        subtitle = "Music Settings"
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

            # Draw value
            if item["type"] == "toggle":
                display_value = item["values"][item["current"]]
                value_text = f"< {display_value} >"
                value_width = get_japanese_text_width(value_text)
                value_x = pyxel.width - 10 - value_width
                draw_japanese_text(value_x, y, value_text, color)

        # Status bar
        self.status_bar.set_text(
            left="BGM Config",
            center="",
            right=f"{self.selected_index + 1}/{len(self.menu_items)}"
        )
        self.status_bar.draw()

        # Help text
        self.help_text.draw()
