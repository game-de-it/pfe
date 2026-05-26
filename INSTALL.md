# Installation Instructions

This document covers the general Linux/PC installation flow.

For ROCKNIX, use the dedicated [ROCKNIX setup guide](docs/ROCKNIX_JP.md). ROCKNIX setup is based on copying `tools/rocknix/ports/` to `/roms/ports/` and launching scripts from EmulationStation Ports.

## Requirements

- Python 3.8 or higher
- pip
- RetroArch, PPSSPP, or other emulators you want to use
- ROM files

## 1. Install Dependencies

Recommended:

```bash
./scripts/install_deps.sh
```

With a specific Python:

```bash
PFE_PYTHON=/path/to/python3 ./scripts/install_deps.sh
```

Manual install:

```bash
pip install "pyxel>=2.9.5"
pip install Pillow>=10.0.0
pip install pyxel-universal-font>=0.2.0
pip install pygame>=2.0.0
```

`scripts/install_deps.sh` also avoids pip bytecode issues seen on some ROCKNIX/plumOS Python builds, so it is the preferred path.

## 2. Prepare Configuration

Copy the sample config:

```bash
cp data/pfe.cfg.example data/pfe.cfg
```

Set your ROM path and launcher scripts:

```ini
ROM_BASE=/path/to/your/roms

TYPE_RA=./bin/retroarch.sh

; Optional standalone launchers
;TYPE_SA_PPSSPP=./bin/ppsspp.sh
;TYPE_SA_YABASANSHIRO=./bin/yabasanshiro.sh
```

Define systems with `-TITLE`, `-DIR`, `-EXT`, and `-CORE`.

```ini
-TITLE=Famicom
-DIR=nes
-EXT=nes,fds
-CORE=nestopia,fceumm

-TITLE=PSP
-DIR=psp
-EXT=iso,cso,pbp
-CORE=SA:PPSSPP
```

Relative `-DIR` values are resolved under `ROM_BASE`. Plain core names use RetroArch. `SA:NAME` uses `TYPE_SA_NAME`.

See `data/pfe.cfg.example` for all available options.

## 3. Emulator Launcher Scripts

PFE delegates emulator startup to external scripts.

Bundled examples:

```txt
bin/retroarch.sh
bin/ppsspp.sh
bin/yabasanshiro.sh
bin/drastic.sh
bin/pyxel.sh
```

Make scripts executable:

```bash
chmod +x bin/*.sh scripts/*.sh
```

RetroArch scripts receive:

```txt
bin/retroarch.sh <core_path_or_filename> <rom_path>
```

Standalone scripts usually receive only the ROM path:

```txt
bin/ppsspp.sh <rom_path>
```

Edit `bin/*.sh` or point `TYPE_RA` / `TYPE_SA_*` to your own scripts as needed.

## 4. Assets

### BGM

The default BGM directory is `assets/bgm/`.

```txt
assets/bgm/
  song1.mp3
  song2.ogg
```

Override it with:

```ini
BGM_DIR=./assets/bgm
```

### Screenshots

The default screenshot directory is `assets/screenshots/`. You can override it with `SCREENSHOT_DIR`.

```ini
SCREENSHOT_DIR=assets/screenshots
```

Basic layout:

```txt
assets/screenshots/
  nes/
    Game Name.png
  snes/
    Another Game.png
```

Screenshot filenames should match ROM filenames without the extension.

### Splash Image

Optional startup images:

```txt
assets/splash.png
assets/splash.jpg
```

### Fonts

To force a specific Japanese font:

```ini
FONT_PATH=assets/fonts/your-font.ttf
BDF_FONT_PATH=assets/fonts/umplus_j10r.bdf
```

If omitted, PFE tries to detect a usable font automatically.

## 5. Launch

Recommended:

```bash
./launcher.sh
```

`launcher.sh` handles the environment and returns to PFE after game exit.

Direct launch:

```bash
python3 main.py
```

With a specific Python:

```bash
PFE_PYTHON=/path/to/python3 ./launcher.sh
```

## 6. OS Integration Scripts

WiFi, brightness, battery, CPU governor, reboot, and shutdown actions are handled by scripts in `scripts/`.

Examples:

```txt
scripts/wifi_scan.sh
scripts/wifi_connect.sh
scripts/get_battery.sh
scripts/get_brightness.sh
scripts/set_brightness.sh
scripts/get_cpu_governor.sh
scripts/set_cpu_governor.sh
scripts/system_reboot.sh
scripts/system_shutdown.sh
```

These scripts may need customization for your OS. See `scripts/samples/` for examples.

Normal users may need sudoers rules for WiFi or power actions:

```bash
echo "username ALL=(ALL) NOPASSWD: /usr/bin/nmcli" | sudo tee /etc/sudoers.d/pfe-wifi
sudo chmod 440 /etc/sudoers.d/pfe-wifi
```

## 7. Autostart

Minimal systemd example:

```ini
[Unit]
Description=PFE Frontend

[Service]
Type=simple
WorkingDirectory=/path/to/pfe
ExecStart=/bin/bash /path/to/pfe/launcher.sh
Restart=on-failure

[Install]
WantedBy=default.target
```

ROCKNIX uses `02_install_pfe.sh` instead; see [ROCKNIX setup guide](docs/ROCKNIX_JP.md).

## Troubleshooting

### PFE Does Not Start

```bash
./scripts/install_deps.sh
python3 -m compileall -q main.py pfe_app ui
tail -n 80 data/debug.log
```

If `pfe_app` is missing, copy the whole PFE directory tree again.

### ROMs Do Not Appear

- Check `ROM_BASE` and `-DIR`
- Check that `-EXT` includes your ROM extension
- Check directory permissions

### Games Do Not Launch

- Check `TYPE_RA` and `TYPE_SA_*`
- Check script executable permissions
- Check RetroArch core paths
- Read `data/debug.log`

### BGM Does Not Play

- Check `BGM_DIR`
- Check that supported audio files exist
- Check BGM is enabled in Settings
- Check pygame is installed

### Screenshots Do Not Appear

- Check `SCREENSHOT_DIR`
- Check system subdirectory names
- Check screenshot filenames match ROM names

### WiFi or Power Actions Fail

- Check that `scripts/*.sh` match your OS
- Check required commands are installed
- Check sudoers or other permission settings

### Debug Logs

Set `DEBUG=true` in `data/pfe.cfg` for more logs.

```bash
tail -f data/debug.log
```
