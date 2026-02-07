"""
Debug utility for PFE.
Provides centralized debug logging controlled by pfe.cfg.
Logs are written to both console and data/debug.log file.
"""

import os
from datetime import datetime

# Global debug flag
_debug_enabled = False
_log_file = None
_log_path = "data/debug.log"


def set_debug(enabled: bool):
    """Set debug mode on/off."""
    global _debug_enabled, _log_file
    _debug_enabled = enabled

    if enabled and _log_file is None:
        _init_log_file()
    elif not enabled and _log_file is not None:
        _close_log_file()


def _init_log_file():
    """Initialize log file for writing."""
    global _log_file
    try:
        # Ensure data directory exists
        os.makedirs(os.path.dirname(_log_path), exist_ok=True)

        # Open file in append mode
        _log_file = open(_log_path, 'a', encoding='utf-8')

        # Write session separator
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _log_file.write(f"\n{'='*60}\n")
        _log_file.write(f"=== PFE Debug Session Started: {timestamp} ===\n")
        _log_file.write(f"{'='*60}\n")
        _log_file.flush()
    except Exception as e:
        print(f"[DEBUG] Failed to open log file: {e}")
        _log_file = None


def _close_log_file():
    """Close log file."""
    global _log_file
    if _log_file:
        try:
            _log_file.close()
        except Exception:
            pass
        _log_file = None


def is_debug_enabled() -> bool:
    """Check if debug mode is enabled."""
    return _debug_enabled


def debug_print(*args, **kwargs):
    """Print debug message if debug mode is enabled.

    Writes to both console (stdout) and log file (data/debug.log).
    """
    if _debug_enabled:
        # Console output
        print(*args, **kwargs)

        # File output
        if _log_file:
            try:
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                message = ' '.join(str(arg) for arg in args)
                _log_file.write(f"[{timestamp}] {message}\n")
                _log_file.flush()
            except Exception:
                pass
