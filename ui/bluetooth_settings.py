"""
Bluetooth settings screen with device scanning, pairing, and ON/OFF control.
"""

import os
import pyxel
import subprocess
import json
from ui.base import ScrollableList
from ui.components import StatusBar, HelpText, SystemStatus
from ui.window import DQWindow
from ui.software_keyboard import SoftwareKeyboard
from pfe_app.japanese_text import draw_japanese_text
from pfe_app.theme_manager import get_theme_manager
from pfe_app.debug import debug_print


class BluetoothSettings(ScrollableList):
    """Bluetooth settings screen for scanning and pairing devices."""

    def __init__(self, input_handler, state_manager, config):
        super().__init__(items_per_page=5)
        self.input_handler = input_handler
        self.state_manager = state_manager
        self.config = config
        self.status_bar = StatusBar(138, 160)
        self.help_text = HelpText(146, 160)
        self.system_status = SystemStatus()

        # Bluetooth script paths
        self.bt_scan_script = config.global_vars.get('BT_SCAN_SCRIPT', '')
        self.bt_pair_script = config.global_vars.get('BT_PAIR_SCRIPT', '')
        self.bt_status_script = config.global_vars.get('BT_STATUS_SCRIPT', '')
        self.bt_toggle_script = config.global_vars.get('BT_TOGGLE_SCRIPT', '')

        # Data file paths
        self.data_dir = "data"
        self.bt_config_file = os.path.join(self.data_dir, "bt_config.json")

        # Device list: [{"name": "...", "mac": "AA:BB:CC:DD:EE:FF"}, ...]
        self.device_list = []
        self.selected_device = None

        # Software keyboard (for PIN input)
        self.keyboard = SoftwareKeyboard(x=4, y=80)

        # Screen state: scan, pin, pairing
        self.mode = "scan"

        # Status message
        self.status_message = ""

        # Bluetooth power state
        self.bt_enabled = True

    def _is_root(self):
        """Check if running as root user."""
        return os.getuid() == 0

    def _get_bt_status(self):
        """Get current Bluetooth power status (enabled/disabled)."""
        try:
            if self.bt_status_script and os.path.exists(self.bt_status_script):
                debug_print(f"[BT] Running status script: {self.bt_status_script}")
                result = subprocess.run([self.bt_status_script],
                                       capture_output=True,
                                       text=True,
                                       timeout=5)
            else:
                # Fallback: use bluetoothctl directly
                result = subprocess.run(['bluetoothctl', 'show'],
                                       capture_output=True,
                                       text=True,
                                       timeout=5)
                # Parse "Powered: yes/no"
                for line in result.stdout.splitlines():
                    if 'Powered:' in line:
                        powered = line.strip().split()[-1]
                        return powered.lower() == 'yes'
                return False

            status = result.stdout.strip().lower()
            debug_print(f"[BT] Status: {status}")
            return status == "enabled"
        except Exception as e:
            debug_print(f"[BT] Failed to get status: {e}")
            return True  # Assume enabled if check fails

    def _set_bt_power(self, enabled: bool):
        """Enable or disable Bluetooth."""
        action = "on" if enabled else "off"
        debug_print(f"[BT] Setting power to: {action}")

        try:
            if self.bt_toggle_script and os.path.exists(self.bt_toggle_script):
                debug_print(f"[BT] Running toggle script: {self.bt_toggle_script}")
                cmd = [self.bt_toggle_script, action]
                result = subprocess.run(cmd,
                                       capture_output=True,
                                       text=True,
                                       timeout=10)
                debug_print(f"[BT] Toggle script stdout: {result.stdout}")
            else:
                # Fallback: use bluetoothctl directly
                if enabled:
                    subprocess.run(['rfkill', 'unblock', 'bluetooth'],
                                  capture_output=True, text=True, timeout=5)
                result = subprocess.run(['bluetoothctl', 'power', action],
                                       capture_output=True,
                                       text=True,
                                       timeout=10)

            debug_print(f"[BT] Power command exit code: {result.returncode}")
            if result.stderr:
                debug_print(f"[BT] Power command stderr: {result.stderr}")

            if result.returncode == 0:
                self.bt_enabled = enabled
                self.status_message = f"Bluetooth {'ON' if enabled else 'OFF'}"
                if enabled:
                    self._scan_devices()
                else:
                    self.device_list = []
                    self.set_items([])
                return True
            else:
                self.status_message = f"Failed to turn {'on' if enabled else 'off'}"
                return False
        except Exception as e:
            debug_print(f"[BT] Power command error: {e}")
            self.status_message = f"Error: {str(e)[:20]}"
            return False

    def activate(self):
        """Called when screen becomes active."""
        super().activate()

        # Load Bluetooth config
        self._load_bt_config()

        # Check Bluetooth power state
        self.bt_enabled = self._get_bt_status()

        # Scan devices if Bluetooth is ON
        if self.bt_enabled:
            self._scan_devices()
        else:
            self.status_message = "Bluetooth is OFF"
            self.device_list = []
            self.set_items([])

        # Set help text
        self._update_help_text()

    def deactivate(self):
        """Called when screen becomes inactive."""
        super().deactivate()
        self.keyboard.deactivate()

    def _update_help_text(self):
        """Update help text based on current mode."""
        if self.mode == "scan":
            self.help_text.set_controls([
                ("A", "Pair"),
                ("X", "On/Off"),
                ("Y", "Scan"),
                ("B", "Back")
            ])
        elif self.mode == "pin":
            self.help_text.set_controls([
                ("D-Pad", "Move"),
                ("A", "Type"),
                ("SELECT", "Shift"),
                ("B", "Cancel")
            ])

    def _load_bt_config(self):
        """Load saved Bluetooth configuration."""
        if os.path.exists(self.bt_config_file):
            try:
                with open(self.bt_config_file, 'r') as f:
                    config = json.load(f)
                    # Restore settings as needed
            except Exception as e:
                debug_print(f"Error loading BT config: {e}")

    def _save_bt_config(self, device_name: str, mac: str):
        """Save Bluetooth configuration."""
        try:
            config = {
                "last_device": device_name,
                "last_mac": mac,
                "saved_at": pyxel.frame_count
            }
            with open(self.bt_config_file, 'w') as f:
                json.dump(config, f, indent=2)
            debug_print(f"BT config saved: {device_name} ({mac})")
        except Exception as e:
            debug_print(f"Error saving BT config: {e}")

    def _scan_devices(self):
        """Scan for available Bluetooth devices."""
        self.status_message = "Scanning..."
        self.device_list = []

        try:
            if self.bt_scan_script and os.path.exists(self.bt_scan_script):
                debug_print(f"[BT] Running scan script: {self.bt_scan_script}")
                result = subprocess.run([self.bt_scan_script],
                                       capture_output=True,
                                       text=True,
                                       timeout=15)
                debug_print(f"[BT] Scan script exit code: {result.returncode}")
                debug_print(f"[BT] Scan script stdout: {result.stdout}")
                debug_print(f"[BT] Scan script stderr: {result.stderr}")
                lines = result.stdout.strip().split('\n')
            else:
                # Fallback: use bluetoothctl directly
                debug_print("[BT] Running bluetoothctl scan...")
                # Start scan in background
                scan_proc = subprocess.Popen(
                    ['bluetoothctl', 'scan', 'on'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                import time
                time.sleep(8)
                scan_proc.terminate()
                scan_proc.wait()

                # Get device list
                result = subprocess.run(['bluetoothctl', 'devices'],
                                       capture_output=True,
                                       text=True,
                                       timeout=5)
                debug_print(f"[BT] Devices stdout: {result.stdout}")
                lines = []
                for line in result.stdout.strip().split('\n'):
                    # Format: "Device AA:BB:CC:DD:EE:FF DeviceName"
                    parts = line.strip().split(' ', 2)
                    if len(parts) >= 3 and parts[0] == 'Device':
                        lines.append(f"{parts[1]}\t{parts[2]}")

            # Parse device list
            seen = set()
            self.device_list = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                parts = line.split('\t', 1)
                if len(parts) >= 2:
                    mac = parts[0].strip()
                    name = parts[1].strip()
                else:
                    mac = line.strip()
                    name = mac
                if mac and mac not in seen:
                    seen.add(mac)
                    self.device_list.append({"name": name, "mac": mac})

            debug_print(f"[BT] Found devices: {self.device_list}")

            if self.device_list:
                self.status_message = f"Found {len(self.device_list)} devices"
                display_names = [d["name"] for d in self.device_list]
                self.set_items(display_names)
            else:
                self.status_message = "No devices found"
                self.set_items([])

        except subprocess.TimeoutExpired:
            debug_print("[BT] Scan timeout")
            self.status_message = "Scan timeout"
        except FileNotFoundError as e:
            debug_print(f"[BT] Command not found: {e}")
            self.status_message = "bluetoothctl not found"
        except Exception as e:
            debug_print(f"[BT] Scan error: {e}")
            self.status_message = f"Scan error: {str(e)[:20]}"

    def _pair_device(self, device, pin: str):
        """Pair and connect to a Bluetooth device."""
        self.status_message = "Pairing..."
        self.mode = "pairing"

        mac = device["mac"]
        name = device["name"]

        debug_print(f"[BT] ===== Pairing Start =====")
        debug_print(f"[BT] Device: {name} ({mac})")
        debug_print(f"[BT] PIN: {'(none)' if not pin else '****'}")

        try:
            # Save config
            self._save_bt_config(name, mac)

            if self.bt_pair_script and os.path.exists(self.bt_pair_script):
                cmd = [self.bt_pair_script, mac]
                if pin:
                    cmd.append(pin)
                debug_print(f"[BT] Running pair script: {cmd[0]}")
                result = subprocess.run(cmd,
                                       capture_output=True,
                                       text=True,
                                       timeout=30)
            else:
                # Fallback: use bluetoothctl directly
                debug_print("[BT] Using bluetoothctl directly")
                # Trust
                subprocess.run(['bluetoothctl', 'trust', mac],
                              capture_output=True, text=True, timeout=5)
                # Pair
                subprocess.run(['bluetoothctl', 'pair', mac],
                              capture_output=True, text=True, timeout=15)
                import time
                time.sleep(3)
                # Connect
                result = subprocess.run(['bluetoothctl', 'connect', mac],
                                       capture_output=True,
                                       text=True,
                                       timeout=15)

            debug_print(f"[BT] Pair exit code: {result.returncode}")
            debug_print(f"[BT] Pair stdout: {result.stdout}")
            debug_print(f"[BT] Pair stderr: {result.stderr}")

            if result.returncode == 0:
                output = result.stdout.strip().lower()
                if 'connected' in output or result.returncode == 0:
                    debug_print("[BT] Pairing successful!")
                    self.status_message = "Connected!"
                else:
                    self.status_message = "Paired (not connected)"
            else:
                debug_print(f"[BT] Pairing failed with exit code: {result.returncode}")
                error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                self.status_message = f"Failed: {error_msg[:15]}"

        except subprocess.TimeoutExpired:
            debug_print("[BT] Pairing timeout")
            self.status_message = "Pairing timeout"
        except Exception as e:
            debug_print(f"[BT] Pairing error: {e}")
            self.status_message = f"Error: {str(e)[:20]}"

        self.mode = "scan"
        self._update_help_text()
        debug_print(f"[BT] ===== Pairing End =====")
        debug_print()

    def update(self):
        """Update Bluetooth settings screen."""
        if not self.active:
            return

        from pfe_app.input_handler import Action

        if self.mode == "scan":
            # Device selection mode
            if self.input_handler.is_pressed_with_repeat(Action.UP):
                self.scroll_up()
            elif self.input_handler.is_pressed_with_repeat(Action.DOWN):
                self.scroll_down()

            # Select device and go to PIN input
            if self.input_handler.is_pressed(Action.A):
                if self.device_list:
                    idx = self.selected_index
                    if 0 <= idx < len(self.device_list):
                        self.selected_device = self.device_list[idx]
                        self.mode = "pin"
                        self.keyboard.clear()
                        self.keyboard.activate()
                        self._update_help_text()

            # Rescan
            if self.input_handler.is_pressed(Action.Y):
                if self.bt_enabled:
                    self._scan_devices()
                else:
                    self.status_message = "Bluetooth is OFF"

            # Toggle Bluetooth ON/OFF
            if self.input_handler.is_pressed(Action.X):
                self._set_bt_power(not self.bt_enabled)

            # Back
            if self.input_handler.is_pressed(Action.B):
                self.state_manager.go_back()

        elif self.mode == "pin":
            # PIN input mode (keyboard operation)
            if self.input_handler.is_pressed_with_repeat(Action.UP):
                self.keyboard.move_up()
            elif self.input_handler.is_pressed_with_repeat(Action.DOWN):
                self.keyboard.move_down()
            elif self.input_handler.is_pressed_with_repeat(Action.LEFT):
                self.keyboard.move_left()
            elif self.input_handler.is_pressed_with_repeat(Action.RIGHT):
                self.keyboard.move_right()

            # Character input
            if self.input_handler.is_pressed(Action.A):
                done = self.keyboard.input_char()
                if done:
                    # OK button was pressed
                    pin = self.keyboard.get_text()
                    self.keyboard.deactivate()
                    self._pair_device(self.selected_device, pin)

            # Toggle Shift
            if self.input_handler.is_pressed(Action.SELECT):
                self.keyboard.toggle_shift()

            # Cancel
            if self.input_handler.is_pressed(Action.B):
                self.keyboard.deactivate()
                self.mode = "scan"
                self._update_help_text()

    def draw(self):
        """Draw Bluetooth settings screen."""
        if not self.active:
            return

        # Get theme colors
        theme = get_theme_manager()
        bg_color = theme.get_color("background")
        text_color = theme.get_color("text")
        text_selected_color = theme.get_color("text_selected")
        border_color = theme.get_color("border")

        # Clear screen
        pyxel.cls(bg_color)

        # Draw title
        title = "Bluetooth Settings"
        pyxel.text(2, 2, title, text_selected_color)

        # Draw system status
        self.system_status.draw()

        # Draw status message
        pyxel.text(2, 10, self.status_message, text_color)

        center_x = pyxel.width // 2
        window_width = pyxel.width - 8

        if self.mode == "scan":
            # Draw device list
            DQWindow.draw(2, 18, window_width, 100, bg_color=bg_color, border_color=border_color)

            start_y = 26
            line_height = 13
            visible = self.get_visible_items()
            visible_start, _ = self.get_visible_range()

            if not self.bt_enabled:
                msg = "Bluetooth is OFF"
                pyxel.text(center_x - len(msg) * 2, 60, msg, text_color)
                hint = "Press X to turn ON"
                pyxel.text(center_x - len(hint) * 2, 75, hint, text_color)
            elif not self.device_list:
                msg = "No devices found"
                pyxel.text(center_x - len(msg) * 2, 70, msg, text_color)
            else:
                for i, device_name in enumerate(visible):
                    y = start_y + i * line_height
                    index = visible_start + i

                    # Truncate long names
                    display_name = device_name[:30] if len(device_name) > 30 else device_name

                    color = text_selected_color if index == self.selected_index else text_color
                    draw_japanese_text(6, y, display_name, color)

        elif self.mode == "pin":
            # Draw PIN input screen
            DQWindow.draw(2, 18, window_width, 60, bg_color=bg_color, border_color=border_color)

            # Display device name
            dev_name = self.selected_device["name"][:20] if self.selected_device else ""
            pyxel.text(6, 26, f"Device: {dev_name}", text_color)
            pyxel.text(6, 34, "PIN (empty=no PIN):", text_color)

            # Draw software keyboard
            self.keyboard.draw()

        elif self.mode == "pairing":
            # Draw pairing screen
            DQWindow.draw(2, 18, window_width, 100, bg_color=bg_color, border_color=border_color)
            msg = "Pairing..."
            pyxel.text(center_x - len(msg) * 2, 70, msg, text_selected_color)

        # Status bar
        bt_status = "ON" if self.bt_enabled else "OFF"
        self.status_bar.set_text(
            left=f"BT:{bt_status}",
            center="",
            right=f"{len(self.device_list)} Dev"
        )
        self.status_bar.draw()

        # Help text
        self.help_text.draw()
