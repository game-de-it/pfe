#!/bin/sh

# Run Pyxel apps on ROCKNIX from EmulationStation.
#
# Expected es_systems.cfg command:
#   /storage/.config/rocknix-pyxel/rocknix_pyxel_run.sh "%ROM%"

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

if [ -z "$APP_PATH" ]; then
    fail "No ROM/app path was provided."
fi

if [ ! -e "$APP_PATH" ]; then
    fail "App not found: $APP_PATH"
fi

if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
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
        # .edit is a small convenience marker. If its first line points to a
        # .pyxres file, open that resource; otherwise open Pyxel's editor.
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
