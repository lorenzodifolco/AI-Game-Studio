---
paths:
  - ".claude/agents/**"
  - ".claude/skills/**"
  - ".claude/rules/**"
  - "scripts/**"
  - "studio/pipeline.json"
  - "studio/config.json"
---
# Changing studio infrastructure

- Keep the layering: CLAUDE.md = permanent rules (keep it short) · skills = procedures · agents = roles (tools + persona) · studio.py = deterministic checks · hooks = guards.
- Agents: frontmatter `name` must equal the filename. Give each the narrowest tool set and no `Agent` tool (workers don't delegate).
- Skills: `name` = directory. Keep SKILL.md short; put templates and rubrics in sibling files that subagents read on demand.
- If a pipeline exit criterion changes, update `docs/PIPELINE.md` in the same commit.
- Verify with `python scripts/studio.py validate` and `python -m unittest discover -s tests`, then add an ADR to `DECISIONS.md` if behaviour changed.
