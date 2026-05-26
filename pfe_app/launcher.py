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
import tempfile
from typing import Optional, Tuple
from pfe_app.config import Category
from pfe_app.rom_manager import ROMFile
from pfe_app.debug import debug_print


class Launcher:
    """Handles launching ROMs with appropriate emulators."""

    def __init__(self, config):
        self.config = config
        self.last_error = None
        self.last_launch_handoff = False
        # Get the app root directory (where main.py is located).
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
            return (parts[0], parts[1])
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
        self.last_launch_handoff = False

        # Stop BGM before game launch
        from pfe_app.bgm_manager import get_bgm_manager
        bgm_manager = get_bgm_manager()
        bgm_was_playing = bgm_manager.is_bgm_playing()
        debug_print(f"BGM status before game launch: playing={bgm_was_playing}, enabled={bgm_manager.is_enabled()}")
        if bgm_was_playing:
            debug_print("Stopping BGM before game launch")
            bgm_manager.stop(release_driver=True)
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
        if launcher_type.upper() == "RA":
            result = self._launch_retroarch(rom_file, category, launcher_name, core)
        elif launcher_type.upper() == "SA":
            result = self._launch_standalone(rom_file, category, launcher_name, core)
        else:
            # Try as custom type (e.g., PPSSPP -> TYPE_PPSSPP)
            result = self._launch_custom(rom_file, category, launcher_type, launcher_name, core)

        # Post-launch processing
        debug_print(f"Game exited. result={result}, BGM was_playing={bgm_was_playing}, enabled={bgm_manager.is_enabled()}")

        if result:
            debug_print("Game launched successfully. PFE will exit, not resuming BGM here.")
        else:
            if bgm_was_playing and bgm_manager.is_enabled():
                debug_print("Game launch failed. Resuming BGM.")
                bgm_manager.play()

        return result

    def _get_category_system_id(self, category: Category) -> str:
        """Return the EmulationStation/ROCKNIX system id for a category."""
        if getattr(category, "system_id", ""):
            return category.system_id
        directory = getattr(category, "directory", "") or ""
        if directory:
            return os.path.basename(os.path.normpath(directory))
        return category.name

    def _build_launch_env(
        self,
        category: Category,
        launcher_type: str,
        launcher_name: str,
        core_spec: str,
        core_arg: str = "",
    ) -> dict:
        """Build environment values consumed by device-specific launcher scripts."""
        env = {
            "PFE_CATEGORY_NAME": category.name,
            "PFE_SYSTEM": self._get_category_system_id(category),
            "PFE_ROM_DIR": getattr(category, "directory", "") or "",
            "PFE_LAUNCHER_TYPE": launcher_type,
            "PFE_EMULATOR": "retroarch" if launcher_type.upper() == "RA" else launcher_type,
            "PFE_CORE_NAME": launcher_name,
            "PFE_CORE_SPEC": core_spec,
        }
        if core_arg:
            env["PFE_CORE_ARG"] = core_arg
        ra_launch_mode = getattr(self.config, "global_vars", {}).get("RA_LAUNCH_MODE", "")
        if ra_launch_mode:
            env["PFE_RA_LAUNCH_MODE"] = ra_launch_mode
        return env

    def _launch_retroarch(
        self,
        rom_file: ROMFile,
        category: Category,
        core_name: str,
        core_spec: str,
    ) -> bool:
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

        env = self._build_launch_env(category, "RA", core_name, core_spec, core_full_path)
        return self._execute_command(command, ra_path, env=env)

    def _launch_standalone(
        self,
        rom_file: ROMFile,
        category: Category,
        emulator_name: str,
        core_spec: str,
    ) -> bool:
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

        env = self._build_launch_env(category, "SA", emulator_name, core_spec)
        if self._should_handoff_launch("SA", emulator_name):
            env["PFE_LAUNCH_HANDOFF"] = "1"
            self.last_launch_handoff = True
        return self._execute_command(command, emu_path, env=env)

    def _launch_custom(
        self,
        rom_file: ROMFile,
        category: Category,
        emulator_type: str,
        core_name: str,
        core_spec: str,
    ) -> bool:
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

        env = self._build_launch_env(category, emulator_type, core_name, core_spec)
        if self._should_handoff_launch(emulator_type, core_name):
            env["PFE_LAUNCH_HANDOFF"] = "1"
            self.last_launch_handoff = True
        return self._execute_command(command, emu_path, env=env)

    def _should_handoff_launch(self, emulator_type: str, core_name: str) -> bool:
        """Return True when the launcher should exit while the game runs."""
        if emulator_type.lower() != "pyxel" and core_name.lower() != "pyxel":
            return False

        mode = str(getattr(self.config, "global_vars", {}).get("PYXEL_LAUNCH_MODE", "handoff")).strip().lower()
        if mode in ("handoff", "detached", "external"):
            return True
        if mode in ("direct", "wait", "inline", "resume"):
            return False

        return True

    def _execute_command(self, command: list, executable_path: str, env: Optional[dict] = None) -> bool:
        """
        Execute a command and wait for it to complete.

        Args:
            command: Command list to execute
            executable_path: Path to executable (for error messages)

        Returns:
            True if successful
        """
        command = self._prepare_script_command(command, executable_path)
        debug_print(f"Launching: {' '.join(command)}")

        try:
            import time
            process_env = os.environ.copy()
            if env:
                process_env.update({key: str(value) for key, value in env.items()})
            handoff_launch = str(process_env.get("PFE_LAUNCH_HANDOFF", "")).strip().lower() in (
                "1", "true", "yes", "on"
            )
            with tempfile.TemporaryFile(mode="w+t", encoding="utf-8", errors="replace") as stdout_file, \
                    tempfile.TemporaryFile(mode="w+t", encoding="utf-8", errors="replace") as stderr_file:
                process = subprocess.Popen(
                    command,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    stdin=subprocess.DEVNULL,
                    env=process_env,
                    start_new_session=handoff_launch,
                )

                if handoff_launch:
                    time.sleep(0.25)
                    if process.poll() is None:
                        debug_print("Handoff launcher is running; treating launch as scheduled.")
                        return True

                    stdout_file.seek(0)
                    stderr_file.seek(0)
                    stdout = stdout_file.read().strip()
                    stderr = stderr_file.read().strip()

                    if process.returncode != 0:
                        self.last_error = f"Handoff launcher failed (code: {process.returncode})"
                        debug_print(self.last_error)
                        if stdout:
                            debug_print(f"Emulator stdout: {stdout[-2000:]}")
                        if stderr:
                            debug_print(f"Emulator stderr: {stderr[-2000:]}")
                        return False

                    if stdout:
                        debug_print(f"Emulator stdout: {stdout[-2000:]}")
                    if stderr:
                        debug_print(f"Emulator stderr: {stderr[-2000:]}")
                    debug_print("Handoff launcher scheduled successfully.")
                    return True

                # Brief wait to check if process started
                time.sleep(0.1)

                if process.poll() is not None:
                    stdout_file.seek(0)
                    stderr_file.seek(0)
                    stdout = stdout_file.read().strip()
                    stderr = stderr_file.read().strip()
                    self.last_error = f"Emulator exited immediately (code: {process.returncode})"
                    debug_print(self.last_error)
                    if stdout:
                        debug_print(f"Emulator stdout: {stdout[-2000:]}")
                    if stderr:
                        debug_print(f"Emulator stderr: {stderr[-2000:]}")
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

    def _prepare_script_command(self, command: list, executable_path: str) -> list:
        """Run non-executable shell scripts via sh so copied ZIP files still work."""
        if not executable_path.endswith(".sh"):
            return command
        if os.access(executable_path, os.X_OK):
            return command
        if not command or command[0] != executable_path:
            return command
        return ["sh", executable_path] + command[1:]

    def get_last_error(self) -> Optional[str]:
        """Get the last error message."""
        return self.last_error

    def should_exit_after_launch(self) -> bool:
        """Return True when PFE should quit after scheduling a launch."""
        return self.last_launch_handoff


# Example usage
if __name__ == "__main__":
    print("Launcher module initialized")
