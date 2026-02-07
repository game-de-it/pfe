"""
Reusable UI components for the launcher.
"""

import pyxel
from typing import List, Optional
from system_monitor import get_system_monitor


class StatusBar:
    """Status bar component showing current state info."""

    def __init__(self, y: int, width: int = None):
        self.y = y
        # width parameter is kept for backwards compatibility but always use pyxel.width
        self.left_text = ""
        self.center_text = ""
        self.right_text = ""

    @property
    def width(self):
        """Get width - always use pyxel.width for dynamic resolution support."""
        return pyxel.width

    def set_text(self, left: str = "", center: str = "", right: str = ""):
        """Set status bar text."""
        self.left_text = left
        self.center_text = center
        self.right_text = right

    def draw(self):
        """Draw the status bar."""
        from theme_manager import get_theme_manager
        theme = get_theme_manager()
        status_bg = theme.get_color("status_bg")
        text_color = theme.get_color("text")

        width = self.width  # Get actual width

        # Background
        pyxel.rect(0, self.y, width, 8, status_bg)

        # Left text
        if self.left_text:
            pyxel.text(2, self.y + 1, self.left_text, text_color)

        # Center text
        if self.center_text:
            text_width = len(self.center_text) * 4
            pyxel.text(width // 2 - text_width // 2, self.y + 1, self.center_text, text_color)

        # Right text
        if self.right_text:
            text_width = len(self.right_text) * 4
            pyxel.text(width - text_width - 2, self.y + 1, self.right_text, text_color)


class Breadcrumb:
    """Breadcrumb navigation component."""

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.path: List[str] = []

    def set_path(self, path: List[str]):
        """Set breadcrumb path."""
        self.path = path

    def draw(self):
        """Draw breadcrumb navigation."""
        if not self.path:
            return

        from theme_manager import get_theme_manager
        theme = get_theme_manager()
        text_color = theme.get_color("text")
        border_accent = theme.get_color("border_accent")

        x = self.x
        for i, item in enumerate(self.path):
            # Draw item
            pyxel.text(x, self.y, item, text_color)
            x += len(item) * 4

            # Draw separator
            if i < len(self.path) - 1:
                pyxel.text(x, self.y, " > ", border_accent)
                x += 12  # " > " is 3 chars


class CategoryTitle:
    """Category title display component (supports Japanese)."""

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.title = ""

    def set_title(self, title: str):
        """Set category title."""
        self.title = title

    def draw(self):
        """Draw category title."""
        if not self.title:
            return

        from japanese_text import draw_japanese_text
        from theme_manager import get_theme_manager

        theme = get_theme_manager()
        text_selected_color = theme.get_color("text_selected")
        draw_japanese_text(self.x, self.y, self.title, text_selected_color)


class Toast:
    """Toast notification component."""

    def __init__(self):
        self.message = ""
        self.duration = 0
        self.max_duration = 60  # frames (2 seconds at 30fps)

    def show(self, message: str, duration: int = 60):
        """Show a toast notification."""
        self.message = message
        self.duration = duration
        self.max_duration = duration

    def update(self):
        """Update toast timer."""
        if self.duration > 0:
            self.duration -= 1

    def draw(self, screen_width: int, screen_height: int):
        """Draw toast notification."""
        if self.duration <= 0:
            return

        # Calculate position (centered at top)
        text_width = len(self.message) * 4
        box_width = text_width + 8
        box_x = (screen_width - box_width) // 2
        box_y = 10

        # Fade effect
        alpha_factor = min(1.0, self.duration / 15)  # Fade in/out
        if alpha_factor < 1.0:
            # Simple fade by using darker color when fading
            bg_color = 1
            text_color = 5
        else:
            bg_color = 0
            text_color = 7

        # Draw box
        pyxel.rect(box_x, box_y, box_width, 10, bg_color)
        pyxel.rectb(box_x, box_y, box_width, 10, 7)

        # Draw text
        pyxel.text(box_x + 4, box_y + 2, self.message, text_color)


class Counter:
    """Item counter component (e.g., "15 / 234 ROMs")."""

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.current = 0
        self.total = 0
        self.label = "items"

    def set_count(self, current: int, total: int, label: str = "items"):
        """Set counter values."""
        self.current = current
        self.total = total
        self.label = label

    def draw(self):
        """Draw counter."""
        from theme_manager import get_theme_manager
        theme = get_theme_manager()
        text_color = theme.get_color("text")

        # 短縮表記にして枠にかぶらないようにする
        text = f"{self.current + 1}/{self.total}"
        pyxel.text(self.x, self.y, text, text_color)


class LoadingSpinner:
    """Loading spinner animation."""

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.frame = 0
        self.chars = ["|", "/", "-", "\\"]

    def update(self):
        """Update animation frame."""
        self.frame = (self.frame + 1) % (len(self.chars) * 4)

    def draw(self):
        """Draw spinner."""
        from theme_manager import get_theme_manager
        theme = get_theme_manager()
        text_selected_color = theme.get_color("text_selected")

        char = self.chars[self.frame // 4]
        pyxel.text(self.x, self.y, char, text_selected_color)


class ProgressBar:
    """Progress bar component."""

    def __init__(self, x: int, y: int, width: int, height: int = 4):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.progress = 0.0  # 0.0 to 1.0

    def set_progress(self, progress: float):
        """Set progress (0.0 to 1.0)."""
        self.progress = max(0.0, min(1.0, progress))

    def draw(self):
        """Draw progress bar."""
        # Background
        pyxel.rect(self.x, self.y, self.width, self.height, 1)
        # Progress
        fill_width = int(self.width * self.progress)
        if fill_width > 0:
            pyxel.rect(self.x, self.y, fill_width, self.height, 11)
        # Border
        pyxel.rectb(self.x, self.y, self.width, self.height, 7)


class HelpText:
    """Help text component showing available controls."""

    def __init__(self, y: int, width: int = None):
        self.y = y
        # width parameter is kept for backwards compatibility but always use pyxel.width
        self.controls: List[tuple] = []

    @property
    def width(self):
        """Get width - always use pyxel.width for dynamic resolution support."""
        return pyxel.width

    def set_controls(self, controls: List[tuple]):
        """
        Set control hints.
        Format: [(key, action), ...]
        Example: [("A", "Select"), ("B", "Back")]
        """
        self.controls = controls

    def draw(self):
        """Draw help text."""
        if not self.controls:
            return

        # Build help string (短縮表記)
        parts = []
        for key, action in self.controls:
            # アクション名を短縮
            short_action = action[:3] if len(action) > 3 else action
            parts.append(f"{key}:{short_action}")

        help_text = " ".join(parts)  # スペースを1つに減らす

        # Draw at bottom (画面内に収まるように調整)
        from theme_manager import get_theme_manager
        theme = get_theme_manager()
        text_color = theme.get_color("text")
        pyxel.text(2, self.y, help_text, text_color)


class Icon:
    """Simple icon drawing helper."""

    @staticmethod
    def draw_star(x: int, y: int, filled: bool = True, color: int = 10):
        """Draw a star icon (for favorites)."""
        if filled:
            # Simple filled star using pixels
            pyxel.pset(x + 2, y, color)
            pyxel.pset(x + 1, y + 1, color)
            pyxel.pset(x + 2, y + 1, color)
            pyxel.pset(x + 3, y + 1, color)
            pyxel.pset(x, y + 2, color)
            pyxel.pset(x + 1, y + 2, color)
            pyxel.pset(x + 2, y + 2, color)
            pyxel.pset(x + 3, y + 2, color)
            pyxel.pset(x + 4, y + 2, color)
            pyxel.pset(x + 1, y + 3, color)
            pyxel.pset(x + 3, y + 3, color)
        else:
            # Just use text as fallback
            pyxel.text(x, y, "*", color)

    @staticmethod
    def draw_folder(x: int, y: int, color: int = 10):
        """Draw a folder icon."""
        pyxel.rectb(x, y + 1, 6, 5, color)
        pyxel.line(x, y + 1, x + 2, y + 1, color)
        pyxel.line(x + 2, y, x + 4, y, color)

    @staticmethod
    def draw_file(x: int, y: int, color: int = 7):
        """Draw a file icon."""
        pyxel.rectb(x, y, 5, 6, color)
        pyxel.line(x + 1, y + 2, x + 3, y + 2, color)
        pyxel.line(x + 1, y + 4, x + 3, y + 4, color)


class SystemStatus:
    """System status display (time, battery, network) in top-right corner."""

    def __init__(self, x: int = 0, y: int = 2):
        self.x = x
        self.y = y

    def draw(self, screen_width: int = None):
        """Draw system status."""
        monitor = get_system_monitor()
        if not monitor:
            return

        # Get status text
        status_text = monitor.get_status_text()
        if not status_text:
            return

        # Use pyxel.width if screen_width not specified
        if screen_width is None:
            screen_width = pyxel.width

        # Calculate position (right-aligned)
        text_width = len(status_text) * 4
        x = screen_width - text_width - 2

        # Draw text
        from theme_manager import get_theme_manager
        theme = get_theme_manager()
        text_color = theme.get_color("text")
        pyxel.text(x, self.y, status_text, text_color)
