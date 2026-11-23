---
name: evaluate-concepts
description: Score all new game concepts with the independent concept-critic subagent against the studio rubric (hard gates, weighted criteria, IP/clone check), update their status and produce studio/concepts/RANKING.md. Use when concepts have status new.
argument-hint: "[optional: specific concept slugs]"
---

# Concept evaluation

Scope: `$ARGUMENTS` (empty = every concept with `status: new`).

## Steps
1. List the target concepts (`grep -l "^status: new" studio/concepts/*.md`). If there are none, report that and stop.
2. Dispatch **one** `concept-critic` subagent for all targets (a single judge keeps scoring comparable). Brief: the target files, the rubric path `.claude/skills/evaluate-concepts/rubric.md`, the latest research report, and the outputs (frontmatter `score`/`status`, a `## Evaluation` section in each file, and a refreshed `studio/concepts/RANKING.md`).
3. **Verify:** `python scripts/studio.py validate` passes. No target is still `status: new`. Every shortlisted concept has score ≥ the rubric threshold and an `## Evaluation` section. At most 3 are shortlisted.
4. Checkpoint: `python scripts/studio.py checkpoint studio -m "evaluate: <n> concepts, <k> shortlisted"`.
5. Report the ranking (`slug | score | status | reason`). For shortlisted concepts, tell the user that greenlighting is **their** decision and give the exact command: `python scripts/studio.py greenlight <slug>`. If none were shortlisted, the next step is `/ideate` with the critic's feedback as the theme.
