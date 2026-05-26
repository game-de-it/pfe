#!/bin/sh

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec sh "$SCRIPT_DIR/rocknix_runemu.sh" yabasanshiro yabasanshiro-sa "$1"
