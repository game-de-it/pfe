"""
Date/Time settings screen.
"""

import pyxel
from datetime import datetime
from ui.base import UIScreen
from ui.components import HelpText
from ui.window import DQWindow
from japanese_text import draw_japanese_text, get_japanese_text_width
from theme_manager import get_theme_manager
from system_monitor import get_system_monitor
from debug import debug_print


class DateTimeSettings(UIScreen):
    """Date/Time settings screen."""

    def __init__(self, input_handler, state_manager, config):
        super().__init__()
        self.input_handler = input_handler
        self.state_manager = state_manager
        self.config = config
        self.help_text = HelpText(146, 160)

        # System monitor
        self.system_monitor = get_system_monitor()

        # Date/Time values
        self.year = 2024
        self.month = 1
        self.day = 1
        self.hour = 0
        self.minute = 0

        # Field names and their ranges
        self.fields = [
            {"name": "Year", "key": "year", "min": 2020, "max": 2099},
            {"name": "Month", "key": "month", "min": 1, "max": 12},
            {"name": "Day", "key": "day", "min": 1, "max": 31},
            {"name": "Hour", "key": "hour", "min": 0, "max": 23},
            {"name": "Minute", "key": "minute", "min": 0, "max": 59},
            {"name": "Apply", "key": "apply", "type": "button"},
        ]

        self.selected_index = 0
        self.message = ""
        self.message_timer = 0

    def activate(self):
        """Called when screen becomes active."""
        super().activate()

        # Load current date/time
        if self.system_monitor:
            year, month, day, hour, minute = self.system_monitor.get_current_datetime()
            self.year = year
            self.month = month
            self.day = day
            self.hour = hour
            self.minute = minute
        else:
            now = datetime.now()
            self.year = now.year
            self.month = now.month
            self.day = now.day
            self.hour = now.hour
            self.minute = now.minute

        self.selected_index = 0
        self.message = ""
        self.message_timer = 0

        # Set help text
        self.help_text.set_controls([
            ("Up/Down", "Select"),
            ("Left/Right", "Change"),
            ("A", "Apply"),
            ("B", "Back")
        ])

    def _get_max_day(self) -> int:
        """Get maximum day for current month/year."""
        if self.month in [1, 3, 5, 7, 8, 10, 12]:
            return 31
        elif self.month in [4, 6, 9, 11]:
            return 30
        elif self.month == 2:
            # Leap year check
            if (self.year % 4 == 0 and self.year % 100 != 0) or (self.year % 400 == 0):
                return 29
            else:
                return 28
        return 31

    def _validate_day(self):
        """Validate and adjust day if needed."""
        max_day = self._get_max_day()
        if self.day > max_day:
            self.day = max_day

    def _get_field_value(self, field) -> int:
        """Get value for a field."""
        key = field["key"]
        if key == "year":
            return self.year
        elif key == "month":
            return self.month
        elif key == "day":
            return self.day
        elif key == "hour":
            return self.hour
        elif key == "minute":
            return self.minute
        return 0

    def _set_field_value(self, field, value: int):
        """Set value for a field."""
        key = field["key"]
        if key == "year":
            self.year = value
        elif key == "month":
            self.month = value
            self._validate_day()
        elif key == "day":
            self.day = value
        elif key == "hour":
            self.hour = value
        elif key == "minute":
            self.minute = value

    def _apply_datetime(self):
        """Apply the date/time settings."""
        if self.system_monitor:
            success = self.system_monitor.set_datetime(
                self.year, self.month, self.day, self.hour, self.minute
            )
            if success:
                self.message = "Date/Time updated!"
                debug_print(f"[DateTime] Set to {self.year}-{self.month:02d}-{self.day:02d} {self.hour:02d}:{self.minute:02d}")
            else:
                self.message = "Failed to set date/time"
                debug_print("[DateTime] Failed to set date/time")
        else:
            self.message = "System monitor not available"

        self.message_timer = 90  # Show message for 3 seconds

    def update(self):
        """Update date/time settings screen."""
        if not self.active:
            return

        from input_handler import Action

        # Update message timer
        if self.message_timer > 0:
            self.message_timer -= 1
            if self.message_timer == 0:
                self.message = ""

        # Navigation
        if self.input_handler.is_pressed_with_repeat(Action.UP):
            self.selected_index = (self.selected_index - 1) % len(self.fields)
        elif self.input_handler.is_pressed_with_repeat(Action.DOWN):
            self.selected_index = (self.selected_index + 1) % len(self.fields)

        # Get selected field
        field = self.fields[self.selected_index]

        # Change value (for non-button fields)
        if field.get("type") != "button":
            if self.input_handler.is_pressed_with_repeat(Action.LEFT):
                current = self._get_field_value(field)
                new_value = current - 1
                if new_value < field["min"]:
                    new_value = field["max"]
                self._set_field_value(field, new_value)

            elif self.input_handler.is_pressed_with_repeat(Action.RIGHT):
                current = self._get_field_value(field)
                new_value = current + 1
                if new_value > field["max"]:
                    new_value = field["min"]
                self._set_field_value(field, new_value)

            # Update max day when month/year changes
            if field["key"] in ["month", "year"]:
                self.fields[2]["max"] = self._get_max_day()
                self._validate_day()

        # Apply button
        if self.input_handler.is_pressed(Action.A):
            if field.get("type") == "button":
                self._apply_datetime()
            else:
                # Move to Apply button when A is pressed on any field
                for i, f in enumerate(self.fields):
                    if f.get("type") == "button":
                        self.selected_index = i
                        break

        # Back
        if self.input_handler.is_pressed(Action.B):
            self.state_manager.go_back()

    def draw(self):
        """Draw date/time settings screen."""
        if not self.active:
            return

        # Get theme colors
        theme = get_theme_manager()
        bg_color = theme.get_color("background")
        text_color = theme.get_color("text")
        text_selected_color = theme.get_color("text_selected")
        border_color = theme.get_color("border")
        success_color = theme.get_color("success")

        # Clear screen
        pyxel.cls(bg_color)

        # Draw title
        title = "DATE/TIME"
        pyxel.text(2, 2, title, text_selected_color)

        # Draw subtitle
        subtitle = "Set System Date and Time"
        subtitle_x = pyxel.width // 2 - len(subtitle) * 2
        pyxel.text(subtitle_x, 10, subtitle, text_color)

        # Draw main window frame
        window_width = pyxel.width - 8
        DQWindow.draw(2, 18, window_width, 100, bg_color=bg_color, border_color=border_color)

        # Draw current date/time preview
        preview = f"{self.year}/{self.month:02d}/{self.day:02d} {self.hour:02d}:{self.minute:02d}"
        preview_x = pyxel.width // 2 - len(preview) * 2
        pyxel.text(preview_x, 26, preview, text_selected_color)

        # Draw fields
        start_y = 40
        line_height = 12

        for i, field in enumerate(self.fields):
            y = start_y + i * line_height
            is_selected = (i == self.selected_index)
            color = text_selected_color if is_selected else text_color

            if field.get("type") == "button":
                # Draw button
                button_text = f"[ {field['name']} ]"
                button_x = pyxel.width // 2 - len(button_text) * 2
                pyxel.text(button_x, y, button_text, color)
            else:
                # Draw field name and value
                draw_japanese_text(10, y, field["name"], color)

                value = self._get_field_value(field)
                if field["key"] in ["month", "day", "hour", "minute"]:
                    value_text = f"< {value:02d} >"
                else:
                    value_text = f"< {value} >"

                value_width = get_japanese_text_width(value_text)
                value_x = pyxel.width - 14 - value_width
                draw_japanese_text(value_x, y, value_text, color)

        # Draw message
        if self.message:
            msg_y = start_y + len(self.fields) * line_height + 8
            msg_x = pyxel.width // 2 - len(self.message) * 2
            msg_color = success_color if "updated" in self.message else text_color
            pyxel.text(msg_x, msg_y, self.message, msg_color)

        # Help text
        self.help_text.draw()
