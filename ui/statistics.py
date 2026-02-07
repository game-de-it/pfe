"""
Statistics screen showing play history and usage data.
"""

import os
import pyxel
from ui.base import ScrollableList
from ui.components import StatusBar, HelpText
from ui.window import DQWindow
from japanese_text import draw_japanese_text
from theme_manager import get_theme_manager
from datetime import datetime, timedelta
from collections import defaultdict


class Statistics(ScrollableList):
    """Statistics screen with play history information."""

    def __init__(self, input_handler, state_manager, config, persistence):
        super().__init__(items_per_page=10)
        self.input_handler = input_handler
        self.state_manager = state_manager
        self.config = config
        self.persistence = persistence
        self.status_bar = StatusBar(138, 160)
        self.help_text = HelpText(146, 160)

        self.info_lines = []

    def activate(self):
        """Called when screen becomes active."""
        super().activate()

        # Gather statistics
        self._gather_statistics()

        # Set help text
        self.help_text.set_controls([
            ("Up/Down", "Scroll"),
            ("B", "Back")
        ])

    def deactivate(self):
        """Called when screen becomes inactive."""
        super().deactivate()

    def _gather_statistics(self):
        """Gather statistics."""
        self.info_lines = []

        # Get play history
        history = self.persistence.get_recent_history(limit=1000)

        if not history:
            self.info_lines.append("No play history found")
            self.set_items(self.info_lines)
            return

        # Total play count
        total_plays = sum(entry.get("play_count", 1) for entry in history)
        self.info_lines.append(f"Total Plays: {total_plays}")
        self.info_lines.append("")

        # Top 10 most played games
        self.info_lines.append("Most Played Games:")

        # Sort by play_count
        sorted_history = sorted(history, key=lambda x: x.get("play_count", 1), reverse=True)

        for i, entry in enumerate(sorted_history[:10]):
            rom_path = entry.get("rom_path", "")
            play_count = entry.get("play_count", 1)

            # Extract ROM name
            rom_name = os.path.basename(rom_path)
            if len(rom_name) > 30:
                rom_name = rom_name[:27] + "..."

            self.info_lines.append(f"  {i+1}. {rom_name}")
            self.info_lines.append(f"     Plays: {play_count}")

        self.info_lines.append("")

        # Play count by category
        self.info_lines.append("Plays by Category:")

        category_counts = defaultdict(int)
        for entry in history:
            category = entry.get("category", "Unknown")
            play_count = entry.get("play_count", 1)
            category_counts[category] += play_count

        # Sort by play count (descending)
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)

        for category, count in sorted_categories:
            self.info_lines.append(f"  {category}: {count} plays")

        self.info_lines.append("")

        # Play count for last 7 days
        self.info_lines.append("Last 7 Days:")

        # Aggregate play count by date
        daily_plays = defaultdict(int)
        now = datetime.now()

        for entry in history:
            last_played = entry.get("last_played", "")
            if last_played:
                try:
                    played_date = datetime.fromisoformat(last_played.replace('Z', '+00:00'))
                    # Get date only
                    date_str = played_date.strftime("%Y-%m-%d")

                    # Check if within 7 days
                    days_ago = (now - played_date).days
                    if days_ago < 7:
                        daily_plays[date_str] += 1
                except:
                    pass

        # Generate date list for past 7 days
        for i in range(6, -1, -1):
            date = now - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            count = daily_plays.get(date_str, 0)

            # Display date (month/day)
            display_date = date.strftime("%m/%d")

            # Simple bar graph
            bar_length = min(count, 20)
            bar = "=" * bar_length

            self.info_lines.append(f"  {display_date}: {bar} ({count})")

        self.info_lines.append("")

        # ユニークなゲーム数
        unique_games = len(history)
        self.info_lines.append(f"Unique Games Played: {unique_games}")

        # Recently played games (latest 5)
        self.info_lines.append("")
        self.info_lines.append("Recently Played:")

        for i, entry in enumerate(history[:5]):
            rom_path = entry.get("rom_path", "")
            last_played = entry.get("last_played", "")

            rom_name = os.path.basename(rom_path)
            if len(rom_name) > 30:
                rom_name = rom_name[:27] + "..."

            # Format datetime
            if last_played:
                try:
                    played_date = datetime.fromisoformat(last_played.replace('Z', '+00:00'))
                    time_str = played_date.strftime("%m/%d %H:%M")
                except:
                    time_str = "Unknown"
            else:
                time_str = "Unknown"

            self.info_lines.append(f"  {rom_name}")
            self.info_lines.append(f"    {time_str}")

        # Set items for scrolling
        self.set_items(self.info_lines)

    def update(self):
        """Update statistics screen logic."""
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
        """Draw statistics screen."""
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
        title = "Statistics"
        pyxel.text(2, 2, title, text_selected_color)

        # Border line below counter
        pyxel.line(2, 18, pyxel.width - 3, 18, border_color)

        # Draw information
        start_y = 20
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
            left="Statistics",
            center="",
            right=f"{self.scroll_offset + 1}/{len(self.info_lines)}"
        )
        self.status_bar.draw()

        # Help text
        self.help_text.draw()
