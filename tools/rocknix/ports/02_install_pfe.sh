#!/bin/sh

# Install PFE as a ROCKNIX systemd service.
#
# Default behavior only installs/reloads the service. Use --enable to make PFE
# the ROCKNIX boot frontend, and --start to switch to it immediately.

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

maybe_reexec_in_terminal "Install PFE for ROCKNIX" "$@"

UNIT_DIR="${PFE_UNIT_DIR:-/storage/.config/system.d}"
UNIT_FILE="$UNIT_DIR/pfe.service"
PFE_DIR="${PFE_DIR:-/roms/pfe}"
PFE_PYTHON="${PFE_PYTHON:-/usr/bin/python3}"
PFE_PYTHONUSERBASE="${PFE_PYTHONUSERBASE:-/storage/.local}"
UI_SERVICE_FILE="${PFE_UI_SERVICE_FILE:-/storage/.config/profile.d/090-ui_service}"
FRONTEND_STATE_FILE="${PFE_FRONTEND_STATE_FILE:-/storage/.config/pfe/frontend.conf}"
FRONTEND_AUTOSTART_SCRIPT="${PFE_FRONTEND_AUTOSTART_SCRIPT:-/storage/.config/autostart/99-pfe-frontend}"
RETROARCH_CFG="${PFE_RETROARCH_CFG:-/storage/.config/retroarch/retroarch.cfg}"
CONFIGURE_RETROARCH_SCREENSHOTS="${PFE_CONFIGURE_RETROARCH_SCREENSHOTS:-1}"
INSTALL_DEPS="${PFE_INSTALL_DEPS:-1}"
ENABLE=0
START_NOW=0
DISABLE_ES=0

usage() {
    cat <<'EOF'
Usage: 02_install_pfe.sh [options]

Options:
  --pfe-dir DIR       PFE directory (default: /roms/pfe)
  --python PYTHON     Python binary (default: /usr/bin/python3)
  --no-deps           Do not install PFE requirements.txt
  --enable            Use PFE as the ROCKNIX boot frontend
  --disable-es        Compatibility option; --enable selects PFE instead of ES
  --no-ra-screenshot  Do not change RetroArch screenshot settings
  --start             Start pfe.service now
  -h, --help          Show this help
EOF
}

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

    mkdir -p "$ui_service_dir" "$frontend_state_dir"
    if [ -f "$legacy_backup" ]; then
        mv "$legacy_backup" "$backup_file" 2>/dev/null || true
    fi
    if [ -f "$UI_SERVICE_FILE" ] && [ ! -f "$backup_file" ]; then
        cp "$UI_SERVICE_FILE" "$backup_file" 2>/dev/null || true
    fi
    install_frontend_autostart
    printf '%s\n' "$service_list" > "$FRONTEND_STATE_FILE"
    printf 'UI_SERVICE="%s"\n' "$service_list" > "$UI_SERVICE_FILE"
}

bool_enabled() {
    case "$1" in
        0|false|FALSE|no|NO|off|OFF)
            return 1
            ;;
    esac
    return 0
}

set_retroarch_config_value() {
    cfg_file="$1"
    key="$2"
    value="$3"
    tmp_file="${cfg_file}.pfe-tmp.$$"

    awk -v key="$key" -v value="$value" '
        BEGIN {
            pattern = "^[ \t]*" key "[ \t]*="
            wrote = 0
        }
        $0 ~ pattern {
            if (!wrote) {
                print key " = " value
                wrote = 1
            }
            next
        }
        { print }
        END {
            if (!wrote) {
                print key " = " value
            }
        }
    ' "$cfg_file" > "$tmp_file" || {
        rm -f "$tmp_file" 2>/dev/null || true
        return 1
    }

    mv "$tmp_file" "$cfg_file"
}

configure_retroarch_screenshots() {
    bool_enabled "$CONFIGURE_RETROARCH_SCREENSHOTS" || return 0

    cfg_dir=$(dirname "$RETROARCH_CFG")
    mkdir -p "$cfg_dir" 2>/dev/null || {
        echo "WARNING: Could not create RetroArch config directory: $cfg_dir" >&2
        return 0
    }

    if [ ! -f "$RETROARCH_CFG" ]; then
        : > "$RETROARCH_CFG" 2>/dev/null || {
            echo "WARNING: Could not create RetroArch config: $RETROARCH_CFG" >&2
            return 0
        }
    fi

    if [ -f "$RETROARCH_CFG" ] && [ ! -f "$RETROARCH_CFG.pfe-bak" ]; then
        cp "$RETROARCH_CFG" "$RETROARCH_CFG.pfe-bak" 2>/dev/null || true
    fi

    echo "Configuring RetroArch screenshot settings in $RETROARCH_CFG ..."
    set_retroarch_config_value "$RETROARCH_CFG" auto_screenshot_filename '"false"' || {
        echo "WARNING: Failed to set auto_screenshot_filename in $RETROARCH_CFG" >&2
        return 0
    }
    set_retroarch_config_value "$RETROARCH_CFG" screenshots_in_content_dir '"false"' || {
        echo "WARNING: Failed to set screenshots_in_content_dir in $RETROARCH_CFG" >&2
        return 0
    }
    set_retroarch_config_value "$RETROARCH_CFG" sort_screenshots_by_content_enable '"true"' || {
        echo "WARNING: Failed to set sort_screenshots_by_content_enable in $RETROARCH_CFG" >&2
        return 0
    }
}

configure_retroarch_menu() {
    cfg_dir=$(dirname "$RETROARCH_CFG")
    mkdir -p "$cfg_dir" 2>/dev/null || {
        echo "WARNING: Could not create RetroArch config directory: $cfg_dir" >&2
        return 0
    }

    if [ ! -f "$RETROARCH_CFG" ]; then
        : > "$RETROARCH_CFG" 2>/dev/null || {
            echo "WARNING: Could not create RetroArch config: $RETROARCH_CFG" >&2
            return 0
        }
    fi

    if [ -f "$RETROARCH_CFG" ] && [ ! -f "$RETROARCH_CFG.pfe-bak" ]; then
        cp "$RETROARCH_CFG" "$RETROARCH_CFG.pfe-bak" 2>/dev/null || true
    fi

    echo "Configuring RetroArch menu settings in $RETROARCH_CFG ..."
    set_retroarch_config_value "$RETROARCH_CFG" menu_driver '"rgui"' || {
        echo "WARNING: Failed to set menu_driver in $RETROARCH_CFG" >&2
        return 0
    }
}

validate_pfe_tree() {
    [ -r "$PFE_DIR/launcher.sh" ] || {
        echo "ERROR: launcher.sh is not readable: $PFE_DIR/launcher.sh" >&2
        exit 1
    }
    [ -r "$PFE_DIR/main.py" ] || {
        echo "ERROR: main.py is not readable: $PFE_DIR/main.py" >&2
        exit 1
    }
    [ -d "$PFE_DIR/pfe_app" ] || {
        echo "ERROR: pfe_app directory not found: $PFE_DIR/pfe_app" >&2
        echo "Copy the current PFE directory structure, including pfe_app/, to $PFE_DIR." >&2
        exit 1
    }
    [ -r "$PFE_DIR/pfe_app/__init__.py" ] || {
        echo "ERROR: pfe_app package marker not readable: $PFE_DIR/pfe_app/__init__.py" >&2
        exit 1
    }
    [ -r "$PFE_DIR/pfe_app/config.py" ] || {
        echo "ERROR: pfe_app module not readable: $PFE_DIR/pfe_app/config.py" >&2
        exit 1
    }
    [ -r "$PFE_DIR/requirements.txt" ] || {
        echo "ERROR: PFE requirements.txt is not readable: $PFE_DIR/requirements.txt" >&2
        echo "Copy the current PFE directory structure, including requirements.txt, to $PFE_DIR." >&2
        exit 1
    }
    [ -r "$PFE_DIR/scripts/install_deps.sh" ] || {
        echo "ERROR: PFE dependency installer is not readable: $PFE_DIR/scripts/install_deps.sh" >&2
        echo "Copy the current PFE scripts/ directory to $PFE_DIR." >&2
        exit 1
    }
}

install_pfe_requirements() {
    bool_enabled "$INSTALL_DEPS" || {
        echo "Skipping PFE dependency install because --no-deps or PFE_INSTALL_DEPS=false was used."
        return 0
    }

    echo "Installing PFE Python requirements from $PFE_DIR/requirements.txt ..."
    HOME=/storage \
    PYTHONUSERBASE="$PFE_PYTHONUSERBASE" \
    PFE_PIP_USER=1 \
    PFE_PYTHON="$PFE_PYTHON" \
    sh "$PFE_DIR/scripts/install_deps.sh"
}

validate_pfe_python() {
    echo "Checking PFE Python imports ..."
    HOME=/storage \
    PYTHONUSERBASE="$PFE_PYTHONUSERBASE" \
    PATH="$PFE_PYTHONUSERBASE/bin:$PATH" \
    "$PFE_PYTHON" - <<'PY'
import importlib

modules = [
    ("pyxel", "pyxel"),
    ("PIL", "Pillow"),
    ("pygame", "pygame"),
    ("PyxelUniversalFont", "pyxel-universal-font"),
]

missing = []
for module_name, package_name in modules:
    try:
        importlib.import_module(module_name)
    except Exception as exc:
        missing.append(f"{package_name} ({exc})")

if missing:
    raise SystemExit("Missing PFE Python requirements: " + ", ".join(missing))

print("PFE Python import check OK")
PY
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --pfe-dir)
            shift
            [ "$#" -gt 0 ] || { echo "ERROR: --pfe-dir needs a path." >&2; exit 2; }
            PFE_DIR="$1"
            ;;
        --python)
            shift
            [ "$#" -gt 0 ] || { echo "ERROR: --python needs a path." >&2; exit 2; }
            PFE_PYTHON="$1"
            ;;
        --no-deps)
            INSTALL_DEPS=0
            ;;
        --enable)
            ENABLE=1
            ;;
        --disable-es)
            DISABLE_ES=1
            ;;
        --no-ra-screenshot)
            CONFIGURE_RETROARCH_SCREENSHOTS=0
            ;;
        --start)
            START_NOW=1
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

[ -d "$PFE_DIR" ] || { echo "ERROR: PFE directory not found: $PFE_DIR" >&2; exit 1; }

echo "Fixing PFE file permissions under $PFE_DIR ..."
chmod -R "${PFE_PERMISSION_MODE:-755}" "$PFE_DIR" 2>/dev/null || true

validate_pfe_tree
[ -x "$PFE_PYTHON" ] || { echo "ERROR: Python is not executable: $PFE_PYTHON" >&2; exit 1; }
mkdir -p "$PFE_PYTHONUSERBASE"
install_pfe_requirements
validate_pfe_python

configure_retroarch_screenshots
configure_retroarch_menu

mkdir -p "$UNIT_DIR"

cat > "$UNIT_FILE" <<EOF
[Unit]
Description=PFE Frontend
Requires=sway.service
After=sway.service
Conflicts=essway.service

[Service]
Type=simple
Environment=HOME=/storage
Environment=PYTHONUSERBASE=$PFE_PYTHONUSERBASE
Environment=PATH=$PFE_PYTHONUSERBASE/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=SDL_AUDIODRIVER=alsa
Environment=SDL_VIDEODRIVER=wayland
Environment=XDG_RUNTIME_DIR=/var/run/0-runtime-dir
Environment=WAYLAND_DISPLAY=wayland-1
Environment=DISPLAY=:0.0
Environment=SDL_GAMECONTROLLERCONFIG_FILE=/storage/.config/SDL-GameControllerDB/gamecontrollerdb.txt
Environment=PFE_APP_DIR=$PFE_DIR
Environment=PFE_PYTHON=$PFE_PYTHON
Environment=PFE_NO_RESTART_FILE=/tmp/pfe-no-restart
Environment=PFE_FIX_PERMISSIONS=auto
EnvironmentFile=-/etc/profile
EnvironmentFile=-/storage/.config/pfe/pfe.env
WorkingDirectory=$PFE_DIR
ExecStart=/bin/bash $PFE_DIR/launcher.sh
Restart=on-failure
RestartSec=2
KillMode=control-group

[Install]
WantedBy=rocknix.target
EOF

systemctl daemon-reload

if ! systemctl cat pfe.service >/dev/null 2>&1; then
    systemctl link "$UNIT_FILE" >/dev/null 2>&1 || true
    systemctl daemon-reload
fi

if ! systemctl cat pfe.service >/dev/null 2>&1; then
    echo "ERROR: systemd could not load pfe.service from $UNIT_FILE" >&2
    exit 1
fi

if [ "$ENABLE" -eq 1 ]; then
    set_boot_frontend "sway.service pfe.service"
fi

[ "$DISABLE_ES" -eq 0 ] || echo "Note: ROCKNIX boot frontend is controlled by $UI_SERVICE_FILE."

if [ "$START_NOW" -eq 1 ]; then
    systemctl start pfe.service
fi

echo "Installed: $UNIT_FILE"
systemctl status pfe.service --no-pager --lines=0 2>/dev/null || true
