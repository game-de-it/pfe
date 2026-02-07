"""
Configuration parser for pfe.cfg format.
Handles category definitions with DIR/EXT/TYPE/CORE parameters.
"""

import os
import re
from typing import Dict, List, Optional


class Category:
    """Represents a ROM category with its configuration."""

    def __init__(self, name: str):
        self.name = name
        self.directory = ""
        self.extensions = []
        self.emulator_type = ""
        self.cores = []
        self.title_img = ""  # Title image path

    def __repr__(self):
        return f"Category({self.name}, dir={self.directory}, ext={self.extensions})"


class Config:
    """Parses and manages pfe.cfg configuration."""

    def __init__(self, config_path: str = "data/pfe.cfg"):
        self.config_path = config_path
        self.global_vars: Dict[str, str] = {}
        self.categories: List[Category] = []
        self._load_config()

        # Set up debug mode
        self._setup_debug()

    def _expand_vars(self, value: str) -> str:
        """Expand environment variables and global config variables."""
        # Expand environment variables ($VAR)
        value = os.path.expandvars(value)

        # Expand global config variables
        for var_name, var_value in self.global_vars.items():
            value = value.replace(f"${var_name}", var_value)

        return value

    def _load_config(self):
        """Load and parse the pfe.cfg file."""
        if not os.path.exists(self.config_path):
            print(f"Warning: Config file not found: {self.config_path}")
            return

        current_category: Optional[Category] = None

        with open(self.config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                # Skip empty lines and comments (lines starting with ;)
                if not line or line.startswith(';'):
                    continue

                # Global variable assignment (must be before category check)
                if '=' in line and not line.startswith('-'):
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = self._expand_vars(value.strip())
                    self.global_vars[key] = value
                    continue

                # Category parameter (-KEY=VALUE)
                if line.startswith('-'):
                    if '=' in line:
                        key, value = line[1:].split('=', 1)
                        key = key.strip().upper()
                        value = self._expand_vars(value.strip())

                        if key == 'TITLE':
                            # New category definition
                            current_category = Category(value)
                            self.categories.append(current_category)
                        elif current_category:
                            if key == 'DIR':
                                # If DIR is a full path (starts with /), use as-is
                                # If relative path, combine with ROM_BASE
                                if value.startswith('/'):
                                    current_category.directory = value
                                else:
                                    rom_base = self.global_vars.get('ROM_BASE', '')
                                    if rom_base:
                                        current_category.directory = f"{rom_base}/{value}"
                                    else:
                                        current_category.directory = value
                            elif key == 'EXT':
                                # Split extensions by comma
                                current_category.extensions = [ext.strip() for ext in value.split(',')]
                            elif key == 'TYPE':
                                current_category.emulator_type = value
                            elif key == 'CORE':
                                # Split cores by comma
                                current_category.cores = [core.strip() for core in value.split(',')]
                            elif key == 'TITLE_IMG':
                                # Title image path (supports both relative and full paths)
                                if value.startswith('/'):
                                    # Full path
                                    current_category.title_img = value
                                elif value.startswith('./'):
                                    # Relative path from current directory
                                    current_category.title_img = value[2:]  # Remove ./
                                else:
                                    # Other relative paths
                                    current_category.title_img = value

    def get_categories(self) -> List[Category]:
        """Get all configured categories."""
        return self.categories

    def get_category(self, name: str) -> Optional[Category]:
        """Get a specific category by name."""
        for cat in self.categories:
            if cat.name == name:
                return cat
        return None

    def get_emulator_path(self, emulator_type: str) -> Optional[str]:
        """Get the path for a specific emulator type (e.g., TYPE_RA)."""
        type_key = f"TYPE_{emulator_type}"
        return self.global_vars.get(type_key)

    def get_rom_base(self) -> str:
        """Get the ROM_BASE directory."""
        return self.global_vars.get('ROM_BASE', '')

    def get_core_path(self) -> str:
        """Get the CORE_PATH directory."""
        return self.global_vars.get('CORE_PATH', '')

    def get_font_path(self) -> str:
        """Get the FONT_PATH for custom font."""
        return self.global_vars.get('FONT_PATH', '')

    def get_splash_time(self) -> int:
        """Get the SPLASH_TIME in seconds (1-5, default 3)."""
        try:
            splash_time = int(self.global_vars.get('SPLASH_TIME', '3'))
            # Clamp to 1-5 seconds
            return max(1, min(5, splash_time))
        except ValueError:
            return 3  # Default to 3 seconds

    def get_screenshot_dir(self) -> str:
        """Get the SCREENSHOT_DIR for ROM screenshots."""
        from debug import debug_print
        screenshot_dir = self.global_vars.get('SCREENSHOT_DIR', 'assets/screenshots')
        debug_print(f"[CONFIG] SCREENSHOT_DIR from config: {screenshot_dir}")
        return screenshot_dir

    def get_bgm_dir(self) -> str:
        """Get the BGM_DIR for background music files."""
        return self.global_vars.get('BGM_DIR', 'assets/bgm')

    def _setup_debug(self):
        """Setup debug mode based on DEBUG setting in pfe.cfg."""
        import debug
        debug_value = self.global_vars.get('DEBUG', 'false').lower()
        debug_enabled = debug_value in ['true', '1', 'yes', 'on']
        debug.set_debug(debug_enabled)
        if debug_enabled:
            print("[DEBUG] Debug mode enabled")

    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        from debug import is_debug_enabled
        return is_debug_enabled()


# Example usage and testing
if __name__ == "__main__":
    config = Config()
    print(f"Global vars: {config.global_vars}")
    print(f"\nCategories ({len(config.categories)}):")
    for cat in config.categories:
        print(f"  {cat}")
