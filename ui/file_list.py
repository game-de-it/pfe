"""
File list screen for browsing ROMs in a category.
"""

import os
import pyxel
from ui.base import ScrollableList, draw_scrollbar
from ui.components import StatusBar, HelpText, CategoryTitle, Counter, Icon, SystemStatus
from ui.window import DQWindow
from typing import List
from rom_manager import ROMFile
from japanese_text import draw_japanese_text, get_japanese_text_width
from screenshot_loader import ScreenshotLoader
from theme_manager import get_theme_manager
from PIL import Image
from debug import debug_print
from ui.soft_keyboard import SoftKeyboard


class FileList(ScrollableList):
    """File list screen for browsing ROM files."""

    def __init__(self, input_handler, state_manager, config, rom_manager, persistence):
        super().__init__(items_per_page=8)  # Adjusted to 8 so the bottom row doesn't overlap with the frame
        self.input_handler = input_handler
        self.state_manager = state_manager
        self.config = config
        self.rom_manager = rom_manager
        self.persistence = persistence
        self.status_bar = StatusBar(138, 160)  # Status bar position adjustment
        self.help_text = HelpText(146, 160)  # Help text position adjustment (reserving space for 2 lines)
        self.category_title = CategoryTitle(2, 2)  # Category name on first line
        self.counter = Counter(2, 10)  # Counter on second line
        self.system_status = SystemStatus()  # System status (top right)

        self.current_category = None
        self.rom_files: List[ROMFile] = []
        self.current_subdirectory = ""  # Subdirectory path
        self.directory_stack = []  # Directory navigation history

        # Screenshot display
        self.screenshot_loader = ScreenshotLoader(config.get_screenshot_dir())
        # Load screenshot display setting from settings
        settings = self.persistence.load_settings()
        self.show_screenshots = settings.get("show_screenshots", "On") == "On"
        self.current_screenshot_rom = None  # ROM name of currently displayed screenshot
        self.screenshot_cache_bank = 1  # Image bank for screenshots
        self.screenshot_loaded = False  # Whether screenshot is loaded

        # Lookup table for RGB to Pyxel color conversion (for performance)
        self._init_color_lookup_table()

        # Sort settings
        self.sort_mode = 0  # 0: by name, 1: by date (newest first), 2: by date (oldest first)
        self.sort_modes = ["Name", "Date New", "Date Old"]

        # View mode (list or gallery)
        self.view_mode = "list"

        # Animation for gallery mode
        self.gallery_animation_offset = 0.0  # -1.0 to 1.0 (slide direction)
        self.gallery_animation_speed = 0.3  # Animation speed

        # Soft keyboard for quick jump
        self.soft_keyboard = SoftKeyboard()
        self.select_hold_frames = 0  # Number of frames SELECT button is held
        self.select_long_press_threshold = 15  # Frames threshold for long press detection (0.5 seconds)

        # Slideshow
        self.slideshow_active = False
        self.slideshow_timer = 0
        self.slideshow_interval = 90  # 3 seconds (assuming 30fps)

    def activate(self):
        """Called when screen becomes active."""
        super().activate()

        # Reload settings (to reflect changes when returning from settings screen)
        settings = self.persistence.load_settings()
        self.show_screenshots = settings.get("show_screenshots", "On") == "On"
        sort_mode_name = settings.get("sort_mode", "Name")
        if sort_mode_name in self.sort_modes:
            self.sort_mode = self.sort_modes.index(sort_mode_name)

        # Restore view_mode
        self.view_mode = settings.get("view_mode", "list")

        # Reset screenshot cache
        self.current_screenshot_rom = None
        self.screenshot_loaded = False

        # Restore subdirectory and cursor position after game exit
        launch_subdirectory = self.state_manager.get_data('launch_subdirectory')
        launch_directory_stack = self.state_manager.get_data('launch_directory_stack')
        launch_selected_index = self.state_manager.get_data('launch_selected_index', 0)
        launch_scroll_offset = self.state_manager.get_data('launch_scroll_offset', 0)
        debug_print(f"[FILE_LIST.activate] launch_subdirectory={launch_subdirectory}, launch_directory_stack={launch_directory_stack}")
        debug_print(f"[FILE_LIST.activate] launch_selected_index={launch_selected_index}, launch_scroll_offset={launch_scroll_offset}")
        if launch_subdirectory is not None:
            self.current_subdirectory = launch_subdirectory
            self.directory_stack = launch_directory_stack if launch_directory_stack else []
            self._restore_cursor_position = (launch_selected_index, launch_scroll_offset)
            debug_print(f"[FILE_LIST.activate] Restored: current_subdirectory={self.current_subdirectory}")
            # Clear after use
            self.state_manager.set_data('launch_subdirectory', None)
            self.state_manager.set_data('launch_directory_stack', None)
            self.state_manager.set_data('launch_selected_index', None)
            self.state_manager.set_data('launch_scroll_offset', None)
        else:
            self._restore_cursor_position = None

        # Load ROM files for current category
        category_name = self.state_manager.get_selected_category()
        if category_name:
            self.current_category = self.config.get_category(category_name)
            if self.current_category:
                # Reset subdirectory when entering category (only if not restoring after game exit)
                if not self.current_subdirectory and launch_subdirectory is None:
                    self.directory_stack = []

                self._load_roms()

                # Set available cores for core selection
                if self.current_category.cores:
                    self.state_manager.set_available_cores(self.current_category.cores)

        # Set help text (configured based on view_mode)
        self._update_help_text()

        # Set category title
        if self.current_category:
            self.category_title.set_title(self.current_category.name)

    def deactivate(self):
        """Called when screen becomes inactive."""
        super().deactivate()

        # Save current cursor position (only for top directory)
        if self.current_category and not self.current_subdirectory:
            self.state_manager.save_category_position(
                self.current_category.name,
                self.selected_index,
                self.scroll_offset
            )

        # Save view_mode
        settings = self.persistence.load_settings()
        settings["view_mode"] = self.view_mode
        self.persistence.save_settings(settings)

        # Stop slideshow
        self.slideshow_active = False
        self.slideshow_timer = 0

        # Reset subdirectory when leaving file list (maintained when launching game)
        if not self.state_manager.get_data('rom_to_launch'):
            self.current_subdirectory = ""
            self.directory_stack = []

    def _load_roms(self):
        """Load ROM files from current category and subdirectory."""
        if not self.current_category:
            return

        self.rom_files = self.rom_manager.scan_category(self.current_category, self.current_subdirectory)

        # Apply sort
        self._apply_sort()

        self.set_items(self.rom_files)

        # Restore cursor position after returning from game
        if hasattr(self, '_restore_cursor_position') and self._restore_cursor_position is not None:
            restore_index, restore_scroll = self._restore_cursor_position
            self.selected_index = min(restore_index, len(self.rom_files) - 1) if self.rom_files else 0
            self.scroll_offset = restore_scroll
            self._restore_cursor_position = None
            debug_print(f"[_load_roms] Restored cursor: index={self.selected_index}, scroll={self.scroll_offset}")
        # Restore saved cursor position (only for top directory)
        elif not self.current_subdirectory:
            saved_position = self.state_manager.get_category_position(self.current_category.name)
            self.selected_index = min(saved_position['index'], len(self.rom_files) - 1) if self.rom_files else 0
            self.scroll_offset = saved_position['scroll']
        else:
            # For subdirectories, start from the beginning
            self.selected_index = 0
            self.scroll_offset = 0

        self._update_scroll()

        # Update counter
        if self.rom_files:
            self.counter.set_count(self.selected_index, len(self.rom_files), "Items")

    def update(self):
        """Update file list logic."""
        if not self.active:
            return

        from input_handler import Action
        from state_manager import AppState

        # ソフトキーボード処理
        if self.soft_keyboard.is_active():
            # キーボード操作
            if self.input_handler.is_pressed(Action.UP):
                self.soft_keyboard.move_cursor(0, -1)
            elif self.input_handler.is_pressed(Action.DOWN):
                self.soft_keyboard.move_cursor(0, 1)
            elif self.input_handler.is_pressed(Action.LEFT):
                self.soft_keyboard.move_cursor(-1, 0)
            elif self.input_handler.is_pressed(Action.RIGHT):
                self.soft_keyboard.move_cursor(1, 0)
            elif self.input_handler.is_pressed(Action.A):
                # Character selection
                self.soft_keyboard.select_current_char()
                selected_char = self.soft_keyboard.get_selected_char()
                if selected_char:
                    self._jump_to_char(selected_char)
                self.soft_keyboard.deactivate()
            elif self.input_handler.is_pressed(Action.B):
                # Cancel
                self.soft_keyboard.deactivate()
            return

        # スライドショー処理（ギャラリーモードのみ）
        if self.view_mode == "gallery":
            # STARTボタンでスライドショーのON/OFF切り替え
            if self.input_handler.is_pressed(Action.START):
                self.slideshow_active = not self.slideshow_active
                self.slideshow_timer = 0
                print(f"Slideshow: {'On' if self.slideshow_active else 'Off'}")

            # スライドショー中の処理
            if self.slideshow_active:
                # 任意のキー入力で停止（STARTボタン以外）
                if (self.input_handler.is_pressed(Action.A) or
                    self.input_handler.is_pressed(Action.B) or
                    self.input_handler.is_pressed(Action.LEFT) or
                    self.input_handler.is_pressed(Action.RIGHT) or
                    self.input_handler.is_pressed(Action.UP) or
                    self.input_handler.is_pressed(Action.DOWN) or
                    self.input_handler.is_pressed(Action.X) or
                    self.input_handler.is_pressed(Action.Y)):
                    self.slideshow_active = False
                    print("Slideshow stopped by user input")
                else:
                    # Update timer
                    self.slideshow_timer += 1
                    if self.slideshow_timer >= self.slideshow_interval:
                        # Auto-advance to next ROM
                        if self.selected_index >= len(self.rom_files) - 1:
                            # Reached last ROM -> return to first
                            self.selected_index = 0
                            self._update_scroll()
                            self.counter.set_count(self.selected_index, len(self.rom_files), "ROMs")
                        else:
                            self._gallery_navigate(1)
                        self.slideshow_timer = 0

        # SELECT button long press detection
        if self.input_handler.is_held(Action.SELECT):
            self.select_hold_frames += 1
            if self.select_hold_frames >= self.select_long_press_threshold:
                # Long press detected -> show soft keyboard
                self.soft_keyboard.activate()
                self.select_hold_frames = 0
        else:
            # SELECT button released
            if 0 < self.select_hold_frames < self.select_long_press_threshold:
                # Short press -> core selection (normal behavior)
                selected = self.get_selected_item()
                if selected and not selected.is_directory and self.current_category and self.current_category.cores:
                    self.state_manager.set_selected_file(selected.path, self.selected_index)
                    from state_manager import AppState
                    self.state_manager.change_state(AppState.CORE_SELECT)
            self.select_hold_frames = 0

        # Check if we have a core override (from core selection)
        core_override = self.state_manager.get_temp_core_override()
        if core_override:
            # Launch ROM with selected core
            selected_file_path = self.state_manager.get_selected_file()
            if selected_file_path and self.rom_files:
                # Find ROM by path
                rom_to_launch = None
                for rom in self.rom_files:
                    if rom.path == selected_file_path:
                        rom_to_launch = rom
                        break

                if rom_to_launch:
                    self._launch_rom(rom_to_launch)

            return

        # View mode toggle (X button)
        if self.input_handler.is_pressed(Action.X):
            if self.view_mode == "list":
                self.view_mode = "gallery"
                print("View mode: Gallery")
            else:
                self.view_mode = "list"
                print("View mode: List")
                # Stop slideshow when returning to list mode
                if self.slideshow_active:
                    self.slideshow_active = False
                    self.slideshow_timer = 0
            # Update help text
            self._update_help_text()

        # Navigation (behavior varies based on view_mode)
        if self.view_mode == "list":
            # List mode: normal scrolling
            if self.input_handler.is_pressed_with_repeat(Action.UP):
                self.scroll_up()
                self.counter.set_count(self.selected_index, len(self.rom_files), "ROMs")
            elif self.input_handler.is_pressed_with_repeat(Action.DOWN):
                self.scroll_down()
                self.counter.set_count(self.selected_index, len(self.rom_files), "ROMs")
            elif self.input_handler.is_pressed(Action.L):
                self.jump_to_start()
                self.counter.set_count(self.selected_index, len(self.rom_files), "ROMs")
            elif self.input_handler.is_pressed(Action.R):
                self.jump_to_end()
                self.counter.set_count(self.selected_index, len(self.rom_files), "ROMs")

            # Page navigation (left/right arrows)
            if self.input_handler.is_pressed(Action.LEFT):
                self.page_up()
                self.counter.set_count(self.selected_index, len(self.rom_files), "ROMs")
            elif self.input_handler.is_pressed(Action.RIGHT):
                self.page_down()
                self.counter.set_count(self.selected_index, len(self.rom_files), "ROMs")
        else:
            # Gallery mode: move one at a time or 5 at a time (key repeat enabled)
            if self.input_handler.is_pressed_with_repeat(Action.LEFT):
                self._gallery_navigate(-1)  # Left for previous
            elif self.input_handler.is_pressed_with_repeat(Action.RIGHT):
                self._gallery_navigate(1)  # Right for next
            elif self.input_handler.is_pressed_with_repeat(Action.UP):
                self._gallery_navigate(-5)  # Up for 5 previous
            elif self.input_handler.is_pressed_with_repeat(Action.DOWN):
                self._gallery_navigate(5)  # Down for 5 next
            elif self.input_handler.is_pressed(Action.L):
                self.jump_to_start()
                self.counter.set_count(self.selected_index, len(self.rom_files), "ROMs")
            elif self.input_handler.is_pressed(Action.R):
                self.jump_to_end()
                self.counter.set_count(self.selected_index, len(self.rom_files), "ROMs")

        # Selection - Open directory or Launch ROM
        if self.input_handler.is_pressed(Action.A):
            selected = self.get_selected_item()
            if selected:
                if selected.is_directory:
                    # Navigate into subdirectory
                    import os
                    self.directory_stack.append(self.current_subdirectory)
                    if self.current_subdirectory:
                        self.current_subdirectory = os.path.join(self.current_subdirectory, selected.name)
                    else:
                        self.current_subdirectory = selected.name
                    self._load_roms()
                else:
                    # Launch ROM
                    self.state_manager.set_selected_file(selected.path, self.selected_index)
                    self._launch_rom(selected)


        # Toggle favorite (list mode only)
        if self.view_mode == "list" and self.input_handler.is_pressed(Action.START):
            selected = self.get_selected_item()
            if selected and self.current_category:
                if self.persistence.is_favorite(selected.path):
                    self.persistence.remove_from_favorites(selected.path)
                    print(f"Removed from favorites: {selected.name}")
                else:
                    self.persistence.add_to_favorites(selected.path, self.current_category.name)
                    print(f"Added to favorites: {selected.name}")

        # Toggle screenshot (Y button, list mode only)
        if self.view_mode == "list" and self.input_handler.is_pressed(Action.Y):
            self.show_screenshots = not self.show_screenshots
            # Save settings to sync with Settings screen
            settings = self.persistence.load_settings()
            screenshot_value = "On" if self.show_screenshots else "Off"
            settings["show_screenshots"] = screenshot_value
            self.persistence.save_settings(settings)
            print(f"Screenshots: {screenshot_value}")
            print(f"Settings saved: show_screenshots = {screenshot_value}")

        # Back to parent directory or main menu
        if self.input_handler.is_pressed(Action.B):
            import os
            if self.current_subdirectory:
                # Go back to parent directory
                if self.directory_stack:
                    self.current_subdirectory = self.directory_stack.pop()
                else:
                    self.current_subdirectory = ""
                self._load_roms()
            else:
                # Go back to main menu
                self.state_manager.go_back()

    def _update_help_text(self):
        """Update help text (based on view_mode)."""
        if self.view_mode == "gallery":
            self.help_text.set_controls([
                ("L/R", "Next"),
                ("A", "Open"),
                ("START", "Slideshow"),
                ("B", "Back")
            ])
        else:
            self.help_text.set_controls([
                ("Up/Down", "Select"),
                ("A", "Open"),
                ("Y", "Screenshot"),
                ("B", "Back")
            ])

    def _jump_to_char(self, char: str):
        """
        Jump to ROM starting with the specified character.

        Args:
            char: Character to jump to.
        """
        if not self.rom_files:
            return

        char_upper = char.upper()
        char_lower = char.lower()

        # Search from current position
        for i in range(len(self.rom_files)):
            rom = self.rom_files[i]
            if rom.name and len(rom.name) > 0:
                first_char = rom.name[0]
                if first_char == char_upper or first_char == char_lower:
                    # Found
                    self.selected_index = i
                    self._update_scroll()
                    self.counter.set_count(self.selected_index, len(self.rom_files), "ROMs")
                    print(f"Jumped to: {rom.name}")
                    return

        print(f"No ROM starting with '{char}' found")

    def _gallery_navigate(self, delta: int):
        """
        Navigation in gallery mode (with animation).

        Args:
            delta: Movement amount (positive=next, negative=previous).
        """
        if not self.rom_files:
            return

        # Calculate new index
        new_index = self.selected_index + delta
        new_index = max(0, min(new_index, len(self.rom_files) - 1))

        if new_index != self.selected_index:
            # Start animation (set movement direction)
            # Next (delta > 0): slide from right to left (offset = 1.0 -> 0)
            # Previous (delta < 0): slide from left to right (offset = -1.0 -> 0)
            self.gallery_animation_offset = 1.0 if delta > 0 else -1.0

            # Update index
            self.selected_index = new_index
            self._update_scroll()
            self.counter.set_count(self.selected_index, len(self.rom_files), "ROMs")

    def _apply_sort(self):
        """Apply sort."""
        import os

        # Separate directories and files
        directories = [f for f in self.rom_files if f.is_directory]
        files = [f for f in self.rom_files if not f.is_directory]

        # Sort files
        if self.sort_mode == 0:
            # By name (alphabetical order)
            files.sort(key=lambda x: x.name.lower())
        elif self.sort_mode == 1:
            # By date (newest first)
            files.sort(key=lambda x: os.path.getmtime(x.path) if os.path.exists(x.path) else 0, reverse=True)
        elif self.sort_mode == 2:
            # By date (oldest first)
            files.sort(key=lambda x: os.path.getmtime(x.path) if os.path.exists(x.path) else 0)

        # Directories are always sorted by name
        directories.sort(key=lambda x: x.name.lower())

        # Directories first, then files
        self.rom_files = directories + files

    def _draw_window_screenshot(self, rom_path: str):
        """
        Display screenshot in background (cached for performance, maintains aspect ratio).

        Args:
            rom_path: Full path to the ROM file.
        """
        # Display area size
        area_width = pyxel.width - 8
        area_height = 118
        area_x = 4
        area_y = 20

        # Only load image when selected ROM changes
        if self.current_screenshot_rom != rom_path:
            self.current_screenshot_rom = rom_path
            self.screenshot_loaded = False

            try:
                # Search for screenshot file
                screenshot_path = self._find_screenshot_file(rom_path)
                if not screenshot_path:
                    return

                # 画像を読み込み
                img = Image.open(screenshot_path)
                orig_width, orig_height = img.size

                # アスペクト比を維持してフィットするサイズを計算
                scale_w = area_width / orig_width
                scale_h = area_height / orig_height
                scale = min(scale_w, scale_h)

                new_width = int(orig_width * scale)
                new_height = int(orig_height * scale)

                # リサイズ
                img = img.resize((new_width, new_height), Image.Resampling.BILINEAR)
                img = img.convert('RGB')

                # Speed up pixel access
                pixels = img.load()

                # Save to Pyxel image bank (only once)
                pyxel_img = pyxel.image(self.screenshot_cache_bank)
                for y in range(new_height):
                    for x in range(new_width):
                        r, g, b = pixels[x, y]
                        # Convert RGB to nearest Pyxel color (using LUT)
                        color = self._rgb_to_pyxel_color(r, g, b)
                        pyxel_img.pset(x, y, color)

                self.screenshot_loaded = True
                self._screenshot_width = new_width
                self._screenshot_height = new_height
                # 中央配置用オフセット
                self._screenshot_offset_x = (area_width - new_width) // 2
                self._screenshot_offset_y = (area_height - new_height) // 2

            except Exception as e:
                # Mark as failed to load on error
                pass

        # Fast drawing from image bank
        if self.screenshot_loaded:
            ss_w = getattr(self, '_screenshot_width', area_width)
            ss_h = getattr(self, '_screenshot_height', area_height)
            offset_x = area_x + getattr(self, '_screenshot_offset_x', 0)
            offset_y = area_y + getattr(self, '_screenshot_offset_y', 0)
            pyxel.blt(offset_x, offset_y, self.screenshot_cache_bank, 0, 0, ss_w, ss_h)

    def _find_screenshot_file(self, rom_path: str) -> str:
        """
        Search for screenshot file (tries multiple patterns).

        Args:
            rom_path: Full path to the ROM file.

        Returns:
            Path to the screenshot file, or None if not found.
        """
        import re

        screenshot_base_dir = self.screenshot_loader.screenshot_dir
        extensions = ['.png', '.jpg', '.jpeg']

        # Get parent directory name and file name of ROM file
        # Example: /roms/psx/Arc The Lad/SCPS-10008.bin
        #     -> Parent directory: Arc The Lad
        #     -> File name: SCPS-10008
        #     -> Screenshot: assets/screenshots/Arc The Lad/SCPS-10008.png
        parent_dir = os.path.basename(os.path.dirname(rom_path))
        rom_name = os.path.basename(rom_path)

        # Get ROM name without extension (use extensions from current category's pfe.cfg -EXT= setting)
        rom_name_without_ext = rom_name
        if self.current_category and self.current_category.extensions:
            for ext in self.current_category.extensions:
                # Add dot prefix if not present
                ext_with_dot = ext if ext.startswith('.') else '.' + ext
                if rom_name.lower().endswith(ext_with_dot.lower()):
                    rom_name_without_ext = rom_name[:-len(ext_with_dot)]
                    break

        # Screenshot search directory
        # Example: assets/screenshots/Arc The Lad/SCPS-10008.png
        dir_screenshot_dir = os.path.join(screenshot_base_dir, parent_dir)

        # Debug log
        debug_print(f"[Screenshot] ROM path: {rom_path}")
        debug_print(f"[Screenshot] Parent dir: {parent_dir}")
        debug_print(f"[Screenshot] ROM name: {rom_name_without_ext}")
        debug_print(f"[Screenshot] Directory: {dir_screenshot_dir}")

        # List of patterns to try
        name_patterns = []

        # 1. Exact match
        name_patterns.append(rom_name_without_ext)

        # 2. Remove [...] (version info, etc.)
        name_without_brackets = re.sub(r'\[.*?\]', '', rom_name_without_ext)
        name_without_brackets = name_without_brackets.strip()
        if name_without_brackets != rom_name_without_ext:
            name_patterns.append(name_without_brackets)

        # 3. Remove (...) (region info, etc.)
        name_without_parens = re.sub(r'\(.*?\)', '', rom_name_without_ext)
        name_without_parens = name_without_parens.strip()
        if name_without_parens != rom_name_without_ext:
            name_patterns.append(name_without_parens)

        # 4. Remove both [...] and (...)
        name_clean = re.sub(r'[\[\(].*?[\]\)]', '', rom_name_without_ext)
        name_clean = name_clean.strip()
        if name_clean and name_clean not in name_patterns:
            name_patterns.append(name_clean)

        # 5. Normalize multiple spaces to one
        for pattern in name_patterns[:]:  # Iterate over a copy
            normalized = re.sub(r'\s+', ' ', pattern).strip()
            if normalized not in name_patterns:
                name_patterns.append(normalized)

        # Search with each pattern
        for pattern in name_patterns:
            if not pattern:  # Skip empty strings
                continue
            for ext in extensions:
                path = os.path.join(dir_screenshot_dir, pattern + ext)
                debug_print(f"[Screenshot] Trying: {path}")
                if os.path.exists(path):
                    debug_print(f"[Screenshot] Found: {path}")
                    return path

        debug_print(f"[Screenshot] Not found for: {rom_path}")
        return None

    def _init_color_lookup_table(self):
        """Initialize lookup table for RGB to Pyxel color conversion (for performance)."""
        # Pyxel color palette
        palette = [
            (0, 0, 0), (43, 51, 95), (126, 32, 114), (25, 149, 156),
            (139, 72, 82), (57, 92, 152), (169, 193, 255), (238, 238, 238),
            (212, 24, 108), (211, 132, 65), (233, 195, 91), (112, 198, 169),
            (118, 150, 222), (163, 163, 163), (255, 151, 152), (237, 199, 176),
        ]

        # 32x32x32 lookup table (quantize RGB from 8 to 5 bits)
        self.color_lut = {}
        for r5 in range(32):
            for g5 in range(32):
                for b5 in range(32):
                    # Convert 5-bit value to 8-bit value
                    r = (r5 * 255) // 31
                    g = (g5 * 255) // 31
                    b = (b5 * 255) // 31

                    # Find nearest Pyxel color
                    min_distance = float('inf')
                    nearest_color = 0

                    for i, (pr, pg, pb) in enumerate(palette):
                        distance = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
                        if distance < min_distance:
                            min_distance = distance
                            nearest_color = i

                    # Save to LUT
                    self.color_lut[(r5, g5, b5)] = nearest_color

    def _rgb_to_pyxel_color(self, r: int, g: int, b: int) -> int:
        """Convert RGB to nearest Pyxel color (using LUT for performance)."""
        # Quantize from 8-bit to 5-bit
        r5 = (r * 31) // 255
        g5 = (g * 31) // 255
        b5 = (b * 31) // 255

        return self.color_lut.get((r5, g5, b5), 0)

    def _draw_list_view(self):
        """Draw list view."""
        # Get theme colors
        theme = get_theme_manager()
        bg_color = theme.get_color("background")
        text_color = theme.get_color("text")
        text_selected_color = theme.get_color("text_selected")
        scrollbar_color = theme.get_color("scrollbar")

        start_y = 20  # 境界線の下から開始
        line_height = 13
        visible = self.get_visible_items()
        visible_start, _ = self.get_visible_range()

        for i, rom_file in enumerate(visible):
            y = start_y + i * line_height
            index = visible_start + i

            # Draw ROM name or directory (up to 38 half-width characters displayable)
            if rom_file.is_directory:
                # Directory indicator
                display_name = "[" + rom_file.name + "]"
                if len(display_name) > 38:
                    display_name = "[" + rom_file.name[:34] + "...]"
            else:
                display_name = self.rom_manager.get_rom_display_name(rom_file, max_length=38, max_width=155)

                # Add favorite indicator
                if self.persistence.is_favorite(rom_file.path):
                    display_name = display_name + " *"

            # Darken text background slightly to improve visibility
            # Draw background color box
            text_bg_width = len(display_name) * 4 + 2
            pyxel.rect(6, y, text_bg_width, 8, bg_color)

            color = text_selected_color if index == self.selected_index else text_color
            draw_japanese_text(6, y, display_name, color)

        # Draw scrollbar if needed
        if len(self.rom_files) > self.items_per_page:
            scrollbar_x = pyxel.width - 4
            draw_scrollbar(scrollbar_x, start_y, self.items_per_page * line_height,
                          len(self.rom_files), self.items_per_page, self.scroll_offset, scrollbar_color)

    def _draw_gallery_view(self):
        """Draw gallery view (museum-style, borderless fullscreen display, maintains aspect ratio)."""
        if not self.rom_files:
            return

        # Update animation
        if abs(self.gallery_animation_offset) > 0.01:
            # Gradually approach 0 (easing)
            self.gallery_animation_offset *= (1.0 - self.gallery_animation_speed)
        else:
            self.gallery_animation_offset = 0.0

        # Get theme colors
        theme = get_theme_manager()
        bg_color = theme.get_color("background")
        text_color = theme.get_color("text")
        text_selected_color = theme.get_color("text_selected")

        # Get selected ROM
        selected = self.get_selected_item()
        if not selected:
            return

        # Apply animation offset (horizontal slide)
        anim_offset_x = int(self.gallery_animation_offset * pyxel.width)

        # Screenshot display area (maximum size without border)
        # Available area: from below border line y=18, top y=20 to bottom y=138
        # Image size: (screen width-8)x106 (reserving 12px for title)
        area_width = pyxel.width - 8
        area_height = 106
        area_x = 4
        area_y = 20

        # Draw screenshot (always ON in gallery mode)
        if self.current_category and not selected.is_directory:
            # Load screenshot (using cache)
            if self.current_screenshot_rom != selected.path:
                self.current_screenshot_rom = selected.path
                self.screenshot_loaded = False

                try:
                    screenshot_path = self._find_screenshot_file(selected.path)
                    if screenshot_path:
                        # Load image
                        img = Image.open(screenshot_path)
                        orig_width, orig_height = img.size

                        # Calculate size that fits while maintaining aspect ratio
                        scale_w = area_width / orig_width
                        scale_h = area_height / orig_height
                        scale = min(scale_w, scale_h)

                        new_width = int(orig_width * scale)
                        new_height = int(orig_height * scale)

                        # Resize
                        img = img.resize((new_width, new_height), Image.Resampling.BILINEAR)
                        img = img.convert('RGB')
                        pixels = img.load()

                        # Save to Pyxel image bank
                        pyxel_img = pyxel.image(self.screenshot_cache_bank)
                        for y in range(new_height):
                            for x in range(new_width):
                                r, g, b = pixels[x, y]
                                color = self._rgb_to_pyxel_color(r, g, b)
                                pyxel_img.pset(x, y, color)

                        self.screenshot_loaded = True
                        self._gallery_ss_width = new_width
                        self._gallery_ss_height = new_height
                        # Offset for center alignment
                        self._gallery_ss_offset_x = (area_width - new_width) // 2
                        self._gallery_ss_offset_y = (area_height - new_height) // 2
                except:
                    pass

            # Draw screenshot
            if self.screenshot_loaded:
                ss_w = getattr(self, '_gallery_ss_width', area_width)
                ss_h = getattr(self, '_gallery_ss_height', area_height)
                ss_offset_x = getattr(self, '_gallery_ss_offset_x', 0)
                ss_offset_y = getattr(self, '_gallery_ss_offset_y', 0)
                draw_x = area_x + ss_offset_x + anim_offset_x
                draw_y = area_y + ss_offset_y
                pyxel.blt(draw_x, draw_y, self.screenshot_cache_bank, 0, 0, ss_w, ss_h)
            else:
                # Placeholder (gray frame)
                placeholder_x = area_x + anim_offset_x
                pyxel.rect(placeholder_x, area_y, area_width, area_height, 5)
                no_img_text = "No Image"
                text_x = placeholder_x + (area_width // 2) - len(no_img_text) * 2
                text_y = area_y + (area_height // 2) - 4
                pyxel.text(text_x, text_y, no_img_text, text_color)
        else:
            # For directories
            placeholder_x = area_x + anim_offset_x
            pyxel.rect(placeholder_x, area_y, area_width, area_height, 5)
            if selected.is_directory:
                folder_text = "[Folder]"
                text_x = placeholder_x + (area_width // 2) - len(folder_text) * 2
                text_y = area_y + (area_height // 2) - 4
                pyxel.text(text_x, text_y, folder_text, text_color)

        # Title display (below screenshot)
        title_y = area_y + area_height + 4

        # タイトルテキスト
        if selected.is_directory:
            display_name = "[" + selected.name + "]"
        else:
            display_name = self.rom_manager.get_rom_display_name(selected, max_length=38, max_width=155)

            # Favorite mark
            if self.persistence.is_favorite(selected.path):
                display_name = display_name + " *"

        # Draw title center-aligned (Japanese text supported)
        title_width = get_japanese_text_width(display_name)
        title_x = pyxel.width // 2 - (title_width // 2) + anim_offset_x

        # Title background
        pyxel.rect(title_x - 2, title_y, title_width + 4, 8, bg_color)

        # タイトルテキスト
        draw_japanese_text(title_x, title_y, display_name, text_selected_color)

    def _launch_rom(self, rom_file: ROMFile):
        """
        Launch selected ROM.
        This will be handled by the launcher module.
        """
        # Set data for launcher
        self.state_manager.set_data('rom_to_launch', rom_file)
        self.state_manager.set_data('launch_category', self.current_category)
        # Save subdirectory info (to restore after game exit)
        self.state_manager.set_data('launch_subdirectory', self.current_subdirectory)
        self.state_manager.set_data('launch_directory_stack', self.directory_stack.copy())

    def draw(self):
        """Draw file list screen."""
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

        # Draw category title (上部1行目)
        self.category_title.draw()

        # Draw system status (top right)
        self.system_status.draw()

        # Draw counter (上部2行目)
        if self.rom_files:
            self.counter.draw()

        # Draw border line below counter
        pyxel.line(2, 18, pyxel.width - 3, 18, border_color)

        # Draw main window frame (borderless for both modes)

        if not self.rom_files:
            # Empty state (positioned at screen center)
            msg1 = "No ROMs found"
            msg2 = "Check directory path"
            center_x = pyxel.width // 2
            pyxel.text(center_x - len(msg1) * 2, 70, msg1, text_color)
            pyxel.text(center_x - len(msg2) * 2, 80, msg2, text_color)
        else:
            # Draw based on view_mode
            if self.view_mode == "gallery":
                # Gallery mode: always show screenshots
                self._draw_gallery_view()
            else:
                # List mode: follow show_screenshots setting
                if self.show_screenshots and self.current_category:
                    selected = self.get_selected_item()
                    if selected and not selected.is_directory:
                        self._draw_window_screenshot(selected.path)

                self._draw_list_view()

        # Status bar
        if self.current_category:
            # Left: view mode/screenshot state, Right: total count
            if self.view_mode == "gallery":
                if self.slideshow_active:
                    left_text = "Slideshow"
                else:
                    left_text = "Gallery"
            else:
                screenshot_state = "On" if self.show_screenshots else "Off"
                left_text = f"SS:{screenshot_state}"

            self.status_bar.set_text(
                left=left_text,
                center="",
                right=f"{len(self.rom_files)}"
            )
        self.status_bar.draw()

        # Help text
        self.help_text.draw()

        # Soft keyboard (draw on top)
        if self.soft_keyboard.is_active():
            self.soft_keyboard.draw()
