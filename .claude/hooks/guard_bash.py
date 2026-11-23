#!/usr/bin/env python3
"""PreToolUse guard for Bash/PowerShell commands.

Blocks (exit 2, reason on stderr -> shown to Claude) commands that would cross a
human gate, publish, destroy history/work, or expose secrets. This is a safety
net against mistakes, not a sandbox; permissions in settings.json are layer one.
"""
import json
import re
import sys

RULES = [
    (r"studio\.py[\"']?\s+(greenlight|approve|kill)\b",
     "Human gate. Ask the user to run this studio.py command in their own terminal."),
    (r"studio\.py[\"']?\s+build\b[^|;&]*--release",
     "Release signing is human-only. Ask the user to run the release build."),
    (r"\bgit\s+push\b.*\s(-f|--force(-with-lease)?|--mirror|--delete)(\s|$)",
     "Destructive push is not allowed."),
    (r"\bgit\s+reset\s+.*--hard\b", "git reset --hard discards work. Use a new commit or git revert."),
    (r"\bgit\s+clean\s+-\w*f", "git clean -f deletes untracked work."),
    (r"\bgit\s+(checkout|restore)\s+(--\s+)?\.(\s|$)", "Discarding all working-tree changes is not allowed."),
    (r"\bgit\s+(tag\s+-d|branch\s+-D|filter-branch|filter-repo)\b", "Rewriting/deleting refs is not allowed."),
    (r"\brm\s+(-\w+\s+)*-\w*[rR]\w*\s+([^\s;&|]+\s+)*[\"']?(/|~|\.|\.\.|\*|\.git|\.claude|studio|scripts|games|games/[^/\s]+)/?[\"']?(\s|$|;|&|\|)",
     "Recursive delete of a protected path. Delete specific files instead."),
    (r"Remove-Item\b.*-Recurse.*\b(\.git|\.claude|studio|scripts|games)\b",
     "Recursive delete of a protected path. Delete specific files instead."),
    (r"\b(fastlane|supply|androidpublisher|publishBundle|publishApk|bundletool\s+upload)\b",
     "Publishing to a store is human-only."),
    (r"\b(cat|type|more|less|head|tail|Get-Content|gc|base64|xxd|od|strings|cp|copy|scp|curl)\b[^|;&]*(\.jks|\.keystore|\.env\b|studio/secrets)",
     "Secrets (keystores, .env, studio/secrets) must not be read, copied or transmitted."),
    (r"(printenv|echo|Write-Output|Write-Host)\b.*(KEYSTORE.*PASSWORD|_PASSWORD|_SECRET|API_KEY)",
     "Do not print secrets."),
]


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    cmd = (data.get("tool_input") or {}).get("command") or ""
    norm = cmd.replace("\\", "/")
    for pattern, reason in RULES:
        if re.search(pattern, norm, re.I):
            print(f"BLOCKED by studio guard: {reason}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
