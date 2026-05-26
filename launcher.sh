#!/bin/bash

# PFE auto-restart launcher.
# Prefer a storage-local Python runtime on handheld Linux distributions.

set -u

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
APP_DIR="${PFE_APP_DIR:-$SCRIPT_DIR}"
LOCK_DIR="${PFE_LOCK_DIR:-/tmp/pfe-launcher.lock}"
NO_RESTART_FILE="${PFE_NO_RESTART_FILE:-/tmp/pfe-no-restart}"
LAUNCH_HOLD_FILE="${PFE_LAUNCH_HOLD_FILE:-/tmp/pfe-launch-hold}"
PFE_CHILD_PID=""

export SDL_AUDIODRIVER="${SDL_AUDIODRIVER:-alsa}"

FALLBACK_SDL_GAMECONTROLLERCONFIG="19009b4d4b4800000111000000010000,retrogame_joypad,a:b1,b:b0,x:b2,y:b3,back:b8,guide:b10,start:b9,leftstick:b11,rightstick:b12,leftshoulder:b4,rightshoulder:b5,dpup:b13,dpdown:b14,dpleft:b15,dpright:b16,leftx:a0,lefty:a1,rightx:a2,righty:a3,lefttrigger:b6,righttrigger:b7,crc:4d9b,platform:Linux"

should_fix_permissions() {
    case "${PFE_FIX_PERMISSIONS:-auto}" in
        1|true|TRUE|yes|YES|on|ON)
            return 0
            ;;
        0|false|FALSE|no|NO|off|OFF)
            return 1
            ;;
    esac

    case "$APP_DIR" in
        /roms/*|/storage/*|/mnt/*)
            return 0
            ;;
    esac

    return 1
}

fix_app_permissions() {
    local mode
    mode="${PFE_PERMISSION_MODE:-755}"

    should_fix_permissions || return 0

    echo "PFE: fixing app permissions under $APP_DIR (chmod -R $mode)."
    if ! chmod -R "$mode" "$APP_DIR" 2>/dev/null; then
        echo "PFE: warning: failed to fully update permissions under $APP_DIR." >&2
    fi
}

fix_app_permissions

validate_app_tree() {
    local missing
    missing=0

    if [ ! -r "$APP_DIR/main.py" ]; then
        echo "PFE: main.py is not readable: $APP_DIR/main.py" >&2
        missing=1
    fi
    if [ ! -d "$APP_DIR/pfe_app" ]; then
        echo "PFE: pfe_app directory not found: $APP_DIR/pfe_app" >&2
        missing=1
    fi
    if [ ! -r "$APP_DIR/pfe_app/__init__.py" ]; then
        echo "PFE: pfe_app package marker is not readable: $APP_DIR/pfe_app/__init__.py" >&2
        missing=1
    fi
    if [ ! -r "$APP_DIR/pfe_app/config.py" ]; then
        echo "PFE: pfe_app/config.py is not readable: $APP_DIR/pfe_app/config.py" >&2
        missing=1
    fi

    if [ "$missing" -ne 0 ]; then
        echo "PFE: install/copy looks incomplete. Copy the current PFE tree including pfe_app/." >&2
        exit 1
    fi
}

should_apply_system_volume() {
    case "${PFE_APPLY_SYSTEM_VOLUME:-auto}" in
        1|true|TRUE|yes|YES|on|ON)
            return 0
            ;;
        0|false|FALSE|no|NO|off|OFF)
            return 1
            ;;
    esac

    case "$APP_DIR" in
        /roms/*|/storage/*|/mnt/*)
            return 0
            ;;
    esac

    return 1
}

apply_system_volume() {
    local script
    script="$APP_DIR/scripts/rocknix_apply_volume.sh"

    should_apply_system_volume || return 0
    [ -r "$script" ] || return 0

    if ! sh "$script"; then
        echo "PFE: warning: failed to apply ROCKNIX system volume." >&2
    fi
}

le16() {
    local hex
    hex="$(printf '%04s' "$1" | tr ' ' '0')"
    printf '%s%s' "${hex#??}" "${hex%??}"
}

input_block() {
    [ -r /proc/bus/input/devices ] || return 1
    awk 'BEGIN { RS="" } /Handlers=.*js0/ { print; exit }' /proc/bus/input/devices
}

controller_name() {
    input_block | sed -n 's/.*N: Name="\([^"]*\)".*/\1/p' | head -n 1
}

controller_guid() {
    local block bus vendor product version
    block="$(input_block || true)"
    [ -n "$block" ] || return 1
    bus="$(printf '%s\n' "$block" | sed -n 's/.*Bus=\([0-9A-Fa-f]*\).*/\1/p' | head -n 1)"
    vendor="$(printf '%s\n' "$block" | sed -n 's/.*Vendor=\([0-9A-Fa-f]*\).*/\1/p' | head -n 1)"
    product="$(printf '%s\n' "$block" | sed -n 's/.*Product=\([0-9A-Fa-f]*\).*/\1/p' | head -n 1)"
    version="$(printf '%s\n' "$block" | sed -n 's/.*Version=\([0-9A-Fa-f]*\).*/\1/p' | head -n 1)"
    [ -n "$bus" ] && [ -n "$vendor" ] && [ -n "$product" ] && [ -n "$version" ] || return 1
    printf '%s%s%s%s0000000000000000\n' "$(le16 "$bus")" "$(le16 "$vendor")" "$(le16 "$product")" "$(le16 "$version")"
}

controller_mapping_from_file() {
    local file name guid mapping
    file="$1"
    [ -r "$file" ] || return 1
    name="$(controller_name || true)"
    guid="$(controller_guid || true)"
    if [ -n "$guid" ]; then
        mapping="$(grep -i "^$guid," "$file" | grep -F "platform:Linux" | head -n 1 || true)"
        if [ -n "$mapping" ]; then
            printf '%s\n' "$mapping"
            return
        fi
    fi
    if [ -n "$name" ]; then
        mapping="$(grep -F ",$name," "$file" | grep -F "platform:Linux" | head -n 1 || true)"
        if [ -n "$mapping" ]; then
            printf '%s\n' "$mapping"
            return
        fi
    fi
    return 1
}

normalize_controller_mapping() {
    local mapping
    mapping="$1"

    case "$mapping" in
        *",retrogame_joypad,"*)
            # ROCKNIX's SDL DB is Xbox-oriented for A/B. PFE defaults to a
            # Nintendo handheld layout, matching RetroArch's retrogame_joypad
            # autoconfig: A=1, B=0, X=2, Y=3.
            printf '%s\n' "$mapping" | sed \
                -e 's/,a:b[0-9][0-9]*/,__PFE_A__/g' \
                -e 's/,b:b[0-9][0-9]*/,__PFE_B__/g' \
                -e 's/,x:b[0-9][0-9]*/,__PFE_X__/g' \
                -e 's/,y:b[0-9][0-9]*/,__PFE_Y__/g' \
                -e 's/__PFE_A__/,a:b1/g' \
                -e 's/__PFE_B__/,b:b0/g' \
                -e 's/__PFE_X__/,x:b2/g' \
                -e 's/__PFE_Y__/,y:b3/g'
            ;;
        *)
            printf '%s\n' "$mapping"
            ;;
    esac
}

setup_controller_mapping() {
    local file mapping
    if [ -n "${SDL_GAMECONTROLLERCONFIG:-}" ]; then
        echo "PFE: using SDL_GAMECONTROLLERCONFIG from environment."
        return
    fi

    for file in \
        "${SDL_GAMECONTROLLERCONFIG_FILE:-}" \
        /storage/.config/SDL-GameControllerDB/gamecontrollerdb.txt \
        /usr/config/SDL-GameControllerDB/gamecontrollerdb.txt; do
        [ -n "$file" ] || continue
        [ -r "$file" ] || continue
        export SDL_GAMECONTROLLERCONFIG_FILE="$file"
        mapping="$(controller_mapping_from_file "$file" || true)"
        if [ -n "$mapping" ]; then
            mapping="$(normalize_controller_mapping "$mapping")"
            export SDL_GAMECONTROLLERCONFIG="$mapping"
            echo "PFE: loaded SDL controller mapping from $file"
            return
        fi
    done

    export SDL_GAMECONTROLLERCONFIG="$FALLBACK_SDL_GAMECONTROLLERCONFIG"
    echo "PFE: using fallback SDL controller mapping."
}

setup_controller_mapping

cleanup() {
    if [ -n "${PFE_CHILD_PID:-}" ] && kill -0 "$PFE_CHILD_PID" 2>/dev/null; then
        kill "$PFE_CHILD_PID" 2>/dev/null || true
        wait "$PFE_CHILD_PID" 2>/dev/null || true
    fi
    rm -rf "$LOCK_DIR"
}

wait_for_launch_handoff() {
    local hold_file pid_file pid timeout waited
    hold_file="$LAUNCH_HOLD_FILE"
    pid_file="$hold_file.pid"
    timeout="${PFE_LAUNCH_HOLD_TIMEOUT:-0}"
    waited=0

    [ -e "$hold_file" ] || return 0

    case "$timeout" in
        ''|*[!0-9]*)
            timeout=0
            ;;
    esac

    echo "PFE: waiting for handoff launch to finish."
    while [ -e "$hold_file" ]; do
        pid="$(cat "$pid_file" 2>/dev/null || true)"
        if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
            echo "PFE: removing stale handoff launch marker."
            rm -f "$hold_file" "$pid_file"
            break
        fi

        sleep 0.5
        waited=$((waited + 1))
        if [ "$timeout" -gt 0 ] && [ "$waited" -ge $((timeout * 2)) ]; then
            echo "PFE: handoff launch wait timed out after ${timeout}s." >&2
            rm -f "$hold_file" "$pid_file"
            break
        fi
    done
}

handle_signal() {
    cleanup
    exit 130
}

acquire_lock() {
    local old_pid
    if mkdir "$LOCK_DIR" 2>/dev/null; then
        echo "$$" > "$LOCK_DIR/pid"
        trap cleanup EXIT
        trap handle_signal INT TERM
        return 0
    fi

    old_pid="$(cat "$LOCK_DIR/pid" 2>/dev/null || true)"
    if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
        echo "PFE: launcher is already running (pid $old_pid)." >&2
        exit 0
    fi

    echo "PFE: removing stale launcher lock." >&2
    rm -rf "$LOCK_DIR"
    if mkdir "$LOCK_DIR" 2>/dev/null; then
        echo "$$" > "$LOCK_DIR/pid"
        trap cleanup EXIT
        trap handle_signal INT TERM
        return 0
    fi

    echo "PFE: failed to acquire launcher lock: $LOCK_DIR" >&2
    exit 1
}

acquire_lock

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

case "$PYTHON_BIN" in
    /usr/bin/python3)
        echo "PFE: warning: /usr/bin/python3 is known to be fragile on ROCKNIX/plumOS." >&2
        echo "PFE: set PFE_PYTHON=/storage/pyxel_Python/bin/python3 when possible." >&2
        ;;
esac

cd "$APP_DIR" || exit 1
validate_app_tree

while true; do
    apply_system_volume
    echo "Starting PFE with $PYTHON_BIN ..."
    "$PYTHON_BIN" main.py &
    PFE_CHILD_PID=$!
    wait "$PFE_CHILD_PID"

    EXIT_CODE=$?
    PFE_CHILD_PID=""
    echo "PFE exited with code $EXIT_CODE"

    if [ "$EXIT_CODE" -eq 130 ] || [ "$EXIT_CODE" -eq 143 ]; then
        exit "$EXIT_CODE"
    fi

    if [ -f "$NO_RESTART_FILE" ]; then
        echo "PFE: no-restart flag found; launcher is exiting."
        rm -f "$NO_RESTART_FILE"
        exit 0
    fi

    wait_for_launch_handoff

    sleep "${PFE_RESTART_DELAY:-0.5}"
done
