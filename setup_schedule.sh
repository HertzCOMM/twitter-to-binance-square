#!/bin/bash
# Setup LaunchAgent (macOS) to run sync every 2 hours.
# For Linux, use cron instead: */120 * * * * cd /path/to/twitter-to-binance-square && python3 sync.py

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$(which python3)"
LABEL="com.twitter-bsq-sync"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOG_DIR="$HOME/.twitter-bsq-sync"

mkdir -p "$LOG_DIR"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON}</string>
        <string>-X</string>
        <string>utf8</string>
        <string>${SCRIPT_DIR}/sync.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${SCRIPT_DIR}</string>
    <key>StartInterval</key>
    <integer>7200</integer>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/sync.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/sync.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONIOENCODING</key>
        <string>utf-8</string>
    </dict>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo "✓ LaunchAgent installed: ${LABEL}"
echo "  Schedule: every 2 hours"
echo "  Logs: ${LOG_DIR}/sync.log"
echo ""
echo "To stop:  launchctl unload ${PLIST}"
echo "To start: launchctl load ${PLIST}"
