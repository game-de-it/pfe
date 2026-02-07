"""
WiFi settings screen with SSID scanning and password input.
"""

import os
import pyxel
import subprocess
import json
from ui.base import ScrollableList
from ui.components import StatusBar, HelpText, SystemStatus
from ui.window import DQWindow
from ui.software_keyboard import SoftwareKeyboard
from japanese_text import draw_japanese_text
from theme_manager import get_theme_manager
from debug import debug_print


class WiFiSettings(ScrollableList):
    """WiFi settings screen for scanning and connecting to networks."""

    def __init__(self, input_handler, state_manager, config):
        super().__init__(items_per_page=5)
        self.input_handler = input_handler
        self.state_manager = state_manager
        self.config = config
        self.status_bar = StatusBar(138, 160)
        self.help_text = HelpText(146, 160)
        self.system_status = SystemStatus()

        # WiFi settings
        self.wifi_interface = config.global_vars.get('WIFI_INTERFACE', 'wlan0')
        self.wifi_scan_script = config.global_vars.get('WIFI_SCAN_SCRIPT', '')
        self.wifi_connect_script = config.global_vars.get('WIFI_CONNECT_SCRIPT', '')
        self.wifi_status_script = config.global_vars.get('WIFI_STATUS_SCRIPT', '')
        self.wifi_toggle_script = config.global_vars.get('WIFI_TOGGLE_SCRIPT', '')

        # Data file paths
        self.data_dir = "data"
        self.wifi_config_file = os.path.join(self.data_dir, "wifi_config.json")
        self.wpa_supplicant_file = os.path.join(self.data_dir, "wpa_supplicant.conf")

        # SSID list
        self.ssid_list = []
        self.selected_ssid = ""

        # Software keyboard
        self.keyboard = SoftwareKeyboard(x=4, y=80)

        # Screen state
        self.mode = "scan"  # scan, password, connecting

        # Connection message
        self.status_message = ""

        # WiFi power state
        self.wifi_enabled = True

    def _is_root(self):
        """Check if running as root user."""
        return os.getuid() == 0

    def _get_wifi_radio_status(self):
        """Get current WiFi radio status (enabled/disabled)."""
        try:
            # If custom script is specified
            if self.wifi_status_script and os.path.exists(self.wifi_status_script):
                debug_print(f"[WiFi] Running status script: {self.wifi_status_script}")
                result = subprocess.run([self.wifi_status_script],
                                      capture_output=True,
                                      text=True,
                                      timeout=5)
            else:
                # Default: use nmcli
                result = subprocess.run(['nmcli', 'radio', 'wifi'],
                                      capture_output=True,
                                      text=True,
                                      timeout=5)

            status = result.stdout.strip().lower()
            debug_print(f"[WiFi] Radio status: {status}")
            return status == "enabled"
        except Exception as e:
            debug_print(f"[WiFi] Failed to get radio status: {e}")
            return True  # Assume enabled if check fails

    def _set_wifi_radio(self, enabled: bool):
        """Enable or disable WiFi radio."""
        action = "on" if enabled else "off"
        debug_print(f"[WiFi] Setting radio to: {action}")

        try:
            # If custom script is specified
            if self.wifi_toggle_script and os.path.exists(self.wifi_toggle_script):
                debug_print(f"[WiFi] Running toggle script: {self.wifi_toggle_script}")
                cmd = [self.wifi_toggle_script, action]
                result = subprocess.run(cmd,
                                      capture_output=True,
                                      text=True,
                                      timeout=10)
                debug_print(f"[WiFi] Toggle script stdout: {result.stdout}")
            else:
                # Default: use nmcli (may require sudo)
                if self._is_root():
                    cmd = ['nmcli', 'radio', 'wifi', action]
                else:
                    cmd = ['sudo', 'nmcli', 'radio', 'wifi', action]

                result = subprocess.run(cmd,
                                      capture_output=True,
                                      text=True,
                                      timeout=10)

            debug_print(f"[WiFi] Radio command exit code: {result.returncode}")
            if result.stderr:
                debug_print(f"[WiFi] Radio command stderr: {result.stderr}")

            if result.returncode == 0:
                self.wifi_enabled = enabled
                self.status_message = f"WiFi {'ON' if enabled else 'OFF'}"
                if enabled:
                    # Scan when WiFi is turned ON
                    self._scan_wifi()
                else:
                    # Clear list when WiFi is turned OFF
                    self.ssid_list = []
                    self.set_items([])
                return True
            else:
                self.status_message = f"Failed to turn {'on' if enabled else 'off'}"
                return False
        except Exception as e:
            debug_print(f"[WiFi] Radio command error: {e}")
            self.status_message = f"Error: {str(e)[:20]}"
            return False

    def activate(self):
        """Called when screen becomes active."""
        super().activate()

        # Load WiFi settings
        self._load_wifi_config()

        # Check WiFi power state
        self.wifi_enabled = self._get_wifi_radio_status()

        # Scan SSID list if WiFi is ON
        if self.wifi_enabled:
            self._scan_wifi()
        else:
            self.status_message = "WiFi is OFF"
            self.ssid_list = []
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
                ("A", "Conn"),
                ("X", "On/Off"),
                ("Y", "Scan"),
                ("B", "Back")
            ])
        elif self.mode == "password":
            self.help_text.set_controls([
                ("D-Pad", "Move"),
                ("A", "Type"),
                ("SELECT", "Shift"),
                ("B", "Cancel")
            ])

    def _load_wifi_config(self):
        """Load saved WiFi configuration."""
        if os.path.exists(self.wifi_config_file):
            try:
                with open(self.wifi_config_file, 'r') as f:
                    config = json.load(f)
                    # Restore settings as needed
            except Exception as e:
                debug_print(f"Error loading WiFi config: {e}")

    def _save_wifi_config(self, ssid: str, password: str):
        """Save WiFi configuration."""
        try:
            # Save WiFi settings to JSON
            config = {
                "ssid": ssid,
                "saved_at": pyxel.frame_count
            }
            with open(self.wifi_config_file, 'w') as f:
                json.dump(config, f, indent=2)

            # Save in wpa_supplicant.conf format
            with open(self.wpa_supplicant_file, 'w') as f:
                f.write("network={\n")
                f.write(f'    ssid="{ssid}"\n')
                f.write(f'    psk="{password}"\n')
                f.write("    key_mgmt=WPA-PSK\n")
                f.write("}\n")

            debug_print(f"WiFi config saved: {ssid}")
        except Exception as e:
            debug_print(f"Error saving WiFi config: {e}")

    def _scan_wifi(self):
        """Scan for available WiFi networks."""
        self.status_message = "Scanning..."
        self.ssid_list = []

        try:
            # If custom script is specified
            if self.wifi_scan_script and os.path.exists(self.wifi_scan_script):
                debug_print(f"[WiFi] Running custom scan script: {self.wifi_scan_script}")
                result = subprocess.run([self.wifi_scan_script],
                                      capture_output=True,
                                      text=True,
                                      timeout=10)
                debug_print(f"[WiFi] Scan script exit code: {result.returncode}")
                debug_print(f"[WiFi] Scan script stdout: {result.stdout}")
                debug_print(f"[WiFi] Scan script stderr: {result.stderr}")
                ssids = result.stdout.strip().split('\n')
            else:
                # Default: use nmcli
                # First, explicitly trigger a rescan
                rescan_cmd = ['nmcli', 'device', 'wifi', 'rescan']
                debug_print(f"[WiFi] Triggering WiFi rescan: {' '.join(rescan_cmd)}")
                subprocess.run(rescan_cmd,
                             capture_output=True,
                             text=True,
                             timeout=5)

                # Wait a moment before getting the list
                import time
                time.sleep(2)

                cmd = ['nmcli', '-t', '-f', 'SSID', 'device', 'wifi', 'list']
                debug_print(f"[WiFi] Running scan command: {' '.join(cmd)}")
                result = subprocess.run(cmd,
                                      capture_output=True,
                                      text=True,
                                      timeout=10)
                debug_print(f"[WiFi] Scan exit code: {result.returncode}")
                debug_print(f"[WiFi] Scan stdout: {result.stdout}")
                debug_print(f"[WiFi] Scan stderr: {result.stderr}")
                ssids = result.stdout.strip().split('\n')

            # Exclude empty SSIDs and remove duplicates (preserve order)
            seen = set()
            self.ssid_list = []
            for ssid in ssids:
                ssid = ssid.strip()
                if ssid and ssid not in seen:
                    seen.add(ssid)
                    self.ssid_list.append(ssid)
            debug_print(f"[WiFi] Found SSIDs: {self.ssid_list}")

            if self.ssid_list:
                self.status_message = f"Found {len(self.ssid_list)} networks"
                self.set_items(self.ssid_list)
            else:
                self.status_message = "No networks found"

        except subprocess.TimeoutExpired:
            debug_print("[WiFi] Scan timeout")
            self.status_message = "Scan timeout"
        except FileNotFoundError as e:
            debug_print(f"[WiFi] Command not found: {e}")
            self.status_message = "nmcli not found"
        except Exception as e:
            debug_print(f"[WiFi] Scan error: {e}")
            self.status_message = f"Scan error: {str(e)[:20]}"

    def _connect_wifi(self, ssid: str, password: str):
        """Connect to WiFi network."""
        self.status_message = "Connecting..."

        debug_print(f"[WiFi] ===== Connection Start =====")
        debug_print(f"[WiFi] SSID: {ssid}")
        debug_print(f"[WiFi] Password length: {len(password)}")

        try:
            # Save settings
            debug_print(f"[WiFi] Saving config to: {self.wifi_config_file}")
            debug_print(f"[WiFi] Saving wpa_supplicant to: {self.wpa_supplicant_file}")
            self._save_wifi_config(ssid, password)

            # If custom script is specified
            if self.wifi_connect_script and os.path.exists(self.wifi_connect_script):
                cmd = [self.wifi_connect_script, ssid, password]
                debug_print(f"[WiFi] Running custom connect script: {cmd[0]}")
                result = subprocess.run(cmd,
                                      capture_output=True,
                                      text=True,
                                      timeout=30)
            else:
                # Default: use nmcli
                # First, delete existing connection profile (to avoid key-mgmt error)
                delete_cmd = ['nmcli', 'connection', 'delete', ssid]
                debug_print(f"[WiFi] Deleting existing connection: nmcli connection delete {ssid}")
                delete_result = subprocess.run(delete_cmd,
                                             capture_output=True,
                                             text=True,
                                             timeout=5)
                debug_print(f"[WiFi] Delete exit code: {delete_result.returncode} (0=deleted, 10=not found)")
                if delete_result.stderr:
                    debug_print(f"[WiFi] Delete stderr: {delete_result.stderr}")

                # Attempt connection (password quoted)
                cmd = ['nmcli', '--wait', '30', 'device', 'wifi', 'connect', ssid, 'password', password]
                debug_print(f"[WiFi] Running connect command: nmcli --wait 30 device wifi connect {ssid} password [HIDDEN]")
                result = subprocess.run(cmd,
                                      capture_output=True,
                                      text=True,
                                      timeout=35)

            debug_print(f"[WiFi] Connect exit code: {result.returncode}")
            debug_print(f"[WiFi] Connect stdout: {result.stdout}")
            debug_print(f"[WiFi] Connect stderr: {result.stderr}")

            if result.returncode == 0:
                debug_print("[WiFi] Connection successful!")
                self.status_message = "Connected!"
                self.mode = "scan"
            else:
                debug_print(f"[WiFi] Connection failed with exit code: {result.returncode}")
                error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                debug_print(f"[WiFi] Error message: {error_msg}")
                self.status_message = f"Failed: {error_msg[:15]}"
                self.mode = "scan"

        except subprocess.TimeoutExpired:
            debug_print("[WiFi] Connection timeout (30s)")
            self.status_message = "Connection timeout"
            self.mode = "scan"
        except Exception as e:
            debug_print(f"[WiFi] Connection error: {e}")
            import traceback
            traceback.print_exc()
            self.status_message = f"Error: {str(e)[:20]}"
            self.mode = "scan"

        debug_print(f"[WiFi] ===== Connection End =====")
        debug_print()

    def update(self):
        """Update WiFi settings screen."""
        if not self.active:
            return

        from input_handler import Action

        if self.mode == "scan":
            # SSID selection mode
            if self.input_handler.is_pressed_with_repeat(Action.UP):
                self.scroll_up()
            elif self.input_handler.is_pressed_with_repeat(Action.DOWN):
                self.scroll_down()

            # Select SSID and go to password input
            if self.input_handler.is_pressed(Action.A):
                if self.ssid_list:
                    self.selected_ssid = self.get_selected_item()
                    self.mode = "password"
                    self.keyboard.clear()
                    self.keyboard.activate()
                    self._update_help_text()

            # Rescan
            if self.input_handler.is_pressed(Action.Y):
                if self.wifi_enabled:
                    self._scan_wifi()
                else:
                    self.status_message = "WiFi is OFF"

            # Toggle WiFi ON/OFF
            if self.input_handler.is_pressed(Action.X):
                self._set_wifi_radio(not self.wifi_enabled)

            # Back
            if self.input_handler.is_pressed(Action.B):
                self.state_manager.go_back()

        elif self.mode == "password":
            # Password input mode (keyboard operation)
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
                    password = self.keyboard.get_text()
                    self.keyboard.deactivate()
                    self.mode = "connecting"
                    self._connect_wifi(self.selected_ssid, password)

            # Toggle Shift
            if self.input_handler.is_pressed(Action.SELECT):
                self.keyboard.toggle_shift()

            # Cancel
            if self.input_handler.is_pressed(Action.B):
                self.keyboard.deactivate()
                self.mode = "scan"
                self._update_help_text()

    def draw(self):
        """Draw WiFi settings screen."""
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

        # Draw title (left-aligned to avoid overlap with system status)
        title = "WiFi Settings"
        pyxel.text(2, 2, title, text_selected_color)

        # Draw system status
        self.system_status.draw()

        # Draw status message
        pyxel.text(2, 10, self.status_message, text_color)

        center_x = pyxel.width // 2
        window_width = pyxel.width - 8

        if self.mode == "scan":
            # Draw SSID list
            DQWindow.draw(2, 18, window_width, 100, bg_color=bg_color, border_color=border_color)

            start_y = 26
            line_height = 13
            visible = self.get_visible_items()
            visible_start, _ = self.get_visible_range()

            if not self.wifi_enabled:
                msg = "WiFi is OFF"
                pyxel.text(center_x - len(msg) * 2, 60, msg, text_color)
                hint = "Press X to turn ON"
                pyxel.text(center_x - len(hint) * 2, 75, hint, text_color)
            elif not self.ssid_list:
                msg = "No networks found"
                pyxel.text(center_x - len(msg) * 2, 70, msg, text_color)
            else:
                for i, ssid in enumerate(visible):
                    y = start_y + i * line_height
                    index = visible_start + i

                    # Truncate long SSIDs
                    display_ssid = ssid[:30] if len(ssid) > 30 else ssid

                    color = text_selected_color if index == self.selected_index else text_color
                    draw_japanese_text(6, y, display_ssid, color)

        elif self.mode == "password":
            # Draw password input screen
            DQWindow.draw(2, 18, window_width, 60, bg_color=bg_color, border_color=border_color)

            # Display SSID
            pyxel.text(6, 26, f"SSID: {self.selected_ssid[:20]}", text_color)
            pyxel.text(6, 34, "Password:", text_color)

            # Draw software keyboard
            self.keyboard.draw()

        elif self.mode == "connecting":
            # Draw connecting screen
            DQWindow.draw(2, 18, window_width, 100, bg_color=bg_color, border_color=border_color)
            msg = "Connecting..."
            pyxel.text(center_x - len(msg) * 2, 70, msg, text_selected_color)

        # Status bar
        wifi_status = "ON" if self.wifi_enabled else "OFF"
        self.status_bar.set_text(
            left=f"WiFi:{wifi_status}",
            center="",
            right=f"{len(self.ssid_list)} AP"
        )
        self.status_bar.draw()

        # Help text
        self.help_text.draw()
