"""
Music Mode manager.
Provides a low-power music playback mode with screen off.
"""

from debug import debug_print


class MusicModeManager:
    """Manages Music Mode state and behavior."""

    def __init__(self):
        self.active = False
        self.saved_brightness = 5  # Brightness to restore on exit
        self.saved_governor = "ondemand"  # Governor to restore on exit

    def is_active(self) -> bool:
        """Check if Music Mode is active."""
        return self.active

    def activate(self, current_brightness: int, current_governor: str):
        """
        Activate Music Mode.

        Args:
            current_brightness: Current brightness level to restore later
            current_governor: Current CPU governor to restore later
        """
        if self.active:
            return

        # Save current state for restoration
        self.saved_brightness = current_brightness
        self.saved_governor = current_governor

        self.active = True
        debug_print(f"Music Mode activated. Saved: brightness={self.saved_brightness}, governor={self.saved_governor}")

        # Apply Music Mode settings
        self._apply_music_mode_settings()

    def deactivate(self):
        """
        Deactivate Music Mode and restore previous settings.

        Returns:
            Tuple of (saved_brightness, saved_governor) for restoration
        """
        if not self.active:
            return (self.saved_brightness, self.saved_governor)

        self.active = False
        debug_print(f"Music Mode deactivated. Restoring: brightness={self.saved_brightness}, governor={self.saved_governor}")

        return (self.saved_brightness, self.saved_governor)

    def _apply_music_mode_settings(self):
        """Apply Music Mode settings (brightness off, ondemand governor)."""
        # Set brightness to 0
        from brightness_manager import get_brightness_manager
        brightness_manager = get_brightness_manager()
        if brightness_manager.is_available():
            brightness_manager.set_brightness_off()
            debug_print("Music Mode: Brightness set to 0")

        # Set CPU governor to ondemand
        from system_monitor import get_system_monitor
        system_monitor = get_system_monitor()
        if system_monitor:
            system_monitor.set_cpu_governor("ondemand")
            debug_print("Music Mode: CPU governor set to ondemand")

    def check_exit_combo(self, input_handler) -> bool:
        """
        Check if the exit combo (X + Y) is pressed.

        Args:
            input_handler: The input handler instance

        Returns:
            True if exit combo is pressed
        """
        if not self.active:
            return False

        from input_handler import Action
        import pyxel

        # Check for X + Y simultaneous press
        x_held = input_handler.is_held(Action.X)
        y_held = input_handler.is_held(Action.Y)

        if x_held and y_held:
            debug_print("Music Mode: Exit combo detected (X + Y)")
            return True

        return False

    def should_block_input(self, action) -> bool:
        """
        Check if the given action should be blocked in Music Mode.

        Args:
            action: The action to check

        Returns:
            True if action should be blocked
        """
        if not self.active:
            return False

        from input_handler import Action

        # Allow X and Y buttons (for exit combo)
        allowed_actions = [Action.X, Action.Y]

        return action not in allowed_actions


# Global instance
_music_mode_manager = None


def get_music_mode_manager() -> MusicModeManager:
    """Get the global Music Mode manager instance."""
    global _music_mode_manager
    if _music_mode_manager is None:
        _music_mode_manager = MusicModeManager()
    return _music_mode_manager
