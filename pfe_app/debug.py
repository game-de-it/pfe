"""
Debug utility for PFE.
Provides centralized debug logging controlled by pfe.cfg.
Logs are written to both console and data/debug.log file.
"""

import os
import sys
import time
import traceback
from contextlib import contextmanager
from datetime import datetime

# Global debug flag
_debug_enabled = False
_log_file = None
_log_path = "data/debug.log"
_console_enabled = True
_level_name = "DEBUG"
_level_value = 10

_LEVELS = {
    "TRACE": 5,
    "DEBUG": 10,
    "INFO": 20,
    "WARN": 30,
    "WARNING": 30,
    "ERROR": 40,
}


def configure(enabled: bool, log_path: str = "data/debug.log",
              level: str = "DEBUG", console: bool = True):
    """Configure debug logging."""
    global _debug_enabled, _log_path, _console_enabled, _level_name, _level_value
    _debug_enabled = bool(enabled)
    _log_path = log_path or "data/debug.log"
    _console_enabled = bool(console)
    _level_name = (level or "DEBUG").upper()
    _level_value = _LEVELS.get(_level_name, 10)

    if _debug_enabled:
        _init_log_file()
    else:
        _close_log_file()


def set_debug(enabled: bool):
    """Set debug mode on/off."""
    configure(enabled=enabled, log_path=_log_path, level=_level_name,
              console=_console_enabled)


def _init_log_file():
    """Initialize log file for writing."""
    global _log_file
    if _log_file is not None:
        return
    try:
        # Ensure data directory exists
        os.makedirs(os.path.dirname(_log_path), exist_ok=True)

        # Open file in append mode
        _log_file = open(_log_path, 'a', encoding='utf-8')

        # Write session separator
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _log_file.write(f"\n{'='*60}\n")
        _log_file.write(f"=== PFE Debug Session Started: {timestamp} ===\n")
        _log_file.write(f"=== level={_level_name} console={_console_enabled} ===\n")
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


def _should_log(level: str) -> bool:
    if not _debug_enabled:
        return False
    return _LEVELS.get((level or "DEBUG").upper(), 10) >= _level_value


def _format_message(level: str, message: str) -> str:
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    return f"[{timestamp}] [{level.upper()}] {message}"


def log(level: str, *args, **kwargs):
    """Write a structured debug log line if enabled."""
    if not _should_log(level):
        return

    sep = kwargs.pop("sep", " ")
    end = kwargs.pop("end", "\n")
    flush = kwargs.pop("flush", False)
    message = sep.join(str(arg) for arg in args)
    line = _format_message(level, message)

    if _console_enabled:
        print(line, end=end, flush=flush, **kwargs)

    if _log_file:
        try:
            _log_file.write(line + "\n")
            _log_file.flush()
        except Exception:
            pass


def debug_print(*args, **kwargs):
    """Backward-compatible DEBUG logger."""
    log("DEBUG", *args, **kwargs)


def trace(*args, **kwargs):
    log("TRACE", *args, **kwargs)


def info(*args, **kwargs):
    log("INFO", *args, **kwargs)


def warning(*args, **kwargs):
    log("WARN", *args, **kwargs)


def error(*args, **kwargs):
    log("ERROR", *args, **kwargs)


def exception(message: str = "Exception"):
    """Log the current exception traceback."""
    if not _should_log("ERROR"):
        return
    error(message)
    tb = traceback.format_exc()
    for line in tb.rstrip().splitlines():
        log("ERROR", line)


@contextmanager
def timed(label: str, level: str = "DEBUG", slow_ms: float | None = None):
    """Context manager that logs elapsed time for a block."""
    start = time.perf_counter()
    try:
        yield
    except Exception:
        exception(f"{label} failed")
        raise
    finally:
        elapsed = (time.perf_counter() - start) * 1000.0
        if slow_ms is None or elapsed >= slow_ms:
            log(level, f"{label}: {elapsed:.1f}ms")


def environment_snapshot():
    """Log a small runtime environment snapshot."""
    if not _should_log("INFO"):
        return
    info(f"python={sys.version.split()[0]}")
    info(f"cwd={os.getcwd()}")
    try:
        import pyxel
        info(f"pyxel={getattr(pyxel, '__version__', 'unknown')}")
    except Exception:
        pass
