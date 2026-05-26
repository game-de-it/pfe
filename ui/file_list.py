"""
File list screen for browsing ROMs in a category.
"""

import os
import pyxel
from ui.base import ScrollableList, draw_scrollbar
from ui.components import StatusBar, HelpText, CategoryTitle, Counter, Icon, SystemStatus
from ui.window import DQWindow
from typing import List
from pfe_app.rom_manager import ROMFile
from pfe_app.japanese_text import (
    draw_japanese_text,
    draw_japanese_text_small,
    get_japanese_text_width,
    get_japanese_text_width_small,
)
from pfe_app.screenshot_loader import ScreenshotLoader
from pfe_app.theme_manager import get_theme_manager
from pfe_app.debug import debug_print, trace
from pfe_app.image_cache import ImageCache
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
        self.image_cache = ImageCache(memory_limit=64)
        self._screenshot_path_cache = {}
        # Load screenshot display setting from settings
        settings = self.persistence.load_settings()
        self.show_screenshots = settings.get("show_screenshots", "On") == "On"

        # Sort settings
        self.sort_mode = 0  # 0: by name, 1: by date (newest first), 2: by date (oldest first)
        self.sort_modes = ["Name", "Date New", "Date Old"]

        # View mode (list or gallery)
        self.view_mode = "list"

        # Animation for gallery mode
        self.gallery_animation_offset = 0.0  # -1.0 to 1.0 (slide direction)
        self.gallery_animation_direction = 0
        self.gallery_animation_frame = 0
        self.gallery_animation_duration = max(
            4,
            min(
                30,
                self._coerce_non_negative_int(
                    getattr(config, "global_vars", {}).get("GALLERY_SCROLL_FRAMES", 8),
                    8,
                ),
            ),
        )
        self.gallery_previous_index = None
        self.gallery_defer_image_load = (
            str(getattr(config, "global_vars", {}).get("GALLERY_DEFER_IMAGE_LOAD", "true")).strip().lower()
            in ("1", "true", "yes", "on")
        )
        self.gallery_post_scroll_load_delay = max(
            0,
            min(
                30,
                self._coerce_non_negative_int(
                    getattr(config, "global_vars", {}).get("GALLERY_POST_SCROLL_LOAD_DELAY", 3),
                    3,
                ),
            ),
        )
        self.gallery_post_scroll_load_cooldown = 0
        self.gallery_pending_deferred_image_load = False
        self.gallery_prefetch_radius = 2
        self.gallery_prefetch_enabled = (
            str(getattr(config, "global_vars", {}).get("GALLERY_PREFETCH", "false")).strip().lower()
            in ("1", "true", "yes", "on")
        )
        self._gallery_prefetch_queue: list[tuple[str, int, int]] = []
        self._gallery_prefetched_keys: set[tuple[str, int, int]] = set()
        self._gallery_prefetch_signature = None

        # Soft keyboard for quick jump
        self.soft_keyboard = SoftKeyboard()
        self.select_hold_frames = 0  # Number of frames SELECT button is held
        self.select_long_press_threshold = 15  # Frames threshold for long press detection (0.5 seconds)

        # Slideshow
        self.slideshow_active = False
        self.slideshow_timer = 0
        self.slideshow_interval = 90  # 3 seconds (assuming 30fps)
        self._restore_cursor_position = None

    @staticmethod
    def _coerce_non_negative_int(value, default: int = 0) -> int:
        """Return a safe non-negative integer for restored cursor state."""
        try:
            number = int(value)
        except (TypeError, ValueError):
            return default
        return max(0, number)

    def _clamp_item_index(self, value, item_count: int) -> int:
        if item_count <= 0:
            return 0
        index = self._coerce_non_negative_int(value)
        return min(index, item_count - 1)

    def _gallery_layout(self) -> tuple[int, int, int, int, int, int, int]:
        """Return geometry used by ROM gallery drawing and prefetching."""
        area_width = max(1, pyxel.width - 8)
        area_x = 4
        area_y = 22
        title_height = 8
        title_margin = 4
        title_bottom_gap = 3
        bottom_limit = max(
            area_y + 32,
            self.status_bar.y - title_height - title_margin - title_bottom_gap,
        )
        area_height = max(24, bottom_limit - area_y)
        return area_x, area_y, area_width, area_height, title_height, title_margin, title_bottom_gap

    def _fit_small_text(self, text: str, max_width: int) -> str:
        """Fit compact text to a pixel width."""
        if get_japanese_text_width_small(text) <= max_width:
            return text
        if max_width <= get_japanese_text_width_small(".."):
            return ""
        trimmed = text
        while trimmed and get_japanese_text_width_small(trimmed + "..") > max_width:
            trimmed = trimmed[:-1]
        return trimmed + ".." if trimmed else ""

    @staticmethod
    def _has_non_ascii(text: str) -> bool:
        return any(ord(char) >= 128 for char in text)

    def _gallery_title_width(self, text: str) -> int:
        if self._has_non_ascii(text):
            return get_japanese_text_width(text)
        return get_japanese_text_width_small(text)

    def _fit_gallery_title(self, text: str, max_width: int) -> str:
        """Fit ROM title while keeping Japanese text readable."""
        if self._gallery_title_width(text) <= max_width:
            return text
        if max_width <= self._gallery_title_width(".."):
            return ""
        trimmed = text
        while trimmed and self._gallery_title_width(trimmed + "..") > max_width:
            trimmed = trimmed[:-1]
        return trimmed + ".." if trimmed else ""

    def _draw_gallery_title_text(self, x: int, y: int, text: str, color: int):
        if self._has_non_ascii(text):
            draw_japanese_text(x, y, text, color)
        else:
            draw_japanese_text_small(x, y + 1, text, color)

    def _draw_gallery_header(self):
        """Draw a compact category title for the ROM gallery screen."""
        if not self.current_category:
            return

        theme = get_theme_manager()
        text_selected_color = theme.get_color("text_selected")
        # Draw on the second header row so it never collides with system status.
        max_width = max(16, pyxel.width - 4)
        title = self._fit_gallery_title(self.current_category.name, max_width)
        self._draw_gallery_title_text(2, 10, title, text_selected_color)

    def _reset_gallery_prefetch(self, clear_seen: bool = True):
        """Reset pending gallery screenshot preloads."""
        self._gallery_prefetch_queue = []
        self._gallery_prefetch_signature = None
        if clear_seen:
            self._gallery_prefetched_keys.clear()

    def _reset_gallery_deferred_load(self):
        """Clear deferred image-load state after navigation or list changes."""
        self.gallery_post_scroll_load_cooldown = 0
        self.gallery_pending_deferred_image_load = False

    def _queue_gallery_prefetch(self):
        """Queue the selected and nearby gallery screenshots for idle preloading."""
        if not self.rom_files or not self.current_category:
            return

        _, _, area_width, area_height, _, _, _ = self._gallery_layout()
        signature = (
            self.current_category.name,
            self.current_subdirectory,
            self.selected_index,
            len(self.rom_files),
            area_width,
            area_height,
        )
        if signature == self._gallery_prefetch_signature:
            return

        self._gallery_prefetch_signature = signature
        self._gallery_prefetch_queue = []
        offsets = [0]
        for step in range(1, self.gallery_prefetch_radius + 1):
            offsets.extend((step, -step))

        queued = set()
        for offset in offsets:
            index = self.selected_index + offset
            if index < 0 or index >= len(self.rom_files):
                continue
            rom = self.rom_files[index]
            if rom.is_directory:
                continue
            screenshot_path = self._get_screenshot_path(rom.path)
            if not screenshot_path:
                continue
            key = (screenshot_path, area_width, area_height)
            if key in self._gallery_prefetched_keys or key in queued:
                continue
            self._gallery_prefetch_queue.append(key)
            queued.add(key)

    def _update_gallery_prefetch(self):
        """Preload one queued gallery screenshot while the UI is idle."""
        if not self.gallery_prefetch_enabled:
            return
        if self.view_mode != "gallery" or self.gallery_animation_direction != 0:
            return

        self._queue_gallery_prefetch()
        if not self._gallery_prefetch_queue:
            return

        screenshot_path, area_width, area_height = self._gallery_prefetch_queue.pop(0)
        self._gallery_prefetched_keys.add((screenshot_path, area_width, area_height))
        try:
            self.image_cache.get_fit(screenshot_path, area_width, area_height, upscale=True)
        except Exception as e:
            debug_print(f"[Gallery] Prefetch failed: {e}")

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

        # Restore subdirectory and cursor position after game exit
        launch_subdirectory = self.state_manager.get_data('launch_subdirectory')
        launch_directory_stack = self.state_manager.get_data('launch_directory_stack')
        launch_selected_index = self._coerce_non_negative_int(
            self.state_manager.get_data('launch_selected_index', 0)
        )
        launch_scroll_offset = self._coerce_non_negative_int(
            self.state_manager.get_data('launch_scroll_offset', 0)
        )
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
        self._reset_gallery_prefetch()
        self._reset_gallery_deferred_load()

        # Restore cursor position after returning from game
        if hasattr(self, '_restore_cursor_position') and self._restore_cursor_position is not None:
            restore_index, restore_scroll = self._restore_cursor_position
            self.selected_index = self._clamp_item_index(restore_index, len(self.rom_files))
            self.scroll_offset = self._coerce_non_negative_int(restore_scroll)
            self._restore_cursor_position = None
            debug_print(f"[_load_roms] Restored cursor: index={self.selected_index}, scroll={self.scroll_offset}")
        # Restore saved cursor position (only for top directory)
        elif not self.current_subdirectory:
            saved_position = self.state_manager.get_category_position(self.current_category.name)
            self.selected_index = self._clamp_item_index(saved_position.get('index'), len(self.rom_files))
            self.scroll_offset = self._coerce_non_negative_int(saved_position.get('scroll'))
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

        from pfe_app.input_handler import Action
        from pfe_app.state_manager import AppState

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
                    from pfe_app.state_manager import AppState
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
                self._reset_gallery_prefetch(clear_seen=False)
                self._reset_gallery_deferred_load()
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

        if self.view_mode == "gallery":
            self._update_gallery_animation()
            has_input = any(self.input_handler.is_held(action) for action in Action)
            if (
                not has_input
                and self.gallery_post_scroll_load_cooldown <= 0
                and not self.gallery_pending_deferred_image_load
            ):
                self._update_gallery_prefetch()

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
            self.gallery_previous_index = self.selected_index
            self.gallery_animation_direction = 1 if delta > 0 else -1
            self.gallery_animation_frame = 0
            self.gallery_animation_offset = float(self.gallery_animation_direction)
            self._reset_gallery_deferred_load()

            # Update index
            self.selected_index = new_index
            self._update_scroll()
            self.counter.set_count(self.selected_index, len(self.rom_files), "ROMs")

    def _update_gallery_animation(self):
        """Update gallery slide animation with a smooth stop."""
        if self.gallery_animation_direction == 0:
            self.gallery_animation_offset = 0.0
            self.gallery_previous_index = None
            if self.gallery_post_scroll_load_cooldown > 0:
                self.gallery_post_scroll_load_cooldown -= 1
            return

        self.gallery_animation_frame += 1
        t = min(1.0, self.gallery_animation_frame / self.gallery_animation_duration)
        remaining = 1.0 - t
        self.gallery_animation_offset = self.gallery_animation_direction * (remaining ** 3)
        screen_width = pyxel.width or 160

        if t >= 1.0 or abs(self.gallery_animation_offset * screen_width) < 0.5:
            self.gallery_animation_direction = 0
            self.gallery_animation_frame = 0
            self.gallery_animation_offset = 0.0
            self.gallery_previous_index = None
            if self.gallery_defer_image_load:
                self.gallery_post_scroll_load_cooldown = self.gallery_post_scroll_load_delay
                self.gallery_pending_deferred_image_load = True

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

        screenshot_path = self._get_screenshot_path(rom_path)
        if not screenshot_path:
            return

        try:
            image = self.image_cache.get_fit(screenshot_path, area_width, area_height, upscale=True)
        except Exception as e:
            debug_print(f"[Screenshot] Failed to cache image: {e}")
            return
        if image is None:
            return

        offset_x = area_x + (area_width - image.width) // 2
        offset_y = area_y + (area_height - image.height) // 2
        pyxel.blt(offset_x, offset_y, image.image, 0, 0, image.width, image.height)

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

        # Detailed search tracing is useful, but too noisy for normal DEBUG logs.
        trace(f"[Screenshot] ROM path: {rom_path}")
        trace(f"[Screenshot] Parent dir: {parent_dir}")
        trace(f"[Screenshot] ROM name: {rom_name_without_ext}")
        trace(f"[Screenshot] Directory: {dir_screenshot_dir}")

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
                trace(f"[Screenshot] Trying: {path}")
                if os.path.exists(path):
                    debug_print(f"[Screenshot] Found: {path}")
                    return path

        trace(f"[Screenshot] Not found for: {rom_path}")
        return None

    def _get_screenshot_path(self, rom_path: str) -> str | None:
        """Return a cached screenshot path lookup for a ROM path."""
        cached = self._screenshot_path_cache.get(rom_path)
        if cached:
            if os.path.exists(cached):
                return cached
            self._screenshot_path_cache.pop(rom_path, None)

        screenshot_path = self._find_screenshot_file(rom_path)
        if screenshot_path:
            self._screenshot_path_cache[rom_path] = screenshot_path
        return screenshot_path

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

    def _gallery_display_name(self, rom_file: ROMFile) -> str:
        if rom_file.is_directory:
            return "[" + rom_file.name + "]"

        display_name = self.rom_manager.get_rom_display_name(rom_file, max_length=38, max_width=155)
        if self.persistence.is_favorite(rom_file.path):
            display_name = display_name + " *"
        return display_name

    def _get_gallery_image(
        self,
        rom_file: ROMFile,
        area_width: int,
        area_height: int,
        allow_process: bool,
    ) -> tuple[object, bool]:
        if not self.current_category or rom_file.is_directory:
            return None, False

        screenshot_path = self._get_screenshot_path(rom_file.path)
        if not screenshot_path:
            return None, False

        try:
            if allow_process:
                return self.image_cache.get_fit(screenshot_path, area_width, area_height, upscale=True), True
            return self.image_cache.get_fit_cached(screenshot_path, area_width, area_height, upscale=True), True
        except Exception as e:
            debug_print(f"[Gallery] Failed to cache image: {e}")
            return None, True

    def _draw_gallery_item(
        self,
        rom_file: ROMFile,
        offset_x: int,
        allow_process: bool,
        layout: tuple[int, int, int, int, int, int, int],
        bg_color: int,
        text_color: int,
        text_selected_color: int,
    ) -> bool:
        area_x, area_y, area_width, area_height, title_height, title_margin, title_bottom_gap = layout

        image, has_screenshot = self._get_gallery_image(rom_file, area_width, area_height, allow_process)
        if image is not None:
            draw_x = area_x + (area_width - image.width) // 2 + offset_x
            draw_y = area_y + (area_height - image.height) // 2
            pyxel.blt(draw_x, draw_y, image.image, 0, 0, image.width, image.height)
        else:
            placeholder_x = area_x + offset_x
            pyxel.rect(placeholder_x, area_y, area_width, area_height, 5)
            if rom_file.is_directory:
                placeholder_text = "[Folder]"
            elif has_screenshot and not allow_process:
                placeholder_text = "Loading"
            else:
                placeholder_text = "No Image"
            text_x = placeholder_x + (area_width // 2) - len(placeholder_text) * 2
            text_y = area_y + (area_height // 2) - 4
            pyxel.text(text_x, text_y, placeholder_text, text_color)

        title_y = min(
            area_y + area_height + title_margin,
            self.status_bar.y - title_height - title_bottom_gap,
        )
        display_name = self._fit_gallery_title(self._gallery_display_name(rom_file), max(16, pyxel.width - 8))
        title_width = self._gallery_title_width(display_name)
        title_x = pyxel.width // 2 - (title_width // 2) + offset_x
        pyxel.rect(title_x - 2, title_y, title_width + 4, title_height, bg_color)
        self._draw_gallery_title_text(title_x, title_y, display_name, text_selected_color)
        return image is not None or not has_screenshot or allow_process

    def _draw_gallery_view(self):
        """Draw gallery view (museum-style, borderless fullscreen display, maintains aspect ratio)."""
        if not self.rom_files:
            return

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
        anim_offset_x = int(round(self.gallery_animation_offset * pyxel.width))

        layout = self._gallery_layout()
        is_animating = self.gallery_animation_direction != 0
        allow_process = not (
            self.gallery_defer_image_load
            and (
                is_animating
                or self.gallery_post_scroll_load_cooldown > 0
            )
        )

        if is_animating and self.gallery_previous_index is not None:
            previous_index = self._clamp_item_index(self.gallery_previous_index, len(self.rom_files))
            previous = self.rom_files[previous_index]
            previous_offset_x = anim_offset_x - self.gallery_animation_direction * pyxel.width
            self._draw_gallery_item(
                previous,
                previous_offset_x,
                False,
                layout,
                bg_color,
                text_color,
                text_selected_color,
            )

        selected_ready = self._draw_gallery_item(
            selected,
            anim_offset_x,
            allow_process,
            layout,
            bg_color,
            text_color,
            text_selected_color,
        )
        if allow_process and selected_ready:
            self.gallery_pending_deferred_image_load = False

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
        if self.view_mode == "gallery":
            self._draw_gallery_header()
        else:
            self.category_title.draw()

        # Draw system status (top right)
        self.system_status.draw()

        # Draw counter (上部2行目)
        # Gallery mode shows the counter in the status bar, so the category title
        # can use the full header height without text collisions.
        if self.rom_files and self.view_mode != "gallery":
            self.counter.draw()

        # Draw border line below the header. Gallery mode uses two header rows:
        # status on top, emulator name below.
        header_line_y = 20 if self.view_mode == "gallery" else 18
        pyxel.line(2, header_line_y, pyxel.width - 3, header_line_y, border_color)

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
                right=(
                    f"{self.selected_index + 1}/{len(self.rom_files)}"
                    if self.view_mode == "gallery" and self.rom_files
                    else f"{len(self.rom_files)}"
                )
            )
        self.status_bar.draw()

        # Help text
        self.help_text.draw()

        # Soft keyboard (draw on top)
        if self.soft_keyboard.is_active():
            self.soft_keyboard.draw()
