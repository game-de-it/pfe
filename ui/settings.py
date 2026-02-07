"""
Settings screen for app configuration.
"""

import pyxel
from ui.base import ScrollableList
from ui.components import StatusBar, HelpText
from ui.window import DQWindow
from japanese_text import draw_japanese_text, get_japanese_text_width
from theme_manager import get_theme_manager
from debug import debug_print
from system_monitor import get_system_monitor
from brightness_manager import get_brightness_manager


class Settings(ScrollableList):
    """Settings screen for configuring the application."""

    def __init__(self, input_handler, state_manager, config, persistence):
        super().__init__(items_per_page=8)
        self.input_handler = input_handler
        self.state_manager = state_manager
        self.config = config
        self.persistence = persistence
        self.status_bar = StatusBar(138, 160)
        self.help_text = HelpText(146, 160)

        # テーママネージャーを取得
        self.theme_manager = get_theme_manager()
        theme_names = self.theme_manager.get_theme_names()
        theme_ids = self.theme_manager.get_theme_ids()
        current_theme_id = self.theme_manager.get_current_theme()
        current_theme_index = theme_ids.index(current_theme_id) if current_theme_id in theme_ids else 0

        # システムモニターを取得（CPUガバナー用）
        self.system_monitor = get_system_monitor()

        # 輝度マネージャーを取得
        self.brightness_manager = get_brightness_manager()

        # 設定ファイルから設定を読み込み
        settings = self.persistence.load_settings()

        # Resolution設定
        resolution_values = ["1:1", "4:3"]
        resolution_str = settings.get("resolution", "1:1")
        resolution_index = resolution_values.index(resolution_str) if resolution_str in resolution_values else 0

        # CPUガバナーの現在の設定を取得
        cpu_governor_values = ["ondemand", "performance"]
        current_governor = self.system_monitor.get_cpu_governor() if self.system_monitor else None
        cpu_governor_index = 0
        if current_governor and current_governor in cpu_governor_values:
            cpu_governor_index = cpu_governor_values.index(current_governor)

        # 設定項目（新しい順序）
        # 1. Brightness, 2. Theme, 3. CPU Governor, 4. Resolution, 5. WiFi,
        # 6. Key Config, 7. BGM Config, 8. Statistics, 9. About, 10. Quit
        self.settings_items = [
            {"name": "Brightness", "type": "toggle", "key": "brightness", "values": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"], "current": 4},
            {"name": "Theme", "type": "toggle", "key": "theme", "values": theme_ids, "display_values": theme_names, "current": current_theme_index},
            {"name": "CPU Governor", "type": "toggle", "key": "cpu_governor", "values": cpu_governor_values, "current": cpu_governor_index},
            {"name": "Resolution", "type": "toggle", "key": "resolution", "values": resolution_values, "display_values": ["160x160", "214x160"], "current": resolution_index},
            {"name": "Date/Time", "type": "submenu", "key": "datetime"},
            {"name": "WiFi", "type": "submenu", "key": "wifi"},
            {"name": "Key Config", "type": "submenu", "key": "key_config_menu"},
            {"name": "BGM Config", "type": "submenu", "key": "bgm_config"},
            {"name": "Statistics", "type": "submenu", "key": "statistics"},
            {"name": "About", "type": "submenu", "key": "about"},
            {"name": "Quit", "type": "submenu", "key": "quit"},
        ]

        self.set_items(self.settings_items)

        # WiFi設定
        self.wifi_enabled = False
        self.wifi_ssid = ""
        self.wifi_password = ""
        self.wifi_connected = False

        # 設定が読み込まれたかどうかのフラグ
        self.settings_loaded = False

    def activate(self):
        """Called when screen becomes active."""
        super().activate()

        # 設定を読み込む
        self._load_settings()
        self.settings_loaded = True

        # 現在の輝度を取得して反映（OS側で変更されている場合があるため）
        if self.brightness_manager.is_available():
            current_brightness = self.brightness_manager.get_brightness()
            if current_brightness >= 1:
                for item in self.settings_items:
                    if item["key"] == "brightness":
                        # 1-10 を index 0-9 に変換
                        item["current"] = current_brightness - 1
                        debug_print(f"Brightness synced from system: {current_brightness}")
                        break

        # デバッグ出力
        for item in self.settings_items:
            if item["type"] == "toggle":
                debug_print(f"Settings loaded - {item['name']}: {item['values'][item['current']]}")

        # Set help text
        self.help_text.set_controls([
            ("Left/Right", "Change"),
            ("A", "Select"),
            ("B", "Back")
        ])

    def deactivate(self):
        """Called when screen becomes inactive."""
        super().deactivate()
        # 設定を保存（activate()された後のみ）
        if self.settings_loaded:
            self._save_settings()
            self.settings_loaded = False

    def _load_settings(self):
        """設定をロード"""
        settings = self.persistence.load_settings()

        # 各設定項目に値を反映
        for item in self.settings_items:
            if item["type"] == "toggle":
                key = item["key"]
                if key in settings:
                    # values配列のインデックスを探す
                    value = settings[key]
                    if value in item["values"]:
                        item["current"] = item["values"].index(value)

        # WiFi設定
        self.wifi_enabled = settings.get("wifi_enabled", False)
        self.wifi_ssid = settings.get("wifi_ssid", "")
        self.wifi_password = settings.get("wifi_password", "")

    def _save_settings(self):
        """設定を保存"""
        # 既存の設定を読み込む（view_modeなど他の設定を保持するため）
        settings = self.persistence.load_settings()

        # 各設定項目の値を更新
        for item in self.settings_items:
            if item["type"] == "toggle":
                key = item["key"]
                current_index = item["current"]
                settings[key] = item["values"][current_index]

        # WiFi設定を更新
        settings["wifi_enabled"] = self.wifi_enabled
        settings["wifi_ssid"] = self.wifi_ssid
        settings["wifi_password"] = self.wifi_password

        self.persistence.save_settings(settings)

    def update(self):
        """Update settings screen logic."""
        if not self.active:
            return

        from input_handler import Action

        # Navigation
        if self.input_handler.is_pressed_with_repeat(Action.UP):
            self.scroll_up()
        elif self.input_handler.is_pressed_with_repeat(Action.DOWN):
            self.scroll_down()

        # Change setting value
        selected = self.get_selected_item()
        if selected and selected["type"] == "toggle":
            changed = False
            if self.input_handler.is_pressed(Action.LEFT):
                # Decrement
                selected["current"] = (selected["current"] - 1) % len(selected["values"])
                debug_print(f"{selected['name']}: {selected['values'][selected['current']]}")
                changed = True
                self._apply_setting(selected)

            elif self.input_handler.is_pressed(Action.RIGHT):
                # Increment
                selected["current"] = (selected["current"] + 1) % len(selected["values"])
                debug_print(f"{selected['name']}: {selected['values'][selected['current']]}")
                changed = True
                self._apply_setting(selected)

            # 設定が変更されたら即座に保存
            if changed:
                self._save_settings()

        # Enter submenu
        if self.input_handler.is_pressed(Action.A):
            if selected and selected["type"] == "submenu":
                from state_manager import AppState
                if selected["key"] == "datetime":
                    self.state_manager.change_state(AppState.DATETIME_SETTINGS)
                elif selected["key"] == "wifi":
                    self.state_manager.change_state(AppState.WIFI_SETTINGS)
                elif selected["key"] == "key_config_menu":
                    self.state_manager.change_state(AppState.KEY_CONFIG_MENU)
                elif selected["key"] == "bgm_config":
                    self.state_manager.change_state(AppState.BGM_CONFIG)
                elif selected["key"] == "statistics":
                    self.state_manager.change_state(AppState.STATISTICS)
                elif selected["key"] == "about":
                    self.state_manager.change_state(AppState.ABOUT)
                elif selected["key"] == "quit":
                    self.state_manager.change_state(AppState.QUIT_MENU)

        # Back
        if self.input_handler.is_pressed(Action.B):
            self.state_manager.go_back()

    def _apply_setting(self, item):
        """Apply setting change immediately."""
        key = item["key"]

        if key == "theme":
            theme_id = item["values"][item["current"]]
            self.theme_manager.set_theme(theme_id)
        elif key == "cpu_governor":
            governor = item["values"][item["current"]]
            debug_print(f"Setting CPU governor to: {governor}")
            if self.system_monitor:
                success = self.system_monitor.set_cpu_governor(governor)
                debug_print(f"CPU governor set result: {success}")
        elif key == "brightness":
            brightness_level = int(item["values"][item["current"]])
            debug_print(f"Setting brightness to: {brightness_level}")
            if self.brightness_manager.is_available():
                self.brightness_manager.set_brightness(brightness_level)

    def draw(self):
        """Draw settings screen."""
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

        # Draw title (left-aligned to avoid overlap with system status)
        title = "SETTINGS"
        pyxel.text(2, 2, title, text_selected_color)

        # Draw subtitle
        subtitle = "Configure Options"
        subtitle_x = pyxel.width // 2 - len(subtitle) * 2
        pyxel.text(subtitle_x, 10, subtitle, text_color)

        # Draw main window frame
        window_width = pyxel.width - 8
        DQWindow.draw(2, 18, window_width, 120, bg_color=bg_color, border_color=border_color)

        # Draw settings list
        start_y = 26
        line_height = 13
        visible = self.get_visible_items()
        visible_start, _ = self.get_visible_range()

        for i, item in enumerate(visible):
            y = start_y + i * line_height
            index = visible_start + i

            # Draw setting name
            color = text_selected_color if index == self.selected_index else text_color
            draw_japanese_text(6, y, item["name"], color)

            # Draw value
            if item["type"] == "toggle":
                # Use display_values if available, otherwise use values
                if "display_values" in item:
                    display_value = item["display_values"][item["current"]]
                else:
                    display_value = item["values"][item["current"]]
                value_text = f"< {display_value} >"

                # Right-align the value to avoid overlapping with window border
                value_width = get_japanese_text_width(value_text)
                value_x = pyxel.width - 10 - value_width
                draw_japanese_text(value_x, y, value_text, color)
            elif item["type"] == "submenu":
                submenu_x = pyxel.width - 30
                draw_japanese_text(submenu_x, y, ">", color)

        # Draw scrollbar if needed
        if len(self.settings_items) > self.items_per_page:
            from ui.base import draw_scrollbar
            scrollbar_x = pyxel.width - 4
            draw_scrollbar(scrollbar_x, start_y, self.items_per_page * line_height,
                          len(self.settings_items), self.items_per_page, self.scroll_offset, scrollbar_color)

        # Status bar
        self.status_bar.set_text(
            left=f"Settings",
            center="",
            right=f"{self.selected_index + 1}/{len(self.settings_items)}"
        )
        self.status_bar.draw()

        # Help text
        self.help_text.draw()
