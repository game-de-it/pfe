#!/bin/sh

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CORE_ARG=$1
ROM=$2

case "${PFE_RA_LAUNCH_MODE:-direct}" in
    runemu|rocknix)
        exec sh "$SCRIPT_DIR/rocknix_runemu.sh" retroarch "$CORE_ARG" "$ROM"
        ;;
esac

if [ -z "$CORE_ARG" ] || [ -z "$ROM" ]; then
    echo "retroarch.sh: usage: retroarch.sh <core_path> <rom_path>" >&2
    exit 2
fi

if [ -x /usr/bin/retroarch ]; then
    exec /usr/bin/retroarch -L "$CORE_ARG" "$ROM"
fi

if command -v retroarch >/dev/null 2>&1; then
    exec retroarch -L "$CORE_ARG" "$ROM"
fi

exec sh "$SCRIPT_DIR/rocknix_runemu.sh" retroarch "$CORE_ARG" "$ROM"
