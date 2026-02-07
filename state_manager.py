"""
State manager for UI navigation and state transitions.
Implements state machine pattern for screen management.
"""

from enum import Enum
from typing import Dict, Any, Optional, List


class AppState(Enum):
    """Available application states/screens."""
    SPLASH = "splash"
    MAIN_MENU = "main_menu"
    FILE_LIST = "file_list"
    CORE_SELECT = "core_select"
    FAVORITES = "favorites"
    RECENT = "recent"
    SEARCH = "search"
    SETTINGS = "settings"
    WIFI_SETTINGS = "wifi_settings"
    KEY_CONFIG_MENU = "key_config_menu"  # Key Config submenu
    KEY_CONFIG = "key_config"  # Key Mapping screen
    BGM_CONFIG = "bgm_config"  # BGM Config submenu
    DATETIME_SETTINGS = "datetime_settings"  # Date/Time settings
    STATISTICS = "statistics"
    ABOUT = "about"
    QUIT_MENU = "quit_menu"


class StateManager:
    """Manages application state transitions and state data."""

    def __init__(self):
        self.current_state = AppState.SPLASH
        self.previous_state: Optional[AppState] = None
        self.state_history: List[AppState] = []
        self.state_data: Dict[str, Any] = {}

        # Initialize state data containers
        self._init_state_data()

    def _init_state_data(self):
        """Initialize state-specific data containers."""
        self.state_data = {
            'selected_category': None,
            'selected_file': None,
            'selected_file_index': 0,
            'file_list_scroll': 0,
            'category_scroll': 0,
            'selected_core': None,
            'available_cores': [],
            'search_query': '',
            'temp_core_override': None,  # Temporary core selection for current launch
            'category_positions': {},  # Cursor position per category {category_name: {'index': int, 'scroll': int}}
        }

    def change_state(self, new_state: AppState, push_history: bool = True):
        """
        Change to a new state.

        Args:
            new_state: The state to transition to
            push_history: Whether to push current state to history (for back navigation)
        """
        if push_history and self.current_state != new_state:
            self.state_history.append(self.current_state)
            # Limit history size
            if len(self.state_history) > 10:
                self.state_history.pop(0)

        self.previous_state = self.current_state
        self.current_state = new_state

    def go_back(self) -> bool:
        """
        Go back to previous state from history.

        Returns:
            True if successfully went back, False if no history
        """
        if self.state_history:
            previous = self.state_history.pop()
            self.previous_state = self.current_state
            self.current_state = previous
            return True
        return False

    def get_state(self) -> AppState:
        """Get current state."""
        return self.current_state

    def set_data(self, key: str, value: Any):
        """Set state data."""
        self.state_data[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        """Get state data with optional default."""
        return self.state_data.get(key, default)

    def clear_history(self):
        """Clear state history."""
        self.state_history.clear()

    def reset(self):
        """Reset to initial state."""
        self.current_state = AppState.MAIN_MENU
        self.previous_state = None
        self.state_history.clear()
        self._init_state_data()

    # Convenience methods for common state data operations
    def set_selected_category(self, category_name: str):
        """Set the currently selected category."""
        self.state_data['selected_category'] = category_name

    def get_selected_category(self) -> Optional[str]:
        """Get the currently selected category."""
        return self.state_data.get('selected_category')

    def set_selected_file(self, file_path: str, index: int = 0):
        """Set the currently selected file and its index."""
        self.state_data['selected_file'] = file_path
        self.state_data['selected_file_index'] = index

    def get_selected_file(self) -> Optional[str]:
        """Get the currently selected file."""
        return self.state_data.get('selected_file')

    def get_selected_file_index(self) -> int:
        """Get the currently selected file index."""
        return self.state_data.get('selected_file_index', 0)

    def set_file_list_scroll(self, scroll: int):
        """Set the file list scroll position."""
        self.state_data['file_list_scroll'] = scroll

    def get_file_list_scroll(self) -> int:
        """Get the file list scroll position."""
        return self.state_data.get('file_list_scroll', 0)

    def set_available_cores(self, cores: List[str]):
        """Set available cores for current category."""
        self.state_data['available_cores'] = cores

    def get_available_cores(self) -> List[str]:
        """Get available cores."""
        return self.state_data.get('available_cores', [])

    def set_selected_core(self, core: str):
        """Set the selected core."""
        self.state_data['selected_core'] = core

    def get_selected_core(self) -> Optional[str]:
        """Get the selected core."""
        return self.state_data.get('selected_core')

    def set_temp_core_override(self, core: Optional[str]):
        """Set temporary core override for next launch."""
        self.state_data['temp_core_override'] = core

    def get_temp_core_override(self) -> Optional[str]:
        """Get temporary core override."""
        return self.state_data.get('temp_core_override')

    def save_category_position(self, category_name: str, selected_index: int, scroll_offset: int):
        """
        Save cursor position for a category.

        Args:
            category_name: Category name
            selected_index: Index of selected file
            scroll_offset: Scroll offset
        """
        if 'category_positions' not in self.state_data:
            self.state_data['category_positions'] = {}

        self.state_data['category_positions'][category_name] = {
            'index': selected_index,
            'scroll': scroll_offset
        }

    def get_category_position(self, category_name: str) -> dict:
        """
        Get saved cursor position for a category.

        Args:
            category_name: Category name

        Returns:
            {'index': int, 'scroll': int} or {'index': 0, 'scroll': 0}
        """
        positions = self.state_data.get('category_positions', {})
        return positions.get(category_name, {'index': 0, 'scroll': 0})


# Example usage
if __name__ == "__main__":
    manager = StateManager()
    print(f"Initial state: {manager.get_state()}")

    manager.change_state(AppState.FILE_LIST)
    print(f"Changed to: {manager.get_state()}")

    manager.set_selected_category("PS1")
    print(f"Selected category: {manager.get_selected_category()}")

    manager.go_back()
    print(f"Went back to: {manager.get_state()}")
