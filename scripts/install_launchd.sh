#!/bin/sh
set -e

ROOT="/Users/ssg/Documents/CodeX/RedbookAuto"
PLIST="$ROOT/launchd/com.redbookauto.publisher.plist"
DEST="$HOME/Library/LaunchAgents/com.redbookauto.publisher.plist"

mkdir -p "$HOME/Library/LaunchAgents"
mkdir -p "$ROOT/logs"

cp "$PLIST" "$DEST"

launchctl bootout "gui/$UID" "$DEST" 2>/dev/null || true
launchctl bootstrap "gui/$UID" "$DEST"
launchctl enable "gui/$UID/com.redbookauto.publisher"
launchctl kickstart -k "gui/$UID/com.redbookauto.publisher"
