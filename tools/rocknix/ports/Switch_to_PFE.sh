#!/bin/sh

# Switch from ROCKNIX EmulationStation to PFE.
# User-facing script intended to be launched from ES Ports.

set -eu

PFE_SERVICE="${PFE_SERVICE:-pfe.service}"
ES_SERVICE="${PFE_ES_SERVICE:-essway.service}"
NO_RESTART_FILE="${PFE_NO_RESTART_FILE:-/tmp/pfe-no-restart}"
UI_SERVICE_FILE="${PFE_UI_SERVICE_FILE:-/storage/.config/profile.d/090-ui_service}"
FRONTEND_STATE_FILE="${PFE_FRONTEND_STATE_FILE:-/storage/.config/pfe/frontend.conf}"
FRONTEND_AUTOSTART_SCRIPT="${PFE_FRONTEND_AUTOSTART_SCRIPT:-/storage/.config/autostart/99-pfe-frontend}"
SWITCH_WORKER_SCRIPT="${PFE_SWITCH_WORKER_SCRIPT:-/storage/.config/pfe/switch_to_pfe_worker.sh}"
PFE_START_TIMEOUT="${PFE_START_TIMEOUT:-20}"
PFE_READY_SECONDS="${PFE_READY_SECONDS:-3}"
PFE_SWITCH_LOG="${PFE_SWITCH_LOG:-/storage/.config/pfe/switch-to-pfe.log}"

install_frontend_autostart() {
    frontend_autostart_dir=$(dirname "$FRONTEND_AUTOSTART_SCRIPT")

    mkdir -p "$frontend_autostart_dir" 2>/dev/null || return 0
    {
        printf '%s\n' '#!/bin/sh'
        printf '%s\n' 'STATE_FILE="${PFE_FRONTEND_STATE_FILE:-/storage/.config/pfe/frontend.conf}"'
        printf '%s\n' 'UI_SERVICE_FILE="${PFE_UI_SERVICE_FILE:-/storage/.config/profile.d/090-ui_service}"'
        printf '%s\n' 'LOG_FILE="${PFE_FRONTEND_AUTOSTART_LOG:-/storage/.config/pfe/frontend-autostart.log}"'
        printf '%s\n' ''
        printf '%s\n' 'log_message() {'
        printf '%s\n' '    log_dir=$(dirname "$LOG_FILE")'
        printf '%s\n' '    mkdir -p "$log_dir" 2>/dev/null || true'
        printf '%s\n' '    printf '\''%s %s\n'\'' "$(date '\''+%Y-%m-%d %H:%M:%S'\'')" "$*" >> "$LOG_FILE" 2>/dev/null || true'
        printf '%s\n' '}'
        printf '%s\n' ''
        printf '%s\n' '[ -r "$STATE_FILE" ] || { log_message "state file missing: $STATE_FILE"; exit 0; }'
        printf '%s\n' 'IFS= read -r service_list < "$STATE_FILE" || { log_message "state file unreadable: $STATE_FILE"; exit 0; }'
        printf '%s\n' 'case "$service_list" in'
        printf '%s\n' '    *service*) ;;'
        printf '%s\n' '    *) log_message "ignored invalid frontend state: $service_list"; exit 0 ;;'
        printf '%s\n' 'esac'
        printf '%s\n' 'mkdir -p "$(dirname "$UI_SERVICE_FILE")" 2>/dev/null || { log_message "failed to create UI service directory"; exit 0; }'
        printf '%s\n' 'if printf '\''UI_SERVICE="%s"\n'\'' "$service_list" > "$UI_SERVICE_FILE" 2>/dev/null; then'
        printf '%s\n' '    log_message "applied frontend: $service_list"'
        printf '%s\n' 'else'
        printf '%s\n' '    log_message "failed to write UI service file: $UI_SERVICE_FILE"'
        printf '%s\n' 'fi'
    } > "$FRONTEND_AUTOSTART_SCRIPT" 2>/dev/null || return 0
    chmod +x "$FRONTEND_AUTOSTART_SCRIPT" 2>/dev/null || true
}

install_switch_worker() {
    worker_dir=$(dirname "$SWITCH_WORKER_SCRIPT")
    mkdir -p "$worker_dir" 2>/dev/null || {
        echo "ERROR: could not create switch worker directory: $worker_dir" >&2
        exit 1
    }

    cat > "$SWITCH_WORKER_SCRIPT" <<'EOF'
#!/bin/sh
# systemd-launched worker for switching from EmulationStation to PFE.

set -u

PFE_SERVICE="${PFE_SERVICE:-pfe.service}"
ES_SERVICE="${PFE_ES_SERVICE:-essway.service}"
NO_RESTART_FILE="${PFE_NO_RESTART_FILE:-/tmp/pfe-no-restart}"
UI_SERVICE_FILE="${PFE_UI_SERVICE_FILE:-/storage/.config/profile.d/090-ui_service}"
FRONTEND_STATE_FILE="${PFE_FRONTEND_STATE_FILE:-/storage/.config/pfe/frontend.conf}"
FRONTEND_AUTOSTART_SCRIPT="${PFE_FRONTEND_AUTOSTART_SCRIPT:-/storage/.config/autostart/99-pfe-frontend}"
PFE_START_TIMEOUT="${PFE_START_TIMEOUT:-20}"
PFE_READY_SECONDS="${PFE_READY_SECONDS:-3}"
LOG_FILE="${PFE_SWITCH_LOG:-/storage/.config/pfe/switch-to-pfe.log}"

log_message() {
    log_dir=$(dirname "$LOG_FILE")
    mkdir -p "$log_dir" 2>/dev/null || true
    printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$LOG_FILE" 2>/dev/null || true
}

install_frontend_autostart() {
    frontend_autostart_dir=$(dirname "$FRONTEND_AUTOSTART_SCRIPT")

    mkdir -p "$frontend_autostart_dir" 2>/dev/null || return 0
    {
        printf '%s\n' '#!/bin/sh'
        printf '%s\n' 'STATE_FILE="${PFE_FRONTEND_STATE_FILE:-/storage/.config/pfe/frontend.conf}"'
        printf '%s\n' 'UI_SERVICE_FILE="${PFE_UI_SERVICE_FILE:-/storage/.config/profile.d/090-ui_service}"'
        printf '%s\n' 'LOG_FILE="${PFE_FRONTEND_AUTOSTART_LOG:-/storage/.config/pfe/frontend-autostart.log}"'
        printf '%s\n' ''
        printf '%s\n' 'log_message() {'
        printf '%s\n' '    log_dir=$(dirname "$LOG_FILE")'
        printf '%s\n' '    mkdir -p "$log_dir" 2>/dev/null || true'
        printf '%s\n' '    printf '\''%s %s\n'\'' "$(date '\''+%Y-%m-%d %H:%M:%S'\'')" "$*" >> "$LOG_FILE" 2>/dev/null || true'
        printf '%s\n' '}'
        printf '%s\n' ''
        printf '%s\n' '[ -r "$STATE_FILE" ] || { log_message "state file missing: $STATE_FILE"; exit 0; }'
        printf '%s\n' 'IFS= read -r service_list < "$STATE_FILE" || { log_message "state file unreadable: $STATE_FILE"; exit 0; }'
        printf '%s\n' 'case "$service_list" in'
        printf '%s\n' '    *service*) ;;'
        printf '%s\n' '    *) log_message "ignored invalid frontend state: $service_list"; exit 0 ;;'
        printf '%s\n' 'esac'
        printf '%s\n' 'mkdir -p "$(dirname "$UI_SERVICE_FILE")" 2>/dev/null || { log_message "failed to create UI service directory"; exit 0; }'
        printf '%s\n' 'if printf '\''UI_SERVICE="%s"\n'\'' "$service_list" > "$UI_SERVICE_FILE" 2>/dev/null; then'
        printf '%s\n' '    log_message "applied frontend: $service_list"'
        printf '%s\n' 'else'
        printf '%s\n' '    log_message "failed to write UI service file: $UI_SERVICE_FILE"'
        printf '%s\n' 'fi'
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
    log_message "saved boot frontend: $service_list"
}

pfe_runtime_ready() {
    systemctl is-active --quiet "$PFE_SERVICE" || return 1
    if command -v pgrep >/dev/null 2>&1; then
        pgrep -f 'main.py' >/dev/null 2>&1
        return $?
    fi
    ps -ef 2>/dev/null | grep '[p]ython' | grep 'main.py' >/dev/null 2>&1
}

fallback_to_es() {
    reason="$1"
    log_message "$reason; restoring EmulationStation"
    systemctl status "$PFE_SERVICE" --no-pager --lines=30 >> "$LOG_FILE" 2>&1 || true
    systemctl stop "$PFE_SERVICE" >/dev/null 2>&1 || true
    systemctl reset-failed "$PFE_SERVICE" >/dev/null 2>&1 || true
    set_boot_frontend "sway.service $ES_SERVICE"
    systemctl start sway.service >/dev/null 2>&1 || true
    systemctl start "$ES_SERVICE" >/dev/null 2>&1 || true
    exit 1
}

log_message "switch to PFE requested"
rm -f "$NO_RESTART_FILE" 2>/dev/null || true
systemctl start sway.service >/dev/null 2>&1 || true
systemctl stop "$ES_SERVICE" >/dev/null 2>&1 || true
systemctl reset-failed "$ES_SERVICE" >/dev/null 2>&1 || true

if ! systemctl start "$PFE_SERVICE" >> "$LOG_FILE" 2>&1; then
    fallback_to_es "failed to start $PFE_SERVICE"
fi

count=0
ready_count=0
while [ "$count" -lt "$PFE_START_TIMEOUT" ]; do
    if pfe_runtime_ready; then
        ready_count=$((ready_count + 1))
    else
        ready_count=0
    fi

    if [ "$ready_count" -ge "$PFE_READY_SECONDS" ]; then
        set_boot_frontend "sway.service $PFE_SERVICE"
        log_message "PFE frontend active"
        exit 0
    fi

    sleep 1
    count=$((count + 1))
done

fallback_to_es "$PFE_SERVICE did not become ready within ${PFE_START_TIMEOUT}s"
EOF
    chmod +x "$SWITCH_WORKER_SCRIPT" 2>/dev/null || true
}

verify_pfe_service_installed() {
    if ! systemctl cat "$PFE_SERVICE" >/dev/null 2>&1; then
        echo "ERROR: $PFE_SERVICE is not installed. Run 02_install_pfe.sh first." >&2
        exit 1
    fi
}

start_switch_worker() {
    unit_name="pfe-switch-to-pfe-$(date +%s)"

    echo "Starting PFE switch worker..."
    if command -v systemd-run >/dev/null 2>&1; then
        if systemd-run \
            --unit="$unit_name" \
            --collect \
            --no-block \
            /bin/sh "$SWITCH_WORKER_SCRIPT"; then
            exit 0
        fi
    fi

    /bin/sh "$SWITCH_WORKER_SCRIPT" >/dev/null 2>&1 &
}

verify_pfe_service_installed
install_frontend_autostart
install_switch_worker
start_switch_worker

exit 0
