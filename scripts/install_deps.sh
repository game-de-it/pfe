#!/bin/sh

# Install or update PFE Python dependencies using the same runtime as launcher.sh.
# ROCKNIX/plumOS /usr/bin/python3 currently has a compileall/pip mismatch, so
# pip is bootstrapped into the user site and run with --no-compile.

set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
APP_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
CHECK_ONLY=0

case "${1:-}" in
    "")
        ;;
    --check|--check-only|--dry-run)
        CHECK_ONLY=1
        ;;
    *)
        echo "Usage: $0 [--check-only]" >&2
        exit 2
        ;;
esac

select_python() {
    if [ -n "${PFE_PYTHON:-}" ]; then
        printf '%s\n' "$PFE_PYTHON"
    elif [ -x /storage/pyxel_Python/bin/python3 ]; then
        printf '%s\n' /storage/pyxel_Python/bin/python3
    elif [ -x "$APP_DIR/.venv/bin/python3" ]; then
        printf '%s\n' "$APP_DIR/.venv/bin/python3"
    elif command -v python3 >/dev/null 2>&1; then
        command -v python3
    else
        echo "PFE: python3 was not found." >&2
        exit 1
    fi
}

PYTHON_BIN="$(select_python)"

if [ ! -x "$PYTHON_BIN" ]; then
    echo "PFE: selected Python is not executable: $PYTHON_BIN" >&2
    exit 1
fi

echo "PFE: using Python: $PYTHON_BIN"

USER_INSTALL="$("$PYTHON_BIN" - <<'PY'
import os
import site
import sysconfig

override = os.environ.get("PFE_PIP_USER", "").strip().lower()
if override in {"1", "true", "yes", "on"}:
    print("1")
elif override in {"0", "false", "no", "off"}:
    print("0")
else:
    purelib = sysconfig.get_path("purelib")
    if purelib and not os.access(purelib, os.W_OK) and site.ENABLE_USER_SITE:
        print("1")
    else:
        print("0")
PY
)"

"$PYTHON_BIN" - <<'PY'
import compileall
import importlib.util
import pathlib
import shutil
import sys
import tempfile

tmp = pathlib.Path(tempfile.mkdtemp(prefix="pfe_compile_check_"))
try:
    source = tmp / "probe.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    ok = compileall.compile_file(str(source), quiet=1, legacy=False)
    expected = pathlib.Path(importlib.util.cache_from_source(str(source)))
    legacy = source.with_suffix(".pyc")
    if ok and legacy.exists() and not expected.exists():
        print(
            "PFE: warning: this Python writes legacy pyc files; pip will use --no-compile.",
            file=sys.stderr,
        )
finally:
    shutil.rmtree(tmp, ignore_errors=True)
PY

if ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
    echo "PFE: pip is not available; bootstrapping pip into the user site."
    "$PYTHON_BIN" - <<'PY'
import ensurepip
import runpy
import sys
from pathlib import Path

bundle = Path(ensurepip.__file__).parent / "_bundled"
pip_wheel = next(bundle.glob("pip-*.whl"))
setuptools_wheel = next(bundle.glob("setuptools-*.whl"))
sys.path = [str(setuptools_wheel), str(pip_wheel)] + sys.path
sys.argv[1:] = [
    "install",
    "--no-cache-dir",
    "--no-index",
    "--find-links",
    str(bundle),
    "--user",
    "--no-compile",
    "--upgrade",
    "setuptools",
    "pip",
]
runpy.run_module("pip", run_name="__main__", alter_sys=True)
PY
fi

if [ "$CHECK_ONLY" -eq 1 ]; then
    "$PYTHON_BIN" -m pip --version
    if [ "$USER_INSTALL" -eq 1 ]; then
        echo "PFE: dependencies will be installed with --user."
    else
        echo "PFE: dependencies will be installed into the selected Python runtime."
    fi
    echo "PFE: dependency install check completed."
    exit 0
fi

if [ "$USER_INSTALL" -eq 1 ]; then
    "$PYTHON_BIN" -m pip install \
        --user \
        --disable-pip-version-check \
        --upgrade \
        --no-compile \
        -r "$APP_DIR/requirements.txt"
else
    "$PYTHON_BIN" -m pip install \
        --disable-pip-version-check \
        --upgrade \
        --no-compile \
        -r "$APP_DIR/requirements.txt"
fi
