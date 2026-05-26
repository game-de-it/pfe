"""
Image cache build screen.
"""

import os
import re
from collections.abc import Iterator

import pyxel

from pfe_app.image_cache import ImageCache
from pfe_app.japanese_text import draw_japanese_text, get_japanese_text_width
from ui.base import ScrollableList
from ui.components import HelpText, StatusBar
from ui.window import DQWindow
from pfe_app.theme_manager import get_theme_manager
from pfe_app.debug import debug_print


class ImageCacheScreen(ScrollableList):
    """Build screenshot image caches before browsing ROM galleries."""

    def __init__(self, input_handler, state_manager, config):
        super().__init__(items_per_page=3)
        self.input_handler = input_handler
        self.state_manager = state_manager
        self.config = config
        self.status_bar = StatusBar(138, 160)
        self.help_text = HelpText(146, 160)
        self.image_cache = ImageCache(memory_limit=32)
        self.screenshot_dir = self.config.get_screenshot_dir()

        self.menu_items = [
            {"name": "Build Current", "scope": "current"},
            {"name": "Build All Systems", "scope": "all"},
        ]
        self.set_items(self.menu_items)

        self.mode = "idle"
        self.status_message = "Select cache target"
        self.worker: Iterator | None = None
        self.seen_screenshots: set[str] = set()
        self.checked = 0
        self.ready = 0
        self.built = 0
        self.disk = 0
        self.memory = 0
        self.missing = 0
        self.failed = 0
        self.duplicates = 0
        self.current_system = ""
        self.last_rom = ""
        self.last_image = ""
        self.last_source = ""
        self.last_elapsed_ms = 0.0
        self.target_label = ""

    def activate(self):
        super().activate()
        self.help_text.set_controls([
            ("Up/Down", "Select"),
            ("A", "Start"),
            ("B", "Back"),
        ])

    def deactivate(self):
        super().deactivate()
        if self.mode == "running":
            self.image_cache.flush_metadata()
        self.mode = "idle"
        self.worker = None

    def update(self):
        if not self.active:
            return

        from pfe_app.input_handler import Action

        if self.mode == "running":
            if self.input_handler.is_pressed(Action.B):
                self.mode = "cancelled"
                self.worker = None
                self.image_cache.flush_metadata()
                self.status_message = "Cancelled"
                self._set_idle_help()
                return
            self._process_build_step()
            return

        if self.input_handler.is_pressed_with_repeat(Action.UP):
            self.scroll_up()
        elif self.input_handler.is_pressed_with_repeat(Action.DOWN):
            self.scroll_down()

        if self.input_handler.is_pressed(Action.A):
            selected = self.get_selected_item()
            if selected:
                self._start_build(selected["scope"])

        if self.input_handler.is_pressed(Action.B):
            self.state_manager.go_back()

    def _set_idle_help(self):
        self.help_text.set_controls([
            ("Up/Down", "Select"),
            ("A", "Start"),
            ("B", "Back"),
        ])

    def _set_running_help(self):
        self.help_text.set_controls([
            ("B", "Cancel"),
        ])

    def _start_build(self, scope: str):
        categories = self._target_categories(scope)
        if not categories:
            self.mode = "done"
            self.status_message = "No target system"
            return

        self.mode = "running"
        self.worker = self._iter_rom_paths(categories)
        self.seen_screenshots.clear()
        self.checked = 0
        self.ready = 0
        self.built = 0
        self.disk = 0
        self.memory = 0
        self.missing = 0
        self.failed = 0
        self.duplicates = 0
        self.current_system = ""
        self.last_rom = ""
        self.last_image = ""
        self.last_source = ""
        self.last_elapsed_ms = 0.0
        self.target_label = "All Systems" if scope == "all" else categories[0].name
        self.status_message = "Building..."
        self._set_running_help()
        debug_print(f"[ImageCacheBuild] start scope={scope} target={self.target_label}")

    def _target_categories(self, scope: str) -> list:
        if scope == "all":
            return list(self.config.get_categories())

        selected_name = self.state_manager.get_selected_category()
        if not selected_name:
            return []
        category = self.config.get_category(selected_name)
        return [category] if category else []

    def _iter_rom_paths(self, categories: list) -> Iterator[tuple[object, str]]:
        for category in categories:
            directory = category.directory
            extensions = {ext.lower().lstrip(".") for ext in category.extensions}
            if not os.path.isdir(directory):
                continue
            for root, dirs, files in os.walk(directory):
                dirs.sort(key=str.lower)
                files.sort(key=str.lower)
                for filename in files:
                    ext = os.path.splitext(filename)[1].lstrip(".").lower()
                    if ext in extensions:
                        yield category, os.path.join(root, filename)

    def _process_build_step(self):
        if self.worker is None:
            self.mode = "done"
            return

        max_width, max_height = self._gallery_cache_bounds()
        skipped_this_frame = 0

        while skipped_this_frame < 12:
            try:
                category, rom_path = next(self.worker)
            except StopIteration:
                self.mode = "done"
                self.worker = None
                self.status_message = "Done"
                self.image_cache.flush_metadata()
                self._set_idle_help()
                debug_print(
                    "[ImageCacheBuild] done "
                    f"checked={self.checked} ready={self.ready} built={self.built} "
                    f"disk={self.disk} missing={self.missing} failed={self.failed}"
                )
                return

            self.checked += 1
            self.current_system = category.name
            self.last_rom = os.path.basename(rom_path)
            screenshot_path = self._find_screenshot_file(rom_path, category)
            if not screenshot_path:
                self.missing += 1
                skipped_this_frame += 1
                continue

            if screenshot_path in self.seen_screenshots:
                self.duplicates += 1
                skipped_this_frame += 1
                continue

            self.seen_screenshots.add(screenshot_path)
            image = self.image_cache.get_fit(screenshot_path, max_width, max_height, upscale=True)
            self.last_image = os.path.basename(screenshot_path)
            self.last_source = self.image_cache.last_access_source or (image.source if image else "failed")
            self.last_elapsed_ms = self.image_cache.last_access_elapsed_ms

            if image is None:
                self.failed += 1
            else:
                self.ready += 1
                if self.last_source == "process":
                    self.built += 1
                elif self.last_source == "disk":
                    self.disk += 1
                elif self.last_source == "memory":
                    self.memory += 1

            if self.ready and self.ready % 8 == 0:
                self.image_cache.flush_metadata()
            return

    def _gallery_cache_bounds(self) -> tuple[int, int]:
        area_width = max(1, pyxel.width - 8)
        area_y = 22
        title_height = 8
        title_margin = 4
        title_bottom_gap = 3
        bottom_limit = max(area_y + 32, self.status_bar.y - title_height - title_margin - title_bottom_gap)
        area_height = max(24, bottom_limit - area_y)
        return area_width, area_height

    def _find_screenshot_file(self, rom_path: str, category) -> str | None:
        screenshot_base_dir = self.screenshot_dir
        extensions = [".png", ".jpg", ".jpeg"]

        parent_dir = os.path.basename(os.path.dirname(rom_path))
        rom_name = os.path.basename(rom_path)
        rom_name_without_ext = rom_name
        for ext in category.extensions:
            ext_with_dot = ext if ext.startswith(".") else "." + ext
            if rom_name.lower().endswith(ext_with_dot.lower()):
                rom_name_without_ext = rom_name[:-len(ext_with_dot)]
                break

        dir_screenshot_dir = os.path.join(screenshot_base_dir, parent_dir)
        name_patterns = [rom_name_without_ext]

        name_without_brackets = re.sub(r"\[.*?\]", "", rom_name_without_ext).strip()
        if name_without_brackets != rom_name_without_ext:
            name_patterns.append(name_without_brackets)

        name_without_parens = re.sub(r"\(.*?\)", "", rom_name_without_ext).strip()
        if name_without_parens != rom_name_without_ext:
            name_patterns.append(name_without_parens)

        name_clean = re.sub(r"[\[\(].*?[\]\)]", "", rom_name_without_ext).strip()
        if name_clean and name_clean not in name_patterns:
            name_patterns.append(name_clean)

        for pattern in name_patterns[:]:
            normalized = re.sub(r"\s+", " ", pattern).strip()
            if normalized not in name_patterns:
                name_patterns.append(normalized)

        for pattern in name_patterns:
            if not pattern:
                continue
            for ext in extensions:
                path = os.path.join(dir_screenshot_dir, pattern + ext)
                if os.path.exists(path):
                    return path
        return None

    def _text_width(self, text: str) -> int:
        try:
            return get_japanese_text_width(text)
        except Exception:
            return len(text) * 4

    def _fit_text(self, text: str, max_width: int) -> str:
        if self._text_width(text) <= max_width:
            return text
        if max_width <= self._text_width(".."):
            return ""
        trimmed = text
        while trimmed and self._text_width(trimmed + "..") > max_width:
            trimmed = trimmed[:-1]
        return trimmed + ".." if trimmed else ""

    def draw(self):
        if not self.active:
            return

        theme = get_theme_manager()
        bg_color = theme.get_color("background")
        text_color = theme.get_color("text")
        text_selected_color = theme.get_color("text_selected")
        border_color = theme.get_color("border")

        pyxel.cls(bg_color)
        pyxel.text(2, 2, "IMAGE CACHE", text_selected_color)
        pyxel.text(pyxel.width // 2 - len("Build Gallery Cache") * 2, 10, "Build Gallery Cache", text_color)
        DQWindow.draw(2, 18, pyxel.width - 8, 120, bg_color=bg_color, border_color=border_color)

        if self.mode == "running":
            self._draw_progress(text_color, text_selected_color)
        else:
            self._draw_menu(text_color, text_selected_color)

        self.status_bar.set_text(left=self.status_message, center="", right=self._status_right())
        self.status_bar.draw()
        self.help_text.draw()

    def _draw_menu(self, text_color: int, text_selected_color: int):
        start_y = 28
        line_height = 15
        visible = self.get_visible_items()
        visible_start, _ = self.get_visible_range()
        for i, item in enumerate(visible):
            y = start_y + i * line_height
            index = visible_start + i
            color = text_selected_color if index == self.selected_index else text_color
            label = item["name"]
            if item["scope"] == "current" and not self.state_manager.get_selected_category():
                label = "Build Current (N/A)"
            draw_japanese_text(8, y, self._fit_text(label, pyxel.width - 36), color)
            draw_japanese_text(pyxel.width - 30, y, ">", color)

        y = start_y + len(visible) * line_height + 8
        notes = [
            "Prebuilds ROM gallery images.",
            "Use before long scrolling.",
        ]
        for note in notes:
            pyxel.text(8, y, self._fit_text(note, pyxel.width - 16), text_color)
            y += 9

        if self.mode in ("done", "cancelled"):
            y += 4
            summary = f"Ready:{self.ready} New:{self.built} Disk:{self.disk}"
            pyxel.text(8, y, self._fit_text(summary, pyxel.width - 16), text_selected_color)
            y += 9
            summary = f"Checked:{self.checked} Missing:{self.missing} Failed:{self.failed}"
            pyxel.text(8, y, self._fit_text(summary, pyxel.width - 16), text_color)

    def _draw_progress(self, text_color: int, text_selected_color: int):
        y = 26
        lines = [
            ("Target", self.target_label),
            ("System", self.current_system),
            ("ROM", self.last_rom),
            ("Image", self.last_image),
            ("Source", f"{self.last_source} {self.last_elapsed_ms:.1f}ms" if self.last_source else ""),
            ("Checked", str(self.checked)),
            ("Ready", f"{self.ready}  New:{self.built} Disk:{self.disk}"),
            ("Missing", f"{self.missing}  Failed:{self.failed}"),
        ]
        for label, value in lines:
            draw_japanese_text(8, y, label + ":", text_selected_color)
            draw_japanese_text(58, y, self._fit_text(value, pyxel.width - 66), text_color)
            y += 13

    def _status_right(self) -> str:
        if self.mode == "running":
            return "RUN"
        if self.mode == "done":
            return "DONE"
        if self.mode == "cancelled":
            return "STOP"
        return ""
