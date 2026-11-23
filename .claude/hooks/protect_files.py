#!/usr/bin/env python3
"""PreToolUse guard for file edits (Edit|Write|NotebookEdit).

- deny : games/*/state.json (owned by scripts/studio.py), secrets.
- ask  : the studio's own safety controls (.claude/settings*.json, .claude/hooks/).
         In headless runs 'ask' resolves to deny, so autonomous agents cannot
         weaken their own guardrails; an interactive user can approve.
"""
import json
import os
import re
import sys

DENY = [
    (r"(^|/)games/[^/]+/state\.json$", "state.json is owned by scripts/studio.py; use its commands."),
    (r"\.(jks|keystore)$|(^|/)\.env(\.|$)|(^|/)studio/secrets/", "Secrets are human-managed."),
]
ASK = [
    (r"(^|/)\.claude/(settings(\.local)?\.json|hooks/)", "This edits the studio's safety controls."),
]


def rel(path: str) -> str:
    p = path.replace("\\", "/")
    root = (os.environ.get("CLAUDE_PROJECT_DIR") or "").replace("\\", "/").rstrip("/")
    if root and p.lower().startswith(root.lower() + "/"):
        p = p[len(root) + 1:]
    return p


def decide(kind: str, reason: str) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": kind,
        "permissionDecisionReason": f"studio guard: {reason}",
    }}))
    return 0


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    ti = data.get("tool_input") or {}
    path = rel(ti.get("file_path") or ti.get("notebook_path") or "")
    if not path:
        return 0
    for pattern, reason in DENY:
        if re.search(pattern, path, re.I):
            return decide("deny", reason)
    for pattern, reason in ASK:
        if re.search(pattern, path, re.I):
            return decide("ask", reason)
    return 0


if __name__ == "__main__":
    sys.exit(main())
