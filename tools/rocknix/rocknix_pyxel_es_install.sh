#!/bin/sh

# Install/update the Pyxel system entry in ROCKNIX EmulationStation.

set -eu

ES_SYSTEMS_CFG="${ES_SYSTEMS_CFG:-/storage/.config/emulationstation/es_systems.cfg}"
PYXEL_ROM_DIR="${PYXEL_ROM_DIR:-/storage/roms/pyxel}"
PYXEL_RUNNER="${PYXEL_RUNNER:-/storage/.config/rocknix-pyxel/rocknix_pyxel_run.sh}"

if [ ! -f "$ES_SYSTEMS_CFG" ]; then
    echo "ERROR: es_systems.cfg not found: $ES_SYSTEMS_CFG" >&2
    exit 1
fi

if [ ! -x "$PYXEL_RUNNER" ]; then
    echo "ERROR: Pyxel runner is missing or not executable: $PYXEL_RUNNER" >&2
    echo "Run 01_install_pyxel.sh first, or set PYXEL_RUNNER=/path/to/rocknix_pyxel_run.sh." >&2
    exit 1
fi

mkdir -p "$PYXEL_ROM_DIR"

BACKUP="${ES_SYSTEMS_CFG}.bak.$(date +%Y%m%d-%H%M%S)"
cp "$ES_SYSTEMS_CFG" "$BACKUP"

if [ -L "$ES_SYSTEMS_CFG" ]; then
    LINK_TARGET="$(readlink "$ES_SYSTEMS_CFG")"
    echo "$LINK_TARGET" > "${BACKUP}.symlink"
    ES_SYSTEMS_CFG="$ES_SYSTEMS_CFG" BACKUP="$BACKUP" python3 - <<'PY'
import os
import shutil
from pathlib import Path

cfg = Path(os.environ["ES_SYSTEMS_CFG"])
backup = Path(os.environ["BACKUP"])

cfg.unlink()
shutil.copyfile(backup, cfg)
PY
    echo "Replaced read-only symlink with writable copy: $ES_SYSTEMS_CFG"
    echo "Original symlink target saved: ${BACKUP}.symlink"
fi

PYXEL_ROM_DIR="$PYXEL_ROM_DIR" \
PYXEL_RUNNER="$PYXEL_RUNNER" \
ES_SYSTEMS_CFG="$ES_SYSTEMS_CFG" \
python3 - <<'PY'
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

cfg = Path(os.environ["ES_SYSTEMS_CFG"])
rom_dir = os.environ["PYXEL_ROM_DIR"]
runner = os.environ["PYXEL_RUNNER"]

system_block = f"""        <system>
                <name>pyxel</name>
                <fullname>Pyxel</fullname>
                <manufacturer>... System</manufacturer>
                <release>System</release>
                <hardware>System</hardware>
                <path>{rom_dir}</path>
                <extension>.py .pyxapp .edit</extension>
                <command>{runner} "%ROM%"</command>
                <platform>pyxel</platform>
                <theme>pyxel</theme>
                <emulators>
                        <emulator name="pyxel">
                                <cores>
                                        <core default="true">pyxel</core>
                                </cores>
                        </emulator>
                </emulators>
        </system>"""

text = cfg.read_text(encoding="utf-8", errors="replace")

def count_systems(xml_text):
    try:
        return len(ET.fromstring(xml_text).findall("system"))
    except ET.ParseError as exc:
        print(f"ERROR: invalid es_systems.cfg XML: {exc}", file=sys.stderr)
        sys.exit(1)

original_count = count_systems(text)
system_pattern = re.compile(r"(?ms)^[ \t]*<system[ \t]*>.*?^[ \t]*</system>")
blocks = list(system_pattern.finditer(text))
pyxel_name_pattern = re.compile(r"<name>\s*pyxel\s*</name>")
target = next((match for match in blocks if pyxel_name_pattern.search(match.group(0))), None)

if target:
    text = text[:target.start()] + system_block + text[target.end():]
    action = "updated"
elif "</systemList>" in text:
    text = text.replace("</systemList>", system_block + "\n</systemList>", 1)
    action = "added"
else:
    text = "<systemList>\n" + system_block + "\n</systemList>\n"
    action = "created"

new_count = count_systems(text)
minimum_count = original_count if target else original_count + 1
if original_count > 1 and new_count < minimum_count:
    print(
        f"ERROR: refusing to write es_systems.cfg; system count would change from {original_count} to {new_count}",
        file=sys.stderr,
    )
    sys.exit(1)

cfg.write_text(text, encoding="utf-8")
print(f"Pyxel system entry {action}: {cfg} ({original_count} -> {new_count} systems)")
PY

echo "Backup: $BACKUP"
echo "ROM dir: $PYXEL_ROM_DIR"
echo "Runner: $PYXEL_RUNNER"
echo "Restart EmulationStation or reboot ROCKNIX to reload the systems list."
