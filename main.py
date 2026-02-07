"""
Main entry point for Pyxel ROM Launcher.
"""

import time
_start_time = time.time()
def _log_time(label):
    from debug import debug_print
    debug_print(f"[STARTUP] {label}: {(time.time() - _start_time)*1000:.0f}ms")

_log_time("Before imports")
import pyxel
_log_time("pyxel imported")
from config import Config
from state_manager import StateManager, AppState
from input_handler import InputHandler
from rom_manager import ROMManager
from launcher import Launcher
from persistence import PersistenceManager
_log_time("Core modules imported")
from ui.splash import Splash
from ui.main_menu import MainMenu
from ui.file_list import FileList
from ui.core_select import CoreSelect
from ui.favorites import Favorites
from ui.recent import Recent
from ui.search import Search
from ui.settings import Settings
from ui.wifi_settings import WiFiSettings
from ui.key_config_menu import KeyConfigMenu
from ui.key_config import KeyConfig
from ui.bgm_config import BGMConfig
from ui.datetime_settings import DateTimeSettings
from ui.statistics import Statistics
from ui.about import About
from ui.quit_menu import QuitMenu
from ui.components import Toast
_log_time("UI modules imported")
from japanese_text import init_japanese_text
from theme_manager import get_theme_manager, init_theme
from system_monitor import init_system_monitor, get_system_monitor
from bgm_manager import init_bgm, get_bgm_manager
from debug import debug_print
_log_time("All imports done")


class ROMApp:
    """Main application class for ROM Launcher."""

    def _get_screen_resolution(self):
        """Load screen resolution from settings.json"""
        import json
        import os
        settings_file = "data/settings.json"
        resolution = "1:1"  # Default

        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    resolution = data.get("settings", {}).get("resolution", "1:1")
            except:
                pass

        # Map resolution to actual dimensions
        if resolution == "4:3":
            return 214, 160
        else:  # "1:1" or default
            return 160, 160

    def __init__(self):
        _log_time("Start __init__")

        # Load resolution setting before Pyxel init
        screen_width, screen_height = self._get_screen_resolution()
        _log_time(f"Resolution loaded: {screen_width}x{screen_height}")

        # Initialize Pyxel with configured resolution
        pyxel.init(screen_width, screen_height, title="ROM Launcher", fps=30)
        _log_time("Pyxel init")

        # Load configuration first
        self.config = Config("data/pfe.cfg")
        _log_time("Config loaded")

        # Initialize Japanese text support with custom font
        font_path = self.config.get_font_path()
        init_japanese_text(font_path=font_path if font_path else None)
        _log_time("Japanese text init")

        # Initialize managers (persistence must be first for settings loading)
        self.persistence = PersistenceManager()
        self.state_manager = StateManager()

        # Get button layout from settings.json (default: NINTENDO)
        settings = self.persistence.load_settings()
        button_layout = settings.get('button_layout', 'NINTENDO')
        debug_print(f"Button layout: {button_layout}")

        self.input_handler = InputHandler(button_layout)
        self.rom_manager = ROMManager()
        self.launcher = Launcher(self.config)
        _log_time("Managers init")

        # Initialize theme system (after persistence)
        settings = self.persistence.load_settings()
        theme_id = settings.get("theme", "dark")
        init_theme(theme_id)
        self.theme_manager = get_theme_manager()
        _log_time("Theme init")

        # Initialize system monitor
        self.system_monitor = init_system_monitor(self.config)
        _log_time("System monitor init")

        # Get BGM manager
        self.bgm_manager = get_bgm_manager()
        # Set BGM directory from config
        self.bgm_manager.set_bgm_directory(self.config.get_bgm_dir())
        _log_time("BGM manager get")

        # Load BGM settings
        settings = self.persistence.load_settings()
        bgm_enabled = settings.get("bgm_enabled", "On") == "On"
        bgm_volume_str = settings.get("bgm_volume", "5")
        try:
            bgm_volume = int(bgm_volume_str) / 10.0
        except:
            bgm_volume = 0.5
        bgm_mode = settings.get("bgm_mode", "Normal")

        # Apply BGM settings first (enabled flag, volume, play mode)
        # Note: Actual mixer operations are deferred to delay pygame import
        self.bgm_manager.enabled = bgm_enabled
        self.bgm_manager.set_volume(bgm_volume)
        self.bgm_manager.set_play_mode(bgm_mode)

        # Defer BGM initialization until after splash screen
        self._bgm_auto_play = bgm_enabled
        self._bgm_initialized = False
        _log_time("BGM settings saved (deferred init)")

        # Apply screen brightness
        from brightness_manager import get_brightness_manager
        self.brightness_manager = get_brightness_manager()
        if self.brightness_manager.is_available():
            brightness_str = settings.get("brightness", "5")
            try:
                brightness = int(brightness_str)
                brightness = max(1, min(10, brightness))
            except:
                brightness = 5
            self.brightness_manager.set_brightness(brightness)
            debug_print(f"Brightness set to: {brightness}")
        _log_time("Brightness init")

        # UI screens - lazy initialization (initialized when needed)
        self._splash = None
        self._main_menu = None
        self._file_list = None
        self._core_select = None
        self._favorites = None
        self._recent = None
        self._search = None
        self._settings = None
        self._wifi_settings = None
        self._key_config_menu = None
        self._key_config = None
        self._bgm_config = None
        self._datetime_settings = None
        self._statistics = None
        self._about = None
        self._quit_menu = None
        _log_time("UI screens init (lazy)")

        # UI components
        self.toast = Toast()

        # Restore session state (state is saved in state_data and applied after splash)
        self._restore_session()
        _log_time("Session restored")

        # Always start from splash screen
        self.state_manager.current_state = AppState.SPLASH
        self.splash.activate()

        # Launch request handling
        self.pending_launch = False

        # Screen update optimization (skip drawing when no input or animation)
        self._needs_redraw = True  # Always draw on first frame
        self._redraw_interval = 30  # Force redraw every 30 frames (for clock update)
        self._redraw_counter = 0
        _log_time("Init complete")

    # Lazy initialization properties for UI screens
    @property
    def splash(self):
        if self._splash is None:
            self._splash = Splash(self.input_handler, self.state_manager, self.config)
        return self._splash

    @property
    def main_menu(self):
        if self._main_menu is None:
            self._main_menu = MainMenu(self.input_handler, self.state_manager, self.config, self.persistence)
        return self._main_menu

    @property
    def file_list(self):
        if self._file_list is None:
            self._file_list = FileList(self.input_handler, self.state_manager, self.config, self.rom_manager, self.persistence)
        return self._file_list

    @property
    def core_select(self):
        if self._core_select is None:
            self._core_select = CoreSelect(self.input_handler, self.state_manager, self.persistence)
        return self._core_select

    @property
    def favorites(self):
        if self._favorites is None:
            self._favorites = Favorites(self.input_handler, self.state_manager, self.config, self.persistence)
        return self._favorites

    @property
    def recent(self):
        if self._recent is None:
            self._recent = Recent(self.input_handler, self.state_manager, self.config, self.persistence)
        return self._recent

    @property
    def search(self):
        if self._search is None:
            self._search = Search(self.input_handler, self.state_manager, self.config, self.rom_manager, self.persistence)
        return self._search

    @property
    def settings(self):
        if self._settings is None:
            self._settings = Settings(self.input_handler, self.state_manager, self.config, self.persistence)
        return self._settings

    @property
    def wifi_settings(self):
        if self._wifi_settings is None:
            self._wifi_settings = WiFiSettings(self.input_handler, self.state_manager, self.config)
        return self._wifi_settings

    @property
    def key_config_menu(self):
        if self._key_config_menu is None:
            self._key_config_menu = KeyConfigMenu(self.input_handler, self.state_manager, self.persistence)
        return self._key_config_menu

    @property
    def key_config(self):
        if self._key_config is None:
            self._key_config = KeyConfig(self.input_handler, self.state_manager, self.config)
        return self._key_config

    @property
    def bgm_config(self):
        if self._bgm_config is None:
            self._bgm_config = BGMConfig(self.input_handler, self.state_manager, self.persistence)
        return self._bgm_config

    @property
    def datetime_settings(self):
        if self._datetime_settings is None:
            self._datetime_settings = DateTimeSettings(self.input_handler, self.state_manager, self.config)
        return self._datetime_settings

    @property
    def statistics(self):
        if self._statistics is None:
            self._statistics = Statistics(self.input_handler, self.state_manager, self.config, self.persistence)
        return self._statistics

    @property
    def about(self):
        if self._about is None:
            self._about = About(self.input_handler, self.state_manager, self.config)
        return self._about

    @property
    def quit_menu(self):
        if self._quit_menu is None:
            self._quit_menu = QuitMenu(self.input_handler, self.state_manager, self.config)
        return self._quit_menu

    def _deactivate_all_except(self, exclude_attr):
        """Deactivate all initialized screens except the specified one."""
        screens = [
            '_splash', '_main_menu', '_file_list', '_core_select',
            '_favorites', '_recent', '_search', '_settings',
            '_wifi_settings', '_key_config_menu', '_key_config', '_bgm_config', '_datetime_settings',
            '_statistics', '_about', '_quit_menu'
        ]
        for attr in screens:
            if attr != exclude_attr:
                screen = getattr(self, attr)
                if screen is not None:
                    screen.deactivate()

    def _check_any_input(self) -> bool:
        """Check if any input was detected."""
        from input_handler import Action
        for action in Action:
            if self.input_handler.is_held(action):
                return True
        return False

    def update(self):
        """Update game logic."""
        # Get current state
        current_state = self.state_manager.get_state()

        # Deferred BGM initialization: Initialize after splash screen ends
        if not self._bgm_initialized and current_state != AppState.SPLASH:
            self._bgm_initialized = True
            debug_print("[STARTUP] Deferred BGM initialization starting...")
            init_bgm(auto_play=self._bgm_auto_play)
            debug_print("[STARTUP] Deferred BGM initialization complete")

        # Check if BGM track ended (advance to next track)
        if self._bgm_initialized:
            self.bgm_manager.check_music_end()

        # Check input (for redraw decision)
        has_input = self._check_any_input()
        if has_input:
            self._needs_redraw = True

        # Periodic forced redraw (for clock and battery display updates)
        self._redraw_counter += 1
        if self._redraw_counter >= self._redraw_interval:
            self._redraw_counter = 0
            self._needs_redraw = True

        # Handle pending ROM launch
        if self.pending_launch:
            self._handle_launch()
            self.pending_launch = False
            return

        # Check if we need to launch a ROM
        rom_to_launch = self.state_manager.get_data('rom_to_launch')
        if rom_to_launch:
            self.pending_launch = True
            return

        # Update active screen
        if current_state == AppState.SPLASH:
            if not self.splash.active:
                self._deactivate_all_except('_splash')
                self.splash.activate()
            self.splash.update()

        elif current_state == AppState.MAIN_MENU:
            if not self.main_menu.active:
                self._deactivate_all_except('_main_menu')
                self.main_menu.activate()
            self.main_menu.update()

        elif current_state == AppState.FILE_LIST:
            if not self.file_list.active:
                self._deactivate_all_except('_file_list')
                self.file_list.activate()
            self.file_list.update()

        elif current_state == AppState.CORE_SELECT:
            if not self.core_select.active:
                self._deactivate_all_except('_core_select')
                self.core_select.activate()
            self.core_select.update()

        elif current_state == AppState.FAVORITES:
            if not self.favorites.active:
                self._deactivate_all_except('_favorites')
                self.favorites.activate()
            self.favorites.update()

        elif current_state == AppState.RECENT:
            if not self.recent.active:
                self._deactivate_all_except('_recent')
                self.recent.activate()
            self.recent.update()

        elif current_state == AppState.SEARCH:
            if not self.search.active:
                self._deactivate_all_except('_search')
                self.search.activate()
            self.search.update()

        elif current_state == AppState.SETTINGS:
            if not self.settings.active:
                self._deactivate_all_except('_settings')
                self.settings.activate()
            self.settings.update()

        elif current_state == AppState.WIFI_SETTINGS:
            if not self.wifi_settings.active:
                self._deactivate_all_except('_wifi_settings')
                self.wifi_settings.activate()
            self.wifi_settings.update()

        elif current_state == AppState.KEY_CONFIG_MENU:
            if not self.key_config_menu.active:
                self._deactivate_all_except('_key_config_menu')
                self.key_config_menu.activate()
            self.key_config_menu.update()

        elif current_state == AppState.KEY_CONFIG:
            if not self.key_config.active:
                self._deactivate_all_except('_key_config')
                self.key_config.activate()
            self.key_config.update()

        elif current_state == AppState.BGM_CONFIG:
            if not self.bgm_config.active:
                self._deactivate_all_except('_bgm_config')
                self.bgm_config.activate()
            self.bgm_config.update()

        elif current_state == AppState.DATETIME_SETTINGS:
            if not self.datetime_settings.active:
                self._deactivate_all_except('_datetime_settings')
                self.datetime_settings.activate()
            self.datetime_settings.update()

        elif current_state == AppState.STATISTICS:
            if not self.statistics.active:
                self._deactivate_all_except('_statistics')
                self.statistics.activate()
            self.statistics.update()

        elif current_state == AppState.ABOUT:
            if not self.about.active:
                self._deactivate_all_except('_about')
                self.about.activate()
            self.about.update()

        elif current_state == AppState.QUIT_MENU:
            if not self.quit_menu.active:
                self._deactivate_all_except('_quit_menu')
                self.quit_menu.activate()
            self.quit_menu.update()

        # Update toast notifications
        self.toast.update()

        # Redraw is needed during animations
        # While toast is displayed
        if self.toast.duration > 0:
            self._needs_redraw = True

        # Splash screen animation
        if current_state == AppState.SPLASH:
            self._needs_redraw = True

        # Gallery mode animation and slideshow
        if current_state == AppState.FILE_LIST and self._file_list is not None:
            if self._file_list.view_mode == "gallery":
                # Redraw during slide animation
                if abs(self._file_list.gallery_animation_offset) > 0.01:
                    self._needs_redraw = True
                # During slideshow, only redraw when switching images
                # (Periodic clock updates are handled by _redraw_interval)
                if self._file_list.slideshow_active:
                    # Just before or after switch (when timer is reset to 0)
                    if self._file_list.slideshow_timer <= 1:
                        self._needs_redraw = True

    def _restore_session(self):
        """Restore session state (saved to state_data for application after splash)."""
        session_state = self.persistence.load_session_state()
        debug_print(f"[RESTORE_SESSION] session_state={session_state}")
        if session_state:
            # Save the state to restore (applied after splash screen closes)
            state_name = session_state.get('current_state')
            if state_name:
                try:
                    restored_state = AppState(state_name)
                    # Save as the state to transition to after splash
                    self.state_manager.set_data('post_splash_state', restored_state)

                    # If FILE_LIST state, add MAIN_MENU to history (so B button can go back)
                    if restored_state == AppState.FILE_LIST:
                        self.state_manager.state_history = [AppState.MAIN_MENU]
                except:
                    pass

            # Restore category positions
            category_positions = session_state.get('category_positions', {})
            self.state_manager.state_data['category_positions'] = category_positions

            # Restore selected category
            selected_category = session_state.get('selected_category')
            if selected_category:
                self.state_manager.set_selected_category(selected_category)

            # Restore subdirectory info (empty string is also a valid value)
            launch_subdirectory = session_state.get('launch_subdirectory')
            launch_directory_stack = session_state.get('launch_directory_stack')
            launch_selected_index = session_state.get('launch_selected_index', 0)
            launch_scroll_offset = session_state.get('launch_scroll_offset', 0)
            debug_print(f"[RESTORE_SESSION] launch_subdirectory={launch_subdirectory}, launch_directory_stack={launch_directory_stack}")
            debug_print(f"[RESTORE_SESSION] launch_selected_index={launch_selected_index}, launch_scroll_offset={launch_scroll_offset}")
            if launch_subdirectory is not None:
                self.state_manager.set_data('launch_subdirectory', launch_subdirectory)
                self.state_manager.set_data('launch_directory_stack', launch_directory_stack)
                self.state_manager.set_data('launch_selected_index', launch_selected_index)
                self.state_manager.set_data('launch_scroll_offset', launch_scroll_offset)
                debug_print(f"[RESTORE_SESSION] Subdirectory and cursor info set to state_manager")

            print("Session restored")

    def _save_session(self):
        """Save session state."""
        # Call deactivate to save current screen state
        current_state = self.state_manager.get_state()
        debug_print(f"[SAVE_SESSION] current_state={current_state}, _file_list={self._file_list is not None}")
        if self._file_list is not None:
            debug_print(f"[SAVE_SESSION] file_list.active={self._file_list.active}, view_mode={self._file_list.view_mode}")
        if current_state == AppState.FILE_LIST and self._file_list is not None and self._file_list.active:
            debug_print("[SAVE_SESSION] Calling file_list.deactivate()")
            self._file_list.deactivate()

        # Don't save SPLASH state (start from MAIN_MENU on next launch)
        state_to_save = self.state_manager.current_state.value
        if self.state_manager.current_state == AppState.SPLASH:
            state_to_save = AppState.MAIN_MENU.value

        # Get subdirectory info and cursor position
        launch_subdirectory = None
        launch_directory_stack = None
        launch_selected_index = 0
        launch_scroll_offset = 0
        if self._file_list is not None:
            launch_subdirectory = self._file_list.current_subdirectory
            launch_directory_stack = self._file_list.directory_stack.copy() if self._file_list.directory_stack else []
            launch_selected_index = self._file_list.selected_index
            launch_scroll_offset = self._file_list.scroll_offset
            debug_print(f"[SAVE_SESSION] launch_subdirectory={launch_subdirectory}, launch_directory_stack={launch_directory_stack}")
            debug_print(f"[SAVE_SESSION] launch_selected_index={launch_selected_index}, launch_scroll_offset={launch_scroll_offset}")

        session_state = {
            'current_state': state_to_save,
            'selected_category': self.state_manager.get_selected_category(),
            'category_positions': self.state_manager.state_data.get('category_positions', {}),
            'launch_subdirectory': launch_subdirectory,
            'launch_directory_stack': launch_directory_stack,
            'launch_selected_index': launch_selected_index,
            'launch_scroll_offset': launch_scroll_offset
        }
        self.persistence.save_session_state(session_state)

    def _handle_launch(self):
        """Handle ROM launch."""
        rom_to_launch = self.state_manager.get_data('rom_to_launch')
        launch_category = self.state_manager.get_data('launch_category')

        if rom_to_launch and launch_category:
            # Get core override if any (from core selection screen)
            core = self.state_manager.get_temp_core_override()

            # If no override, check for last used core for this ROM
            if not core:
                last_core = self.persistence.get_last_core(rom_to_launch.path)
                if last_core and last_core in launch_category.cores:
                    core = last_core
                    print(f"Using last core for this ROM: {core}")

            # Show launching message
            print(f"Launching: {rom_to_launch.name}")
            self.toast.show(f"Launching {rom_to_launch.name}...", duration=90)

            # Launch ROM
            success = self.launcher.launch_rom(rom_to_launch, launch_category, core)

            if success:
                print("ROM launched successfully")

                # Determine actual core used
                core_name = core if core else (launch_category.cores[0] if launch_category.cores else "unknown")

                # Save core choice for this ROM (for next time)
                if core_name:
                    self.persistence.save_core_choice(rom_to_launch.path, core_name)

                # Add to play history
                self.persistence.add_to_history(
                    rom_to_launch.path,
                    launch_category.name,
                    core_name
                )

                # Save session state (for restoration after restart)
                self._save_session()

                # Exit PFE (restart required due to KMS/DRM display constraints)
                # launcher.sh will restart PFE and the session will be restored
                pyxel.quit()
            else:
                error = self.launcher.get_last_error()
                print(f"Launch failed: {error}")
                self.toast.show(f"Launch failed: {error}", duration=120)

            # Clear launch data
            self.state_manager.set_data('rom_to_launch', None)
            self.state_manager.set_data('launch_category', None)
            self.state_manager.set_temp_core_override(None)

    def draw(self):
        """Draw graphics."""
        # Skip if redraw is not needed (reduce CPU load)
        if not self._needs_redraw:
            return

        # Reset redraw flag (will be evaluated again next frame)
        self._needs_redraw = False

        # Clear screen
        pyxel.cls(0)

        # Draw active screen
        current_state = self.state_manager.get_state()

        if current_state == AppState.SPLASH:
            self.splash.draw()
        elif current_state == AppState.MAIN_MENU:
            self.main_menu.draw()
        elif current_state == AppState.FILE_LIST:
            self.file_list.draw()
        elif current_state == AppState.CORE_SELECT:
            self.core_select.draw()
        elif current_state == AppState.FAVORITES:
            self.favorites.draw()
        elif current_state == AppState.RECENT:
            self.recent.draw()
        elif current_state == AppState.SEARCH:
            self.search.draw()
        elif current_state == AppState.SETTINGS:
            self.settings.draw()
        elif current_state == AppState.WIFI_SETTINGS:
            self.wifi_settings.draw()
        elif current_state == AppState.KEY_CONFIG_MENU:
            self.key_config_menu.draw()
        elif current_state == AppState.KEY_CONFIG:
            self.key_config.draw()
        elif current_state == AppState.BGM_CONFIG:
            self.bgm_config.draw()
        elif current_state == AppState.DATETIME_SETTINGS:
            self.datetime_settings.draw()
        elif current_state == AppState.STATISTICS:
            self.statistics.draw()
        elif current_state == AppState.ABOUT:
            self.about.draw()
        elif current_state == AppState.QUIT_MENU:
            self.quit_menu.draw()

        # Draw toast on top (adjusted to screen size)
        self.toast.draw(pyxel.width, pyxel.height)

    def run(self):
        """Start the application."""
        debug_print("ROM Launcher started")
        debug_print(f"Loaded {len(self.config.get_categories())} categories")
        pyxel.run(self.update, self.draw)


def main():
    """Main entry point."""
    app = ROMApp()
    app.run()


if __name__ == "__main__":
    main()
