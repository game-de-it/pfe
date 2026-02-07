"""
Theme manager for color customization.
"""

import json
import os
from typing import Dict, Any


class ThemeManager:
    """Manages color themes for the application."""

    def __init__(self, themes_dir: str = "assets/themes"):
        self.themes_dir = themes_dir
        self.current_theme = "dark"
        self.themes = {}
        self.colors = {}

        # Create themes directory if it doesn't exist
        os.makedirs(themes_dir, exist_ok=True)

        # Load default themes
        self._create_default_themes()
        self._load_themes()

    def _create_default_themes(self):
        """Create default theme files if they don't exist."""
        # Dark theme (default)
        dark_theme = {
            "name": "Dark",
            "colors": {
                "background": 0,      # Black
                "text": 7,            # White
                "text_selected": 10,  # Yellow
                "border": 7,          # White
                "border_accent": 11,  # Light blue
                "scrollbar": 11,      # Light blue
                "status_bg": 1,       # Dark blue
                "help_bg": 1,         # Dark blue
                "error": 8,           # Red
                "success": 11,        # Green
                "info": 12            # Light blue
            }
        }

        # Light theme
        light_theme = {
            "name": "Light",
            "colors": {
                "background": 7,      # White
                "text": 0,            # Black
                "text_selected": 8,   # Red
                "border": 0,          # Black
                "border_accent": 12,  # Blue
                "scrollbar": 12,      # Blue
                "status_bg": 13,      # Light gray
                "help_bg": 13,        # Light gray
                "error": 8,           # Red
                "success": 11,        # Green
                "info": 12            # Blue
            }
        }

        # Retro theme (original Game Boy colors)
        retro_theme = {
            "name": "Retro",
            "colors": {
                "background": 3,      # Dark green
                "text": 11,           # Light green
                "text_selected": 10,  # Yellow
                "border": 11,         # Light green
                "border_accent": 10,  # Yellow
                "scrollbar": 10,      # Yellow
                "status_bg": 4,       # Dark purple
                "help_bg": 4,         # Dark purple
                "error": 8,           # Red
                "success": 11,        # Green
                "info": 11            # Green
            }
        }

        # Neon theme
        neon_theme = {
            "name": "Neon",
            "colors": {
                "background": 0,      # Black
                "text": 14,           # Pink
                "text_selected": 6,   # Cyan
                "border": 14,         # Pink
                "border_accent": 6,   # Cyan
                "scrollbar": 6,       # Cyan
                "status_bg": 1,       # Dark blue
                "help_bg": 1,         # Dark blue
                "error": 8,           # Red
                "success": 11,        # Green
                "info": 6             # Cyan
            }
        }

        # Save default themes
        themes = {
            "dark": dark_theme,
            "light": light_theme,
            "retro": retro_theme,
            "neon": neon_theme
        }

        for theme_id, theme_data in themes.items():
            theme_file = os.path.join(self.themes_dir, f"{theme_id}.json")
            if not os.path.exists(theme_file):
                with open(theme_file, 'w', encoding='utf-8') as f:
                    json.dump(theme_data, f, ensure_ascii=False, indent=2)

    def _load_themes(self):
        """Load all theme files from themes directory."""
        if not os.path.exists(self.themes_dir):
            return

        for filename in os.listdir(self.themes_dir):
            if filename.endswith('.json'):
                theme_id = filename[:-5]  # Remove .json extension
                theme_file = os.path.join(self.themes_dir, filename)

                try:
                    with open(theme_file, 'r', encoding='utf-8') as f:
                        theme_data = json.load(f)
                        self.themes[theme_id] = theme_data
                except Exception as e:
                    print(f"Error loading theme {filename}: {e}")

    def set_theme(self, theme_id: str):
        """
        Set the current theme.

        Args:
            theme_id: Theme identifier (e.g., "dark", "light")
        """
        if theme_id in self.themes:
            self.current_theme = theme_id
            self.colors = self.themes[theme_id].get("colors", {})
            print(f"Theme set to: {theme_id}")
        else:
            print(f"Theme not found: {theme_id}")

    def get_color(self, color_key: str) -> int:
        """
        Get a color value from the current theme.

        Args:
            color_key: Color key (e.g., "background", "text")

        Returns:
            Pyxel color index (0-15)
        """
        return self.colors.get(color_key, 7)  # Default to white

    def get_theme_names(self) -> list:
        """
        Get list of available theme names.

        Returns:
            List of theme names
        """
        return [theme_data.get("name", theme_id) for theme_id, theme_data in self.themes.items()]

    def get_theme_ids(self) -> list:
        """
        Get list of available theme IDs.

        Returns:
            List of theme IDs
        """
        return list(self.themes.keys())

    def get_current_theme(self) -> str:
        """
        Get the current theme ID.

        Returns:
            Current theme ID
        """
        return self.current_theme


# Global theme manager instance
_theme_manager = None


def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance."""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager


def init_theme(theme_id: str = "dark"):
    """Initialize the theme system."""
    manager = get_theme_manager()
    manager.set_theme(theme_id)


# Example usage
if __name__ == "__main__":
    manager = ThemeManager()
    print(f"Available themes: {manager.get_theme_names()}")
    print(f"Current theme: {manager.get_current_theme()}")
    print(f"Background color: {manager.get_color('background')}")
