---
name: develop
description: Production development loop - implement the game's remaining backlog in milestone batches with the godot-engineer subagent, verifying tests and checkpointing after each batch. Use when a game is in the production stage, or to fix bugs from a QA report.
argument-hint: "<slug> [max-batches, default 3] [focus or bug list]"
---

# Production stage

Arguments: `$ARGUMENTS` (slug, optional batch limit, optional focus such as "fix qa/qa-report.md P0-P1").

## Steps
1. `python scripts/studio.py check <slug> --fast`, then read the unticked items in `games/<slug>/design/backlog.md`.
2. Plan batches of 3–6 related items in priority order (P1 before P2 before P3, dependencies first). A batch should produce a playable, testable increment.
3. For each batch, up to the limit:
   1. Dispatch the `godot-engineer` subagent with the batch's item ids, acceptance criteria, and relevant GDD sections.
   2. **Verify:** `python scripts/studio.py test <slug>` passes, the claimed items are ticked, and `git diff --stat` touches only `games/<slug>/`.
   3. Checkpoint: `python scripts/studio.py checkpoint <slug> -m "develop: <batch summary>"`.
4. Parallelism: batches that touch disjoint systems may go to two `godot-engineer` subagents at once **only** if you name the files each one owns in its brief. Otherwise run batches sequentially.
5. When no unticked items remain, run `python scripts/studio.py advance <slug>`.
6. Report: items done/remaining, test status, commits, and issues the engineers raised (design questions go to the user, or to the `game-designer` subagent for a decision).
