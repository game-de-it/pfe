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
        self.system_id = ""
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
        self._categories_by_id: Dict[str, Category] = {}
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

                # Skip empty lines and comments (retroarch.cfg uses #, PFE uses ;)
                if not line or line.startswith(';') or line.startswith('#'):
                    continue

                # Global or retro-style assignment (must be before category check)
                if '=' in line and not line.startswith('-'):
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = self._expand_vars(self._strip_value(value.strip()))
                    if self._parse_retro_assignment(key, value):
                        continue
                    self.global_vars[key.upper()] = value
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
                            if key in ('SYSTEM', 'ES_SYSTEM'):
                                current_category.system_id = value
                            elif key == 'DIR':
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

    def _strip_value(self, value: str) -> str:
        """Strip retroarch.cfg-style quotes from a config value."""
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            return value[1:-1]
        return value

    def _split_list(self, value: str) -> List[str]:
        """Split comma or pipe separated config values."""
        if '|' in value:
            parts = value.split('|')
        else:
            parts = value.split(',')
        return [part.strip() for part in parts if part.strip()]

    def _category_for_id(self, system_id: str) -> Category:
        key = system_id.strip().lower()
        if key in self._categories_by_id:
            return self._categories_by_id[key]
        category = Category(system_id)
        self._categories_by_id[key] = category
        self.categories.append(category)
        return category

    def _parse_retro_assignment(self, key: str, value: str) -> bool:
        """Parse retroarch.cfg-style PFE keys.

        Supported examples:
          rom_base = "/roms"
          screenshot_dir = "/roms/screenshots"
          ui.font_backend = "bdf"
          system.nes.name = "Nintendo Entertainment System"
          system.nes.dir = "nes"
          system.nes.ext = "nes|zip"
          system.nes.core = "nestopia|fceumm"
          script.battery = "./scripts/get_battery.sh"
        """
        normalized = key.strip().lower()
        if not normalized:
            return False

        global_map = {
            "rom_base": "ROM_BASE",
            "core_path": "CORE_PATH",
            "screenshot_dir": "SCREENSHOT_DIR",
            "bgm_dir": "BGM_DIR",
            "debug": "DEBUG",
            "debug_level": "DEBUG_LEVEL",
            "debug_log": "DEBUG_LOG",
            "debug_console": "DEBUG_CONSOLE",
            "font_path": "FONT_PATH",
            "font_backend": "FONT_BACKEND",
            "bdf_font_path": "BDF_FONT_PATH",
            "palette_file": "PALETTE_FILE",
            "palette_preserve_ui": "PALETTE_PRESERVE_UI",
            "splash_time": "SPLASH_TIME",
            "network_check_interval_seconds": "NETWORK_CHECK_INTERVAL_SECONDS",
            "resume_after_game": "RESUME_AFTER_GAME",
        }
        if normalized in global_map:
            self.global_vars[global_map[normalized]] = value
            return True

        dotted_global_map = {
            "ui.font_path": "FONT_PATH",
            "ui.font_backend": "FONT_BACKEND",
            "ui.bdf_font_path": "BDF_FONT_PATH",
            "image.palette_file": "PALETTE_FILE",
            "image.palette_preserve_ui": "PALETTE_PRESERVE_UI",
            "image.screenshot_dir": "SCREENSHOT_DIR",
            "log.debug": "DEBUG",
            "log.level": "DEBUG_LEVEL",
            "log.file": "DEBUG_LOG",
            "log.console": "DEBUG_CONSOLE",
            "status.network_check_interval_seconds": "NETWORK_CHECK_INTERVAL_SECONDS",
            "status.network_interval_seconds": "NETWORK_CHECK_INTERVAL_SECONDS",
            "network.check_interval_seconds": "NETWORK_CHECK_INTERVAL_SECONDS",
            "launcher.resume_after_game": "RESUME_AFTER_GAME",
            "launcher.return_after_game": "RESUME_AFTER_GAME",
            "game.resume_after_exit": "RESUME_AFTER_GAME",
        }
        if normalized in dotted_global_map:
            self.global_vars[dotted_global_map[normalized]] = value
            return True

        if normalized.startswith("script."):
            name = normalized.split(".", 1)[1].upper()
            if name.endswith("_SCRIPT"):
                self.global_vars[name] = value
            else:
                self.global_vars[f"{name}_SCRIPT"] = value
            return True

        if normalized.startswith("launcher."):
            name = normalized.split(".", 1)[1].upper()
            self.global_vars[f"TYPE_{name}"] = value
            return True

        if normalized.startswith("system."):
            parts = normalized.split(".")
            if len(parts) < 3:
                return True
            system_id = parts[1]
            field = ".".join(parts[2:])
            category = self._category_for_id(system_id)

            if field in ("name", "title"):
                category.name = value
            elif field in ("system", "system_id", "es_system"):
                category.system_id = value
            elif field in ("dir", "directory"):
                if value.startswith('/'):
                    category.directory = value
                else:
                    rom_base = self.global_vars.get('ROM_BASE', '')
                    category.directory = f"{rom_base}/{value}" if rom_base else value
            elif field in ("ext", "extensions"):
                category.extensions = self._split_list(value)
            elif field in ("core", "cores"):
                category.cores = self._split_list(value)
            elif field in ("type", "emulator_type"):
                category.emulator_type = value
            elif field in ("title_img", "image", "title_image"):
                category.title_img = value[2:] if value.startswith('./') else value
            return True

        return False

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
        return self.global_vars.get(type_key) or self.global_vars.get(type_key.upper())

    def get_rom_base(self) -> str:
        """Get the ROM_BASE directory."""
        return self.global_vars.get('ROM_BASE', '')

    def get_core_path(self) -> str:
        """Get the CORE_PATH directory."""
        return self.global_vars.get('CORE_PATH', '')

    def get_font_path(self) -> str:
        """Get the FONT_PATH for custom font."""
        return self.global_vars.get('FONT_PATH', '')

    def get_font_backend(self) -> str:
        """Get text rendering backend: auto, ttf, or bdf."""
        return self.global_vars.get('FONT_BACKEND', 'auto').lower()

    def get_bdf_font_path(self) -> str:
        """Get the BDF font path for bitmap text rendering."""
        return self.global_vars.get('BDF_FONT_PATH', '')

    def get_palette_path(self) -> str:
        """Get the optional 256-color .pyxpal palette file."""
        return self.global_vars.get('PALETTE_FILE', '')

    def preserve_ui_palette(self) -> bool:
        """Whether palette loading should keep Pyxel's first 16 UI colors."""
        value = self.global_vars.get('PALETTE_PRESERVE_UI', 'true').lower()
        return value in ['true', '1', 'yes', 'on']

    def get_debug_level(self) -> str:
        """Get configured debug log level."""
        return self.global_vars.get('DEBUG_LEVEL', 'DEBUG')

    def get_debug_log_path(self) -> str:
        """Get configured debug log path."""
        return self.global_vars.get('DEBUG_LOG', 'data/debug.log')

    def debug_console_enabled(self) -> bool:
        """Return whether debug logs should also be printed to console."""
        value = self.global_vars.get('DEBUG_CONSOLE', 'true').lower()
        return value in ['true', '1', 'yes', 'on']

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
        from pfe_app.debug import debug_print
        screenshot_dir = self.global_vars.get('SCREENSHOT_DIR', 'assets/screenshots')
        debug_print(f"[CONFIG] SCREENSHOT_DIR from config: {screenshot_dir}")
        return screenshot_dir

    def get_bgm_dir(self) -> str:
        """Get the BGM_DIR for background music files."""
        return self.global_vars.get('BGM_DIR', 'assets/bgm')

    def _setup_debug(self):
        """Setup debug mode based on DEBUG setting in pfe.cfg."""
        from pfe_app import debug
        debug_value = self.global_vars.get('DEBUG', 'false').lower()
        debug_enabled = debug_value in ['true', '1', 'yes', 'on']
        debug.configure(
            enabled=debug_enabled,
            log_path=self.get_debug_log_path(),
            level=self.get_debug_level(),
            console=self.debug_console_enabled(),
        )
        if debug_enabled:
            print("[DEBUG] Debug mode enabled")

    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        from pfe_app.debug import is_debug_enabled
        return is_debug_enabled()


# Example usage and testing
if __name__ == "__main__":
    config = Config()
    print(f"Global vars: {config.global_vars}")
    print(f"\nCategories ({len(config.categories)}):")
    for cat in config.categories:
        print(f"  {cat}")
