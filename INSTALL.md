# Installation Instructions

## Requirements

* Python 3.8 or higher
* pip
* RetroArch (or other emulators such as PPSSPP)

## Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install pyxel>=2.2.7
pip install Pillow>=10.0.0
pip install pyxel-universal-font>=0.2.0
pip install pygame>=2.0.0  # for BGM playback
```

### 2. Prepare Configuration File

Copy the sample configuration file:

```bash
cp data/pfe.cfg.example data/pfe.cfg
```

Edit `data/pfe.cfg` to set the ROM directory and emulator paths:

```ini
; Global settings
ROM_BASE=/path/to/your/roms

; Emulator settings
; TYPE_RA: RetroArch launcher script (receives <core_filename> <rom_path>)
TYPE_RA=./bin/retroarch.sh

; TYPE_SA_*: Standalone emulator (receives <rom_path> only)
;TYPE_SA_PPSSPP=/usr/local/bin/ppsspp.sh

; Debug (set to true if issues occur)
DEBUG=false

; Category definitions
-TITLE=Famicom
-DIR=nes
-EXT=nes,fds
-CORE=nestopia,fceumm

-TITLE=Super Famicom
-DIR=snes
-EXT=sfc,smc
-CORE=snes9x

; Example of standalone emulator
;-TITLE=PSP
;-DIR=psp
;-EXT=iso,cso,pbp
;-CORE=SA:PPSSPP
```

For detailed configuration options, see `data/pfe.cfg.example`.

### 2.5. Prepare Launcher Scripts

PFE launches emulators via external scripts.

#### Example Script for RetroArch (`bin/retroarch.sh`)

```bash
#!/bin/bash
# Args: $1=core filename, $2=ROM path
CORE_PATH="/path/to/retroarch/cores"
retroarch -L "${CORE_PATH}/$1" "$2"
```

#### Example Script for Standalone Emulator

```bash
#!/bin/bash
# Args: $1=ROM path
/usr/local/bin/ppsspp "$1"
```

Give scripts executable permission:

```bash
chmod +x bin/retroarch.sh
```

#### WiFi / System Scripts

PFE includes the following scripts:

```
scripts/
├── wifi_scan.sh        # Scan WiFi networks
├── wifi_connect.sh     # Connect to WiFi
├── wifi_status.sh      # Get WiFi power status
├── wifi_toggle.sh      # Turn WiFi ON/OFF
├── get_brightness.sh   # Get screen brightness
└── set_brightness.sh   # Set screen brightness
```

These scripts are configured in `data/pfe.cfg`:

```ini
WIFI_SCAN_SCRIPT=./scripts/wifi_scan.sh
WIFI_CONNECT_SCRIPT=./scripts/wifi_connect.sh
WIFI_STATUS_SCRIPT=./scripts/wifi_status.sh
WIFI_TOGGLE_SCRIPT=./scripts/wifi_toggle.sh
```

You can also customize the scripts according to your environment.

### 3. Prepare Assets (Optional)

#### Splash Image

Place `assets/splash.png` or `assets/splash.jpg` to display at startup.

#### BGM

Place `assets/bgm.mp3` to enable BGM playback. Can be toggled On/Off in the Settings screen.

#### Screenshots

To display screenshots in the ROM selection screen:

```
assets/screenshots/
├── nes/
│   ├── Game Name.png  # same name as ROM file
│   └── ...
├── snes/
│   └── ...
```

#### Custom Fonts

To use Japanese fonts:

* Place font files in `assets/fonts/`
* Add to `data/pfe.cfg`: `FONT_PATH=assets/fonts/your-font.ttf`

Recommended fonts:

* Misaki Font (8x8): [http://littlelimit.net/misaki.htm](http://littlelimit.net/misaki.htm)
* Noto Sans CJK: [https://fonts.google.com/noto/specimen/Noto+Sans+JP](https://fonts.google.com/noto/specimen/Noto+Sans+JP)

### 4. Launch

#### Recommended: Auto-Restart Script

```bash
chmod +x launcher.sh
./launcher.sh
```

Returns to the launcher automatically after the game ends.

#### Direct Launch (Manual Restart Required)

```bash
python3 main.py
```

## Linux (Embedded) Settings

### launcher.sh Configuration

If using ALSA audio, set environment variables in `launcher.sh`:

```bash
export SDL_AUDIODRIVER=alsa
export SDL_GAMECONTROLLERCONFIG="..."  # Controller configuration
```

### Auto-Start Setup

To start the launcher automatically at system startup:

```bash
# Add to ~/.bashrc or /etc/rc.local
cd /path/to/pd && ./launcher.sh
```

### CPU Governor

Changing CPU governor requires write permissions to system files:

```bash
# Check permissions
ls -la /sys/devices/system/cpu/cpufreq/policy0/scaling_governor

# Add udev rules if necessary
```

### WiFi Permission

To connect to WiFi as a normal user, sudo permission for nmcli is required:

```bash
echo "ark ALL=(ALL) NOPASSWD: /usr/bin/nmcli" | sudo tee /etc/sudoers.d/wifi
sudo chmod 440 /etc/sudoers.d/wifi
```

### Reboot / Shutdown Permission

To allow a normal user to reboot/shutdown:

```bash
echo "ark ALL=(ALL) NOPASSWD: /usr/bin/systemctl reboot, /usr/bin/systemctl poweroff, /sbin/reboot, /sbin/poweroff" | sudo tee /etc/sudoers.d/power
sudo chmod 440 /etc/sudoers.d/power
```

**Note**: Replace `ark` with your actual username.

## Troubleshooting

### pyxel-universal-font Cannot Be Installed

```bash
pip install --upgrade pip
pip install pyxel-universal-font
```

### BGM Does Not Play

1. Check if pygame is installed:

   ```bash
   pip install pygame
   ```

2. Confirm `SDL_AUDIODRIVER` is exported in `launcher.sh`:

   ```bash
   export SDL_AUDIODRIVER=alsa
   ```

3. Confirm `assets/bgm.mp3` exists

4. Make sure BGM is On in the Settings screen

### Font Does Not Display

1. Check the font path
2. Confirm font file exists
3. Set `DEBUG=true` and check startup logs

### Screen Does Not Display

1. Confirm Pyxel is installed correctly
2. Check graphics driver is up-to-date
3. Verify SDL environment variables

### Launcher Does Not Return After Game

1. Make sure using `launcher.sh`
2. Check permissions of session file (`data/session.json`)

### Cannot Change CPU Governor

1. Check path:

   ```bash
   cat /sys/devices/system/cpu/cpufreq/policy0/scaling_governor
   ```

2. Set `CPU_GOVERNOR_PATH` in `pfe.cfg`:

   ```ini
   CPU_GOVERNOR_PATH=/sys/devices/system/cpu/cpufreq/policy0/scaling_governor
   ```

3. Confirm write permissions to the file

### WiFi Connection Fails

1. Check debug log:

   ```bash
   cat data/debug.log
   ```

2. Verify nmcli works:

   ```bash
   nmcli device wifi list
   ```

3. Add sudoers rule if permission error occurs (see WiFi Permission above)

4. If `Insufficient privileges` appears:

   * Happens when running via systemd service
   * sudoers configuration is required

### Reboot / Shutdown Does Not Work

1. Check debug log:

   ```bash
   tail -20 data/debug.log
   ```

2. Add sudoers rule if permission error occurs (see Reboot / Shutdown Permission above)

### Checking Debug Logs

Setting `DEBUG=true` outputs logs to `data/debug.log`:

```bash
# Check logs in real-time
tail -f data/debug.log

# Check latest log
cat data/debug.log
```

If running as a systemd service, logs may not appear in the console, so file logs are useful for diagnosing issues.

---

