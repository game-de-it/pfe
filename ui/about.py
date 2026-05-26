"""
About screen showing system and application information.
"""

import os
import sys
import pyxel
import subprocess
import shutil
from ui.base import ScrollableList
from ui.components import StatusBar, HelpText
from ui.window import DQWindow
from pfe_app.theme_manager import get_theme_manager
from pfe_app.version import VERSION, VERSION_DATE


class About(ScrollableList):
    """About screen with system information."""

    def __init__(self, input_handler, state_manager, config):
        super().__init__(items_per_page=14)
        self.input_handler = input_handler
        self.state_manager = state_manager
        self.config = config
        self.status_bar = StatusBar(138, 160)
        self.help_text = HelpText(146, 160)

        self.info_lines = []
        self.content_y = 24
        self.content_height = 112
        self.line_height = 8

    def activate(self):
        """Called when screen becomes active."""
        super().activate()

        # Gather system information
        self._gather_system_info()

        # Set help text
        self.help_text.set_controls([
            ("Up/Down", "Scroll"),
            ("B", "Back")
        ])
        self.selected_index = 0
        self.scroll_offset = 0

    def deactivate(self):
        """Called when screen becomes inactive."""
        super().deactivate()

    def _gather_system_info(self):
        """Gather all system information."""
        self.info_lines = []

        # PFE Version
        self.info_lines.append(f"PFE Version: {VERSION}")
        self.info_lines.append(f"Release Date: {VERSION_DATE}")
        self.info_lines.append("")

        # Python Version
        self.info_lines.append(f"Python: {sys.version.split()[0]}")
        self.info_lines.append("")

        # Python Modules (from requirements.txt)
        self.info_lines.append("Python Modules:")
        self._add_module_versions()
        self.info_lines.append("")

        # Current Settings
        try:
            from pfe_app.persistence import PersistenceManager
            persistence = PersistenceManager()
            settings = persistence.load_settings()
            theme = settings.get("theme", "dark")
            self.info_lines.append(f"Theme: {theme}")
            self.info_lines.append("")
            self.info_lines.append(f"Key Config: {self._key_config_status()}")
            self.info_lines.append("")
        except:
            pass

        # Categories/ROMs
        try:
            categories = self.config.get_categories()
            self.info_lines.append(f"Categories: {len(categories)}")
            self.info_lines.append("")
        except:
            pass

        # Network Info
        self._add_network_info()
        self.info_lines.append("")

        # System Info (uname -a)
        try:
            result = subprocess.run(['uname', '-a'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                uname_output = result.stdout.strip()
                self.info_lines.append("System:")
                # Wrap long lines
                self._add_wrapped_lines(uname_output, self._wrap_width_chars())
                self.info_lines.append("")
        except:
            pass

        # CPU Info
        try:
            # Get CPU count
            cpu_count = os.cpu_count() or 1

            # Get max frequency from cpuinfo
            max_freq = "Unknown"
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if 'cpu MHz' in line:
                            freq = float(line.split(':')[1].strip())
                            max_freq = f"{int(freq)} MHz"
                            break
            except:
                pass

            self.info_lines.append(f"CPU: {cpu_count} cores")
            if max_freq != "Unknown":
                self.info_lines.append(f"CPU Freq: {max_freq}")
        except:
            pass
        self.info_lines.append("")

        # Memory Info
        self._add_memory_info()
        self.info_lines.append("")

        self._add_storage_info()

        # Set items for scrolling
        self.items_per_page = self._visible_line_count()
        self.set_items(self.info_lines)
        self.selected_index = 0
        self.scroll_offset = 0

    def _key_config_status(self) -> str:
        """Return whether PFE is using a custom key mapping."""
        config_file = os.path.join("data", "keyconfig.json")
        if os.path.exists(config_file):
            return "Custom"
        return "Default"

    def _visible_line_count(self) -> int:
        """Return how many text rows fit inside the window."""
        return max(1, self.content_height // self.line_height)

    def _wrap_width_chars(self) -> int:
        """Return approximate text wrap width for Pyxel's default font."""
        content_width = max(1, pyxel.width - 18)
        return max(12, content_width // 4)

    def _max_scroll_offset(self) -> int:
        return max(0, len(self.info_lines) - self.items_per_page)

    def _add_memory_info(self):
        """Add total, used, and available memory from /proc/meminfo."""
        values = {}
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if ':' not in line:
                        continue
                    key, rest = line.split(':', 1)
                    parts = rest.split()
                    if parts and parts[0].isdigit():
                        values[key] = int(parts[0])
        except Exception:
            return

        total_kb = values.get('MemTotal', 0)
        if total_kb <= 0:
            return

        available_kb = values.get('MemAvailable')
        if available_kb is None:
            available_kb = (
                values.get('MemFree', 0)
                + values.get('Buffers', 0)
                + values.get('Cached', 0)
                + values.get('SReclaimable', 0)
                - values.get('Shmem', 0)
            )
        available_kb = max(0, min(total_kb, available_kb))
        used_kb = max(0, total_kb - available_kb)
        used_percent = int(round((used_kb / total_kb) * 100))

        self.info_lines.append("Memory:")
        self.info_lines.append(
            f"  Used: {self._format_bytes(used_kb * 1024)} / "
            f"{self._format_bytes(total_kb * 1024)} ({used_percent}%)"
        )
        self.info_lines.append(f"  Free: {self._format_bytes(available_kb * 1024)}")

    def _add_network_info(self):
        """Add network addresses without depending on a specific WiFi stack."""
        self.info_lines.append("Network:")

        addresses = self._get_ip_addresses()
        if addresses:
            for iface, address in addresses:
                self.info_lines.append(f"  {iface}: {address}")
        else:
            self.info_lines.append("  IP: Not available")

        ssid = self._get_wifi_ssid()
        if ssid:
            self.info_lines.append(f"  WiFi: {ssid}")

    def _get_ip_addresses(self) -> list[tuple[str, str]]:
        """Return global IPv4 addresses as (interface, address)."""
        ignored_prefixes = (
            "lo", "docker", "br-", "veth", "virbr", "tun", "tap",
        )
        addresses: list[tuple[str, str]] = []

        try:
            result = subprocess.run(
                ["ip", "-o", "-4", "addr", "show", "scope", "global"],
                capture_output=True,
                text=True,
                timeout=2,
            )
        except Exception:
            result = None

        if result and result.returncode == 0:
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) < 4 or "inet" not in parts:
                    continue
                iface = parts[1].split("@", 1)[0]
                if iface.startswith(ignored_prefixes):
                    continue
                inet_index = parts.index("inet")
                if inet_index + 1 >= len(parts):
                    continue
                address = parts[inet_index + 1].split("/", 1)[0]
                if address and not address.startswith("127."):
                    addresses.append((iface, address))

        if addresses:
            return addresses

        # BusyBox systems often still provide hostname -I even when ip output differs.
        try:
            result = subprocess.run(
                ["hostname", "-I"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                for address in result.stdout.split():
                    if "." in address and ":" not in address and not address.startswith("127."):
                        return [("IP", address)]
        except Exception:
            pass

        return []

    def _get_wifi_ssid(self) -> str:
        """Best-effort WiFi SSID lookup for About; absence is not an error."""
        commands = (
            ["iwgetid", "-r"],
            ["nmcli", "-t", "-f", "ACTIVE,SSID", "device", "wifi", "list"],
        )

        for command in commands:
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=2)
            except Exception:
                continue
            if result.returncode != 0:
                continue

            output = result.stdout.strip()
            if not output:
                continue
            if command[0] == "nmcli":
                for line in output.splitlines():
                    if line.startswith("yes:"):
                        return line[4:].strip()
                continue
            return output.splitlines()[0].strip()

        return ""

    def _scroll_content(self, delta: int):
        """Scroll the visible window directly; About has no selectable cursor."""
        max_scroll = self._max_scroll_offset()
        self.scroll_offset = max(0, min(max_scroll, self.scroll_offset + delta))

    def _add_storage_info(self):
        """Add concise, user-facing storage summaries."""
        rows = []
        rows_by_device = {}
        for label, path in self._storage_targets():
            if not path or not os.path.exists(path):
                continue
            try:
                real_path = os.path.realpath(path)
                stat = os.stat(real_path)
                device_key = getattr(stat, "st_dev", real_path)
                usage = shutil.disk_usage(real_path)
            except Exception:
                continue

            priority = self._storage_label_priority(label)
            row = rows_by_device.get(device_key)
            if row is None:
                row = {
                    "labels": [],
                    "path": real_path,
                    "usage": usage,
                    "priority": priority,
                }
                rows_by_device[device_key] = row
                rows.append(row)

            if label not in row["labels"]:
                row["labels"].append(label)
            if priority < row["priority"]:
                row["path"] = real_path
                row["priority"] = priority

        if not rows:
            return

        self.info_lines.append("Storage:")
        for index, row in enumerate(rows):
            label = self._format_storage_labels(row["labels"])
            path = row["path"]
            usage = row["usage"]
            total = max(1, usage.total)
            used = usage.used
            free = usage.free
            used_percent = int(round((used / total) * 100))
            mount_label = self._display_mount_path(path)

            self.info_lines.append(f"  {label}: {mount_label}")
            self.info_lines.append(
                f"  Used: {self._format_bytes(used)} / {self._format_bytes(total)} ({used_percent}%)"
            )
            self.info_lines.append(f"  Free: {self._format_bytes(free)}")
            if index < len(rows) - 1:
                self.info_lines.append("")

    def _storage_targets(self):
        """Return semantic storage targets for common handheld Linux layouts."""
        targets = []

        def add(label: str, path: str):
            if path:
                targets.append((label, path))

        add("System", "/")

        try:
            add("ROMs", self.config.get_rom_base())
        except Exception:
            pass
        for key in ("ROM_DIR", "ROMS_DIR", "ROM_PATH", "ROMS_PATH"):
            add("ROMs", self.config.global_vars.get(key, ""))
        for key in (
            "SAVE_DIR", "SAVES_DIR", "SAVE_PATH", "SAVES_PATH",
            "STATE_DIR", "STATES_DIR", "RETROARCH_SAVE_DIR",
            "RETROARCH_STATE_DIR",
        ):
            add("Saves", self.config.global_vars.get(key, ""))

        # ROCKNIX / JELOS style storage.
        add("ROMs", "/storage/roms")
        add("Saves", "/storage/saves")
        add("Saves", "/storage/save")
        add("Saves", "/storage/.config/retroarch/saves")
        add("Saves", "/storage/.config/retroarch/states")
        add("Saves", "/storage/retroarch/saves")
        add("Saves", "/storage/retroarch/states")
        add("Storage", "/storage")
        add("Flash", "/flash")

        # muOS style storage.
        add("ROMs", "/mnt/union/ROMS")
        add("Ports", "/mnt/union/ports")
        add("Saves", "/run/muos/storage/save")
        add("Saves", "/mnt/mmc/MUOS/save")
        add("Saves", "/mnt/mmc/MUOS/saves")
        add("Saves", "/mnt/mmc/SAVES")
        add("Saves", "/mnt/mmc/saves")
        add("Saves", "/mnt/mmc/save")
        add("SD Card", "/mnt/mmc")
        add("Boot", "/mnt/boot")

        # Other common handheld layouts.
        add("ROMs", "/roms")
        add("Saves", "/saves")
        add("ROMs", "/userdata/roms")
        add("Saves", "/userdata/saves")
        add("ROMs", "/mnt/SDCARD/Roms")
        add("ROMs", "/mnt/SDCARD/ROMS")
        add("Saves", "/mnt/SDCARD/Saves")
        add("Saves", "/mnt/SDCARD/SAVES")

        try:
            add("Screens", self.config.get_screenshot_dir())
        except Exception:
            pass
        add("Screens", "/run/muos/storage/screenshot")
        add("PFE", os.getcwd())

        for label, path in self._discover_storage_mounts():
            add(label, path)

        return targets

    def _discover_storage_mounts(self):
        """Discover likely persistent storage mounts without parsing df -h columns."""
        mounts_file = "/proc/mounts"
        if not os.path.exists(mounts_file):
            return []

        ignored_types = {
            "tmpfs", "devtmpfs", "proc", "sysfs", "devpts", "cgroup",
            "cgroup2", "debugfs", "securityfs", "pstore", "efivarfs",
            "configfs", "fusectl", "mqueue", "hugetlbfs",
        }
        ignored_prefixes = (
            "/dev", "/proc", "/sys", "/tmp", "/var",
            "/usr/lib", "/usr/lib32",
        )
        important_prefixes = (
            "/storage", "/mnt/mmc", "/mnt/union", "/flash", "/roms",
            "/saves", "/userdata", "/mnt/SDCARD", "/run/muos/storage",
        )
        device_prefixes = (
            "/dev/mmc", "/dev/sd", "/dev/nvme", "/dev/mapper",
        )

        discovered = []
        try:
            with open(mounts_file, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception:
            return []

        for line in lines:
            parts = line.split()
            if len(parts) < 3:
                continue
            device, mount_point, fs_type = parts[:3]
            mount_point = mount_point.replace("\\040", " ")
            if fs_type in ignored_types:
                continue
            mount_is_storage = mount_point.startswith(important_prefixes)
            if mount_point != "/" and mount_point.startswith(ignored_prefixes) and not mount_is_storage:
                continue
            if os.path.isfile(mount_point):
                continue

            device_is_storage = device.startswith(device_prefixes)
            fs_is_union = fs_type in ("unionfs", "overlay")
            if not (device_is_storage or mount_is_storage or fs_is_union):
                continue

            label = self._storage_label_for_mount(mount_point)
            discovered.append((label, mount_point))

        return discovered

    def _storage_label_for_mount(self, mount_point: str) -> str:
        """Choose a friendly label for a discovered mount point."""
        lowered = mount_point.lower()
        if "rom" in lowered:
            return "ROMs"
        if "save" in lowered or "state" in lowered:
            return "Saves"
        if "port" in lowered:
            return "Ports"
        if "screenshot" in lowered or "screen" in lowered:
            return "Screens"
        if mount_point == "/flash":
            return "Flash"
        if mount_point == "/mnt/boot":
            return "Boot"
        if mount_point in ("/storage", "/mnt/mmc"):
            return "Storage"
        return "Storage"

    def _storage_label_priority(self, label: str) -> int:
        """Priority for choosing the best display path for a partition."""
        priority = {
            "ROMs": 0,
            "Saves": 1,
            "Ports": 2,
            "Screens": 3,
            "Storage": 4,
            "SD Card": 4,
            "Flash": 5,
            "Boot": 6,
            "PFE": 10,
            "System": 9,
        }
        return priority.get(label, 7)

    def _format_storage_labels(self, labels: list[str]) -> str:
        """Compact multiple semantic targets on the same partition."""
        ordered = sorted(labels, key=self._storage_label_priority)
        result = []
        for label in ordered:
            if label == "PFE" and (
                "System" in labels or any(existing in result for existing in ("ROMs", "Saves", "Ports", "Screens"))
            ):
                continue
            if label == "System" and any(existing in result for existing in ("ROMs", "Saves", "Ports", "Screens")):
                continue
            if label in ("Storage", "SD Card", "PFE") and any(
                existing in result for existing in ("ROMs", "Saves", "Ports", "Screens")
            ):
                continue
            if label == "Screens" and any(existing in result for existing in ("ROMs", "Saves")):
                continue
            if label not in result:
                result.append(label)
        if len(result) > 3:
            return "/".join(result[:3]) + "+"
        return "/".join(result) if result else "Storage"

    def _display_mount_path(self, path: str) -> str:
        """Shorten long paths for the small About window."""
        if path == "/":
            return "/"
        home = os.path.expanduser("~")
        if path.startswith(home):
            path = "~" + path[len(home):]
        max_chars = self._wrap_width_chars() - 12
        if len(path) > max_chars:
            return "..." + path[-max(6, max_chars - 3):]
        return path

    def _format_bytes(self, value: int) -> str:
        """Format byte counts for humans in the small UI."""
        units = ["B", "KB", "MB", "GB", "TB"]
        amount = float(value)
        unit_index = 0
        while amount >= 1024 and unit_index < len(units) - 1:
            amount /= 1024.0
            unit_index += 1
        if unit_index == 0:
            return f"{int(amount)}{units[unit_index]}"
        if amount >= 100 or amount.is_integer():
            return f"{int(round(amount))}{units[unit_index]}"
        return f"{amount:.1f}{units[unit_index]}"

    def _add_module_versions(self):
        """Add Python module versions from requirements.txt."""
        try:
            import importlib.metadata as metadata
        except ImportError:
            import importlib_metadata as metadata

        # Read requirements.txt
        requirements_file = "requirements.txt"
        if not os.path.exists(requirements_file):
            self.info_lines.append("  requirements.txt not found")
            return

        try:
            with open(requirements_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    # Parse module name (handle ==, >=, <=, etc.)
                    module_name = line.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0].strip()

                    # Get installed version
                    try:
                        version = metadata.version(module_name)
                        self.info_lines.append(f"  {module_name}: {version}")
                    except:
                        # Try alternative names (e.g., Pillow -> PIL)
                        alt_names = {
                            'Pillow': 'PIL',
                            'pyxel-universal-font': 'pyxel_universal_font'
                        }
                        if module_name in alt_names:
                            try:
                                version = metadata.version(alt_names[module_name])
                                self.info_lines.append(f"  {module_name}: {version}")
                            except:
                                self.info_lines.append(f"  {module_name}: Not installed")
                        else:
                            self.info_lines.append(f"  {module_name}: Not installed")
        except Exception as e:
            self.info_lines.append(f"  Error reading requirements: {str(e)[:20]}")

    def _add_wrapped_lines(self, text: str, width: int):
        """Add text with line wrapping."""
        words = text.split()
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 <= width:
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word
            else:
                if current_line:
                    self.info_lines.append(f"  {current_line}")
                current_line = word
        if current_line:
            self.info_lines.append(f"  {current_line}")

    def update(self):
        """Update about screen logic."""
        if not self.active:
            return

        from pfe_app.input_handler import Action

        # Scrolling
        if self.input_handler.is_pressed_with_repeat(Action.UP):
            self._scroll_content(-1)
        elif self.input_handler.is_pressed_with_repeat(Action.DOWN):
            self._scroll_content(1)

        # Back
        if self.input_handler.is_pressed(Action.B):
            self.state_manager.go_back()

    def draw(self):
        """Draw about screen."""
        if not self.active:
            return

        # Get theme colors
        theme = get_theme_manager()
        bg_color = theme.get_color("background")
        text_color = theme.get_color("text")
        text_selected_color = theme.get_color("text_selected")
        border_color = theme.get_color("border")
        scrollbar_color = theme.get_color("scrollbar")

        # Clear screen
        pyxel.cls(bg_color)

        # Draw title
        title = "About"
        pyxel.text(2, 2, title, text_selected_color)

        # Draw main window frame
        window_width = pyxel.width - 8
        DQWindow.draw(2, 18, window_width, 120, bg_color=bg_color, border_color=border_color)

        # Draw information. About is a direct scroller, not a selectable list.
        start_y = self.content_y
        line_height = self.line_height
        self.items_per_page = self._visible_line_count()
        visible_start = self.scroll_offset
        visible_end = min(len(self.info_lines), visible_start + self.items_per_page)
        visible = self.info_lines[visible_start:visible_end]

        for i, line in enumerate(visible):
            y = start_y + i * line_height
            # Use small font
            pyxel.text(6, y, line, text_color)

        # Draw scrollbar if needed
        if len(self.info_lines) > self.items_per_page:
            from ui.base import draw_scrollbar
            scrollbar_x = pyxel.width - 4
            draw_scrollbar(scrollbar_x, start_y, self.items_per_page * line_height,
                          len(self.info_lines), self.items_per_page, self.scroll_offset, scrollbar_color)

        # Status bar
        visible_end = min(len(self.info_lines), self.scroll_offset + self.items_per_page)
        self.status_bar.set_text(
            left="About",
            center="",
            right=f"{self.scroll_offset + 1}-{visible_end}/{len(self.info_lines)}"
        )
        self.status_bar.draw()

        # Help text
        self.help_text.draw()
