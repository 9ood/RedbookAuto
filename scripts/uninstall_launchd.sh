#!/bin/sh
set -e

DEST="$HOME/Library/LaunchAgents/com.redbookauto.publisher.plist"

launchctl bootout "gui/$UID" "$DEST" 2>/dev/null || true
rm -f "$DEST"
