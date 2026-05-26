#!/bin/sh
# Switch from PFE to ROCKNIX EmulationStation.

set -u

NO_RESTART_FILE="${PFE_NO_RESTART_FILE:-/tmp/pfe-no-restart}"
ES_SERVICE="${PFE_ES_SERVICE:-essway.service}"
PFE_SERVICE="${PFE_SERVICE:-pfe.service}"
UI_SERVICE_FILE="${PFE_UI_SERVICE_FILE:-/storage/.config/profile.d/090-ui_service}"
FRONTEND_STATE_FILE="${PFE_FRONTEND_STATE_FILE:-/storage/.config/pfe/frontend.conf}"
FRONTEND_AUTOSTART_SCRIPT="${PFE_FRONTEND_AUTOSTART_SCRIPT:-/storage/.config/autostart/99-pfe-frontend}"

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

: > "$NO_RESTART_FILE"
set_boot_frontend "sway.service $ES_SERVICE"

switch_command="sleep 0.5; systemctl start sway.service >/dev/null 2>&1 || true; systemctl start \"$ES_SERVICE\"; systemctl stop \"$PFE_SERVICE\" 2>/dev/null || true; systemctl reset-failed \"$PFE_SERVICE\" 2>/dev/null || true"

if command -v systemd-run >/dev/null 2>&1; then
    systemd-run \
        --unit="pfe-switch-to-es-$(date +%s)" \
        --collect \
        --no-block \
        /bin/sh -c "$switch_command"
else
    sh -c "$switch_command" >/dev/null 2>&1 &
fi

exit 0
