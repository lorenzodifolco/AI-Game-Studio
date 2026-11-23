---
name: prototype
description: Build a playable greybox prototype of a game's core loop in Godot 4 (godot-engineer subagent) and evaluate it against the prototype hypothesis (qa-tester subagent), ending at the human prototype gate. Use when a game is in the prototype stage, or to iterate on a prototype with feedback.
argument-hint: "<slug> [iteration feedback]"
---

# Prototype stage

Arguments: `$ARGUMENTS` (first word = slug; the rest = iteration feedback from a human playtest, which is the top priority when present).

## Steps
1. `python scripts/studio.py check <slug> --fast`. The stage must be `prototype`. If `games/<slug>/project/project.godot` is missing, run `python scripts/studio.py scaffold <slug>`.
2. Dispatch the `godot-engineer` subagent. Brief: implement the `## Prototype` backlog items (plus the feedback, if any) so that the core loop is playable within 10 s of launch. Use greybox or SVG art, tunables from `balance.json`, and logic in testable classes with tests. Done means `python scripts/studio.py test <slug>` passes and the items are ticked.
3. **Verify:** `python scripts/studio.py test <slug>`. If the result is `BLOCKED` (Godot missing), stop and tell the user to run `python scripts/studio.py doctor`. If tests fail, send the output back to the engineer once.
4. Dispatch the `qa-tester` subagent in **prototype mode**. Brief: evaluate against the GDD's `## Prototype Hypothesis` and the concept's kill criteria; write `qa/prototype-report.md` from `.claude/skills/qa/prototype-report-template.md`, including a step-by-step human playtest script.
5. Optional playtest build: `python scripts/studio.py build <slug>` (debug APK). If it's blocked, give the desktop alternative: `godot --path games/<slug>/project`.
6. Checkpoint: `python scripts/studio.py checkpoint <slug> -m "prototype: <iteration n>"`, then `python scripts/studio.py advance <slug>`. This normally stops at the human gate.
7. Report: the QA recommendation, how the human can play it (APK path or desktop command), what to pay attention to, and the gate commands: `python scripts/studio.py approve <slug> prototype` to continue, `/prototype <slug> <feedback>` to iterate, or `python scripts/studio.py kill <slug> --reason "..."`.
