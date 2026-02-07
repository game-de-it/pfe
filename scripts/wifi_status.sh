#!/bin/sh
# Get current WiFi radio status
#
# Output:
#   "enabled" - WiFi is ON
#   "disabled" - WiFi is OFF
#
# Exit codes:
#   0 - Success
#   1 - Error

# Ensure PATH includes common locations for nmcli
export PATH="/usr/bin:/usr/sbin:/bin:/sbin:$PATH"

# Get WiFi radio status
nmcli radio wifi 2>/dev/null

exit $?
