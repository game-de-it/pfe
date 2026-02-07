"""
About screen showing system and application information.
"""

import os
import sys
import pyxel
import subprocess
from ui.base import ScrollableList
from ui.components import StatusBar, HelpText
from ui.window import DQWindow
from japanese_text import draw_japanese_text
from theme_manager import get_theme_manager
from version import VERSION, VERSION_DATE


class About(ScrollableList):
    """About screen with system information."""

    def __init__(self, input_handler, state_manager, config):
        super().__init__(items_per_page=10)
        self.input_handler = input_handler
        self.state_manager = state_manager
        self.config = config
        self.status_bar = StatusBar(138, 160)
        self.help_text = HelpText(146, 160)

        self.info_lines = []

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
        settings_loaded = False
        try:
            from persistence import PersistenceManager
            persistence = PersistenceManager()
            settings = persistence.load_settings()
            theme = settings.get("theme", "dark")
            button_layout = settings.get("button_layout", "NINTENDO")
            self.info_lines.append(f"Theme: {theme}")
            self.info_lines.append(f"Button Layout: {button_layout}")
            settings_loaded = True
        except:
            pass

        # Categories/ROMs
        try:
            categories = self.config.get_categories()
            self.info_lines.append(f"Categories: {len(categories)}")
        except:
            pass

        if settings_loaded:
            self.info_lines.append("")

        # WiFi Status
        try:
            result = subprocess.run(['nmcli', '-t', '-f', 'ACTIVE,SSID', 'device', 'wifi', 'list'],
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.startswith('yes:'):
                        ssid = line[4:]
                        self.info_lines.append(f"WiFi: {ssid}")
                        break
                else:
                    self.info_lines.append("WiFi: Not connected")
            else:
                self.info_lines.append("WiFi: Unknown")
        except:
            self.info_lines.append("WiFi: N/A")
        self.info_lines.append("")

        # System Info (uname -a)
        try:
            result = subprocess.run(['uname', '-a'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                uname_output = result.stdout.strip()
                self.info_lines.append("System:")
                # Wrap long lines
                self._add_wrapped_lines(uname_output, 35)
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
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        # Parse KB and convert to MB
                        mem_kb = int(line.split()[1])
                        mem_mb = mem_kb // 1024
                        self.info_lines.append(f"Memory: {mem_mb} MB")
                        break
        except:
            pass
        self.info_lines.append("")

        # Disk Info (df -h)
        try:
            result = subprocess.run(['df', '-h'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                self.info_lines.append("Storage:")
                lines = result.stdout.strip().split('\n')
                # Skip header, show Filesystem, Size, Used, Mounted on
                for line in lines[1:]:
                    parts = line.split()
                    if len(parts) >= 6:
                        fs = parts[0]
                        size = parts[1]
                        used = parts[2]
                        mounted = parts[5]
                        # Truncate filesystem name if too long
                        if len(fs) > 15:
                            fs = fs[:12] + "..."
                        self.info_lines.append(f"  {fs}")
                        self.info_lines.append(f"    {size} ({used} used)")
                        self.info_lines.append(f"    -> {mounted}")
        except:
            pass

        # Set items for scrolling
        self.set_items(self.info_lines)

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

        from input_handler import Action

        # Scrolling
        if self.input_handler.is_pressed_with_repeat(Action.UP):
            self.scroll_up()
        elif self.input_handler.is_pressed_with_repeat(Action.DOWN):
            self.scroll_down()

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

        # Draw information
        start_y = 26
        line_height = 8
        visible = self.get_visible_items()

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
        self.status_bar.set_text(
            left="About",
            center="",
            right=f"{self.scroll_offset + 1}/{len(self.info_lines)}"
        )
        self.status_bar.draw()

        # Help text
        self.help_text.draw()
