# PFE (Pyxel Frontend) Architecture Document

## 1. Overview

PFE is a ROM launcher built on Pyxel (a retro game engine). It is primarily designed for handheld gaming devices such as Anbernic, providing a feature-rich UI for browsing, searching, and launching ROM files across multiple emulation systems.

### Key Features
- Japanese text support
- Multiple themes (dark, light, retro, neon)
- BGM playback (playlist support)
- Screenshot display
- Favorites and history management
- Session restore
- Custom key configuration

### Tech Stack
- **Python 3.x**
- **Pyxel 2.2.7**: Graphics rendering engine
- **Pillow**: Image processing
- **pygame**: BGM playback (lazy loading)
- **pyxel-universal-font**: Japanese font support

---

## 2. Directory Structure

```
pd/
├── main.py                    # Entry point / main application
├── launcher.py                # ROM launch system
├── config.py                  # Configuration file parser (pfe.cfg)
├── state_manager.py           # UI state management (state machine)
├── input_handler.py           # Input handling (keyboard / gamepad)
├── persistence.py             # Data persistence (JSON)
├── rom_manager.py             # ROM file scanning / filtering
├── theme_manager.py           # Color theme management
├── bgm_manager.py             # BGM playback management
├── system_monitor.py          # System status monitoring (battery / network)
├── brightness_manager.py      # Screen brightness control
├── japanese_text.py           # Japanese text rendering
├── screenshot_loader.py       # Screenshot loading
├── music_mode.py              # Music playback mode
├── debug.py                   # Debug logging utility
├── version.py                 # Version information
│
├── ui/                        # UI components
│   ├── base.py                # Base classes (UIScreen, ScrollableList)
│   ├── components.py          # Reusable UI components
│   ├── window.py              # DQ-style window drawing
│   ├── soft_keyboard.py       # Soft keyboard (for quick jump)
│   ├── software_keyboard.py   # Software keyboard (text input)
│   ├── main_menu.py           # Category selection screen
│   ├── file_list.py           # ROM file browser
│   ├── core_select.py         # Core / emulator selection
│   ├── splash.py              # Splash screen
│   ├── favorites.py           # Favorites screen
│   ├── recent.py              # Recently played ROMs
│   ├── search.py              # ROM search
│   ├── settings.py            # Settings menu
│   ├── wifi_settings.py       # WiFi settings
│   ├── key_config_menu.py     # Key config menu
│   ├── key_config.py          # Key mapping screen
│   ├── bgm_config.py          # BGM settings
│   ├── datetime_settings.py   # Date / time settings
│   ├── statistics.py          # Play statistics
│   ├── about.py               # About screen
│   └── quit_menu.py           # Quit dialog
│
├── data/                      # Configuration / data files
│   ├── pfe.cfg                # Main configuration file
│   ├── session.json           # Session state (generated at runtime)
│   ├── settings.json          # User settings (generated at runtime)
│   ├── favorites.json         # Favorites list
│   ├── history.json           # Play history
│   ├── core_history.json      # Core selection history
│   └── keyconfig.json         # Custom key settings
│
├── assets/                    # Assets
│   ├── screenshots/           # ROM screenshots
│   ├── bgm/                   # BGM files (mp3/wav)
│   ├── themes/                # Color themes
│   └── title/                 # Category title images
│
├── scripts/                   # System integration scripts
│   ├── get_battery.sh         # Get battery status
│   ├── get_network.sh         # Get network status
│   ├── wifi_scan.sh           # WiFi scanning
│   ├── wifi_connect.sh        # WiFi connection
│   ├── set_datetime.sh        # Set date / time
│   └── ...                    # Other system scripts
│
├── bin/                       # External binaries
│   └── retroarch.sh           # RetroArch launcher
│
└── docs/                      # Documentation
    ├── ARCHITECTURE.md        # This file
    └── ARCHITECTURE_JP.md     # Japanese version
```

---

## 3. Core Components

### 3.1 Application Lifecycle

```
launcher.sh (shell wrapper)
    ↓
main.py → ROMApp class
    ├── Load resolution setting (settings.json)
    ├── Initialize Pyxel (160x160 or 214x160)
    ├── Load Config (pfe.cfg)
    ├── Initialize managers:
    │   ├── PersistenceManager (data persistence)
    │   ├── StateManager (state management)
    │   ├── InputHandler (input handling)
    │   ├── ROMManager (ROM management)
    │   ├── Launcher (ROM launching)
    │   ├── ThemeManager (themes)
    │   ├── SystemMonitor (system monitoring)
    │   └── BGMManager (BGM, deferred initialization)
    ├── Restore session
    ├── Initial state: SPLASH
    └── Execute pyxel.run(update, draw)
```

### 3.2 Frame Loop (30 FPS)

```python
def update():
    # 1. Deferred BGM initialization (after splash)
    # 2. Check if BGM track ended (advance to next)
    # 3. Check input (for redraw decision)
    # 4. Periodic forced redraw (for clock update, every 30 frames)
    # 5. Handle ROM launch requests
    # 6. Call active screen's update()
    # 7. Update toast notifications

def draw():
    # Only execute when redraw is needed
    if not self._needs_redraw:
        return
    # 1. Clear screen
    # 2. Call active screen's draw()
    # 3. Draw toast notifications
```

---

## 4. State Management (StateManager)

### 4.1 Application States (AppState)

```python
class AppState(Enum):
    SPLASH            = "splash"            # Splash screen
    MAIN_MENU         = "main_menu"         # Category selection
    FILE_LIST         = "file_list"         # ROM browser (main screen)
    CORE_SELECT       = "core_select"       # Core selection
    FAVORITES         = "favorites"         # Favorites
    RECENT            = "recent"            # Recently played
    SEARCH            = "search"            # Search
    SETTINGS          = "settings"          # Settings
    WIFI_SETTINGS     = "wifi_settings"     # WiFi settings
    KEY_CONFIG_MENU   = "key_config_menu"   # Key config menu
    KEY_CONFIG        = "key_config"        # Key mapping
    BGM_CONFIG        = "bgm_config"        # BGM settings
    DATETIME_SETTINGS = "datetime_settings" # Date / time settings
    STATISTICS        = "statistics"        # Statistics
    ABOUT             = "about"             # About
    QUIT_MENU         = "quit_menu"         # Quit confirmation
```

### 4.2 State Transitions

```
StateManager:
├── current_state: AppState          # Current state
├── state_history: List[AppState]    # History stack (max 10)
├── state_data: Dict                 # Data passing between screens
│
├── change_state(new_state)          # Change state (push to history)
├── go_back()                        # Return to previous state
├── set_data(key, value)             # Set data
└── get_data(key)                    # Get data
```

### 4.3 Category Position Tracking

Remembers cursor position and scroll offset for each category:

```python
category_positions = {
    "Nintendo Entertainment System": {"index": 5, "scroll": 2},
    "MAME": {"index": 10, "scroll": 5},
    ...
}
```

---

## 5. Configuration System (Config)

### 5.1 pfe.cfg Format

```ini
; Comment line (starts with semicolon)

; ========================================
; Global variables
; ========================================
ROM_BASE=/roms                              ; ROM base directory
TYPE_RA=./bin/retroarch.sh                  ; RetroArch launcher
TYPE_SA_PPSSPP=/usr/local/bin/ppsspp        ; Standalone emulator
CORE_PATH=/home/ark/.config/retroarch/cores ; Core library path
DEBUG=true                                  ; Debug mode

; Asset directories
SCREENSHOT_DIR=assets/screenshots           ; Screenshots
BGM_DIR=assets/bgm                          ; BGM files

; System scripts
BATTERY_SCRIPT=./scripts/get_battery.sh
NETWORK_SCRIPT=./scripts/get_network.sh

; ========================================
; Category definitions
; ========================================
-TITLE=Nintendo Entertainment System        ; Display name
-TITLE_IMG=./assets/title/Fc_2.png          ; Title image
-DIR=nes                                    ; ROM directory (relative/absolute)
-EXT=nes,NES,zip,ZIP                        ; Supported extensions
-CORE=nestopia,fceumm,quicknes              ; Available cores
```

### 5.2 Directory Path Resolution

```
-DIR=nes           → ROM_BASE/nes (e.g., /roms/nes)
-DIR=/roms/nes     → /roms/nes (absolute path)
```

### 5.3 Core Path Resolution

```
-CORE=nestopia           → CORE_PATH/nestopia_libretro.so
-CORE=/full/path/core.so → /full/path/core.so (absolute path)
```

---

## 6. ROM Management (ROMManager)

### 6.1 ROMFile Class

```python
class ROMFile:
    path: str           # Full path
    name: str           # Display name
    extension: str      # File extension
    is_directory: bool  # Directory flag
    size: int           # File size (bytes)
```

### 6.2 Key Methods

```python
class ROMManager:
    def scan_category(category, subdirectory=""):
        """Scan ROMs within a category
        - Returns directories and files sorted
        - Supports subdirectories
        """

    def search_roms(query, category):
        """Search ROMs (case-insensitive)"""

    def get_rom_display_name(name, max_width):
        """Display name fitted to width (with ellipsis)"""

    def format_file_size(size):
        """Human-readable size (KB/MB/GB)"""
```

---

## 7. Launch System (Launcher)

### 7.1 Launch Flow

```
Launcher.launch_rom(rom_file, category, core)
    │
    ├── 1. Verify ROM file exists
    ├── 2. Stop BGM
    ├── 3. Core selection logic:
    │   ├── User-specified > Previously used > Default
    │   └── Normalize core name (append _libretro.so suffix)
    │
    ├── 4. Launch based on emulator type:
    │   ├── RA (RetroArch):
    │   │   └── script core_path rom_path
    │   │
    │   ├── SA_* (Standalone):
    │   │   └── script rom_path
    │   │
    │   └── Custom:
    │       └── Use TYPE_* config value
    │
    ├── 5. On successful launch:
    │   ├── Add to history
    │   ├── Save core selection
    │   ├── Save session
    │   └── Exit PFE (launcher.sh restarts)
    │
    └── 6. On launch failure:
        ├── Show error toast
        └── Resume BGM
```

### 7.2 Emulator Types

| Type | Description | Launch Command |
|------|-------------|----------------|
| `RA` | RetroArch | `TYPE_RA core_path rom_path` |
| `SA_PPSSPP` | PPSSPP | `TYPE_SA_PPSSPP rom_path` |
| `SA:pyxel` | Pyxel app | `python rom_path` |
| Custom | Config-defined | `TYPE_* rom_path` |

---

## 8. Input Handling (InputHandler)

### 8.1 Action Definitions

```python
class Action(Enum):
    UP, DOWN, LEFT, RIGHT   # D-pad
    A, B, X, Y              # Face buttons
    L, R, L2, R2            # Shoulder buttons
    START, SELECT           # Special buttons
```

### 8.2 Button Layouts

| Layout | Confirm | Cancel |
|--------|---------|--------|
| Nintendo | A | B |
| Xbox | B | A |

### 8.3 Key Features

```python
class InputHandler:
    def is_pressed(action)     # Pressed this frame
    def is_held(action)        # Being held down
    def is_repeated(action)    # Repeat input (long press support)

    # Key repeat settings
    key_repeat_delay = 8       # ~0.27 seconds
    key_repeat_interval = 2    # ~0.07 seconds
```

---

## 9. Data Persistence (PersistenceManager)

### 9.1 Save Files

| File | Contents |
|------|----------|
| `session.json` | Screen state, category, cursor position |
| `settings.json` | User settings (brightness, volume, theme, etc.) |
| `favorites.json` | Favorite ROM list |
| `history.json` | Play history (max 50 entries) |
| `core_history.json` | Last used core per ROM |
| `keyconfig.json` | Custom key settings |

### 9.2 settings.json Structure

```json
{
  "version": "1.0",
  "settings": {
    "brightness": "5",
    "show_screenshots": "On",
    "sort_mode": "Name",
    "view_mode": "list",
    "button_layout": "NINTENDO",
    "resolution": "1:1",
    "theme": "dark",
    "bgm_enabled": "On",
    "bgm_volume": "5",
    "bgm_mode": "Normal"
  }
}
```

### 9.3 Favorites Cache

Cached as a set for fast lookup:

```python
_favorites_cache = set(rom_paths)  # O(1) lookup
```

---

## 10. UI Component Hierarchy

### 10.1 Base Classes

```python
class UIScreen(ABC):
    """Base class for UI screens"""
    active: bool

    def update()      # Called every frame
    def draw()        # Called every frame
    def activate()    # Called when screen becomes active
    def deactivate()  # Called when screen becomes inactive

class ScrollableList(UIScreen):
    """Base class for scrollable lists"""
    items: list
    selected_index: int
    scroll_offset: int
    items_per_page: int

    def scroll_up/down()
    def page_up/down()
    def jump_to_start/end()
    def get_selected_item()
```

### 10.2 Reusable Components (ui/components.py)

| Component | Purpose |
|-----------|---------|
| `StatusBar` | Top / bottom status display |
| `Breadcrumb` | Path navigation |
| `CategoryTitle` | Category name (Japanese support) |
| `Toast` | Temporary notifications |
| `Counter` | Item counter (X/Y format) |
| `LoadingSpinner` | Loading animation |
| `ProgressBar` | Progress bar |
| `HelpText` | Control hints |
| `Icon` | Star / folder / file icons |
| `SystemStatus` | Time / battery / network display |

### 10.3 Screen Implementations

| Screen | Class | Description |
|--------|-------|-------------|
| Splash | `Splash` | Boot screen |
| Main Menu | `MainMenu` | Category selection |
| File List | `FileList` | ROM browser (list / gallery / slideshow) |
| Core Select | `CoreSelect` | Emulator core selection |
| Favorites | `Favorites` | Favorite ROM list |
| Recent | `Recent` | Recently played ROMs |
| Search | `Search` | ROM search |
| Settings | `Settings` | Various settings |
| WiFi Settings | `WiFiSettings` | Network settings |
| Key Config | `KeyConfig` | Button remapping |
| BGM Config | `BGMConfig` | Music settings |
| Date/Time Settings | `DateTimeSettings` | System date/time settings |
| Statistics | `Statistics` | Play statistics |
| About | `About` | Version information |
| Quit | `QuitMenu` | Quit confirmation |

---

## 11. BGM Management (BGMManager)

### 11.1 Deferred Initialization

To reduce startup time, pygame.mixer is loaded on the first BGM operation:

```python
def _get_mixer():
    """Lazy loading"""
    if not _mixer_import_attempted:
        import pygame.mixer as mixer
        mixer.init(frequency=44100, size=-16, channels=2, buffer=8192)
```

### 11.2 Playlist Feature

```python
class BGMManager:
    playlist: list          # Selected track list
    play_order: list        # Play order (randomized when shuffled)
    current_index: int      # Current track index
    play_mode: str          # "Normal" or "Shuffle"
    max_playlist_size: int  # Max 300 tracks

    def build_playlist()    # Scan BGM directory
    def play_next()         # Play next track
    def check_music_end()   # Check if track ended (every 30 frames)
```

---

## 12. System Monitoring (SystemMonitor)

### 12.1 Monitored Items

| Item | Script | Update Interval |
|------|--------|-----------------|
| Battery | `get_battery.sh` | 60 frames (~2 seconds) |
| Network | `get_network.sh` | 30 frames (~1 second) |
| Time | Python internal | 30 frames (~1 second) |

### 12.2 Date/Time Settings (DateTimeSettings)

A date/time settings screen accessed from the Settings submenu.

```
Settings screen → Select "Date/Time" → DateTimeSettings screen
    ├── Load current system date/time (on activate)
    ├── Select fields with Up/Down, change values with Left/Right
    │   ├── Year   (2020-2099)
    │   ├── Month  (1-12)
    │   ├── Day    (1-28/29/30/31, dynamically adjusted by month and leap year)
    │   ├── Hour   (0-23)
    │   └── Minute (0-59)
    ├── "Apply" button applies the system date/time
    │   └── system_monitor.set_datetime() → scripts/set_datetime.sh
    └── B button returns to Settings
```

**Key Methods (SystemMonitor):**

```python
def get_current_datetime(self) -> tuple:
    """Get current system date/time → (year, month, day, hour, minute)"""

def set_datetime(self, year, month, day, hour, minute) -> bool:
    """Set system date/time via external script"""
```

### 12.3 Caching Strategy

```python
class SystemMonitor:
    _battery_cache: str
    _battery_cache_time: int
    _network_cache: str
    _network_cache_time: int

    # Skip script execution while cache is valid
```

---

## 13. Theme System (ThemeManager)

### 13.1 Built-in Themes

| Theme | Description |
|-------|-------------|
| `dark` | Dark theme (default) |
| `light` | Light theme |
| `retro` | Game Boy style |
| `neon` | Neon colors |

### 13.2 Color Keys

```python
color_keys = [
    "background",      # Background
    "text",            # Normal text
    "text_selected",   # Selected text
    "border",          # Border
    "border_accent",   # Accent border
    "scrollbar",       # Scrollbar
    "status_bg",       # Status bar background
    "help_bg",         # Help background
    "error",           # Error
    "success",         # Success
    "info"             # Info
]
```

---

## 14. Optimization Techniques

### 14.1 Lazy Loading

- pygame/mixer: Only when BGM is needed
- PyxelUniversalFont: On first use
- UI screens: Initialized on access

### 14.2 Caching

- Favorites: Set type (O(1) lookup)
- Theme colors: Pre-loaded
- Color lookup table: For image dithering
- Battery/Network: Updated at 1-2 second intervals

### 14.3 Draw Optimization

```python
def update():
    # Only set redraw flag when there is input
    if has_input:
        self._needs_redraw = True

    # Force redraw every 30 frames for clock update
    if self._redraw_counter >= 30:
        self._needs_redraw = True

def draw():
    # Do nothing if redraw is not needed (save CPU)
    if not self._needs_redraw:
        return
```

---

## 15. Data Flow Diagram

```
User Input
    ↓
InputHandler.is_pressed/is_held()
    ↓
Active Screen.update()
    ├── Handle user actions
    ├── Update state_manager
    └── ROM launch request (optional)
         ↓
    ROM Launch
         ├── Launcher.launch_rom()
         │   ├── Stop BGM
         │   ├── Execute emulator
         │   └── On failure: Resume BGM
         ├── Persistence: Save history/core selection
         ├── Save session
         └── Exit PFE → launcher.sh restarts
                              ↓
                         Restore session
                              ↓
                         Resume from previous state

State Change
    ↓
StateManager.change_state()
    ├── Push current state to history
    └── Update current_state
         ↓
ROMApp.update()
    ├── Check current_state
    ├── Deactivate old screen
    ├── Activate new screen
    └── Call screen.update()
         ↓
ROMApp.draw()
    ├── Check if redraw is needed
    └── Call screen.draw()
         ↓
Render to screen
```

---

## 16. External System Integration

### 16.1 Shell Scripts

| Script | Purpose |
|--------|---------|
| `get_battery.sh` | Get battery status |
| `get_network.sh` | Check network connection |
| `wifi_scan.sh` | Scan available WiFi networks |
| `wifi_connect.sh` | Connect to WiFi |
| `get_cpu_governor.sh` | Get CPU governor |
| `set_cpu_governor.sh` | Set CPU governor |
| `set_datetime.sh` | Set system date/time |
| `system_reboot.sh` | System reboot |
| `system_shutdown.sh` | System shutdown |

### 16.2 Emulator Integration

- **RetroArch**: Pass core + ROM path via shell script
- **Standalone**: Pass ROM path directly to executable
- **Custom**: Configurable launcher

---

## 17. Screen Resolution

| Setting | Resolution | Purpose |
|---------|------------|---------|
| `1:1` | 160x160 | Square (default) |
| `4:3` | 214x160 | 4:3 aspect ratio |

---

## 18. Error Handling

### 18.1 ROM Launch Errors

```python
try:
    launch_result = subprocess.run(...)
except Exception as e:
    self.last_error = str(e)
    # Resume BGM
    # Show error toast
```

### 18.2 Configuration File Errors

```python
try:
    with open(config_path) as f:
        ...
except Exception as e:
    print(f"Warning: Config file not found: {config_path}")
    # Use default values
```

---

## 19. Debug Features

### 19.1 Enabling Debug Mode

```ini
; pfe.cfg
DEBUG=true
```

### 19.2 Debug Logging

```python
from debug import debug_print

debug_print("[BGM] Track ended, playing next")
# Only outputs when DEBUG is true
```

---

## 20. Extension Points

### 20.1 Adding a New Emulator Type

1. Add a `TYPE_SA_*` variable to `pfe.cfg`
2. Use `-CORE=SA:*` in category definitions

### 20.2 Adding a New Theme

1. Add to the `THEMES` dictionary in `theme_manager.py`
2. Define all color keys

### 20.3 Adding a New UI Screen

1. Create a new file in `ui/`
2. Inherit from `UIScreen` or `ScrollableList`
3. Add to `AppState` in `state_manager.py`
4. Add a lazy initialization property in `main.py`

---

## 21. License & Acknowledgments

The source code and original background music (BGM) files of this project
are licensed under the MIT License.

However, **the icon assets included in this repository are NOT covered by the MIT License**.

PFE uses the following open-source projects and resources:

- [**Pyxel**: Retro game engine](https://github.com/kitao/pyxel)
- [**Pillow**: Python image processing library](https://pillow.readthedocs.io/en/stable/#)
- [**pygame**: Multimedia library](https://www.pygame.org/news)
- [**pyxel-universal-font**: Unicode font support](https://pypi.org/project/pyxel-universal-font/)
- [**Yoshikun's Icon Repository**: Various icons](https://yspixel.jpn.org/)
- [**Retro game console icons**: Various icons](https://github.com/KyleBing/retro-game-console-icons)

### Icon Assets

The icon assets included in this project are the property of their respective creators.

- These assets are **NOT licensed under the MIT License**
- Use, modification, or redistribution of the icon assets may require
  permission from the original creators
- Please check the license or obtain permission before using these assets
  outside of this project

---

*This document was auto-generated. Last updated: 2026-02-07*
