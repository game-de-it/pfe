"""
Centralized shell-script execution for handheld Linux integrations.

PFE keeps OS/device-specific behavior in scripts so dArkOS, ROCKNIX, and other
handheld Linux variants can override small pieces without forking the UI. This
runner makes those calls observable and consistent.
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from typing import Iterable

from pfe_app.debug import debug_print, trace, warning


@dataclass
class ScriptResult:
    script: str
    args: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_ms: float

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class ScriptRunner:
    """Run shell scripts with consistent timeout handling and debug logs."""

    def __init__(self, base_dir: str = "."):
        self.base_dir = os.path.abspath(base_dir)
        self._last_log_at: dict[str, float] = {}

    def _should_log(self, log_key: str | None, interval_seconds: float | None) -> bool:
        if interval_seconds is None:
            return True

        key = log_key or "__default__"
        now = time.monotonic()
        last = self._last_log_at.get(key)
        if last is not None and now - last < interval_seconds:
            return False

        self._last_log_at[key] = now
        return True

    def resolve(self, script_path: str) -> str | None:
        if not script_path:
            return None
        path = script_path if os.path.isabs(script_path) else os.path.join(self.base_dir, script_path)
        path = os.path.abspath(path)
        return path if os.path.exists(path) else None

    def run(
        self,
        script_path: str,
        args: Iterable[str] | None = None,
        timeout: int = 5,
        log_interval_seconds: float | None = None,
        log_key: str | None = None,
    ) -> ScriptResult | None:
        log_this_call = self._should_log(log_key or script_path, log_interval_seconds)
        resolved = self.resolve(script_path)
        if not resolved:
            if log_this_call:
                trace(f"[ScriptRunner] missing: {script_path}")
            return None

        safe_args = [str(arg) for arg in (args or [])]
        cmd = ["sh", resolved] + safe_args
        if log_this_call and log_interval_seconds is None:
            debug_print(f"[ScriptRunner] start: {resolved} args={safe_args} timeout={timeout}s")
        started = time.perf_counter()

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            elapsed = (time.perf_counter() - started) * 1000.0
            if log_this_call:
                warning(f"[ScriptRunner] timeout: {resolved} {elapsed:.1f}ms")
            return None
        except Exception as e:
            elapsed = (time.perf_counter() - started) * 1000.0
            if log_this_call:
                warning(f"[ScriptRunner] error: {resolved} {elapsed:.1f}ms {e}")
            return None

        elapsed = (time.perf_counter() - started) * 1000.0
        result = ScriptResult(
            script=resolved,
            args=safe_args,
            returncode=proc.returncode,
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
            duration_ms=elapsed,
        )

        if result.ok:
            if log_this_call:
                if log_interval_seconds is None:
                    trace(f"[ScriptRunner] ok: {resolved} {elapsed:.1f}ms stdout={result.stdout!r}")
                else:
                    debug_print(
                        f"[ScriptRunner] ok: {resolved} args={safe_args} "
                        f"{elapsed:.1f}ms stdout={result.stdout!r}"
                    )
        else:
            if log_this_call:
                warning(
                    f"[ScriptRunner] failed: {resolved} rc={result.returncode} "
                    f"{elapsed:.1f}ms stderr={result.stderr!r}"
                )
        return result

    def run_text(
        self,
        script_path: str,
        args: Iterable[str] | None = None,
        timeout: int = 5,
        log_interval_seconds: float | None = None,
        log_key: str | None = None,
    ) -> str | None:
        result = self.run(
            script_path,
            args=args,
            timeout=timeout,
            log_interval_seconds=log_interval_seconds,
            log_key=log_key,
        )
        if result and result.ok:
            return result.stdout
        return None
