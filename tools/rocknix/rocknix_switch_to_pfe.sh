#!/bin/sh

# Switch from ROCKNIX EmulationStation to PFE.
# Put this script in /roms/ports and launch it from ES Ports.

set -eu

PFE_SERVICE="${PFE_SERVICE:-pfe.service}"
ES_SERVICE="${PFE_ES_SERVICE:-essway.service}"
UI_SERVICE_FILE="${PFE_UI_SERVICE_FILE:-/storage/.config/profile.d/090-ui_service}"
FRONTEND_STATE_FILE="${PFE_FRONTEND_STATE_FILE:-/storage/.config/pfe/frontend.conf}"
FRONTEND_AUTOSTART_SCRIPT="${PFE_FRONTEND_AUTOSTART_SCRIPT:-/storage/.config/autostart/99-pfe-frontend}"
PFE_START_TIMEOUT="${PFE_START_TIMEOUT:-10}"

install_frontend_autostart() {
    frontend_autostart_dir=$(dirname "$FRONTEND_AUTOSTART_SCRIPT")

    mkdir -p "$frontend_autostart_dir" 2>/dev/null || return 0
    {
        printf '%s\n' '#!/bin/sh'
        printf '%s\n' 'STATE_FILE="${PFE_FRONTEND_STATE_FILE:-/storage/.config/pfe/frontend.conf}"'
        printf '%s\n' 'UI_SERVICE_FILE="${PFE_UI_SERVICE_FILE:-/storage/.config/profile.d/090-ui_service}"'
        printf '%s\n' ''
        printf '%s\n' '[ -r "$STATE_FILE" ] || exit 0'
        printf '%s\n' 'IFS= read -r service_list < "$STATE_FILE" || exit 0'
        printf '%s\n' 'case "$service_list" in'
        printf '%s\n' '    *service*) ;;'
        printf '%s\n' '    *) exit 0 ;;'
        printf '%s\n' 'esac'
        printf '%s\n' 'mkdir -p "$(dirname "$UI_SERVICE_FILE")" 2>/dev/null || exit 0'
        printf '%s\n' 'printf '\''UI_SERVICE="%s"\n'\'' "$service_list" > "$UI_SERVICE_FILE" 2>/dev/null || true'
    } > "$FRONTEND_AUTOSTART_SCRIPT" 2>/dev/null || return 0
    chmod +x "$FRONTEND_AUTOSTART_SCRIPT" 2>/dev/null || true
}

set_boot_frontend() {
    service_list="$1"
    ui_service_dir=$(dirname "$UI_SERVICE_FILE")
    frontend_state_dir=$(dirname "$FRONTEND_STATE_FILE")
    legacy_backup="$UI_SERVICE_FILE.pfe-bak"
    backup_file="$frontend_state_dir/090-ui_service.bak"

    mkdir -p "$ui_service_dir" "$frontend_state_dir" 2>/dev/null || return 0
    if [ -f "$legacy_backup" ]; then
        mv "$legacy_backup" "$backup_file" 2>/dev/null || true
    fi
    if [ -f "$UI_SERVICE_FILE" ] && [ ! -f "$backup_file" ]; then
        cp "$UI_SERVICE_FILE" "$backup_file" 2>/dev/null || true
    fi
    install_frontend_autostart
    printf '%s\n' "$service_list" > "$FRONTEND_STATE_FILE" 2>/dev/null || true
    printf 'UI_SERVICE="%s"\n' "$service_list" > "$UI_SERVICE_FILE" 2>/dev/null || true
}

verify_pfe_service() {
    if ! systemctl cat "$PFE_SERVICE" >/dev/null 2>&1; then
        echo "ERROR: $PFE_SERVICE is not installed. Run 02_install_pfe.sh first." >&2
        exit 1
    fi

    systemctl start sway.service >/dev/null 2>&1 || true

    if ! systemctl start "$PFE_SERVICE"; then
        echo "ERROR: failed to start $PFE_SERVICE." >&2
        systemctl status "$PFE_SERVICE" --no-pager --lines=20 2>/dev/null || true
        systemctl start "$ES_SERVICE" >/dev/null 2>&1 || true
        exit 1
    fi

    count=0
    while [ "$count" -lt "$PFE_START_TIMEOUT" ]; do
        if systemctl is-active --quiet "$PFE_SERVICE"; then
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done

    echo "ERROR: $PFE_SERVICE did not become active within ${PFE_START_TIMEOUT}s." >&2
    systemctl status "$PFE_SERVICE" --no-pager --lines=20 2>/dev/null || true
    systemctl start "$ES_SERVICE" >/dev/null 2>&1 || true
    exit 1
}

verify_pfe_service
set_boot_frontend "sway.service $PFE_SERVICE"

switch_command="systemctl stop \"$ES_SERVICE\" 2>/dev/null || true; systemctl reset-failed \"$ES_SERVICE\" 2>/dev/null || true"

if command -v systemd-run >/dev/null 2>&1; then
    systemd-run \
        --unit="es-switch-to-pfe-$(date +%s)" \
        --collect \
        --no-block \
        /bin/sh -c "$switch_command"
else
    sh -c "$switch_command" >/dev/null 2>&1 &
fi

exit 0
