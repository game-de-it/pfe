"""
BGM manager for background music playback.
Uses pygame.mixer for mp3/wav support.
Supports playlist with normal and shuffle modes.

Note: pygame is lazy-imported (to reduce startup time due to numpy dependency)
"""

import os
import random
from debug import debug_print

# Global variables for lazy import
_mixer_module = None
_mixer_import_attempted = False


def _get_mixer():
    """Lazy import pygame.mixer module"""
    global _mixer_module, _mixer_import_attempted

    if _mixer_import_attempted:
        return _mixer_module

    _mixer_import_attempted = True
    try:
        debug_print("[BGM] Lazy importing pygame.mixer...")
        import pygame.mixer as mixer
        _mixer_module = mixer
        debug_print("[BGM] pygame.mixer imported successfully")
    except ImportError:
        debug_print("[BGM] Warning: pygame not installed. BGM feature disabled.")
        _mixer_module = None

    return _mixer_module


def _is_mixer_available():
    """Check if mixer is available (without lazy import)"""
    return _mixer_module is not None


class BGMManager:
    """Manages background music playback with playlist support."""

    # Playback modes
    MODE_NORMAL = "Normal"
    MODE_SHUFFLE = "Shuffle"

    def __init__(self):
        self.enabled = True
        self.volume = 0.5  # 0.0 ~ 1.0
        self.current_bgm = None
        self.is_playing = False

        # Playlist related
        self.playlist = []  # Selected track list
        self.play_order = []  # Actual playback order (shuffled when in shuffle mode)
        self.current_index = 0  # Index of currently playing track
        self.play_mode = self.MODE_NORMAL  # Playback mode
        self.bgm_directory = "assets/bgm"
        self.max_playlist_size = 300  # Maximum playlist size

        # Frame counter for end-of-track check (to reduce CPU load)
        self.check_interval = 30  # Check every 30 frames (approximately 1 second)
        self.frame_counter = 0

        # Lazy initialization flag
        self._mixer_initialized = False
        self.END_EVENT = None

    def _ensure_mixer_initialized(self):
        """Initialize mixer if necessary"""
        if self._mixer_initialized:
            return _is_mixer_available()

        self._mixer_initialized = True
        mixer = _get_mixer()

        if mixer is not None:
            try:
                # Initialize mixer
                mixer.init(frequency=44100, size=-16, channels=2, buffer=8192)
                init_info = mixer.get_init()
                debug_print(f"[BGM] BGM Manager initialized (buffer=8192)")
                debug_print(f"[BGM] Mixer init info: frequency={init_info[0]}, format={init_info[1]}, channels={init_info[2]}")

                # Set end-of-track event
                self.END_EVENT = mixer.music.get_endevent()
                if self.END_EVENT == 0:
                    # Set event if not already set
                    import pygame
                    self.END_EVENT = pygame.USEREVENT + 1
                    mixer.music.set_endevent(self.END_EVENT)
                debug_print(f"[BGM] Music end event set: {self.END_EVENT}")
                return True
            except Exception as e:
                debug_print(f"[BGM] Failed to initialize mixer: {e}")
                import traceback
                traceback.print_exc()
                self.enabled = False
                return False
        else:
            self.enabled = False
            return False

    def scan_bgm_files(self) -> list:
        """
        Recursively search for mp3/wav files in BGM directory (including subdirectories)

        Returns:
            List of paths to found music files
        """
        if not os.path.exists(self.bgm_directory):
            debug_print(f"BGM directory not found: {self.bgm_directory}")
            return []

        bgm_files = []
        for root, dirs, files in os.walk(self.bgm_directory):
            for filename in files:
                if filename.lower().endswith(('.mp3', '.wav')):
                    bgm_files.append(os.path.join(root, filename))

        debug_print(f"Found {len(bgm_files)} BGM files in {self.bgm_directory} (including subdirectories)")
        return bgm_files

    def build_playlist(self):
        """
        Build playlist (randomly select up to max_playlist_size tracks)
        """
        all_files = self.scan_bgm_files()

        if not all_files:
            debug_print("No BGM files found")
            self.playlist = []
            self.play_order = []
            return

        # Randomly select up to max_playlist_size tracks
        if len(all_files) <= self.max_playlist_size:
            self.playlist = all_files[:]
        else:
            self.playlist = random.sample(all_files, self.max_playlist_size)

        debug_print(f"Playlist built with {len(self.playlist)} tracks:")
        for i, track in enumerate(self.playlist):
            debug_print(f"  {i+1}. {os.path.basename(track)}")

        # Set playback order
        self._update_play_order()

    def _update_play_order(self):
        """
        Update playback order (according to mode)
        """
        if not self.playlist:
            self.play_order = []
            return

        if self.play_mode == self.MODE_SHUFFLE:
            # Shuffle mode: randomize order
            self.play_order = list(range(len(self.playlist)))
            random.shuffle(self.play_order)
            debug_print(f"Shuffle play order: {self.play_order}")
        else:
            # Normal mode: sequential order
            self.play_order = list(range(len(self.playlist)))
            debug_print(f"Normal play order: {self.play_order}")

    def set_play_mode(self, mode: str):
        """
        Set playback mode

        Args:
            mode: MODE_NORMAL or MODE_SHUFFLE
        """
        if mode not in [self.MODE_NORMAL, self.MODE_SHUFFLE]:
            return

        old_mode = self.play_mode
        self.play_mode = mode
        debug_print(f"Play mode changed: {old_mode} -> {mode}")

        # Update play order when switching to shuffle mode
        if mode == self.MODE_SHUFFLE and old_mode != self.MODE_SHUFFLE:
            self._update_play_order()
            debug_print("Play order reshuffled")
        elif mode == self.MODE_NORMAL and old_mode != self.MODE_NORMAL:
            self._update_play_order()
            debug_print("Play order reset to normal")

    def get_play_mode(self) -> str:
        """Get current playback mode"""
        return self.play_mode

    def load_bgm(self, bgm_path: str) -> bool:
        """
        Load BGM file

        Args:
            bgm_path: Path to BGM file (mp3/wav)

        Returns:
            True if successful
        """
        if not self._ensure_mixer_initialized():
            debug_print("[BGM] pygame.mixer not available")
            return False

        mixer = _get_mixer()
        if not os.path.exists(bgm_path):
            debug_print(f"[BGM] BGM file not found: {bgm_path}")
            return False

        try:
            mixer.music.load(bgm_path)
            self.current_bgm = bgm_path
            debug_print(f"[BGM] BGM loaded successfully: {bgm_path}")
            return True
        except Exception as e:
            debug_print(f"[BGM] Failed to load BGM: {e}")
            return False

    def play(self, loops: int = 0):
        """
        Play BGM (from playlist)

        Args:
            loops: Number of loops (0 for single play, -1 for infinite loop)
        """
        if not self._ensure_mixer_initialized():
            debug_print("[BGM] Cannot play: pygame.mixer not available")
            return

        if not self.enabled:
            debug_print("[BGM] BGM is disabled, not playing")
            return

        # Build playlist if empty
        if not self.playlist:
            self.build_playlist()

        if not self.playlist:
            debug_print("[BGM] No tracks in playlist")
            return

        # Load and play current track
        self._play_current_track()

    def _play_current_track(self):
        """Play track at current index"""
        if not self.play_order:
            return

        mixer = _get_mixer()
        if mixer is None:
            return

        # Reset to beginning if index is out of range
        if self.current_index >= len(self.play_order):
            self.current_index = 0

        track_index = self.play_order[self.current_index]
        track_path = self.playlist[track_index]

        debug_print(f"[BGM] Playing track {self.current_index + 1}/{len(self.play_order)}: {os.path.basename(track_path)}")

        if self.load_bgm(track_path):
            try:
                mixer.music.set_volume(self.volume)
                mixer.music.play(loops=0)  # Play once (event fires on end)
                self.is_playing = True
                debug_print(f"[BGM] BGM playback started")
            except Exception as e:
                debug_print(f"[BGM] Failed to play BGM: {e}")
                import traceback
                traceback.print_exc()

    def play_next(self):
        """Play next track"""
        if not self.playlist:
            return

        self.current_index += 1
        if self.current_index >= len(self.play_order):
            # Loop back to beginning when playlist ends
            self.current_index = 0
            debug_print("Playlist finished, restarting from beginning")

        self._play_current_track()

    def check_music_end(self):
        """
        Check for end of track and play next track.
        Called every frame, but actual check only every 30 frames (to reduce CPU load)
        """
        if not self._mixer_initialized or not self.enabled or not self.is_playing:
            return

        mixer = _get_mixer()
        if mixer is None:
            return

        # Increment frame counter
        self.frame_counter += 1
        if self.frame_counter < self.check_interval:
            return
        self.frame_counter = 0

        # Track has ended if mixer.music.get_busy() returns False
        if not mixer.music.get_busy():
            debug_print("[BGM] Track ended, playing next")
            self.play_next()

    def stop(self):
        """Stop BGM"""
        mixer = _get_mixer()
        if mixer is None:
            debug_print("[BGM] Cannot stop: pygame.mixer not available")
            return

        try:
            debug_print("[BGM] Calling mixer.music.stop()")
            mixer.music.stop()
            self.is_playing = False
            debug_print("[BGM] BGM stopped successfully")
        except Exception as e:
            debug_print(f"[BGM] Failed to stop BGM: {e}")
            import traceback
            traceback.print_exc()

    def pause(self):
        """Pause BGM"""
        mixer = _get_mixer()
        if mixer is None:
            return

        try:
            mixer.music.pause()
            self.is_playing = False
            debug_print("[BGM] BGM paused")
        except Exception as e:
            debug_print(f"[BGM] Failed to pause BGM: {e}")

    def unpause(self):
        """Resume BGM"""
        mixer = _get_mixer()
        if mixer is None:
            return

        try:
            mixer.music.unpause()
            self.is_playing = True
            debug_print("[BGM] BGM unpaused")
        except Exception as e:
            debug_print(f"[BGM] Failed to unpause BGM: {e}")

    def set_volume(self, volume: float):
        """
        Set volume

        Args:
            volume: Volume level (0.0 ~ 1.0)
        """
        self.volume = max(0.0, min(1.0, volume))

        # Only save value if mixer not initialized (will be applied when playback starts)
        if not self._mixer_initialized:
            return

        mixer = _get_mixer()
        if mixer is None:
            return

        try:
            mixer.music.set_volume(self.volume)
            debug_print(f"[BGM] BGM volume set to: {self.volume}")
        except Exception as e:
            debug_print(f"[BGM] Failed to set volume: {e}")

    def set_enabled(self, enabled: bool):
        """
        Enable/disable BGM

        Args:
            enabled: True to enable
        """
        old_enabled = self.enabled
        self.enabled = enabled

        if enabled:
            # Enable: start playback if playlist exists
            if not self.is_playing:
                self.play()
                debug_print("[BGM] BGM enabled and started")
        else:
            # Disable: stop if currently playing
            if self.is_playing:
                self.stop()
                debug_print("[BGM] BGM disabled and stopped")

    def get_volume(self) -> float:
        """Get current volume"""
        return self.volume

    def is_enabled(self) -> bool:
        """Check if BGM is enabled"""
        return self.enabled

    def is_bgm_playing(self) -> bool:
        """Check if BGM is playing (returns internal flag)"""
        return self.is_playing

    def get_current_track_name(self) -> str:
        """Get name of currently playing track"""
        if self.current_bgm:
            return os.path.basename(self.current_bgm)
        return ""

    def get_playlist_info(self) -> str:
        """Get playlist information"""
        if not self.playlist:
            return "No playlist"
        return f"{self.current_index + 1}/{len(self.playlist)}"

    def set_bgm_directory(self, directory: str):
        """
        Set the BGM directory.

        Args:
            directory: Path to BGM directory
        """
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
