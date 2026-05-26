#!/bin/sh

ROM=${1:-}
EXT=$(printf '%s\n' "$ROM" | sed 's/.*\.//' | tr '[:upper:]' '[:lower:]')
PYXEL_BIN=${PYXEL_BIN:-/storage/pyxel_Python/bin/pyxel}
PYXEL_RUNNER=${PFE_PYXEL_RUNNER:-}
HOLD_FILE=${PFE_LAUNCH_HOLD_FILE:-/tmp/pfe-launch-hold}
HANDOFF_DELAY=${PFE_LAUNCH_HANDOFF_DELAY:-0.4}
HANDOFF_LOG=${PFE_PYXEL_HANDOFF_LOG:-/storage/.config/rocknix-pyxel/pfe-handoff.log}

fail() {
    echo "pyxel.sh: $*" >&2
    exit 2
}

case "$EXT" in
    py|pyxapp|edit)
        ;;
    *)
        fail "unsupported extension .$EXT"
        ;;
esac

[ -n "$ROM" ] || fail "no app path was provided"
[ -e "$ROM" ] || fail "app not found: $ROM"

if [ -z "$PYXEL_RUNNER" ]; then
    for candidate in \
        /storage/.config/rocknix-pyxel/rocknix_pyxel_run.sh \
        /roms/ports/rocknix_pyxel_run.sh; do
        if [ -x "$candidate" ]; then
            PYXEL_RUNNER="$candidate"
            break
        fi
    done
fi

run_pyxel_app() {
    if [ -n "$PYXEL_RUNNER" ] && [ -x "$PYXEL_RUNNER" ]; then
        "$PYXEL_RUNNER" "$ROM"
        return $?
    fi

    case "$EXT" in
        pyxapp)
            "$PYXEL_BIN" play "$ROM"
            ;;
        py)
            "$PYXEL_BIN" run "$ROM"
            ;;
        edit)
            "$PYXEL_BIN" edit "$ROM"
            ;;
    esac
}

exec_pyxel_app() {
    if [ -n "$PYXEL_RUNNER" ] && [ -x "$PYXEL_RUNNER" ]; then
        exec "$PYXEL_RUNNER" "$ROM"
    fi

    case "$EXT" in
        pyxapp)
            exec "$PYXEL_BIN" play "$ROM"
            ;;
        py)
            exec "$PYXEL_BIN" run "$ROM"
            ;;
        edit)
            exec "$PYXEL_BIN" edit "$ROM"
            ;;
    esac
}

case "${PFE_LAUNCH_HANDOFF:-}" in
    1|true|TRUE|yes|YES|on|ON)
        mkdir -p "$(dirname "$HOLD_FILE")" 2>/dev/null || true
        mkdir -p "$(dirname "$HANDOFF_LOG")" 2>/dev/null || true
        : > "$HOLD_FILE"
        echo "$$" > "$HOLD_FILE.pid" 2>/dev/null || true
        exec >> "$HANDOFF_LOG" 2>&1
        trap 'rm -f "$HOLD_FILE" "$HOLD_FILE.pid"' EXIT HUP INT TERM
        sleep "$HANDOFF_DELAY"
        echo "PFE Pyxel handoff start: $ROM"
        run_pyxel_app
        status=$?
        echo "PFE Pyxel handoff exit: $status"
        exit "$status"
        ;;
esac

exec_pyxel_app
