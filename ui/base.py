"""
Base classes for UI screens and components.
"""

import pyxel
from abc import ABC, abstractmethod
from typing import Optional


class UIScreen(ABC):
    """Base class for all UI screens."""

    def __init__(self):
        self.active = False

    @abstractmethod
    def update(self):
        """Update screen logic (called every frame)."""
        pass

    @abstractmethod
    def draw(self):
        """Draw screen graphics (called every frame)."""
        pass

    def activate(self):
        """Called when screen becomes active."""
        self.active = True

    def deactivate(self):
        """Called when screen becomes inactive."""
        self.active = False


class ScrollableList(UIScreen):
    """Base class for scrollable list screens."""

    def __init__(self, items_per_page: int = 15):
        super().__init__()
        self.items = []
        self.selected_index = 0
        self.scroll_offset = 0
        self.items_per_page = items_per_page

    def set_items(self, items: list):
        """Set the list items."""
        self.items = items
        # Clamp selected index
        if self.selected_index >= len(self.items):
            self.selected_index = max(0, len(self.items) - 1)
        self._update_scroll()

    def scroll_up(self):
        """Move selection up by one item."""
        if self.selected_index > 0:
            self.selected_index -= 1
            self._update_scroll()

    def scroll_down(self):
        """Move selection down by one item."""
        if self.selected_index < len(self.items) - 1:
            self.selected_index += 1
            self._update_scroll()

    def page_up(self):
        """Move selection up by one page."""
        self.selected_index = max(0, self.selected_index - self.items_per_page)
        self._update_scroll()

    def page_down(self):
        """Move selection down by one page."""
        self.selected_index = min(len(self.items) - 1, self.selected_index + self.items_per_page)
        self._update_scroll()

    def jump_to_start(self):
        """Jump to first item."""
        self.selected_index = 0
        self._update_scroll()

    def jump_to_end(self):
        """Jump to last item."""
        self.selected_index = max(0, len(self.items) - 1)
        self._update_scroll()

    def get_selected_item(self):
        """Get currently selected item."""
        if 0 <= self.selected_index < len(self.items):
            return self.items[self.selected_index]
        return None

    def _update_scroll(self):
        """Update scroll offset to keep selected item visible."""
        # Keep selected item in view
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + self.items_per_page:
            self.scroll_offset = self.selected_index - self.items_per_page + 1

        # Clamp scroll offset
        max_scroll = max(0, len(self.items) - self.items_per_page)
        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

    def get_visible_items(self):
        """Get items that should be visible on screen."""
        start = self.scroll_offset
        end = min(len(self.items), start + self.items_per_page)
        return self.items[start:end]

    def get_visible_range(self):
        """Get the range of visible items (start, end)."""
        start = self.scroll_offset
        end = min(len(self.items), start + self.items_per_page)
        return start, end

    @abstractmethod
    def update(self):
        """Update screen logic (called every frame)."""
        pass

    @abstractmethod
    def draw(self):
        """Draw screen graphics (called every frame)."""
        pass


# Helper functions for drawing UI elements
def draw_text_centered(x: int, y: int, text: str, color: int):
    """Draw text centered at given position."""
    text_width = len(text) * 4  # Pyxel default font is 4 pixels wide
    pyxel.text(x - text_width // 2, y, text, color)


def draw_box(x: int, y: int, w: int, h: int, border_color: int, fill_color: Optional[int] = None):
    """Draw a box with optional fill."""
    if fill_color is not None:
        pyxel.rect(x, y, w, h, fill_color)
    pyxel.rectb(x, y, w, h, border_color)


def truncate_text(text: str, max_width: int) -> str:
    """Truncate text to fit within max_width pixels."""
    char_width = 4  # Pyxel default font width
    max_chars = max_width // char_width
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 3] + "..."


def draw_scrollbar(x: int, y: int, height: int, total_items: int, visible_items: int, scroll_offset: int, color: int):
    """Draw a scrollbar."""
    if total_items <= visible_items:
        return

    # Calculate scrollbar parameters
    scrollbar_height = max(4, (visible_items / total_items) * height)
    scroll_ratio = scroll_offset / (total_items - visible_items)
    scrollbar_y = y + int(scroll_ratio * (height - scrollbar_height))

    # Draw track
    pyxel.rect(x, y, 2, height, 1)
    # Draw thumb
    pyxel.rect(x, scrollbar_y, 2, int(scrollbar_height), color)
