#!/usr/bin/env bash
# Headless studio run: executes up to N pipeline actions, stops at human gates.
# Usage: scripts/autopilot.sh [N]     Logs: studio/logs/autopilot-<timestamp>.log
set -euo pipefail
cd "$(dirname "$0")/.."
N="${1:-3}"
CLAUDE="${CLAUDE_BIN:-claude}"
mkdir -p studio/logs
LOG="studio/logs/autopilot-$(date +%Y%m%d-%H%M%S).log"
python scripts/studio.py validate
# acceptEdits: edits auto-approved; Bash limited to .claude/settings.json allow-list; hooks still guard gates.
"$CLAUDE" -p "/studio run $N" --permission-mode acceptEdits 2>&1 | tee "$LOG"
echo "Log: $LOG"
python scripts/studio.py status
