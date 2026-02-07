"""
Key configuration screen with wizard-style key binding.
"""

import pyxel
from ui.base import UIScreen
from ui.components import StatusBar, HelpText
from japanese_text import draw_japanese_text
from theme_manager import get_theme_manager
import json
import os


class KeyConfig(UIScreen):
    """Key configuration wizard screen."""

    def __init__(self, input_handler, state_manager, config):
        super().__init__()
        self.input_handler = input_handler
        self.state_manager = state_manager
        self.config = config
        self.status_bar = StatusBar(138, 160)
        self.help_text = HelpText(146, 160)

        # Key configuration order
        self.key_names = ["A", "B", "X", "Y", "START", "SELECT", "L", "R", "L2", "R2"]
        self.current_key_index = 0
        self.key_bindings = {}  # action_name -> pyxel_key

        # Timeout management
        self.waiting_for_input = False
        self.timeout_frames = 0
        self.max_timeout_frames = 90  # 3 seconds (assuming 30fps)

        # Completion flag
        self.config_complete = False

        # Warning message
        self.warning_message = ""
        self.warning_frames = 0

    def activate(self):
        """Called when screen becomes active."""
        super().activate()

        # Reset
        self.current_key_index = 0
        self.key_bindings = {}
        self.waiting_for_input = True
        self.timeout_frames = 0
        self.config_complete = False
        self.warning_message = ""
        self.warning_frames = 0

        # Help text
        self.help_text.set_controls([
            ("Press Key", "Assign"),
            ("Wait 3s", "Skip")
        ])

    def deactivate(self):
        """Called when screen becomes inactive."""
        super().deactivate()

    def _get_current_key_name(self) -> str:
        """Get the name of the key currently being configured."""
        if self.current_key_index < len(self.key_names):
            return self.key_names[self.current_key_index]
        return ""

    def _is_key_required(self, key_name: str) -> bool:
        """Check if the key is required (A/B)."""
        return key_name in ["A", "B"]

    def _check_pressed_key(self) -> int:
        """Detect pressed key (returns Pyxel key code)."""
        # Gamepad buttons
        gamepad_buttons = [
            (pyxel.GAMEPAD1_BUTTON_A, "GP_A"),
            (pyxel.GAMEPAD1_BUTTON_B, "GP_B"),
            (pyxel.GAMEPAD1_BUTTON_X, "GP_X"),
            (pyxel.GAMEPAD1_BUTTON_Y, "GP_Y"),
            (pyxel.GAMEPAD1_BUTTON_LEFTSHOULDER, "GP_L"),
            (pyxel.GAMEPAD1_BUTTON_RIGHTSHOULDER, "GP_R"),
            (pyxel.GAMEPAD1_BUTTON_BACK, "GP_SELECT"),
            (pyxel.GAMEPAD1_BUTTON_START, "GP_START"),
        ]

        for button, name in gamepad_buttons:
            if pyxel.btnp(button):
                return button

        # Analog triggers (L2/R2) - get value with btnv() and check threshold
        trigger_threshold = 0.5
        trigger_axes = [
            (pyxel.GAMEPAD1_AXIS_TRIGGERLEFT, "GP_L2"),
            (pyxel.GAMEPAD1_AXIS_TRIGGERRIGHT, "GP_R2"),
        ]

        for axis, name in trigger_axes:
            value = pyxel.btnv(axis)
            # Compare with previous frame state to detect "just pressed" moment
            prev_key = f"_prev_{axis}"
            prev_value = getattr(self, prev_key, 0.0)
            setattr(self, prev_key, value)

            if value >= trigger_threshold and prev_value < trigger_threshold:
                return axis

        # Keyboard
        keyboard_keys = [
            (pyxel.KEY_Z, "Z"),
            (pyxel.KEY_X, "X"),
            (pyxel.KEY_C, "C"),
            (pyxel.KEY_V, "V"),
            (pyxel.KEY_A, "A"),
            (pyxel.KEY_S, "S"),
            (pyxel.KEY_D, "D"),
            (pyxel.KEY_Q, "Q"),
            (pyxel.KEY_W, "W"),
            (pyxel.KEY_E, "E"),
            (pyxel.KEY_SPACE, "SPACE"),
            (pyxel.KEY_RETURN, "ENTER"),
            (pyxel.KEY_SHIFT, "SHIFT"),
            (pyxel.KEY_ESCAPE, "ESC"),
        ]

        for key, name in keyboard_keys:
            if pyxel.btnp(key):
                return key

        return None

    def _advance_to_next_key(self):
        """Advance to the next key."""
        self.current_key_index += 1
        self.timeout_frames = 0
        self.warning_frames = 0

        if self.current_key_index >= len(self.key_names):
            # All keys configured
            self._finish_configuration()
        else:
            self.waiting_for_input = True

    def _finish_configuration(self):
        """Configuration completion processing."""
        # Check A/B required keys
        if "A" not in self.key_bindings or "B" not in self.key_bindings:
            self.warning_message = "A and B are required!"
            self.warning_frames = 90  # Display for 3 seconds
            # If A/B are not set, restart from the beginning
            self.current_key_index = 0
            self.key_bindings = {}
            self.waiting_for_input = True
            return

        # 設定を保存
        self._save_key_config()

        # input_handlerをリロードして新しい設定を即座に適用
        self.input_handler.load_key_config()
        self.input_handler._build_key_map()

        self.config_complete = True
        print("Key configuration saved and applied!")

    def _save_key_config(self):
        """キー設定を保存"""
        config_file = "data/keyconfig.json"

        # キーコードを保存可能な形式に変換
        config_data = {
            "version": "1.0",
            "bindings": {}
        }

        for action, key_code in self.key_bindings.items():
            config_data["bindings"][action] = key_code

        try:
            os.makedirs("data", exist_ok=True)
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            print(f"Key config saved to {config_file}")
        except Exception as e:
            print(f"Error saving key config: {e}")

    def update(self):
        """Update key config screen logic."""
        if not self.active:
            return

        from input_handler import Action

        # 警告メッセージのタイマー
        if self.warning_frames > 0:
            self.warning_frames -= 1

        # 設定完了後、BボタンまたはESCキーで戻る
        if self.config_complete:
            if self.input_handler.is_pressed(Action.B) or pyxel.btnp(pyxel.KEY_ESCAPE):
                self.state_manager.go_back()
            return

        # キー入力待ち
        if self.waiting_for_input:
            # タイムアウトカウント
            self.timeout_frames += 1

            # キー入力チェック
            pressed_key = self._check_pressed_key()

            if pressed_key is not None:
                # キーが押された
                current_key_name = self._get_current_key_name()
                self.key_bindings[current_key_name] = pressed_key
                print(f"{current_key_name} = {pressed_key}")
                self._advance_to_next_key()

            elif self.timeout_frames >= self.max_timeout_frames:
                # タイムアウト（3秒経過）
                current_key_name = self._get_current_key_name()

                # 必須キー（A/B）の場合はスキップ不可
                if self._is_key_required(current_key_name):
                    self.warning_message = f"{current_key_name} is required!"
                    self.warning_frames = 60  # 2秒表示
                    self.timeout_frames = 0  # タイムアウトリセット
                else:
                    # スキップ（未設定）
                    print(f"{current_key_name} = skipped")
                    self._advance_to_next_key()

        # キャンセル（ESCキーで戻る）
        if pyxel.btnp(pyxel.KEY_ESCAPE):
            self.state_manager.go_back()

    def draw(self):
        """Draw key config screen."""
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

        # タイトル
        title = "Key Configuration"
        pyxel.text(2, 2, title, text_selected_color)

        # 境界線
        pyxel.line(2, 18, pyxel.width - 3, 18, border_color)

        center_x = pyxel.width // 2

        if self.config_complete:
            # 完了メッセージ
            msg1 = "Configuration Complete!"
            msg2 = "Press B to return"
            pyxel.text(center_x - len(msg1) * 2, 30, msg1, text_selected_color)
            pyxel.text(center_x - len(msg2) * 2, 40, msg2, text_color)

            # 設定内容を2列で表示
            y = 55
            col = 0
            for i, (action, key_code) in enumerate(self.key_bindings.items()):
                x = 8 if col == 0 else 85
                line = f"{action}: {key_code}"
                pyxel.text(x, y, line, text_color)
                col += 1
                if col >= 2:
                    col = 0
                    y += 10

        else:
            # 進捗表示
            progress_text = f"Step {self.current_key_index + 1} / {len(self.key_names)}"
            pyxel.text(4, 22, progress_text, text_color)

            # 現在のキー名
            current_key_name = self._get_current_key_name()
            if current_key_name:
                prompt = f"Press key for [{current_key_name}] button"
                pyxel.text(4, 40, prompt, text_selected_color)

                # 必須マーク
                if self._is_key_required(current_key_name):
                    required_text = "(Required)"
                    pyxel.text(4, 50, required_text, 8)  # 赤色

            # タイムアウトバー
            if self.waiting_for_input and not self._is_key_required(current_key_name):
                bar_width = pyxel.width - 10
                bar_height = 8
                bar_x = 5
                bar_y = 65

                # 背景
                pyxel.rect(bar_x, bar_y, bar_width, bar_height, 5)

                # 進捗
                progress = min(1.0, self.timeout_frames / self.max_timeout_frames)
                filled_width = int(bar_width * progress)
                pyxel.rect(bar_x, bar_y, filled_width, bar_height, 11)

                # テキスト
                timeout_text = "Skip in 3 seconds..."
                pyxel.text(bar_x + 2, bar_y + 1, timeout_text, 0)

            # 既に設定されたキー
            y = 80
            pyxel.text(4, y, "Configured:", text_color)
            y += 10

            for action, key_code in self.key_bindings.items():
                line = f"  {action}: OK"
                pyxel.text(4, y, line, 11)  # 緑色
                y += 8
                if y > 130:
                    break

        # 警告メッセージ
        if self.warning_frames > 0:
            msg = self.warning_message
            msg_width = len(msg) * 4
            msg_x = 80 - msg_width // 2
            # 背景
            pyxel.rect(msg_x - 4, 76, msg_width + 8, 12, 8)
            # テキスト
            pyxel.text(msg_x, 79, msg, 7)

        # Status bar
        self.status_bar.set_text(
            left="Key Config",
            center="",
            right=f"{self.current_key_index}/{len(self.key_names)}"
        )
        self.status_bar.draw()

        # Help text
        self.help_text.draw()
