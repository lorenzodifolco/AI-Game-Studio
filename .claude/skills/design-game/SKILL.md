---
name: design-game
description: Turn a greenlit concept into a Game Design Document, balance data and backlog using the game-designer subagent, with an independent scope review. Use when a game is in the design stage, or to revise a design after playtest feedback.
argument-hint: "<slug> [revision feedback]"
---

# Design stage

Arguments: `$ARGUMENTS` (the first word is the game slug; the rest is optional revision feedback).

## Steps
1. `python scripts/studio.py check <slug>`. The game must be in stage `design` (or the user explicitly asked for a revision).
2. Dispatch the `game-designer` subagent. Brief: slug, `games/<slug>/concept.md` (address its `## Evaluation` required changes), any revision feedback, and the templates [gdd-template.md](gdd-template.md) and [backlog-template.md](backlog-template.md). Outputs: `design/gdd.md`, `design/balance.json`, `design/backlog.md`.
3. Dispatch the `concept-critic` subagent for a **scope review only**. Brief: read `gdd.md` and `backlog.md` against `studio/brief.md` scope limits and the concept's kill criteria; return at most 10 lines with the scope verdict (OK or CUT) and specific cuts. Don't let it edit files.
4. If the verdict is CUT, send the cuts back to the `game-designer` subagent once.
5. **Verify:** `python scripts/studio.py check <slug>` shows every criterion PASS. `balance.json` parses (`python -m json.tool games/<slug>/design/balance.json`). The backlog has both `## Prototype` and `## Production` sections.
6. Checkpoint: `python scripts/studio.py checkpoint <slug> -m "design: GDD v1"`, then `python scripts/studio.py advance <slug>`.
7. Report: the prototype hypothesis, backlog size, and the scope-review outcome.
