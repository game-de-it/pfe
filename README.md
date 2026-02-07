# Pyxel ROM Launcher (PFE)

A retro-styled ROM launcher built with Pyxel, supporting multiple emulators and platforms.

## Features

### Core Features
- Configuration file parser (pfe.cfg format)
- Main menu with category selection (list and gallery mode)
- ROM file listing and browsing with subdirectory support
- Input handling (keyboard + gamepad)
- ROM execution with RetroArch/PPSSPP
- Japanese text support (日本語対応)
- Key repeat for smooth navigation
- Category-specific cursor position memory
- Session state persistence (auto-restore on restart)
- Play history tracking
- Auto-restart after game exit

### UI Features
- **Gallery Mode**: Full-screen screenshot view with slideshow
- **TOP Screen Gallery Mode**: 3x3 grid view for category selection on main menu
- **List Mode**: Traditional file list with optional screenshot preview
- **Themes**: Multiple color themes (Dark, Light, Retro, Ocean, Forest, Sunset)
- **Quick Jump**: Soft keyboard for alphabetical navigation
- **Favorites**: Mark and quick-access favorite ROMs
- **Search**: Search ROMs across all categories
- **Statistics**: View play time and launch count per game
- **Screen Resolution**: Selectable display resolution (1:1 or 4:3)

### Settings
Settings menu options (in order):
- **Brightness**: Screen brightness control (1-10)
- **Theme**: Color theme selection
- **CPU Governor**: Power/performance mode (ondemand / performance)
- **Resolution**: Screen resolution (1:1 160x160 / 4:3 214x160) - requires restart
- **WiFi**: Network configuration
- **Key Config** (submenu):
  - Btn Layout: Button layout (Nintendo / Xbox)
  - Key Mapping: Custom key bindings
- **BGM Config** (submenu):
  - BGM ON/OFF: Background music toggle
  - BGM Volume: Volume level control
  - BGM Mode: Background music playback mode
  - Music Mode: Screen off + low power mode for music playback
- **Statistics**: View play time and launch count
- **About**: Version and system information
- **Quit**: System reboot / shutdown

### System
- Battery level display
- Network status display
- Clock display
- BGM playback with volume control
- CPU governor control

## Installation

See [INSTALL.md](INSTALL.md) for detailed installation instructions.

### Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy and configure settings:
```bash
cp data/pfe.cfg.example data/pfe.cfg
# Edit data/pfe.cfg with your paths
```

3. Run the launcher:
```bash
./launcher.sh
```

## Usage

### Running the Launcher

#### Recommended: Auto-Restart Script
```bash
chmod +x launcher.sh
./launcher.sh
```

The launcher automatically restarts after exiting a game and restores your previous screen position.

#### Direct Run (Manual restart required)
```bash
python3 main.py
```

### Controls

#### Main Menu / File List
| Input | Keyboard | Gamepad | Action |
|-------|----------|---------|--------|
| Navigate | ↑/↓ | D-Pad ↑/↓ | Move cursor |
| Page | ←/→ | D-Pad ←/→ | Page up/down (list mode) |
| Confirm | Z / Enter | A | Select item |
| Back | X / Escape | B | Go back |
| Jump Start | Q | L | Jump to first item |
| Jump End | W | R | Jump to last item |
| View Mode | A key | X | Toggle List/Gallery mode |
| Screenshot | S key | Y | Toggle screenshot (list mode) |
| Favorite | - | START | Toggle favorite (list mode) |
| Quick Jump | - | SELECT (hold) | Open soft keyboard |

#### TOP Screen Gallery Mode
| Input | Action |
|-------|--------|
| ↑/↓/←/→ | Navigate 3x3 grid |
| A | Select category |
| X | Switch to list mode |

#### Gallery Mode (ROM list)
| Input | Action |
|-------|--------|
| ←/→ | Previous/Next ROM |
| ↑/↓ | Jump 5 ROMs |
| L/R | Jump to start/end |
| START | Toggle slideshow |
| A | Launch ROM |
| X | Switch to list mode |

#### Settings
| Input | Action |
|-------|--------|
| ↑/↓ | Navigate options |
| ←/→ | Change value |
| A | Enter submenu |
| B | Back |

#### WiFi Settings
| Input | Action |
|-------|--------|
| ↑/↓ | Select network |
| A | Connect to network |
| X | Toggle WiFi ON/OFF |
| Y | Rescan networks |
| B | Back |

## Configuration

### pfe.cfg Format

The configuration file (`data/pfe.cfg`) controls all launcher settings.

#### Global Variables

```ini
; Base directory for ROMs
ROM_BASE=/roms

; Base directory for RetroArch cores (optional)
CORE_PATH=/usr/lib/libretro
```

#### Emulator/Launcher Definitions

PFE delegates ROM launching to external scripts for flexibility.

```ini
; RetroArch launcher script
; Receives: <core_path> <rom_path>
; Example call: ./bin/retroarch.sh /usr/lib/libretro/nestopia_libretro.so /roms/nes/game.nes
TYPE_RA=./bin/retroarch.sh

; Standalone emulator scripts
; Receives: <rom_path>
; Use with SA:NAME in -CORE
TYPE_SA_YABASANSHIRO=/usr/local/bin/yabasanshiro.sh
TYPE_SA_PPSSPP=/usr/local/bin/ppsspp.sh
```

#### UI Settings

```ini
; Custom font path (optional)
;FONT_PATH=/usr/share/fonts/truetype/custom.ttf

; Splash screen duration (1-5 seconds)
;SPLASH_TIME=3

; Debug mode
DEBUG=false
```

#### System Monitor Settings

```ini
; Display toggles
;SHOW_TIME=true
;SHOW_BATTERY=true
;SHOW_NETWORK=true

; Custom battery path (auto-detected if not set)
;BATTERY_PATH=/sys/class/power_supply/battery/capacity

; Custom CPU governor path (auto-detected if not set)
;CPU_GOVERNOR_PATH=/sys/devices/system/cpu/cpufreq/policy0/scaling_governor

; WiFi interface name
;WIFI_INTERFACE=wlan0

; WiFi scripts
WIFI_SCAN_SCRIPT=./scripts/wifi_scan.sh
WIFI_CONNECT_SCRIPT=./scripts/wifi_connect.sh
WIFI_STATUS_SCRIPT=./scripts/wifi_status.sh
WIFI_TOGGLE_SCRIPT=./scripts/wifi_toggle.sh
```

#### Category Definitions

```ini
; RetroArch cores only
-TITLE=Nintendo Entertainment System
-DIR=nes
-EXT=nes,unf,fds
-CORE=nestopia,fceumm

; With category image for gallery mode
-TITLE=Super Nintendo Entertainment System
-TITLE_IMG=assets/title/snes.png
-DIR=snes
-EXT=smc,sfc
-CORE=snes9x

; Mixed: RetroArch core + Standalone emulator
-TITLE=Sega Saturn
-DIR=saturn
-EXT=cue,bin,chd
-CORE=yabasanshiro,SA:YABASANSHIRO

; Standalone emulator only
-TITLE=PlayStation Portable
-DIR=psp
-EXT=iso,cso,pbp
-CORE=SA:PPSSPP
```

### -CORE Format

| Format | Type | Execution |
|--------|------|-----------|
| `nestopia` | RetroArch | `TYPE_RA {CORE_PATH}/nestopia_libretro.so <rom>` |
| `SA:YABASANSHIRO` | Standalone | `TYPE_SA_YABASANSHIRO <rom>` |

Core name conversion:
- `nestopia` → `nestopia_libretro.so` (suffix added if no underscore)
- `nestopia_libretro.dylib` → as-is (kept if has underscore)

When CORE_PATH is set in pfe.cfg, full core paths are built automatically:
- Core name: `nestopia` → Full path: `{CORE_PATH}/nestopia_libretro.so`

### Path Resolution

#### ROM Directories
- **Relative path** (e.g., `nes`): Expands to `{ROM_BASE}/nes`
- **Absolute path** (e.g., `/roms/nes`): Used as-is

#### Script Paths
- **Relative path** (e.g., `./bin/retroarch.sh`): Resolved from PFE directory
- **Absolute path** (e.g., `/usr/local/bin/script.sh`): Used as-is

## Screenshots

Place ROM screenshots in `assets/screenshots/{category}/`:
```
assets/screenshots/
├── nes/
│   ├── Game Name.png
│   └── Another Game.png
├── snes/
│   └── SNES Game.png
└── README.md
```

Screenshot naming:
- Must match ROM filename (without extension)
- Supports: `.png`, `.jpg`, `.jpeg`
- Parenthetical suffixes are ignored for matching

## Category Images

For TOP screen gallery mode, place category images and specify them with `-TITLE_IMG`:
```
assets/categories/
├── nes.png
├── snes.png
├── psp.png
└── ...
```

Image requirements:
- Recommended size: 48x48 pixels
- Supports: `.png`, `.jpg`, `.jpeg`

## Themes

Available themes:
- **dark**: Dark background (default)
- **light**: Light background
- **retro**: Classic amber/green
- **ocean**: Blue tones
- **forest**: Green tones
- **sunset**: Warm orange/red

Custom themes can be added in `assets/themes/`.

## External Scripts

PFE uses external shell scripts for OS-dependent operations, making it easy to customize for different systems.

### Script Categories

| Script | Purpose | Arguments | Output |
|--------|---------|-----------|--------|
| `get_battery.sh` | Get battery status | none | `<level> <status>` |
| `get_network.sh` | Check connectivity | none | `connected` or `disconnected` |
| `get_cpu_governor.sh` | Get CPU governor | none | governor name |
| `set_cpu_governor.sh` | Set CPU governor | `<governor>` | exit code |
| `get_brightness.sh` | Get brightness | none | 1-10 |
| `set_brightness.sh` | Set brightness | `<level>` | exit code |
| `wifi_scan.sh` | Scan networks | none | SSID list |
| `wifi_connect.sh` | Connect to WiFi | `<ssid> <password>` | exit code |
| `wifi_status.sh` | Get WiFi status | none | `enabled` or `disabled` |
| `wifi_toggle.sh` | Toggle WiFi | `on` or `off` | exit code |
| `system_reboot.sh` | Reboot system | none | - |
| `system_shutdown.sh` | Shutdown system | none | - |

### Customization

Sample scripts for different WiFi management tools are available in `scripts/samples/`:
- `wpa_supplicant/` - For wpa_supplicant/wpa_cli
- `iwd/` - For iwctl (iNet Wireless Daemon)
- `connman/` - For ConnMan
- `netctl/` - For netctl (Arch Linux)

To use alternative scripts, copy them to `scripts/` or update paths in `data/pfe.cfg`.

## Project Structure

```
├── main.py                 # Entry point
├── launcher.sh             # Auto-restart script
├── config.py               # Config parser
├── state_manager.py        # UI state machine
├── input_handler.py        # Input management
├── rom_manager.py          # ROM scanning
├── launcher.py             # Emulator execution
├── persistence.py          # Settings/history storage
├── bgm_manager.py          # Background music
├── system_monitor.py       # Battery/network/CPU
├── theme_manager.py        # Theme system
├── japanese_text.py        # Japanese font rendering
├── ui/
│   ├── base.py             # Base UI classes
│   ├── components.py       # Reusable components
│   ├── window.py           # Window drawing
│   ├── splash.py           # Splash screen
│   ├── main_menu.py        # Category menu
│   ├── file_list.py        # ROM browser
│   ├── core_select.py      # Core selection
│   ├── favorites.py        # Favorites list
│   ├── recent.py           # Recent games
│   ├── search.py           # Search screen
│   ├── settings.py         # Settings menu
│   ├── wifi_settings.py    # WiFi configuration
│   ├── key_config.py       # Key configuration submenu
│   ├── key_config_menu.py  # Key mapping configuration
│   ├── bgm_config.py       # BGM configuration submenu
│   ├── statistics.py       # Play statistics
│   ├── about.py            # About screen
│   └── quit_menu.py        # Reboot/Shutdown menu
├── scripts/
│   ├── wifi_scan.sh        # WiFi network scanning
│   ├── wifi_connect.sh     # WiFi connection
│   ├── wifi_status.sh      # WiFi radio status (on/off)
│   ├── wifi_toggle.sh      # WiFi radio toggle
│   ├── get_brightness.sh   # Get screen brightness
│   ├── set_brightness.sh   # Set screen brightness
│   ├── get_battery.sh      # Get battery level/status
│   ├── get_network.sh      # Check network connectivity
│   ├── get_cpu_governor.sh # Get CPU governor
│   ├── set_cpu_governor.sh # Set CPU governor
│   ├── system_reboot.sh    # System reboot
│   └── system_shutdown.sh  # System shutdown
├── assets/
│   ├── bgm.mp3             # Background music
│   ├── splash.png          # Splash image
│   ├── fonts/              # Font files
│   ├── screenshots/        # ROM screenshots
│   ├── categories/         # Category images for gallery mode
│   └── themes/             # Theme definitions
├── data/
│   ├── pfe.cfg             # Configuration
│   ├── pfe.cfg.example     # Example config
│   ├── settings.json       # User settings
│   ├── session.json        # Session state
│   ├── history.json        # Play history
│   └── debug.log           # Debug log (when DEBUG=true)
└── requirements.txt
```

## Troubleshooting

### ROMs Not Showing
- Check directory paths in `data/pfe.cfg`
- Verify file extensions match your ROM files
- Ensure directories exist and are readable

### Launch Failures
- Verify emulator paths (TYPE_RA, TYPE_PPSSPP)
- Check core names for RetroArch
- Review console output for error messages

### BGM Not Playing
- Ensure `assets/bgm.mp3` exists
- Check BGM is enabled in Settings
- Verify `SDL_AUDIODRIVER=alsa` is exported in launcher.sh

### CPU Governor Not Changing
- Check file permissions on `/sys/devices/system/cpu/cpufreq/policy0/scaling_governor`
- Try setting `CPU_GOVERNOR_PATH` in pfe.cfg

### WiFi Connection Failing
- Check `data/debug.log` for detailed error messages
- Ensure nmcli is installed and working
- For non-root users, add sudoers permission for nmcli:
  ```bash
  echo "username ALL=(ALL) NOPASSWD: /usr/bin/nmcli" | sudo tee /etc/sudoers.d/wifi
  sudo chmod 440 /etc/sudoers.d/wifi
  ```
- This permission is also required for WiFi ON/OFF toggle

### Reboot/Shutdown Not Working
- For non-root users, add sudoers permission:
  ```bash
  echo "username ALL=(ALL) NOPASSWD: /usr/bin/systemctl reboot, /usr/bin/systemctl poweroff" | sudo tee /etc/sudoers.d/power
  sudo chmod 440 /etc/sudoers.d/power
  ```

### Resolution Change Not Applied
- Resolution changes require a restart of the launcher to take effect
- Use the Quit menu to reboot or restart the launcher manually

### Debug Mode

Enable debug mode for detailed logs:

1. Set `DEBUG=true` in `data/pfe.cfg`
2. Restart the launcher
3. Check logs:
   - Console output (if running directly)
   - File: `data/debug.log` (always available, useful for systemd services)

View live logs:
```bash
tail -f data/debug.log
```

## License & Acknowledgments

The source code and original background music (BGM) files of this project
are licensed under the MIT License.

However, **the icon assets included in this repository are NOT covered by the MIT License**.

PFE uses the following open source projects and materials:

- [**Pyxel**: Retro Game Engine](https://github.com/kitao/pyxel)
- [**Pillow**: Python Image Processing Library](https://pillow.readthedocs.io/en/stable/#)
- [**pygame**: Multimedia Library](https://www.pygame.org/news)
- [**pyxel-universal-font**: Unicode Font Support](https://pypi.org/project/pyxel-universal-font/)
- [**Yoshi-kun's Icon Warehouse**: Various Icons](https://yspixel.jpn.org/)
- [**Retro Game Console Icons**: Various Icons](https://github.com/KyleBing/retro-game-console-icons)

### Icon Assets

The icon assets included in this project are the property of their respective creators.

- These assets are **NOT licensed under the MIT License**
- Use, modification, or redistribution of the icon assets may require
  permission from the original creators
- Please check the license or obtain permission before using these assets
  outside of this project

---
