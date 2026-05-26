"""
BGM manager for background music playback.
Supports two audio drivers: pyxel (PCM) and pygame (mixer).
Uses Strategy pattern to switch between drivers at runtime.
Supports playlist with normal and shuffle modes.
"""

import os
import random
from pfe_app.debug import debug_print

# --- Audio Driver Interfaces ---

class PyxelAudioDriver:
    """Audio driver using pyxel's PCM playback (22.05kHz mono, supports mp3/wav/ogg)."""

    _BGM_CHANNEL = 0
    _BGM_SOUND = 0

    def __init__(self):
        self._initialized = False

    def init(self) -> bool:
        if self._initialized:
            return True
        self._initialized = True
        try:
            import pyxel
            pyxel.channels[self._BGM_CHANNEL].gain = 0.5
            debug_print("[BGM] PyxelAudioDriver initialized")
            return True
        except Exception as e:
            debug_print(f"[BGM] PyxelAudioDriver init failed: {e}")
            return False

    def load(self, path: str) -> bool:
        try:
            import pyxel
            pyxel.sounds[self._BGM_SOUND].pcm(path)
            debug_print(f"[BGM] Pyxel loaded: {path}")
            return True
        except Exception as e:
            debug_print(f"[BGM] Pyxel load failed: {e}")
            return False

    def play(self):
        import pyxel
        pyxel.play(self._BGM_CHANNEL, self._BGM_SOUND)

    def stop(self):
        try:
            import pyxel
            pyxel.stop(self._BGM_CHANNEL)
        except Exception as e:
            debug_print(f"[BGM] Pyxel stop failed: {e}")

    def shutdown(self):
        self.stop()
        self._initialized = False

    def pause(self):
        self.stop()

    def unpause(self):
        import pyxel
        pyxel.play(self._BGM_CHANNEL, self._BGM_SOUND)

    def set_volume(self, volume: float):
        try:
            import pyxel
            pyxel.channels[self._BGM_CHANNEL].gain = volume
        except Exception as e:
            debug_print(f"[BGM] Pyxel set_volume failed: {e}")

    def is_music_ended(self) -> bool:
        import pyxel
        return pyxel.play_pos(self._BGM_CHANNEL) is None

    def scan_extensions(self):
        return ('.mp3', '.wav', '.ogg')


class PygameAudioDriver:
    """Audio driver using a helper process with pygame.mixer.

    Keeping pygame in a separate process avoids blocking PFE startup on pygame's
    heavy import and avoids the in-process SDL mixer conflict after pyxel.init().
    """

    def __init__(self):
        self._process = None
        self._reader_thread = None
        self._ready = False
        self._music_ended = True
        self._last_error = ""
        self._atexit_registered = False
        self._pending_path = None
        self._queued_path = None
        self._pending_play = False
        self._play_command_sent = False
        self._volume = 0.5

    def init(self) -> bool:
        if self._is_process_alive():
            return True
        try:
            import atexit
            import subprocess
            import sys
            import threading

            worker_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bgm_worker.py")
            if not os.path.exists(worker_path):
                debug_print(f"[BGM] Pygame worker not found: {worker_path}")
                return False

            env = os.environ.copy()
            env.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
            self._process = subprocess.Popen(
                [sys.executable, worker_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
            )
            self._reader_thread = threading.Thread(target=self._read_worker_output, daemon=True)
            self._reader_thread.start()
            if not self._atexit_registered:
                atexit.register(self.shutdown)
                self._atexit_registered = True
            debug_print("[BGM] Pygame worker started")
            return True
        except Exception as e:
            debug_print(f"[BGM] Pygame worker start failed: {e}")
            return False

    def load(self, path: str) -> bool:
        if not os.path.exists(path):
            return False
        self._pending_path = path
        self._queued_path = None
        self._play_command_sent = False
        self._music_ended = False
        return True

    def play(self):
        self._pending_play = True
        self._music_ended = False
        self._flush_pending()

    def stop(self):
        self._pending_play = False
        self._play_command_sent = False
        self._music_ended = True
        self._send({"cmd": "stop"})

    def pause(self):
        self._pending_play = False
        self._send({"cmd": "pause"})

    def unpause(self):
        self._pending_play = True
        self._play_command_sent = False
        self._music_ended = False
        if self._ready:
            self._send({"cmd": "unpause"})

    def set_volume(self, volume: float):
        self._volume = max(0.0, min(1.0, volume))
        if self._ready:
            self._send({"cmd": "volume", "value": self._volume})

    def is_music_ended(self) -> bool:
        if not self._is_process_alive():
            return True
        if self._pending_play and not self._play_command_sent:
            return False
        return self._music_ended

    def scan_extensions(self):
        return ('.mp3', '.wav')

    def shutdown(self):
        import subprocess

        if self._process is None:
            return
        try:
            if self._is_process_alive():
                self._send({"cmd": "quit"}, start_if_needed=False)
                self._process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            try:
                if self._process and self._is_process_alive():
                    self._process.terminate()
                    self._process.wait(timeout=0.5)
            except Exception:
                pass
        except Exception as e:
            debug_print(f"[BGM] Pygame shutdown failed: {e}")
            try:
                if self._process and self._is_process_alive():
                    self._process.terminate()
            except Exception:
                pass
        self._process = None
        self._ready = False
        self._queued_path = None
        self._play_command_sent = False
        self._pending_play = False

    def _is_process_alive(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def _send(self, command: dict, start_if_needed: bool = True) -> bool:
        if not self._is_process_alive():
            if not start_if_needed or not self.init():
                return False
        try:
            import json
            self._process.stdin.write(json.dumps(command) + "\n")
            self._process.stdin.flush()
            return True
        except Exception as e:
            debug_print(f"[BGM] Pygame worker command failed: {e}")
            return False

    def _read_worker_output(self):
        import json
        if self._process is None or self._process.stdout is None:
            return
        for line in self._process.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except Exception:
                debug_print(f"[BGM] Pygame worker: {line}")
                continue
            self._handle_worker_event(event)

    def _handle_worker_event(self, event: dict):
        name = event.get("event")
        if name == "ready":
            self._ready = True
            debug_print(
                f"[BGM] Pygame worker ready (freq={event.get('frequency')}, channels={event.get('channels')})"
            )
            self._flush_pending()
        elif name == "loaded":
            if event.get("ok"):
                debug_print(f"[BGM] Pygame loaded: {event.get('path')}")
            else:
                self._last_error = event.get("error", "")
                self._music_ended = True
                self._play_command_sent = False
                debug_print(f"[BGM] Pygame load failed: {self._last_error}")
        elif name == "playing":
            if event.get("ok"):
                self._music_ended = False
                debug_print("[BGM] Pygame playback started")
            else:
                self._last_error = event.get("error", "")
                self._music_ended = True
                self._play_command_sent = False
                debug_print(f"[BGM] Pygame play failed: {self._last_error}")
        elif name == "ended":
            self._music_ended = True
            self._pending_play = False
            self._play_command_sent = False
        elif name in ("stopped", "paused"):
            self._music_ended = True
            self._pending_play = False
            self._play_command_sent = False
        elif name == "error":
            self._last_error = event.get("error", "")
            debug_print(f"[BGM] Pygame worker error: {self._last_error}")

    def _flush_pending(self):
        if not self._ready or not self._is_process_alive():
            return
        if self._pending_path and self._pending_play and not self._play_command_sent:
            if self._send({
                "cmd": "load_play",
                "path": self._pending_path,
                "volume": self._volume,
                "loops": 0,
            }):
                self._queued_path = self._pending_path
                self._play_command_sent = True
            return
        if self._pending_path and self._queued_path != self._pending_path:
            if self._send({"cmd": "load", "path": self._pending_path}):
                self._queued_path = self._pending_path
        self._send({"cmd": "volume", "value": self._volume})
        if self._pending_play and not self._play_command_sent:
            if self._send({"cmd": "play", "loops": 0}):
                self._play_command_sent = True


# --- BGM Manager ---

class BGMManager:
    """Manages background music playback with playlist support."""

    MODE_NORMAL = "Normal"
    MODE_SHUFFLE = "Shuffle"

    DRIVER_PYXEL = "pyxel"
    DRIVER_PYGAME = "pygame"

    def __init__(self):
        self.enabled = True
        self.volume = 0.5
        self.current_bgm = None
        self.is_playing = False

        # Playlist related
        self.playlist = []
        self.play_order = []
        self.current_index = 0
        self.play_mode = self.MODE_NORMAL
        self.bgm_directory = "assets/bgm"
        self.max_playlist_size = 300

        # Frame counter for end-of-track check
        self.check_interval = 30
        self.frame_counter = 0

        # Driver (default: pygame for high quality)
        self.driver_name = self.DRIVER_PYGAME
        self.driver = PygameAudioDriver()
        self._driver_initialized = False

    def _create_driver(self, driver_name: str):
        if driver_name == self.DRIVER_PYXEL:
            return PyxelAudioDriver()
        return PygameAudioDriver()

    def _ensure_initialized(self, allow_fallback: bool = True):
        if self._driver_initialized:
            return True
        result = self.driver.init()
        if allow_fallback and not result and self.driver_name != self.DRIVER_PYXEL:
            debug_print(f"[BGM] Falling back to '{self.DRIVER_PYXEL}' audio driver")
            self._shutdown_current_driver()
            self.driver_name = self.DRIVER_PYXEL
            self.driver = self._create_driver(self.driver_name)
            result = self.driver.init()
        self._driver_initialized = result
        if not result:
            debug_print(f"[BGM] Driver '{self.driver_name}' init failed")
            if allow_fallback:
                self.enabled = False
        return result

    def _shutdown_current_driver(self):
        shutdown = getattr(self.driver, "shutdown", None)
        if callable(shutdown):
            shutdown()

    def set_driver(self, driver_name: str, initialize: bool = True, allow_fallback: bool = True):
        """Switch audio driver. Stops current playback, switches, and resumes if needed."""
        driver_name = driver_name.lower()
        if driver_name not in (self.DRIVER_PYXEL, self.DRIVER_PYGAME):
            debug_print(f"[BGM] Unknown driver: {driver_name}")
            return

        if driver_name == self.driver_name and self._driver_initialized:
            debug_print(f"[BGM] Driver already set to '{driver_name}'")
            return

        was_playing = self.is_playing
        # Stop current driver
        if self.is_playing:
            self.driver.stop()
            self.is_playing = False

        # Switch driver
        old_name = self.driver_name
        if old_name != driver_name:
            self._shutdown_current_driver()
        self.driver_name = driver_name
        self._driver_initialized = False
        self.driver = self._create_driver(driver_name)

        debug_print(f"[BGM] Driver switched: {old_name} -> {driver_name}")

        if not initialize:
            return

        # Initialize new driver
        if not self._ensure_initialized(allow_fallback=allow_fallback):
            debug_print(f"[BGM] New driver '{driver_name}' failed to initialize")
            return

        # Apply volume
        self.driver.set_volume(self.volume)

        # Rebuild playlist (extensions may differ between drivers)
        self.build_playlist()

        # Resume playback if was playing
        if was_playing and self.enabled and self.playlist:
            self._play_current_track()

    def get_driver_name(self) -> str:
        return self.driver_name

    def scan_bgm_files(self) -> list:
        if not os.path.exists(self.bgm_directory):
            debug_print(f"BGM directory not found: {self.bgm_directory}")
            return []

        extensions = self.driver.scan_extensions()
        bgm_files = []
        for root, dirs, files in os.walk(self.bgm_directory):
            for filename in files:
                if filename.lower().endswith(extensions):
                    bgm_files.append(os.path.join(root, filename))

        debug_print(f"Found {len(bgm_files)} BGM files in {self.bgm_directory} (including subdirectories)")
        return bgm_files

    def build_playlist(self):
        all_files = self.scan_bgm_files()

        if not all_files:
            debug_print("No BGM files found")
            self.playlist = []
            self.play_order = []
            return

        if len(all_files) <= self.max_playlist_size:
            self.playlist = all_files[:]
        else:
            self.playlist = random.sample(all_files, self.max_playlist_size)

        debug_print(f"Playlist built with {len(self.playlist)} tracks:")
        for i, track in enumerate(self.playlist):
            debug_print(f"  {i+1}. {os.path.basename(track)}")

        self._update_play_order()

    def _update_play_order(self):
        if not self.playlist:
            self.play_order = []
            return

        if self.play_mode == self.MODE_SHUFFLE:
            self.play_order = list(range(len(self.playlist)))
            random.shuffle(self.play_order)
            debug_print(f"Shuffle play order: {self.play_order}")
        else:
            self.play_order = list(range(len(self.playlist)))
            debug_print(f"Normal play order: {self.play_order}")

    def set_play_mode(self, mode: str):
        if mode not in [self.MODE_NORMAL, self.MODE_SHUFFLE]:
            return

        old_mode = self.play_mode
        self.play_mode = mode
        debug_print(f"Play mode changed: {old_mode} -> {mode}")

        if mode == self.MODE_SHUFFLE and old_mode != self.MODE_SHUFFLE:
            self._update_play_order()
            debug_print("Play order reshuffled")
        elif mode == self.MODE_NORMAL and old_mode != self.MODE_NORMAL:
            self._update_play_order()
            debug_print("Play order reset to normal")

    def get_play_mode(self) -> str:
        return self.play_mode

    def load_bgm(self, bgm_path: str) -> bool:
        if not self._ensure_initialized():
            debug_print("[BGM] Driver not available")
            return False

        if not os.path.exists(bgm_path):
            debug_print(f"[BGM] BGM file not found: {bgm_path}")
            return False

        result = self.driver.load(bgm_path)
        if not result and self.driver_name != self.DRIVER_PYXEL:
            debug_print(f"[BGM] Falling back to '{self.DRIVER_PYXEL}' after load failure")
            self._shutdown_current_driver()
            self.driver_name = self.DRIVER_PYXEL
            self.driver = self._create_driver(self.driver_name)
            self._driver_initialized = False
            if self._ensure_initialized():
                result = self.driver.load(bgm_path)
        if result:
            self.current_bgm = bgm_path
        return result

    def play(self, loops: int = 0):
        if not self._ensure_initialized():
            debug_print("[BGM] Cannot play: driver not available")
            return

        if not self.enabled:
            debug_print("[BGM] BGM is disabled, not playing")
            return

        if not self.playlist:
            self.build_playlist()

        if not self.playlist:
            debug_print("[BGM] No tracks in playlist")
            return

        self._play_current_track()

    def _play_current_track(self):
        if not self.play_order:
            return

        if self.current_index >= len(self.play_order):
            self.current_index = 0

        track_index = self.play_order[self.current_index]
        track_path = self.playlist[track_index]

        debug_print(f"[BGM] Playing track {self.current_index + 1}/{len(self.play_order)}: {os.path.basename(track_path)}")

        if self.load_bgm(track_path):
            try:
                self.driver.set_volume(self.volume)
                self.driver.play()
                self.is_playing = True
                debug_print(f"[BGM] BGM playback started")
            except Exception as e:
                debug_print(f"[BGM] Failed to play BGM: {e}")
                import traceback
                traceback.print_exc()

    def play_next(self):
        if not self.playlist:
            return

        self.current_index += 1
        if self.current_index >= len(self.play_order):
            self.current_index = 0
            debug_print("Playlist finished, restarting from beginning")

        self._play_current_track()

    def play_prev(self):
        if not self.playlist:
            return

        self.current_index -= 1
        if self.current_index < 0:
            self.current_index = len(self.play_order) - 1
            debug_print("Playlist beginning, wrapping to end")

        self._play_current_track()

    def check_music_end(self):
        if not self._driver_initialized or not self.enabled or not self.is_playing:
            return

        self.frame_counter += 1
        if self.frame_counter < self.check_interval:
            return
        self.frame_counter = 0

        if self.driver.is_music_ended():
            debug_print("[BGM] Track ended, playing next")
            self.play_next()

    def stop(self, release_driver: bool = False):
        try:
            debug_print("[BGM] Stopping playback")
            self.driver.stop()
            if release_driver:
                self._shutdown_current_driver()
                self._driver_initialized = False
            self.is_playing = False
            debug_print("[BGM] BGM stopped successfully")
        except Exception as e:
            debug_print(f"[BGM] Failed to stop BGM: {e}")

    def pause(self):
        try:
            self.driver.pause()
            self.is_playing = False
            debug_print("[BGM] BGM paused")
        except Exception as e:
            debug_print(f"[BGM] Failed to pause BGM: {e}")

    def unpause(self):
        try:
            self.driver.unpause()
            self.is_playing = True
            debug_print("[BGM] BGM unpaused")
        except Exception as e:
            debug_print(f"[BGM] Failed to unpause BGM: {e}")

    def set_volume(self, volume: float):
        self.volume = max(0.0, min(1.0, volume))

        if not self._driver_initialized:
            return

        self.driver.set_volume(self.volume)
        debug_print(f"[BGM] BGM volume set to: {self.volume}")

    def set_enabled(self, enabled: bool):
        self.enabled = enabled

        if enabled:
            if not self.is_playing:
                self.play()
                debug_print("[BGM] BGM enabled and started")
        else:
            if self.is_playing:
                self.stop()
                debug_print("[BGM] BGM disabled and stopped")

    def get_volume(self) -> float:
        return self.volume

    def is_enabled(self) -> bool:
        return self.enabled

    def is_bgm_playing(self) -> bool:
        return self.is_playing

    def get_current_track_name(self) -> str:
        if self.current_bgm:
            return os.path.basename(self.current_bgm)
        return ""

    def get_playlist_info(self) -> str:
        if not self.playlist:
            return "No playlist"
        return f"{self.current_index + 1}/{len(self.playlist)}"

    def set_bgm_directory(self, directory: str):
        self.bgm_directory = directory
        debug_print(f"[BGM] BGM directory set to: {directory}")


# Global instance
_bgm_manager = None


def get_bgm_manager() -> BGMManager:
    """Get the global BGM manager instance."""
    global _bgm_manager
    if _bgm_manager is None:
        _bgm_manager = BGMManager()
    return _bgm_manager


def init_bgm(bgm_path: str = None, auto_play: bool = True):
    """
    Initialize BGM system (playlist mode)

    Args:
        bgm_path: Path to BGM file (kept for compatibility, not used)
        auto_play: Whether to auto-play after initialization (only if enabled is True)
    """
    manager = get_bgm_manager()

    # Build playlist
    manager.build_playlist()

    # Play only if enabled is True and auto_play is True
    if auto_play and manager.is_enabled() and manager.playlist:
        manager.play()


# Example usage
if __name__ == "__main__":
    manager = BGMManager()
    print(f"BGM Manager initialized: {manager.is_enabled()}")
    manager.build_playlist()
    print(f"Playlist: {len(manager.playlist)} tracks")
