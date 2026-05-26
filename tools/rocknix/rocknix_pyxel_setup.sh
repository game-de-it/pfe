#!/bin/sh

# ROCKNIX Pyxel environment setup.
#
# Copy this script to /roms/ports with an optional requirements.txt next to it,
# then run it from EmulationStation's Ports menu or over SSH.
#
# Defaults:
#   - uses /usr/bin/python3
#   - installs into /storage/.local with pip --user
#   - installs pyxel plus modules listed in ./requirements.txt
#   - avoids bytecode compilation because some ROCKNIX Python builds generate
#     legacy .pyc files that break normal pip installs

set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
DEFAULT_USERBASE="/storage/.local"
PYTHON_BIN="${PYXEL_PYTHON:-/usr/bin/python3}"
PYTHONUSERBASE="${PYXEL_PYTHONUSERBASE:-$DEFAULT_USERBASE}"
REQUIREMENTS_FILE="${PYXEL_REQUIREMENTS:-$SCRIPT_DIR/requirements.txt}"
LOG_DIR="${PYXEL_SETUP_LOG_DIR:-/storage/.config/rocknix-pyxel}"
LOG_FILE="$LOG_DIR/install.log"
WHEELHOUSE="${PYXEL_WHEELHOUSE:-$SCRIPT_DIR/wheelhouse}"
CHECK_ONLY=0
INSTALL_BASE=1
OFFLINE=0

usage() {
    cat <<'EOF'
Usage: rocknix_pyxel_setup.sh [options]

Options:
  --requirements FILE  Install additional modules from FILE
  --no-base            Do not install the default pyxel package
  --offline            Install only from ./wheelhouse or $PYXEL_WHEELHOUSE
  --check              Show environment information without installing packages
  -h, --help           Show this help

Environment:
  PYXEL_PYTHON=/path/to/python3
  PYXEL_PYTHONUSERBASE=/storage/.local
  PYXEL_REQUIREMENTS=/path/to/requirements.txt
  PYXEL_WHEELHOUSE=/path/to/wheelhouse
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --requirements)
            shift
            if [ "$#" -eq 0 ]; then
                echo "ERROR: --requirements needs a file path." >&2
                exit 2
            fi
            REQUIREMENTS_FILE="$1"
            ;;
        --no-base)
            INSTALL_BASE=0
            ;;
        --offline)
            OFFLINE=1
            ;;
        --check|--check-only|--dry-run)
            CHECK_ONLY=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

mkdir -p "$LOG_DIR" "$PYTHONUSERBASE"
: > "$LOG_FILE"

log() {
    printf '%s\n' "$*" | tee -a "$LOG_FILE"
}

run_log() {
    tmp="$LOG_DIR/last-command.log"
    log "+ $*"
    if "$@" >"$tmp" 2>&1; then
        cat "$tmp" | tee -a "$LOG_FILE"
        return 0
    fi
    status=$?
    cat "$tmp" | tee -a "$LOG_FILE"
    return "$status"
}

fail() {
    log "ERROR: $*"
    log "Log: $LOG_FILE"
    exit 1
}

export PYTHONUSERBASE
unset PYTHONNOUSERSITE
PATH="$PYTHONUSERBASE/bin:$PATH"
export PATH

if [ ! -x "$PYTHON_BIN" ]; then
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_BIN="$(command -v python3)"
    else
        fail "python3 was not found. Set PYXEL_PYTHON=/path/to/python3."
    fi
fi

log "ROCKNIX Pyxel setup"
log "Script dir: $SCRIPT_DIR"
log "Python: $PYTHON_BIN"
log "Python user base: $PYTHONUSERBASE"
log "Requirements: $REQUIREMENTS_FILE"
log "Log: $LOG_FILE"

USER_SITE="$("$PYTHON_BIN" - <<'PY'
import site
print(site.getusersitepackages())
PY
)"
log "Python user site: $USER_SITE"

"$PYTHON_BIN" - <<'PY' >>"$LOG_FILE" 2>&1 || true
import compileall
import importlib.util
import pathlib
import shutil
import sys
import tempfile

tmp = pathlib.Path(tempfile.mkdtemp(prefix="rocknix_pyxel_compile_check_"))
try:
    source = tmp / "probe.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    ok = compileall.compile_file(str(source), quiet=1, legacy=False)
    expected = pathlib.Path(importlib.util.cache_from_source(str(source)))
    legacy = source.with_suffix(".pyc")
    if ok and legacy.exists() and not expected.exists():
        print("WARNING: Python writes legacy .pyc files; pip will use --no-compile.")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
PY

if ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
    log "pip is not available; bootstrapping pip into the user site."
    run_log "$PYTHON_BIN" - <<'PY' || fail "pip bootstrap failed."
import ensurepip
import runpy
import sys
from pathlib import Path

bundle = Path(ensurepip.__file__).parent / "_bundled"
wheels = sorted(bundle.glob("*.whl"))
if not wheels:
    raise SystemExit("ensurepip bundled wheels were not found")

sys.path = [str(wheel) for wheel in wheels] + sys.path
targets = ["pip"]
if any(wheel.name.startswith("setuptools-") for wheel in wheels):
    targets.insert(0, "setuptools")

sys.argv[1:] = [
    "install",
    "--no-cache-dir",
    "--no-index",
    "--find-links",
    str(bundle),
    "--user",
    "--no-compile",
    "--upgrade",
] + targets
runpy.run_module("pip", run_name="__main__", alter_sys=True)
PY
fi

run_log "$PYTHON_BIN" -m pip --version || fail "pip is still unavailable."

pip_install() {
    if [ "$OFFLINE" -eq 1 ]; then
        [ -d "$WHEELHOUSE" ] || fail "offline wheelhouse not found: $WHEELHOUSE"
        run_log "$PYTHON_BIN" -m pip install \
            --user \
            --disable-pip-version-check \
            --upgrade \
            --no-compile \
            --no-index \
            --find-links "$WHEELHOUSE" \
            "$@"
    else
        run_log "$PYTHON_BIN" -m pip install \
            --user \
            --disable-pip-version-check \
            --upgrade \
            --no-compile \
            "$@"
    fi
}

if [ "$CHECK_ONLY" -eq 1 ]; then
    "$PYTHON_BIN" - <<'PY' | tee -a "$LOG_FILE"
import site
import sys
print("python_version=" + sys.version.split()[0])
print("executable=" + sys.executable)
print("user_base=" + site.getuserbase())
print("user_site=" + site.getusersitepackages())
print("user_site_enabled=" + str(site.ENABLE_USER_SITE))
PY
    log "Check completed."
    exit 0
fi

if [ "$INSTALL_BASE" -eq 1 ]; then
    log "Installing base Pyxel package."
    pip_install "pyxel>=2.9.5" || fail "pyxel install failed."
fi

if [ -f "$REQUIREMENTS_FILE" ]; then
    log "Installing user requirements."
    pip_install -r "$REQUIREMENTS_FILE" || fail "requirements install failed."
else
    log "No requirements.txt found next to the script; skipped user requirements."
fi

ENV_FILE="$LOG_DIR/env.sh"
cat > "$ENV_FILE" <<EOF
export PYTHONUSERBASE="$PYTHONUSERBASE"
export PATH="$PYTHONUSERBASE/bin:\${PATH}"
EOF

run_log "$PYTHON_BIN" - <<'PY' || fail "Pyxel import check failed."
import site
import sys
import pyxel

print("python=" + sys.version.split()[0])
print("pyxel=" + getattr(pyxel, "__version__", "unknown"))
print("user_site=" + site.getusersitepackages())
print("user_site_enabled=" + str(site.ENABLE_USER_SITE))
PY

log "Setup completed."
log "Environment file: $ENV_FILE"
log "For launch scripts, use: . $ENV_FILE"
