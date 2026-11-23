---
name: ideate
description: Generate original mobile game concepts from the latest market research using parallel game-ideator subagents, each with a different ideation lens. Writes studio/concepts/<slug>.md with status new. Use after market research, or when the user asks for game ideas.
argument-hint: "[count, default 9] [optional theme/constraint]"
---

# Ideation

Arguments: `$ARGUMENTS` (count defaults to 9; any extra text is a theme or constraint for every lens).
Today: !`date +%F`

## Steps
1. Find the newest `studio/research/*/report.md` and read its `## Opportunities` and `## Recommendations for Ideation`. List existing concept slugs (`ls studio/concepts`).
2. **In parallel**, dispatch three `game-ideator` subagents, each producing ⌈count/3⌉ concepts. Each brief contains the report path, lens, count, date, existing slugs, and the template path `.claude/skills/ideate/concept-template.md`:
   - **Lens A, proven loop with a fresh angle:** a validated core loop from a top opportunity, with a new theme, audience, or twist.
   - **Lens B, fusion:** combine mechanics from two different successful subgenres into something none of the comparables offers.
   - **Lens C, underserved need:** start from player pain points or niches in the report, then design the game that solves them.
3. **Verify:** `python scripts/studio.py validate` passes, and the expected number of new files have `status: new`. Remove exact duplicates (same hook and loop) by keeping the stronger one; delete the other file and mention it.
4. Checkpoint: `python scripts/studio.py checkpoint studio -m "ideate: <n> concepts from <report-dir>"`.
5. Report a table `slug | title | hook`. The next step is `/evaluate-concepts`.
