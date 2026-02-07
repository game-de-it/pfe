"""
ROM file manager for scanning and filtering ROM files.
"""

import os
from typing import List, Optional
from config import Category


class ROMFile:
    """Represents a ROM file or directory."""

    def __init__(self, path: str, name: str, extension: str = "", is_directory: bool = False):
        self.path = path
        self.name = name
        self.extension = extension
        self.is_directory = is_directory
        self.size = 0
        if not is_directory:
            try:
                self.size = os.path.getsize(path)
            except:
                pass

    def __repr__(self):
        if self.is_directory:
            return f"ROMFile(DIR: {self.name})"
        return f"ROMFile({self.name}.{self.extension})"


class ROMManager:
    """Manages ROM file scanning and filtering."""

    def __init__(self):
        self.cache = {}

    def scan_category(self, category: Category, subdirectory: str = "") -> List[ROMFile]:
        """
        Scan a category directory for ROM files and subdirectories.

        Args:
            category: Category configuration to scan
            subdirectory: Optional subdirectory path relative to category directory

        Returns:
            List of ROMFile objects (including directories)
        """
        rom_files = []

        # Build full directory path
        if subdirectory:
            directory = os.path.join(category.directory, subdirectory)
        else:
            directory = category.directory

        extensions = category.extensions

        # Check if directory exists
        if not os.path.exists(directory):
            print(f"Warning: Directory not found: {directory}")
            return rom_files

        if not os.path.isdir(directory):
            print(f"Warning: Not a directory: {directory}")
            return rom_files

        try:
            # Scan directory
            directories = []
            files = []

            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)

                if os.path.isdir(file_path):
                    # Add directory
                    dir_item = ROMFile(file_path, filename, "", is_directory=True)
                    directories.append(dir_item)
                else:
                    # Check extension
                    name, ext = os.path.splitext(filename)
                    ext = ext.lstrip('.').lower()

                    if ext in [e.lower() for e in extensions]:
                        rom_file = ROMFile(file_path, name, ext, is_directory=False)
                        files.append(rom_file)

            # Sort directories and files separately
            directories.sort(key=lambda x: x.name.lower())
            files.sort(key=lambda x: x.name.lower())

            # Directories first, then files
            rom_files = directories + files

        except Exception as e:
            print(f"Error scanning directory {directory}: {e}")

        return rom_files

    def search_roms(self, rom_files: List[ROMFile], query: str) -> List[ROMFile]:
        """
        Filter ROM files by search query.

        Args:
            rom_files: List of ROM files to filter
            query: Search query string

        Returns:
            Filtered list of ROM files
        """
        if not query:
            return rom_files

        query = query.lower()
        filtered = []

        for rom in rom_files:
            if query in rom.name.lower():
                filtered.append(rom)

        return filtered

    def get_rom_display_name(self, rom_file: ROMFile, max_length: int = 40, max_width: int = 222) -> str:
        """
        Get display name for ROM file.

        Args:
            rom_file: ROM file
            max_length: Maximum character length (fallback)
            max_width: Maximum pixel width to avoid scrollbar overlap

        Returns:
            Display name
        """
        name = rom_file.name

        # Try to get actual text width using japanese_text module
        try:
            from japanese_text import get_japanese_text_width
            current_width = get_japanese_text_width(name)

            # If within width, return as-is
            if current_width <= max_width:
                return name

            # Truncate character by character until it fits
            truncated = name
            while len(truncated) > 0:
                truncated = truncated[:-1]
                test_text = truncated + "..."
                if get_japanese_text_width(test_text) <= max_width:
                    return test_text

            return "..."
        except:
            # Fallback to simple character length truncation
            if len(name) > max_length:
                name = name[:max_length - 3] + "..."
            return name

    def format_file_size(self, size_bytes: int) -> str:
        """
        Format file size for display.

        Args:
            size_bytes: File size in bytes

        Returns:
            Formatted size string
        """
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f}KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f}MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"


# Example usage
if __name__ == "__main__":
    manager = ROMManager()
    print("ROM Manager initialized")
