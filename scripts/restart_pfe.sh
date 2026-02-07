#!/bin/sh
# Restart PFE launcher script
#
# This script is called before pyxel.quit() to perform any cleanup.
# When running under launcher.sh, PFE will automatically restart.

# Nothing to do here - just exit successfully
# The caller will call pyxel.quit() after this script returns
exit 0
