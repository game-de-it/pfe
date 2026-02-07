"""
ROM launcher for executing emulators.

New specification:
- TYPE_RA: RetroArch script (receives core_name and rom_path)
- TYPE_SA_*: Standalone emulators (receives rom_path only)

Core format in -CORE:
- "nestopia" -> RA:nestopia (implicit, for backward compatibility)
- "SA:YABASANSHIRO" -> Standalone emulator using TYPE_SA_YABASANSHIRO

Core name conversion:
- "nestopia" -> "nestopia_libretro.so" (add suffix if no underscore)
- "nestopia_libretro.dylib" -> as-is (keep if has underscore)
"""

import subprocess
import os
from typing import Optional, Tuple
from config import Category
from rom_manager import ROMFile
from debug import debug_print


class Launcher:
    """Handles launching ROMs with appropriate emulators."""

    def __init__(self, config):
        self.config = config
        self.last_error = None
        # Get the base directory (where main.py is located)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

    def _resolve_path(self, path: str) -> str:
        """
        Resolve path - relative paths are resolved from base_dir.

        Args:
            path: Path (relative or absolute)

        Returns:
            Absolute path
        """
        if os.path.isabs(path):
            return path
        return os.path.join(self.base_dir, path)

    def _parse_core_spec(self, core_spec: str, default_type: str = "RA") -> Tuple[str, str]:
        """
        Parse core specification into type and name.

        Args:
            core_spec: Core specification (e.g., "nestopia", "SA:YABASANSHIRO")
            default_type: Default type if not specified (usually "RA")

        Returns:
            Tuple of (type, name) e.g., ("RA", "nestopia") or ("SA", "YABASANSHIRO")
        """
        if ':' in core_spec:
            parts = core_spec.split(':', 1)
            return (parts[0].upper(), parts[1])
        else:
            # No prefix - use default type (RA for backward compatibility)
            return (default_type, core_spec)

    def _convert_core_name(self, core_name: str) -> str:
        """
        Convert core name to proper format.

        Args:
            core_name: Core name (e.g., "nestopia", "mupen64plus_next", "genesis_plus_gx_EX")

        Returns:
            Converted core name (e.g., "nestopia_libretro.so", "mupen64plus_next_libretro.so")
        """
        # If already has _libretro suffix (with any extension), use as-is
        if '_libretro.' in core_name or core_name.endswith('_libretro'):
            return core_name
        # Otherwise, add _libretro.so suffix
        return f"{core_name}_libretro.so"

    def launch_rom(self, rom_file: ROMFile, category: Category, core: Optional[str] = None) -> bool:
        """
        Launch a ROM file with its emulator.

        Args:
            rom_file: ROM file to launch
            category: Category configuration
            core: Optional core/launcher to use (overrides category default)

        Returns:
            True if launch succeeded, False otherwise
        """
        self.last_error = None

        # Stop BGM before game launch
        from bgm_manager import get_bgm_manager
        bgm_manager = get_bgm_manager()
        bgm_was_playing = bgm_manager.is_bgm_playing()
        debug_print(f"BGM status before game launch: playing={bgm_was_playing}, enabled={bgm_manager.is_enabled()}")
        if bgm_was_playing:
            debug_print("Stopping BGM before game launch")
            bgm_manager.stop()
            still_playing = bgm_manager.is_bgm_playing()
            debug_print(f"BGM stopped successfully: {not still_playing}")

        # Validate ROM file exists
        if not os.path.exists(rom_file.path):
            self.last_error = f"ROM file not found: {rom_file.path}"
            debug_print(self.last_error)
            if bgm_was_playing and bgm_manager.is_enabled():
                bgm_manager.play()
            return False

        # Determine core/launcher to use
        if core is None:
            if category.cores:
                core = category.cores[0]
            else:
                self.last_error = "No core/launcher specified for category"
                debug_print(self.last_error)
                if bgm_was_playing and bgm_manager.is_enabled():
                    bgm_manager.play()
                return False

        # Parse core specification
        launcher_type, launcher_name = self._parse_core_spec(core, category.emulator_type or "RA")
        debug_print(f"Launcher type: {launcher_type}, name: {launcher_name}")

        # Launch based on type
        result = False
        if launcher_type == "RA":
            result = self._launch_retroarch(rom_file, launcher_name)
        elif launcher_type == "SA":
            result = self._launch_standalone(rom_file, launcher_name)
        else:
            # Try as custom type (e.g., PPSSPP -> TYPE_PPSSPP)
            result = self._launch_custom(rom_file, launcher_type)

        # Post-launch processing
        debug_print(f"Game exited. result={result}, BGM was_playing={bgm_was_playing}, enabled={bgm_manager.is_enabled()}")

        if result:
            debug_print("Game launched successfully. PFE will exit, not resuming BGM here.")
        else:
            if bgm_was_playing and bgm_manager.is_enabled():
                debug_print("Game launch failed. Resuming BGM.")
                bgm_manager.play()

        return result

    def _launch_retroarch(self, rom_file: ROMFile, core_name: str) -> bool:
        """
        Launch ROM with RetroArch.

        Args:
            rom_file: ROM file to launch
            core_name: Core name (e.g., "nestopia")

        Returns:
            True if successful
        """
        # Get RetroArch script path
        ra_path = self.config.get_emulator_path("RA")
        if not ra_path:
            self.last_error = "RetroArch path not configured (TYPE_RA)"
            debug_print(self.last_error)
            return False

        # Resolve path
        ra_path = self._resolve_path(ra_path)

        # Convert core name to filename
        core_filename = self._convert_core_name(core_name)

        # Build full core path using CORE_PATH from config
        core_path = self.config.get_core_path()
        if core_path:
            core_full_path = os.path.join(core_path, core_filename)
        else:
            # Fallback to just the filename if CORE_PATH is not set
            core_full_path = core_filename

        debug_print(f"Core path: {core_full_path}")

        # Build command: script core_path rom_path
        command = [ra_path, core_full_path, rom_file.path]

        return self._execute_command(command, ra_path)

    def _launch_standalone(self, rom_file: ROMFile, emulator_name: str) -> bool:
        """
        Launch ROM with standalone emulator.

        Args:
            rom_file: ROM file to launch
            emulator_name: Emulator name (used to look up TYPE_SA_*)

        Returns:
            True if successful
        """
        # Get standalone emulator path (TYPE_SA_*)
        type_key = f"SA_{emulator_name}"
        emu_path = self.config.get_emulator_path(type_key)
        if not emu_path:
            self.last_error = f"Standalone emulator not configured (TYPE_{type_key})"
            debug_print(self.last_error)
            return False

        # Resolve path
        emu_path = self._resolve_path(emu_path)

        # Build command: script rom_path
        command = [emu_path, rom_file.path]

        return self._execute_command(command, emu_path)

    def _launch_custom(self, rom_file: ROMFile, emulator_type: str) -> bool:
        """
        Launch ROM with custom emulator type.

        Args:
            rom_file: ROM file to launch
            emulator_type: Emulator type (used to look up TYPE_*)

        Returns:
            True if successful
        """
        # Get emulator path (TYPE_*)
        emu_path = self.config.get_emulator_path(emulator_type)
        if not emu_path:
            self.last_error = f"Emulator not configured (TYPE_{emulator_type})"
            debug_print(self.last_error)
            return False

        # Resolve path
        emu_path = self._resolve_path(emu_path)

        # Build command: script rom_path
        command = [emu_path, rom_file.path]

        return self._execute_command(command, emu_path)

    def _execute_command(self, command: list, executable_path: str) -> bool:
        """
        Execute a command and wait for it to complete.

        Args:
            command: Command list to execute
            executable_path: Path to executable (for error messages)

        Returns:
            True if successful
        """
        debug_print(f"Launching: {' '.join(command)}")

        try:
            import time
            process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )

            # Brief wait to check if process started
            time.sleep(0.1)

            if process.poll() is not None:
                self.last_error = f"Emulator exited immediately (code: {process.returncode})"
                debug_print(self.last_error)
                return False

            debug_print("Waiting for emulator to close...")
            process.wait()
            debug_print(f"Emulator closed with exit code: {process.returncode}")

            return True

        except FileNotFoundError:
            self.last_error = f"Emulator not found: {executable_path}"
            debug_print(self.last_error)
            return False
        except Exception as e:
            self.last_error = f"Launch error: {str(e)}"
            debug_print(self.last_error)
            return False

    def get_last_error(self) -> Optional[str]:
        """Get the last error message."""
        return self.last_error


# Example usage
if __name__ == "__main__":
    print("Launcher module initialized")
