"""
Input handler for keyboard and gamepad controls.
Maps Pyxel inputs to action names for easy remapping.
"""

import pyxel
from enum import Enum
import json
import os


class Action(Enum):
    """Available input actions."""
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    A = "a"  # Confirm/Select
    B = "b"  # Back/Cancel
    X = "x"  # Special action 1
    Y = "y"  # Special action 2
    L = "l"  # Page up / Jump to start
    R = "r"  # Page down / Jump to end
    L2 = "l2"  # Extra button
    R2 = "r2"  # Extra button
    START = "start"  # Menu / Add to favorites
    SELECT = "select"  # Core selection


class InputHandler:
    """Handles input from keyboard and gamepad."""

    def __init__(self, button_layout="NINTENDO"):
        """
        Initialize input handler.

        Args:
            button_layout: "NINTENDO" or "XBOX" button layout
        """
        self.button_layout = button_layout

        # Key repeat settings
        self.repeat_delay = 8  # Frame count (approximately 0.27 seconds @ 30fps)
        self.repeat_interval = 2  # Frame count (approximately 0.07 seconds @ 30fps)
        self.hold_frames = {}  # Frame count for how long each action has been held

        # Text input buffer for search
        self.text_input = ""
        self.text_input_mode = False

        # Custom key config
        self.custom_key_config = None
        self.load_key_config()

        # Initialize analog axis tracking
        self._init_axis_tracking()

        # Build key map
        self._build_key_map()

    def load_key_config(self):
        """Load custom key configuration from file."""
        config_file = "data/keyconfig.json"

        if not os.path.exists(config_file):
            self.custom_key_config = None
            return

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                self.custom_key_config = config_data.get("bindings", {})
                print(f"Custom key config loaded: {len(self.custom_key_config)} keys")
        except Exception as e:
            print(f"Error loading key config: {e}")
            self.custom_key_config = None

    def _build_key_map(self):
        """Build key map based on current button layout or custom config."""
        # Prioritize custom settings if available
        if self.custom_key_config:
            self.key_map = {}

            # Map from custom settings
            action_map = {
                "A": Action.A,
                "B": Action.B,
                "X": Action.X,
                "Y": Action.Y,
                "START": Action.START,
                "SELECT": Action.SELECT,
                "L": Action.L,
                "R": Action.R,
                "L2": Action.L2,
                "R2": Action.R2,
            }

            for key_name, action in action_map.items():
                if key_name in self.custom_key_config:
                    self.key_map[action] = [self.custom_key_config[key_name]]
                else:
                    self.key_map[action] = []  # Not configured

            # Direction keys are always fixed
            self.key_map[Action.UP] = [pyxel.KEY_UP, pyxel.GAMEPAD1_BUTTON_DPAD_UP]
            self.key_map[Action.DOWN] = [pyxel.KEY_DOWN, pyxel.GAMEPAD1_BUTTON_DPAD_DOWN]
            self.key_map[Action.LEFT] = [pyxel.KEY_LEFT, pyxel.GAMEPAD1_BUTTON_DPAD_LEFT]
            self.key_map[Action.RIGHT] = [pyxel.KEY_RIGHT, pyxel.GAMEPAD1_BUTTON_DPAD_RIGHT]

            print("Key map built from custom config")
            return

        # Default settings
        # Determine gamepad button mapping based on layout
        if self.button_layout == "XBOX":
            # Xbox/Steam Deck layout: B=confirm, A=back
            gamepad_a = pyxel.GAMEPAD1_BUTTON_B
            gamepad_b = pyxel.GAMEPAD1_BUTTON_A
            gamepad_x = pyxel.GAMEPAD1_BUTTON_Y
            gamepad_y = pyxel.GAMEPAD1_BUTTON_X
        else:
            # Nintendo/Anbernic layout: A=confirm, B=back
            gamepad_a = pyxel.GAMEPAD1_BUTTON_A
            gamepad_b = pyxel.GAMEPAD1_BUTTON_B
            gamepad_x = pyxel.GAMEPAD1_BUTTON_X
            gamepad_y = pyxel.GAMEPAD1_BUTTON_Y

        # Key mappings (keyboard + gamepad)
        self.key_map = {
            Action.UP: [pyxel.KEY_UP, pyxel.GAMEPAD1_BUTTON_DPAD_UP],
            Action.DOWN: [pyxel.KEY_DOWN, pyxel.GAMEPAD1_BUTTON_DPAD_DOWN],
            Action.LEFT: [pyxel.KEY_LEFT, pyxel.GAMEPAD1_BUTTON_DPAD_LEFT],
            Action.RIGHT: [pyxel.KEY_RIGHT, pyxel.GAMEPAD1_BUTTON_DPAD_RIGHT],
            Action.A: [pyxel.KEY_Z, pyxel.KEY_RETURN, gamepad_a],
            Action.B: [pyxel.KEY_X, pyxel.KEY_ESCAPE, gamepad_b],
            Action.X: [pyxel.KEY_A, gamepad_x],
            Action.Y: [pyxel.KEY_S, gamepad_y],
            Action.L: [pyxel.KEY_Q, pyxel.GAMEPAD1_BUTTON_LEFTSHOULDER],
            Action.R: [pyxel.KEY_W, pyxel.GAMEPAD1_BUTTON_RIGHTSHOULDER],
            Action.L2: [pyxel.KEY_E],
            Action.R2: [pyxel.KEY_R],
            Action.START: [pyxel.KEY_RETURN, pyxel.GAMEPAD1_BUTTON_START],
            Action.SELECT: [pyxel.KEY_SHIFT, pyxel.GAMEPAD1_BUTTON_BACK],
        }

    def set_button_layout(self, button_layout: str):
        """
        Change button layout dynamically.

        Args:
            button_layout: "NINTENDO" or "XBOX"
        """
        if button_layout != self.button_layout:
            self.button_layout = button_layout
            self._build_key_map()
            from debug import debug_print
            debug_print(f"Button layout changed to: {button_layout}")

        # Key repeat settings
        self.repeat_delay = 8  # Frame count (approximately 0.27 seconds @ 30fps)
        self.repeat_interval = 2  # Frame count (approximately 0.07 seconds @ 30fps)
        self.hold_frames = {}  # Frame count for how long each action has been held

        # Text input buffer for search
        self.text_input = ""
        self.text_input_mode = False

    def _init_axis_tracking(self):
        """Initialize analog axis tracking."""
        self._axis_keys = {
            pyxel.GAMEPAD1_AXIS_TRIGGERLEFT,
            pyxel.GAMEPAD1_AXIS_TRIGGERRIGHT,
        }
        self._axis_prev_values = {}
        self._axis_threshold = 0.5

    def _is_axis_key(self, key: int) -> bool:
        """Determine if the key is an analog axis key."""
        return key in self._axis_keys

    def _check_axis_pressed(self, key: int) -> bool:
        """Detect the moment when an analog axis is pressed."""
        value = pyxel.btnv(key)
        prev_value = self._axis_prev_values.get(key, 0.0)
        self._axis_prev_values[key] = value
        return value >= self._axis_threshold and prev_value < self._axis_threshold

    def _check_axis_held(self, key: int) -> bool:
        """Detect if an analog axis is being held."""
        return pyxel.btnv(key) >= self._axis_threshold

    def is_pressed(self, action: Action) -> bool:
        """Check if action button was just pressed (btnp)."""
        keys = self.key_map.get(action, [])
        for key in keys:
            if self._is_axis_key(key):
                if self._check_axis_pressed(key):
                    return True
            elif pyxel.btnp(key):
                return True
        return False

    def is_held(self, action: Action) -> bool:
        """Check if action button is being held (btn)."""
        keys = self.key_map.get(action, [])
        for key in keys:
            if self._is_axis_key(key):
                if self._check_axis_held(key):
                    return True
            elif pyxel.btn(key):
                return True
        return False

    def is_pressed_with_repeat(self, action: Action) -> bool:
        """
        Check if action button was pressed with key repeat support.
        Returns True on initial press, then after delay, repeatedly at interval.
        """
        # Check if button is currently held
        if self.is_held(action):
            # Initialize frame counter if not exists
            if action not in self.hold_frames:
                self.hold_frames[action] = 0

            # Increment hold counter
            self.hold_frames[action] += 1

            # Return True on first frame (initial press)
            if self.hold_frames[action] == 1:
                return True

            # Return True after delay, at regular intervals
            if self.hold_frames[action] > self.repeat_delay:
                frames_since_delay = self.hold_frames[action] - self.repeat_delay
                if frames_since_delay % self.repeat_interval == 0:
                    return True

            return False
        else:
            # Button released, reset counter
            if action in self.hold_frames:
                self.hold_frames[action] = 0
            return False

    def any_pressed(self, *actions: Action) -> bool:
        """Check if any of the given actions were just pressed."""
        return any(self.is_pressed(action) for action in actions)

    def any_held(self, *actions: Action) -> bool:
        """Check if any of the given actions are being held."""
        return any(self.is_held(action) for action in actions)

    def enable_text_input(self):
        """Enable text input mode for search/keyboard entry."""
        self.text_input_mode = True
        self.text_input = ""

    def disable_text_input(self):
        """Disable text input mode."""
        self.text_input_mode = False

    def update_text_input(self):
        """Update text input buffer (call in update loop when text input is active)."""
        if not self.text_input_mode:
            return

        # Handle backspace
        if pyxel.btnp(pyxel.KEY_BACKSPACE) and len(self.text_input) > 0:
            self.text_input = self.text_input[:-1]

        # Capture alphanumeric keys
        for key in range(pyxel.KEY_A, pyxel.KEY_Z + 1):
            if pyxel.btnp(key):
                char = chr(ord('a') + (key - pyxel.KEY_A))
                if pyxel.btn(pyxel.KEY_SHIFT):
                    char = char.upper()
                self.text_input += char

        # Numbers
        for key in range(pyxel.KEY_0, pyxel.KEY_9 + 1):
            if pyxel.btnp(key):
                self.text_input += chr(ord('0') + (key - pyxel.KEY_0))

        # Space
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.text_input += ' '

    def get_text_input(self) -> str:
        """Get current text input."""
        return self.text_input

    def clear_text_input(self):
        """Clear text input buffer."""
        self.text_input = ""


# Example usage
if __name__ == "__main__":
    handler = InputHandler()
    print("Input handler initialized")
    print(f"Action mappings: {len(handler.key_map)}")
