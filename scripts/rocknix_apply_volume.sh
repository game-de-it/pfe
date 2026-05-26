#!/bin/sh

# Re-apply ROCKNIX's persisted frontend volume to the live audio stack.
# Some devices boot with the mixer at a default level until a hardware
# volume key causes ROCKNIX to refresh audio.volume.

set -u

CONFIG_FILE="${PFE_ROCKNIX_SYSTEM_CFG:-/storage/.config/system/configs/system.cfg}"
MIXER_NAME="${PFE_ALSA_MIXER:-Master}"

read_system_volume() {
    [ -r "$CONFIG_FILE" ] || return 1

    sed -n 's/^[[:space:]]*audio[.]volume[[:space:]]*=[[:space:]]*//p' "$CONFIG_FILE" \
        | tail -n 1 \
        | tr -d '\r' \
        | sed 's/[[:space:]]*$//'
}

VOLUME="$(read_system_volume || true)"

case "$VOLUME" in
    ''|*[!0-9]*)
        exit 0
        ;;
esac

if [ "$VOLUME" -lt 0 ]; then
    VOLUME=0
elif [ "$VOLUME" -gt 100 ]; then
    VOLUME=100
fi

APPLIED=0

if command -v wpctl >/dev/null 2>&1; then
    if wpctl set-volume @DEFAULT_AUDIO_SINK@ "${VOLUME}%" >/dev/null 2>&1; then
        APPLIED=1
    fi
fi

if command -v amixer >/dev/null 2>&1; then
    if amixer -q sset "$MIXER_NAME" "${VOLUME}%" >/dev/null 2>&1; then
        APPLIED=1
    fi
fi

if [ "$APPLIED" -eq 1 ]; then
    echo "PFE: applied ROCKNIX system volume: ${VOLUME}%."
fi

exit 0
