"""
Screenshot loader for ROM images.
Loads PNG/JPG images and converts them to Pyxel format.
"""

import os
import pyxel
from PIL import Image
from typing import Optional
from debug import debug_print


class ScreenshotLoader:
    """Loads and manages ROM screenshots."""

    def __init__(self, screenshot_dir: str = "assets/screenshots"):
        self.screenshot_dir = screenshot_dir
        debug_print(f"[SCREENSHOT] Screenshot directory: {screenshot_dir}")
        self.cache = {}  # ROM name -> image bank index
        self.image_bank_index = 0  # Image bank to use (0-2)
        self.next_x = 0  # X coordinate for placing the next image
        self.next_y = 0  # Y coordinate for placing the next image
        self.image_size = 48  # Image size (48x48)

    def load_screenshot(self, rom_name: str) -> Optional[tuple]:
        """
        Load a screenshot for the ROM.

        Args:
            rom_name: ROM name (without extension)

        Returns:
            (x, y, width, height) or None
        """
        # Check cache
        if rom_name in self.cache:
            return self.cache[rom_name]

        # Search for file
        screenshot_path = self._find_screenshot(rom_name)
        if not screenshot_path:
            return None

        # Check if there is space in the image bank
        if self.next_x + self.image_size > 256:
            # Move to next row
            self.next_x = 0
            self.next_y += self.image_size

        if self.next_y + self.image_size > 256:
            # Image bank is full
            print(f"Warning: Image bank full, cannot load {rom_name}")
            return None

        # Load image and copy to Pyxel image bank
        try:
            img = Image.open(screenshot_path)
            # Resize
            img = img.resize((self.image_size, self.image_size), Image.Resampling.LANCZOS)
            # Convert to RGB
            img = img.convert('RGB')

            # Copy to Pyxel image bank
            x_pos = self.next_x
            y_pos = self.next_y

            for y in range(self.image_size):
                for x in range(self.image_size):
                    r, g, b = img.getpixel((x, y))
                    # Convert RGB to the nearest Pyxel color
                    color = self._rgb_to_pyxel_color(r, g, b)
                    pyxel.image(self.image_bank_index).pset(
                        x_pos + x,
                        y_pos + y,
                        color
                    )

            # Cache position information
            result = (x_pos, y_pos, self.image_size, self.image_size)
            self.cache[rom_name] = result

            # Update next position
            self.next_x += self.image_size

            return result

        except Exception as e:
            print(f"Error loading screenshot for {rom_name}: {e}")
            return None

    def _find_screenshot(self, rom_name: str) -> Optional[str]:
        """Search for screenshot file."""
        extensions = ['.png', '.jpg', '.jpeg']

        for ext in extensions:
            path = os.path.join(self.screenshot_dir, rom_name + ext)
            if os.path.exists(path):
                return path

        return None

    def _rgb_to_pyxel_color(self, r: int, g: int, b: int) -> int:
        """Convert RGB to the nearest Pyxel color."""
        palette = [
            (0, 0, 0), (43, 51, 95), (126, 32, 114), (25, 149, 156),
            (139, 72, 82), (57, 92, 152), (169, 193, 255), (238, 238, 238),
            (212, 24, 108), (211, 132, 65), (233, 195, 91), (112, 198, 169),
            (118, 150, 222), (163, 163, 163), (255, 151, 152), (237, 199, 176),
        ]

        min_distance = float('inf')
        nearest_color = 0

        for i, (pr, pg, pb) in enumerate(palette):
            # Calculate color distance
            distance = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
            if distance < min_distance:
                min_distance = distance
                nearest_color = i

        return nearest_color

    def draw_screenshot(self, rom_name: str, x: int, y: int) -> bool:
        """
        Draw a screenshot.

        Args:
            rom_name: ROM name
            x: Drawing X coordinate
            y: Drawing Y coordinate

        Returns:
            True if drawing was successful
        """
        screenshot = self.load_screenshot(rom_name)
        if not screenshot:
            return False

        sx, sy, sw, sh = screenshot
        pyxel.blt(x, y, self.image_bank_index, sx, sy, sw, sh)
        return True
