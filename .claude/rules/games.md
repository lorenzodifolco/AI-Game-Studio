---
paths:
  - "games/**"
---
# Working inside games/<slug>/

- Godot 4 project: `games/<slug>/project/`. Use GDScript 4 syntax only (see the `godot-dev` skill; never Godot 3 APIs).
- Scope source of truth: `design/gdd.md`. Task list: `design/backlog.md`. Tick a backlog item only when it is implemented **and** covered by a passing test or a documented manual check.
- Tunable numbers live in `design/balance.json` (data-driven), not hard-coded in scripts.
- After code changes, run `python scripts/studio.py test <slug>`. A run that prints `SCRIPT ERROR` counts as failed.
- Don't edit `state.json`. Don't commit (the Producer checkpoints). Build outputs go to `games/<slug>/build/` (gitignored).
