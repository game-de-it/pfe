#!/bin/sh

# Install Pyxel runtime and register the Pyxel system in ROCKNIX EmulationStation.
#
# This is the user-facing one-shot installer intended to be placed in
# /roms/ports and launched from EmulationStation.

set -eu

maybe_reexec_in_terminal() {
    title="$1"
    shift

    case "${PFE_PORT_TERMINAL:-auto}" in
        0|false|FALSE|no|NO|off|OFF)
            return 0
            ;;
    esac

    [ "${PFE_PORT_TERMINAL_ACTIVE:-0}" = "1" ] && return 0
    [ -n "${SSH_CONNECTION:-}" ] && return 0
    [ -n "${WAYLAND_DISPLAY:-}" ] || return 0
    command -v foot >/dev/null 2>&1 || return 0
    font_size="${PFE_PORT_TERMINAL_FONT_SIZE:-18}"

    script_path="$0"
    case "$script_path" in
        /*) ;;
        *) script_path="$(pwd)/$script_path" ;;
    esac

    exec foot -F -f "monospace:size=$font_size" -T "$title" sh -c '
        script="$1"
        shift
        PFE_PORT_TERMINAL_ACTIVE=1 "$script" "$@"
        status=$?
        printf "\n------------------------------------------------------------\n"
        if [ "$status" -eq 0 ]; then
            printf "Completed successfully. This window will close in 10 seconds.\n"
            sleep 10
        else
            printf "Failed with exit code %s. This window will close in 60 seconds.\n" "$status"
            sleep 60
        fi
        exit "$status"
    ' sh "$script_path" "$@"
}

maybe_reexec_in_terminal "Install Pyxel for ROCKNIX" "$@"

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
DEFAULT_USERBASE="/storage/.local"
PYTHON_BIN="${PYXEL_PYTHON:-/usr/bin/python3}"
PYTHONUSERBASE="${PYXEL_PYTHONUSERBASE:-$DEFAULT_USERBASE}"
REQUIREMENTS_FILE="${PYXEL_REQUIREMENTS:-$SCRIPT_DIR/requirements.txt}"
LOG_DIR="${PYXEL_SETUP_LOG_DIR:-/storage/.config/rocknix-pyxel}"
LOG_FILE="$LOG_DIR/install.log"
WHEELHOUSE="${PYXEL_WHEELHOUSE:-$SCRIPT_DIR/wheelhouse}"
ES_SYSTEMS_CFG="${ES_SYSTEMS_CFG:-/storage/.config/emulationstation/es_systems.cfg}"
PYXEL_ROM_DIR="${PYXEL_ROM_DIR:-/storage/roms/pyxel}"
PYXEL_RUNNER="${PYXEL_RUNNER:-/storage/.config/rocknix-pyxel/rocknix_pyxel_run.sh}"
CHECK_ONLY=0
INSTALL_BASE=1
INSTALL_ES=1
OFFLINE=0

usage() {
    cat <<'EOF'
Usage: 01_install_pyxel.sh [options]

Options:
  --requirements FILE  Install additional modules from FILE
  --no-base            Do not install the default pyxel package
  --offline            Install only from ./wheelhouse or $PYXEL_WHEELHOUSE
  --no-es              Install Pyxel only; do not update EmulationStation
  --runner FILE        Pyxel runner path written to es_systems.cfg
  --check              Show environment information without installing packages
  -h, --help           Show this help

Environment:
  PYXEL_PYTHON=/path/to/python3
  PYXEL_PYTHONUSERBASE=/storage/.local
  PYXEL_REQUIREMENTS=/path/to/requirements.txt
  PYXEL_WHEELHOUSE=/path/to/wheelhouse
  PYXEL_ROM_DIR=/storage/roms/pyxel
  PYXEL_RUNNER=/storage/.config/rocknix-pyxel/rocknix_pyxel_run.sh
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --requirements)
            shift
            [ "$#" -gt 0 ] || { echo "ERROR: --requirements needs a file path." >&2; exit 2; }
            REQUIREMENTS_FILE="$1"
            ;;
        --no-base)
            INSTALL_BASE=0
            ;;
        --offline)
            OFFLINE=1
            ;;
        --no-es)
            INSTALL_ES=0
            ;;
        --runner)
            shift
            [ "$#" -gt 0 ] || { echo "ERROR: --runner needs a file path." >&2; exit 2; }
            PYXEL_RUNNER="$1"
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

log "ROCKNIX Pyxel install"
log "Script dir: $SCRIPT_DIR"
log "Python: $PYTHON_BIN"
log "Python user base: $PYTHONUSERBASE"
log "Requirements: $REQUIREMENTS_FILE"
log "ES systems cfg: $ES_SYSTEMS_CFG"
log "Pyxel ROM dir: $PYXEL_ROM_DIR"
log "Pyxel runner: $PYXEL_RUNNER"
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

install_runner() {
    runner_dir="$(dirname "$PYXEL_RUNNER")"
    mkdir -p "$runner_dir"
    cat > "$PYXEL_RUNNER" <<'EOF'
#!/bin/sh

# Run Pyxel apps on ROCKNIX.

set -eu

APP_PATH="${1:-}"
PYTHON_BIN="${PYXEL_PYTHON:-/usr/bin/python3}"
ENV_FILE="${PYXEL_ENV_FILE:-/storage/.config/rocknix-pyxel/env.sh}"
LOG_DIR="${PYXEL_RUN_LOG_DIR:-/storage/.config/rocknix-pyxel}"
LOG_FILE="$LOG_DIR/run.log"

mkdir -p "$LOG_DIR"

log() {
    printf '%s\n' "$*" | tee -a "$LOG_FILE"
}

fail() {
    log "ERROR: $*"
    exit 1
}

[ -n "$APP_PATH" ] || fail "No ROM/app path was provided."
[ -e "$APP_PATH" ] || fail "App not found: $APP_PATH"

if [ -f "$ENV_FILE" ]; then
    . "$ENV_FILE"
fi

if [ ! -x "$PYTHON_BIN" ]; then
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_BIN="$(command -v python3)"
    else
        fail "python3 was not found. Run 01_install_pyxel.sh first."
    fi
fi

export SDL_AUDIODRIVER="${SDL_AUDIODRIVER:-alsa}"
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"

APP_DIR="$(CDPATH= cd -- "$(dirname -- "$APP_PATH")" && pwd)"
APP_NAME="$(basename -- "$APP_PATH")"
APP_EXT="$(printf '%s' "$APP_NAME" | sed 's/^.*\.//' | tr '[:upper:]' '[:lower:]')"

log "ROCKNIX Pyxel run"
log "App: $APP_PATH"
log "Python: $PYTHON_BIN"
log "Extension: .$APP_EXT"

cd "$APP_DIR"

case "$APP_EXT" in
    py)
        exec "$PYTHON_BIN" -m pyxel run "$APP_PATH"
        ;;
    pyxapp)
        exec "$PYTHON_BIN" -m pyxel play "$APP_PATH"
        ;;
    edit)
        TARGET="$(sed -n '1p' "$APP_PATH" 2>/dev/null | tr -d '\r')"
        if [ -n "$TARGET" ]; then
            case "$TARGET" in
                /*) ;;
                *) TARGET="$APP_DIR/$TARGET" ;;
            esac
            exec "$PYTHON_BIN" -m pyxel edit "$TARGET"
        fi
        exec "$PYTHON_BIN" -m pyxel edit
        ;;
    *)
        fail "Unsupported Pyxel app extension: .$APP_EXT"
        ;;
esac
EOF
    chmod +x "$PYXEL_RUNNER"
    log "Installed Pyxel runner: $PYXEL_RUNNER"
}

install_es_system() {
    [ "$INSTALL_ES" -eq 1 ] || return 0

    if [ ! -f "$ES_SYSTEMS_CFG" ]; then
        fail "es_systems.cfg not found: $ES_SYSTEMS_CFG"
    fi

    mkdir -p "$PYXEL_ROM_DIR"

    BACKUP="${ES_SYSTEMS_CFG}.bak.$(date +%Y%m%d-%H%M%S)"
    cp "$ES_SYSTEMS_CFG" "$BACKUP"

    if [ -L "$ES_SYSTEMS_CFG" ]; then
        LINK_TARGET="$(readlink "$ES_SYSTEMS_CFG")"
        echo "$LINK_TARGET" > "${BACKUP}.symlink"
        ES_SYSTEMS_CFG="$ES_SYSTEMS_CFG" BACKUP="$BACKUP" "$PYTHON_BIN" - <<'PY'
import os
import shutil
from pathlib import Path

cfg = Path(os.environ["ES_SYSTEMS_CFG"])
backup = Path(os.environ["BACKUP"])

cfg.unlink()
shutil.copyfile(backup, cfg)
PY
        log "Replaced read-only symlink with writable copy: $ES_SYSTEMS_CFG"
        log "Original symlink target saved: ${BACKUP}.symlink"
    fi

    PYXEL_ROM_DIR="$PYXEL_ROM_DIR" \
    PYXEL_RUNNER="$PYXEL_RUNNER" \
    ES_SYSTEMS_CFG="$ES_SYSTEMS_CFG" \
    "$PYTHON_BIN" - <<'PY'
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

cfg = Path(os.environ["ES_SYSTEMS_CFG"])
rom_dir = os.environ["PYXEL_ROM_DIR"]
runner = os.environ["PYXEL_RUNNER"]

system_block = f"""        <system>
                <name>pyxel</name>
                <fullname>Pyxel</fullname>
                <manufacturer>... System</manufacturer>
                <release>System</release>
                <hardware>System</hardware>
                <path>{rom_dir}</path>
                <extension>.py .pyxapp .edit</extension>
                <command>{runner} "%ROM%"</command>
                <platform>pyxel</platform>
                <theme>pyxel</theme>
                <emulators>
                        <emulator name="pyxel">
                                <cores>
                                        <core default="true">pyxel</core>
                                </cores>
                        </emulator>
                </emulators>
        </system>"""

text = cfg.read_text(encoding="utf-8", errors="replace")

def count_systems(xml_text):
    try:
        return len(ET.fromstring(xml_text).findall("system"))
    except ET.ParseError as exc:
        print(f"ERROR: invalid es_systems.cfg XML: {exc}", file=sys.stderr)
        sys.exit(1)

original_count = count_systems(text)
system_pattern = re.compile(r"(?ms)^[ \t]*<system[ \t]*>.*?^[ \t]*</system>")
blocks = list(system_pattern.finditer(text))
pyxel_name_pattern = re.compile(r"<name>\s*pyxel\s*</name>")
target = next((match for match in blocks if pyxel_name_pattern.search(match.group(0))), None)

if target:
    text = text[:target.start()] + system_block + text[target.end():]
    action = "updated"
elif "</systemList>" in text:
    text = text.replace("</systemList>", system_block + "\n</systemList>", 1)
    action = "added"
else:
    text = "<systemList>\n" + system_block + "\n</systemList>\n"
    action = "created"

new_count = count_systems(text)
minimum_count = original_count if target else original_count + 1
if original_count > 1 and new_count < minimum_count:
    print(
        f"ERROR: refusing to write es_systems.cfg; system count would change from {original_count} to {new_count}",
        file=sys.stderr,
    )
    sys.exit(1)

cfg.write_text(text, encoding="utf-8")
print(f"Pyxel system entry {action}: {cfg} ({original_count} -> {new_count} systems)")
PY

    log "ES backup: $BACKUP"
    log "ES Pyxel ROM dir: $PYXEL_ROM_DIR"
    log "ES Pyxel runner: $PYXEL_RUNNER"
    log "Restart EmulationStation or reboot ROCKNIX to reload the systems list."
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

install_runner
install_es_system

log "Pyxel install completed."
