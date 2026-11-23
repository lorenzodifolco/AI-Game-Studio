# Headless studio run: executes up to N pipeline actions, stops at human gates.
# Usage:  .\scripts\autopilot.ps1 [-Actions 3] [-Claude path\to\claude.exe]
# Logs:   studio/logs/autopilot-<timestamp>.log (gitignored)
param(
    [int]$Actions = 3,
    [string]$Claude = $(if ($env:CLAUDE_BIN) { $env:CLAUDE_BIN } else { "claude" })
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
New-Item -ItemType Directory -Force "studio/logs" | Out-Null
$log = "studio/logs/autopilot-$(Get-Date -Format yyyyMMdd-HHmmss).log"

python scripts/studio.py validate
if ($LASTEXITCODE -ne 0) { Write-Error "studio.py validate failed; fix before autopilot."; exit 1 }

# acceptEdits: file edits auto-approved; Bash limited to the allow-list in .claude/settings.json.
# Anything not allowed is denied (no one is there to approve), and hooks still block gates.
& $Claude -p "/studio run $Actions" --permission-mode acceptEdits 2>&1 | Tee-Object -FilePath $log
Write-Host "`nLog: $log"
python scripts/studio.py status
