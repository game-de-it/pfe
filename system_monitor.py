"""
System monitor for battery, network, and time display.
Uses external scripts for cross-platform compatibility.
"""

import os
import subprocess
from datetime import datetime
from typing import Optional
from debug import debug_print


class SystemMonitor:
    """Monitors system status (battery, network, time)."""

    def __init__(self, config):
        """
        Initialize system monitor.

        Args:
            config: Config object with global_vars
        """
        self.config = config

        # Script paths from pfe.cfg
        self.scripts_dir = "scripts"
        self.battery_script = config.global_vars.get(
            'BATTERY_SCRIPT',
            os.path.join(self.scripts_dir, "get_battery.sh")
        )
        self.network_script = config.global_vars.get(
            'NETWORK_SCRIPT',
            os.path.join(self.scripts_dir, "get_network.sh")
        )
        self.cpu_governor_get_script = config.global_vars.get(
            'CPU_GOVERNOR_GET_SCRIPT',
            os.path.join(self.scripts_dir, "get_cpu_governor.sh")
        )
        self.cpu_governor_set_script = config.global_vars.get(
            'CPU_GOVERNOR_SET_SCRIPT',
            os.path.join(self.scripts_dir, "set_cpu_governor.sh")
        )
        self.datetime_set_script = config.global_vars.get(
            'DATETIME_SET_SCRIPT',
            os.path.join(self.scripts_dir, "set_datetime.sh")
        )

        # WiFi interface
        self.wifi_interface = config.global_vars.get('WIFI_INTERFACE', 'wlan0')

        # Feature flags
        self.show_battery = config.global_vars.get('SHOW_BATTERY', '1') == '1'
        self.show_network = config.global_vars.get('SHOW_NETWORK', '1') == '1'
        self.show_clock = config.global_vars.get('SHOW_CLOCK', '1') == '1'

        # Cache for network status (to avoid frequent script calls)
        self._network_status = None
        self._network_check_counter = 0
        self._network_check_interval = 30  # Check every 30 frames (1 second at 30fps)

        # Available governors
        self.available_governors = ['ondemand', 'performance']

        # Cache for battery status (to reduce CPU load)
        self._battery_level_cache = None
        self._battery_status_cache = None
        self._battery_check_counter = 0
        self._battery_check_interval = 60  # Check every 60 frames (approximately 2 seconds)

        # Cache for time (to reduce CPU load)
        self._time_cache = ""
        self._time_check_counter = 0
        self._time_check_interval = 30  # Update every 30 frames (approximately 1 second)

        # Check script availability
        self._check_scripts()

    def _check_scripts(self):
        """Check if required scripts are available."""
        if not os.path.exists(self.battery_script):
            debug_print(f"[SystemMonitor] Battery script not found: {self.battery_script}")
        if not os.path.exists(self.network_script):
            debug_print(f"[SystemMonitor] Network script not found: {self.network_script}")
        if not os.path.exists(self.cpu_governor_get_script):
            debug_print(f"[SystemMonitor] CPU governor get script not found: {self.cpu_governor_get_script}")
        if not os.path.exists(self.cpu_governor_set_script):
            debug_print(f"[SystemMonitor] CPU governor set script not found: {self.cpu_governor_set_script}")

    def _run_script(self, script_path: str, args: list = None, timeout: int = 5) -> Optional[str]:
        """
        Run an external script and return its output.

        Args:
            script_path: Path to the script
            args: Optional list of arguments
            timeout: Timeout in seconds

        Returns:
            Script output (stdout), or None on error
        """
        if not os.path.exists(script_path):
            return None

        try:
            cmd = ["sh", script_path]
            if args:
                cmd.extend(args)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                debug_print(f"[SystemMonitor] Script failed: {script_path}, stderr: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            debug_print(f"[SystemMonitor] Script timeout: {script_path}")
            return None
        except Exception as e:
            debug_print(f"[SystemMonitor] Script error: {script_path}, {e}")
            return None

    def _update_battery_cache(self):
        """Update battery cache from script."""
        output = self._run_script(self.battery_script)
        if output:
            parts = output.split(None, 1)
            if len(parts) >= 1:
                try:
                    self._battery_level_cache = int(parts[0])
                    self._battery_status_cache = parts[1] if len(parts) > 1 else None
                    return
                except ValueError:
                    pass

        self._battery_level_cache = None
        self._battery_status_cache = None

    def get_battery_level(self) -> Optional[int]:
        """
        Get battery level (0-100%) with caching.

        Returns:
            Battery level percentage, or None if unavailable
        """
        if not self.show_battery:
            return None

        # Use cache (avoid script calls every frame)
        self._battery_check_counter += 1
        if self._battery_level_cache is not None and self._battery_check_counter < self._battery_check_interval:
            return self._battery_level_cache

        self._battery_check_counter = 0
        self._update_battery_cache()
        return self._battery_level_cache

    def get_battery_status(self) -> Optional[str]:
        """
        Get battery charging status with caching.

        Returns:
            'Charging', 'Discharging', 'Full', or None
        """
        if not self.show_battery:
            return None

        # Use cache (updated at the same time as battery_level)
        if self._battery_status_cache is not None and self._battery_check_counter > 0:
            return self._battery_status_cache

        # Force update if no cache
        self._update_battery_cache()
        return self._battery_status_cache

    def check_network(self) -> bool:
        """
        Check network connectivity using external script.

        Returns:
            True if network is connected, False otherwise
        """
        if not self.show_network:
            return False

        # Check periodically (not every frame)
        self._network_check_counter += 1
        if self._network_status is not None and self._network_check_counter < self._network_check_interval:
            return self._network_status

        self._network_check_counter = 0

        output = self._run_script(self.network_script, timeout=3)
        self._network_status = (output == "connected")
        return self._network_status

    def get_wifi_status(self) -> bool:
        """
        Check if WiFi interface is up.

        Returns:
            True if WiFi is connected, False otherwise
        """
        if not self.show_network:
            return False

        # Use network script result as proxy for WiFi status
        # Or check interface operstate as fallback
        operstate_path = f'/sys/class/net/{self.wifi_interface}/operstate'

        try:
            if os.path.exists(operstate_path):
                with open(operstate_path, 'r') as f:
                    state = f.read().strip()
                    return state == 'up'
        except IOError:
            pass

        return False

    def get_current_time(self) -> str:
        """
        Get current time in 24-hour format with caching.

        Returns:
            Time string (HH:MM)
        """
        if not self.show_clock:
            return ""

        # Use cache (avoid strftime calls every frame)
        self._time_check_counter += 1
        if self._time_cache and self._time_check_counter < self._time_check_interval:
            return self._time_cache

        self._time_check_counter = 0
        self._time_cache = datetime.now().strftime("%H:%M")
        return self._time_cache

    def get_status_text(self) -> str:
        """
        Get combined status text for display.

        Returns:
            Status text string (e.g., "12:34 100% NET")
        """
        parts = []

        # Time
        if self.show_clock:
            parts.append(self.get_current_time())

        # Battery
        if self.show_battery:
            battery_level = self.get_battery_level()
            if battery_level is not None:
                battery_status = self.get_battery_status()
                if battery_status == 'Charging':
                    parts.append(f"{battery_level}%+")
                else:
                    parts.append(f"{battery_level}%")

        # Network
        if self.show_network:
            if self.check_network():
                parts.append("NET")
            # Don't show anything if not connected

        return " ".join(parts)

    def get_cpu_governor(self) -> Optional[str]:
        """
        Get current CPU governor using external script.

        Returns:
            Governor name (e.g., 'ondemand', 'performance'), or None if unavailable
        """
        output = self._run_script(self.cpu_governor_get_script)
        if output:
            return output.strip()
        return None

    def set_cpu_governor(self, governor: str) -> bool:
        """
        Set CPU governor using external script.

        Args:
            governor: Governor name ('ondemand' or 'performance')

        Returns:
            True if successful, False otherwise
        """
        if governor not in self.available_governors:
            return False

        if not os.path.exists(self.cpu_governor_set_script):
            debug_print(f"[SystemMonitor] CPU governor set script not found: {self.cpu_governor_set_script}")
            return False

        try:
            result = subprocess.run(
                ["sh", self.cpu_governor_set_script, governor],
                capture_output=True,
                text=True,
                timeout=5
            )

            success = (result.returncode == 0)
            if success:
                debug_print(f"[SystemMonitor] CPU governor set to: {governor}")
            else:
                debug_print(f"[SystemMonitor] Failed to set CPU governor: {result.stderr}")
            return success

        except subprocess.TimeoutExpired:
            debug_print("[SystemMonitor] CPU governor set timeout")
            return False
        except Exception as e:
            debug_print(f"[SystemMonitor] CPU governor set error: {e}")
            return False

    def get_available_governors(self) -> list:
        """
        Get list of available governors.

        Returns:
            List of governor names
        """
        return self.available_governors.copy()

    def set_datetime(self, year: int, month: int, day: int, hour: int, minute: int) -> bool:
        """
        Set system date and time using external script.

        Args:
            year: Year (e.g., 2024)
            month: Month (1-12)
            day: Day (1-31)
            hour: Hour (0-23)
            minute: Minute (0-59)

        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(self.datetime_set_script):
            debug_print(f"[SystemMonitor] DateTime set script not found: {self.datetime_set_script}")
            return False

        try:
            # Format arguments with leading zeros
            args = [
                str(year),
                f"{month:02d}",
                f"{day:02d}",
                f"{hour:02d}",
                f"{minute:02d}"
            ]

            result = subprocess.run(
                ["sh", self.datetime_set_script] + args,
                capture_output=True,
                text=True,
                timeout=10
            )

            success = (result.returncode == 0)
            if success:
                debug_print(f"[SystemMonitor] DateTime set to: {year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}")
            else:
                debug_print(f"[SystemMonitor] Failed to set datetime: {result.stderr}")
            return success

        except subprocess.TimeoutExpired:
            debug_print("[SystemMonitor] DateTime set timeout")
            return False
        except Exception as e:
            debug_print(f"[SystemMonitor] DateTime set error: {e}")
            return False

    def get_current_datetime(self) -> tuple:
        """
        Get current date and time.

        Returns:
            Tuple of (year, month, day, hour, minute)
        """
        now = datetime.now()
        return (now.year, now.month, now.day, now.hour, now.minute)


# Global system monitor instance
_system_monitor = None


def get_system_monitor(config=None):
    """Get or create the global system monitor instance."""
    global _system_monitor
    if _system_monitor is None and config is not None:
        _system_monitor = SystemMonitor(config)
    return _system_monitor


def init_system_monitor(config):
    """Initialize the system monitor."""
    global _system_monitor
    _system_monitor = SystemMonitor(config)
    return _system_monitor
