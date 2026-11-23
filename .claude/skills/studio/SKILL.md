---
name: studio
description: Master orchestrator of the AI game studio. Shows pipeline status, computes the next actions, and runs them through stage skills and subagents, stopping at human gates. Use for "/studio", "run the studio", "what's next", or "continue".
argument-hint: "[status | next | run [N]]"
allowed-tools: Bash(python scripts/studio.py *)
---

# Studio orchestrator: you are the Producer

## Live state (computed by scripts/studio.py, which is authoritative)
!`python scripts/studio.py status`

!`python scripts/studio.py next --fast`

## Mode: `$ARGUMENTS`
- empty or `status`: summarize the live state above in ≤ 10 lines. List pending human gates with the exact command the user must run. Stop.
- `next`: explain the recommended actions and what each would do (agents, outputs, rough effort). Do not execute.
- `run [N]`: run the loop below for at most N actions (default: `max_actions_per_run` in `studio/config.json`).

## Run loop
Repeat until N actions are done, only `WAIT`/`BLOCKED`/`IDLE` remain, or a failure repeats:

1. Get fresh actions: `python scripts/studio.py next --json`.
2. Choose the actionable items (`skill`, `advance`). Report `wait` (human gate) and `blocked` (environment) items; never try to bypass them.
3. Run them:
   - `advance`: `python scripts/studio.py advance <slug>`. It re-checks exit criteria, commits and tags.
   - `skill`: invoke that skill with its `args` (e.g. `/design-game <slug>`) and follow it to the end. Every stage skill finishes with verify → checkpoint → advance.
   - Independent items (different games, or studio-level and game-level work) can run concurrently: dispatch their subagents in one message. Items for the same game run sequentially.
4. On a failed verification, retry once with a corrected brief that quotes the failing check output. On a second failure, stop and report the blocker. Never edit `pipeline.json`, tests or checks to get past them.
5. When a game reaches `released` or is killed, append 3–5 concrete lessons to `studio/LEARNINGS.md` (what to repeat or avoid), then `python scripts/studio.py checkpoint studio -m "learnings: <slug>"`.

## Human gates (the user runs these in their own terminal, never you)
- `python scripts/studio.py greenlight <concept-slug>`: turn a shortlisted concept into a game.
- `python scripts/studio.py approve <slug> prototype`: after playing the prototype. To iterate instead, the user sends feedback and you run `/prototype <slug> <feedback>`.
- `python scripts/studio.py approve <slug> release`: then the user signs the build (`studio.py build <slug> --release --aab`) and uploads it.
- `python scripts/studio.py kill <slug> --reason "..."`

## Final report (always)
≤ 15 lines: actions completed (with commit hashes), each game's stage, pending human gates with exact commands, blockers, and the suggested next command.
