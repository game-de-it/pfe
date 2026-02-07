"""
Brightness manager for screen brightness control.
Uses external scripts for cross-platform compatibility.
"""

import os
import subprocess
from debug import debug_print


class BrightnessManager:
    """Manages screen brightness through external scripts."""

    def __init__(self):
        self.scripts_dir = "scripts"
        self.get_script = os.path.join(self.scripts_dir, "get_brightness.sh")
        self.set_script = os.path.join(self.scripts_dir, "set_brightness.sh")
        self.min_brightness = 1
        self.max_brightness = 10
        self.available = self._check_scripts()

    def _check_scripts(self) -> bool:
        """Check if brightness scripts are available."""
        get_exists = os.path.exists(self.get_script)
        set_exists = os.path.exists(self.set_script)

        if not get_exists:
            debug_print(f"Brightness get script not found: {self.get_script}")
        if not set_exists:
            debug_print(f"Brightness set script not found: {self.set_script}")

        available = get_exists and set_exists
        debug_print(f"Brightness manager available: {available}")
        return available

    def is_available(self) -> bool:
        """Check if brightness control is available."""
        return self.available

    def get_brightness(self) -> int:
        """
        Get current brightness level (1-10).

        Returns:
            Current brightness level, or -1 if unavailable
        """
        if not self.available:
            return -1

        try:
            result = subprocess.run(
                ["sh", self.get_script],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                brightness = int(result.stdout.strip())
                # Clamp to valid range
                brightness = max(self.min_brightness, min(self.max_brightness, brightness))
                debug_print(f"Current brightness: {brightness}")
                return brightness
            else:
                debug_print(f"Get brightness failed: {result.stderr}")
                return -1

        except subprocess.TimeoutExpired:
            debug_print("Get brightness timeout")
            return -1
        except ValueError as e:
            debug_print(f"Get brightness parse error: {e}")
            return -1
        except Exception as e:
            debug_print(f"Get brightness error: {e}")
            return -1

    def set_brightness(self, level: int) -> bool:
        """
        Set brightness level (1-10).

        Args:
            level: Brightness level (1-10)

        Returns:
            True if successful
        """
        if not self.available:
            return False

        # Clamp to valid range
        level = max(self.min_brightness, min(self.max_brightness, level))

        try:
            result = subprocess.run(
                ["sh", self.set_script, str(level)],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                debug_print(f"Brightness set to: {level}")
                return True
            else:
                debug_print(f"Set brightness failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            debug_print("Set brightness timeout")
            return False
        except Exception as e:
            debug_print(f"Set brightness error: {e}")
            return False

    def set_brightness_off(self) -> bool:
        """
        Set brightness to minimum (for Music Mode).
        Note: This sets to 0, bypassing the normal minimum of 1.

        Returns:
            True if successful
        """
        if not self.available:
            return False

        try:
            result = subprocess.run(
                ["sh", self.set_script, "0"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                debug_print("Brightness set to 0 (off)")
                return True
            else:
                debug_print(f"Set brightness off failed: {result.stderr}")
                return False

        except Exception as e:
            debug_print(f"Set brightness off error: {e}")
            return False


# Global instance
_brightness_manager = None


def get_brightness_manager() -> BrightnessManager:
    """Get the global brightness manager instance."""
    global _brightness_manager
    if _brightness_manager is None:
        _brightness_manager = BrightnessManager()
    return _brightness_manager
