#!/bin/sh

normalize_core() {
    core=$(basename -- "$1")
    core=${core%_libretro.so}
    core=${core%_libretro.dylib}
    core=${core%_libretro.dll}
    core=${core%_libretro}
    printf '%s\n' "$core"
}

derive_system() {
    if [ -n "$PFE_SYSTEM" ]; then
        printf '%s\n' "$PFE_SYSTEM"
        return
    fi

    if [ -n "$PFE_ROM_DIR" ]; then
        basename -- "$PFE_ROM_DIR"
        return
    fi

    rom_path=$1
    rom_dir=$(dirname -- "$rom_path")
    parent_dir=$(dirname -- "$rom_dir")

    case "$parent_dir" in
        */roms|*/roms/)
            basename -- "$rom_dir"
            ;;
        *)
            basename -- "$parent_dir"
            ;;
    esac
}

if [ "$#" -ge 3 ]; then
    EMULATOR=$1
    CORE_ARG_RAW=$2
    CORE_NAME=$(normalize_core "$2")
    shift 2
    ROM=$1
else
    ROM=$1
    EMULATOR=${PFE_EMULATOR:-$PFE_LAUNCHER_TYPE}
    CORE_ARG_RAW=${PFE_CORE_ARG:-$PFE_CORE_NAME}
    CORE_NAME=$(normalize_core "${PFE_CORE_NAME:-$PFE_CORE_ARG}")
fi

SYSTEM=$(derive_system "$ROM")

if [ -z "$ROM" ]; then
    echo "rocknix_runemu.sh: missing ROM path" >&2
    exit 2
fi

if [ -z "$EMULATOR" ] || [ -z "$CORE_NAME" ]; then
    echo "rocknix_runemu.sh: missing emulator/core for $ROM" >&2
    exit 2
fi

if [ -x /usr/bin/runemu.sh ]; then
    if [ -z "$SYSTEM" ]; then
        echo "rocknix_runemu.sh: missing ROCKNIX system id for $ROM" >&2
        exit 2
    fi

    if [ -n "${PFE_CONTROLLERSCONFIG:-$CONTROLLERSCONFIG}" ]; then
        exec /usr/bin/runemu.sh "$ROM" "-P$SYSTEM" "--core=$CORE_NAME" "--emulator=$EMULATOR" \
            "--controllers=${PFE_CONTROLLERSCONFIG:-$CONTROLLERSCONFIG}"
    fi

    exec /usr/bin/runemu.sh "$ROM" "-P$SYSTEM" "--core=$CORE_NAME" "--emulator=$EMULATOR"
fi

if [ "$EMULATOR" = "retroarch" ] && command -v retroarch >/dev/null 2>&1; then
    core_arg=${PFE_CORE_ARG:-$CORE_ARG_RAW}
    if [ -z "$core_arg" ]; then
        core_arg=$CORE_NAME
    fi
    exec retroarch -L "$core_arg" "$ROM"
fi

if command -v "$EMULATOR" >/dev/null 2>&1; then
    exec "$EMULATOR" "$ROM"
fi

echo "rocknix_runemu.sh: /usr/bin/runemu.sh not found and no fallback for $EMULATOR" >&2
exit 127
