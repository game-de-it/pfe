"""
Persistence management - saving and restoring state.
"""

import json
import os
from typing import Optional, Dict, Any
from datetime import datetime


class PersistenceManager:
    """Persistence management for application state."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.session_file = os.path.join(data_dir, "session.json")
        self.history_file = os.path.join(data_dir, "history.json")
        self.favorites_file = os.path.join(data_dir, "favorites.json")
        self.core_history_file = os.path.join(data_dir, "core_history.json")
        self.settings_file = os.path.join(data_dir, "settings.json")

        # Favorites cache (for reducing CPU load)
        self._favorites_cache = None  # set of rom_paths
        self._favorites_cache_valid = False

        # Create directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)

    def save_session_state(self, state_data: Dict[str, Any]):
        """
        Save session state.

        Args:
            state_data: State data to save
        """
        try:
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)
            print(f"Session saved to {self.session_file}")
        except Exception as e:
            print(f"Error saving session: {e}")

    def load_session_state(self) -> Optional[Dict[str, Any]]:
        """
        Load session state.

        Returns:
            Saved state data, or None
        """
        if not os.path.exists(self.session_file):
            return None

        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            print(f"Session loaded from {self.session_file}")
            return state_data
        except Exception as e:
            print(f"Error loading session: {e}")
            return None

    def clear_session_state(self):
        """Clear session state."""
        if os.path.exists(self.session_file):
            try:
                os.remove(self.session_file)
                print("Session cleared")
            except Exception as e:
                print(f"Error clearing session: {e}")

    def add_to_history(self, rom_path: str, category: str, core_used: str):
        """
        Add to play history.

        Args:
            rom_path: ROM file path
            category: Category name
            core_used: Core that was used
        """
        try:
            # Load existing history
            history = self._load_json(self.history_file, {
                "version": "1.0",
                "max_entries": 50,
                "entries": []
            })

            # Search for existing entry
            existing_entry = None
            for entry in history["entries"]:
                if entry["rom_path"] == rom_path:
                    existing_entry = entry
                    break

            if existing_entry:
                # Update existing entry
                existing_entry["play_count"] = existing_entry.get("play_count", 0) + 1
                existing_entry["last_played"] = datetime.now().isoformat()
                existing_entry["core_used"] = core_used
            else:
                # Add new entry
                new_entry = {
                    "rom_path": rom_path,
                    "category": category,
                    "core_used": core_used,
                    "play_count": 1,
                    "last_played": datetime.now().isoformat()
                }
                history["entries"].insert(0, new_entry)

            # Delete if exceeding maximum entries
            max_entries = history.get("max_entries", 50)
            if len(history["entries"]) > max_entries:
                history["entries"] = history["entries"][:max_entries]

            # Save
            self._save_json(self.history_file, history)
            print(f"Added to history: {rom_path}")

        except Exception as e:
            print(f"Error adding to history: {e}")

    def _load_json(self, file_path: str, default: Any) -> Any:
        """Load JSON file."""
        if not os.path.exists(file_path):
            return default

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return default

    def _save_json(self, file_path: str, data: Any):
        """Save to JSON file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving {file_path}: {e}")

    def save_core_choice(self, rom_path: str, core: str):
        """
        Save last used core per ROM.

        Args:
            rom_path: ROM file path
            core: Core name that was used
        """
        try:
            core_history = self._load_json(self.core_history_file, {
                "version": "1.0",
                "core_overrides": {}
            })

            core_history["core_overrides"][rom_path] = core
            self._save_json(self.core_history_file, core_history)

        except Exception as e:
            print(f"Error saving core choice: {e}")

    def get_last_core(self, rom_path: str) -> Optional[str]:
        """
        Get last used core per ROM.

        Args:
            rom_path: ROM file path

        Returns:
            Last used core name, or None
        """
        try:
            core_history = self._load_json(self.core_history_file, {
                "version": "1.0",
                "core_overrides": {}
            })

            return core_history["core_overrides"].get(rom_path)

        except Exception as e:
            print(f"Error loading core choice: {e}")
            return None

    def add_to_favorites(self, rom_path: str, category: str):
        """
        Add to favorites.

        Args:
            rom_path: ROM file path
            category: Category name
        """
        try:
            favorites = self._load_json(self.favorites_file, {
                "version": "1.0",
                "favorites": []
            })

            # Check for duplicates
            for fav in favorites["favorites"]:
                if fav["rom_path"] == rom_path:
                    print(f"Already in favorites: {rom_path}")
                    return

            # Add
            new_fav = {
                "rom_path": rom_path,
                "category": category,
                "added_timestamp": datetime.now().isoformat()
            }
            favorites["favorites"].append(new_fav)

            self._save_json(self.favorites_file, favorites)
            self._invalidate_favorites_cache()
            print(f"Added to favorites: {rom_path}")

        except Exception as e:
            print(f"Error adding to favorites: {e}")

    def remove_from_favorites(self, rom_path: str):
        """
        Remove from favorites.

        Args:
            rom_path: ROM file path
        """
        try:
            favorites = self._load_json(self.favorites_file, {
                "version": "1.0",
                "favorites": []
            })

            # Delete
            favorites["favorites"] = [
                fav for fav in favorites["favorites"]
                if fav["rom_path"] != rom_path
            ]

            self._save_json(self.favorites_file, favorites)
            self._invalidate_favorites_cache()
            print(f"Removed from favorites: {rom_path}")

        except Exception as e:
            print(f"Error removing from favorites: {e}")

    def _load_favorites_cache(self):
        """Load favorites cache (internal use)."""
        if self._favorites_cache_valid and self._favorites_cache is not None:
            return

        try:
            favorites = self._load_json(self.favorites_file, {
                "version": "1.0",
                "favorites": []
            })
            # Create set of rom_paths (for fast lookup)
            self._favorites_cache = set(fav["rom_path"] for fav in favorites["favorites"])
            self._favorites_cache_valid = True
        except Exception as e:
            print(f"Error loading favorites cache: {e}")
            self._favorites_cache = set()
            self._favorites_cache_valid = True

    def _invalidate_favorites_cache(self):
        """Invalidate favorites cache (called after changes)."""
        self._favorites_cache_valid = False
        self._favorites_cache = None

    def is_favorite(self, rom_path: str) -> bool:
        """
        Check if item is a favorite (fast with cache).

        Args:
            rom_path: ROM file path

        Returns:
            True if favorite
        """
        self._load_favorites_cache()
        return rom_path in self._favorites_cache

    def get_favorites(self) -> list:
        """
        Get favorites list.

        Returns:
            List of favorites
        """
        try:
            favorites = self._load_json(self.favorites_file, {
                "version": "1.0",
                "favorites": []
            })

            return favorites["favorites"]

        except Exception as e:
            print(f"Error loading favorites: {e}")
            return []

    def get_recent_history(self, limit: int = 50) -> list:
        """
        Get play history.

        Args:
            limit: Maximum number of entries to retrieve

        Returns:
            List of history (newest first)
        """
        try:
            history = self._load_json(self.history_file, {
                "version": "1.0",
                "max_entries": 50,
                "entries": []
            })

            entries = history["entries"][:limit]
            # Sort by last play time (newest first)
            entries.sort(key=lambda x: x.get("last_played", ""), reverse=True)

            return entries

        except Exception as e:
            print(f"Error loading history: {e}")
            return []

    def save_settings(self, settings: Dict[str, Any]):
        """
        Save settings.

        Args:
            settings: Settings data
        """
        try:
            settings_data = {
                "version": "1.0",
                "settings": settings
            }
            self._save_json(self.settings_file, settings_data)
            print(f"Settings saved to {self.settings_file}")

        except Exception as e:
            print(f"Error saving settings: {e}")

    def load_settings(self) -> Dict[str, Any]:
        """
        Load settings.

        Returns:
            Settings data
        """
        try:
            settings_data = self._load_json(self.settings_file, {
                "version": "1.0",
                "settings": {
                    "show_screenshots": "On",
                    "sort_mode": "Name",
                    "button_layout": "Nintendo",
                    "auto_launch": "Off",
                    "wifi_enabled": False,
                    "wifi_ssid": "",
                    "wifi_password": "",
                    "view_mode": "list",
                    "resolution": "1:1"
                }
            })

            return settings_data.get("settings", {})

        except Exception as e:
            print(f"Error loading settings: {e}")
            return {}


# Example usage
if __name__ == "__main__":
    manager = PersistenceManager()
    print("Persistence manager initialized")
