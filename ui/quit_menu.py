"""
Quit menu screen for system reboot and shutdown.
Uses external scripts for cross-platform compatibility.
"""

import os
import subprocess
import pyxel
from ui.base import ScrollableList
from ui.components import StatusBar, HelpText
from ui.window import DQWindow
from japanese_text import draw_japanese_text
from theme_manager import get_theme_manager
from debug import debug_print


class QuitMenu(ScrollableList):
    """Quit menu screen for reboot and shutdown options."""

    def __init__(self, input_handler, state_manager, config):
        super().__init__(items_per_page=5)
        self.input_handler = input_handler
        self.state_manager = state_manager
        self.config = config
        self.status_bar = StatusBar(138, 160)
        self.help_text = HelpText(146, 160)

        # Script paths from config
        self.scripts_dir = "scripts"
        self.reboot_script = config.global_vars.get(
            'REBOOT_SCRIPT',
            os.path.join(self.scripts_dir, "system_reboot.sh")
        )
        self.shutdown_script = config.global_vars.get(
            'SHUTDOWN_SCRIPT',
            os.path.join(self.scripts_dir, "system_shutdown.sh")
        )
        self.restart_pfe_script = config.global_vars.get(
            'RESTART_PFE_SCRIPT',
            os.path.join(self.scripts_dir, "restart_pfe.sh")
        )

        # Menu items
        self.menu_items = [
            {"name": "Restart PFE", "key": "restart_pfe", "description": "Restart PFE launcher"},
            {"name": "Reboot", "key": "reboot", "description": "Restart the system"},
            {"name": "Shutdown", "key": "shutdown", "description": "Power off the system"},
        ]
        self.set_items(self.menu_items)

        # Confirmation state
        self.confirming = False
        self.confirm_action = None

    def activate(self):
        """Called when screen becomes active."""
        super().activate()
        self.confirming = False
        self.confirm_action = None

        # Set help text
        self._update_help_text()

    def deactivate(self):
        """Called when screen becomes inactive."""
        super().deactivate()
        self.confirming = False
        self.confirm_action = None

    def _update_help_text(self):
        """Update help text based on current mode."""
        if self.confirming:
            self.help_text.set_controls([
                ("A", "Confirm"),
                ("B", "Cancel")
            ])
        else:
            self.help_text.set_controls([
                ("Up/Down", "Select"),
                ("A", "Execute"),
                ("B", "Back")
            ])

    def _execute_script(self, script_path: str) -> bool:
        """Execute a system script."""
        if not os.path.exists(script_path):
            debug_print(f"[QuitMenu] Script not found: {script_path}")
            return False

        try:
            debug_print(f"[QuitMenu] Executing: {script_path}")
            result = subprocess.run(
                ["sh", script_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            debug_print(f"[QuitMenu] Exit code: {result.returncode}")
            if result.stderr:
                debug_print(f"[QuitMenu] stderr: {result.stderr}")
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            debug_print("[QuitMenu] Script timeout")
            return False
        except Exception as e:
            debug_print(f"[QuitMenu] Script error: {e}")
            return False

    def _do_restart_pfe(self):
        """Restart PFE launcher using external script."""
        debug_print("[QuitMenu] Initiating PFE restart...")
        self._execute_script(self.restart_pfe_script)
        # Script will restart PFE, so exit current process
        import pyxel
        pyxel.quit()

    def _do_reboot(self):
        """Execute system reboot using external script."""
        debug_print("[QuitMenu] Initiating reboot...")
        self._execute_script(self.reboot_script)

    def _do_shutdown(self):
        """Execute system shutdown using external script."""
        debug_print("[QuitMenu] Initiating shutdown...")
        self._execute_script(self.shutdown_script)

    def update(self):
        """Update quit menu screen."""
        if not self.active:
            return

        from input_handler import Action

        if self.confirming:
            # Confirmation mode
            if self.input_handler.is_pressed(Action.A):
                # Execute the action
                if self.confirm_action == "restart_pfe":
                    self._do_restart_pfe()
                elif self.confirm_action == "reboot":
                    self._do_reboot()
                elif self.confirm_action == "shutdown":
                    self._do_shutdown()
                self.confirming = False
                self.confirm_action = None

            if self.input_handler.is_pressed(Action.B):
                # Cancel confirmation
                self.confirming = False
                self.confirm_action = None
                self._update_help_text()
        else:
            # Navigation mode
            if self.input_handler.is_pressed_with_repeat(Action.UP):
                self.scroll_up()
            elif self.input_handler.is_pressed_with_repeat(Action.DOWN):
                self.scroll_down()

            # Select action
            if self.input_handler.is_pressed(Action.A):
                selected = self.get_selected_item()
                if selected:
                    self.confirming = True
                    self.confirm_action = selected["key"]
                    self._update_help_text()

            # Back
            if self.input_handler.is_pressed(Action.B):
                self.state_manager.go_back()

    def draw(self):
        """Draw quit menu screen."""
        if not self.active:
            return

        # Get theme colors
        theme = get_theme_manager()
        bg_color = theme.get_color("background")
        text_color = theme.get_color("text")
        text_selected_color = theme.get_color("text_selected")
        border_color = theme.get_color("border")
        warning_color = 8  # Red for warning

        # Clear screen
        pyxel.cls(bg_color)

        # Draw title
        title = "Quit"
        pyxel.text(2, 2, title, text_selected_color)

        center_x = pyxel.width // 2

        if self.confirming:
            # Draw confirmation dialog
            dialog_width = 120
            dialog_x = center_x - dialog_width // 2
            DQWindow.draw(dialog_x, 50, dialog_width, 50, bg_color=bg_color, border_color=warning_color)

            if self.confirm_action == "restart_pfe":
                action_name = "Restart PFE"
            elif self.confirm_action == "reboot":
                action_name = "Reboot"
            else:
                action_name = "Shutdown"
            msg = f"{action_name}?"
            msg_x = center_x - len(msg) * 2
            pyxel.text(msg_x, 65, msg, warning_color)

            hint = "A:OK  B:Cancel"
            hint_x = center_x - len(hint) * 2
            pyxel.text(hint_x, 82, hint, text_color)
        else:
            # Draw menu window
            window_width = pyxel.width - 8
            DQWindow.draw(2, 18, window_width, 60, bg_color=bg_color, border_color=border_color)

            # Draw menu items
            start_y = 30
            line_height = 16

            for i, item in enumerate(self.menu_items):
                y = start_y + i * line_height
                color = text_selected_color if i == self.selected_index else text_color
                draw_japanese_text(20, y, item["name"], color)

        # Status bar
        self.status_bar.set_text(
            left="System",
            center="",
            right=""
        )
        self.status_bar.draw()

        # Help text
        self.help_text.draw()
