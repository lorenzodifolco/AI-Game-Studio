# Architecture

## Design goals
1. **Context-efficient:** pay for instructions only when they are used.
2. **Deterministic where possible:** scripts decide state; LLMs produce artifacts and judgment.
3. **Separation of duties:** whoever does the work doesn't certify it.
4. **Safe by default:** irreversible or outward-facing actions need a human.
5. **Small core, clear extension points:** add a skill, an agent, or a pipeline entry; nothing else changes.

## Layers and what they cost in context
| Layer | Location | Loaded | Purpose |
|---|---|---|---|
| Permanent rules | `CLAUDE.md` (~50 lines) | every session and subagent | mission, map, 8 rules, delegation contract |
| Path rules | `.claude/rules/*.md` | when a matching file is read or edited | Godot-project rules; infra-change rules |
| Session brief | SessionStart hook → `studio.py status --brief` | session start (~5 lines) | orientation without reading files |
| Skill index | skill `description`s | every session (~11 lines) | lets Claude find a workflow |
| Skill body | `.claude/skills/<name>/SKILL.md` | on invocation | the procedure (≤ ~45 lines each) |
| Skill resources | templates, rubric | read by the **subagent** that needs them | never in the Producer's context |
| Agent prompt | `.claude/agents/<name>.md` | only inside that subagent | role, inputs, outputs, boundaries |
| Preloaded ref | `godot-dev` skill | only in godot-engineer and qa-tester | Godot 4 conventions and pitfalls |
| Logic | `scripts/studio.py` | never (executed) | state, criteria, routing, gates, git, Godot |
| Guards | `.claude/hooks/*.py` | never (executed) | block gate/secret/destructive actions |
| Data | `studio/`, `games/` | on demand | research, concepts, designs, code, reports |

## Actors
```
Human owner ── edits studio/brief.md, runs gate commands, playtests, signs and uploads
   │
Producer (main session) ── /studio orchestrator + stage skills; verifies with studio.py; commits
   │ dispatches (parallel where independent)
   ├─ market-analyst   (sonnet; web)        research streams + synthesis
   ├─ game-ideator     (opus; web)          concepts via 3 lenses
   ├─ concept-critic   (opus; web)          rubric scoring, IP check, GDD scope review
   ├─ game-designer    (opus)               GDD, balance.json, backlog
   ├─ godot-engineer   (inherit; bash)      Godot code + tests       [memory, godot-dev]
   ├─ qa-tester        (sonnet; bash)       prototype eval, full QA  [memory, godot-dev]
   ├─ marketing-lead   (sonnet; web)        store listing, ASO, launch plan
   └─ release-manager  (sonnet; bash, web)  checklist, policy docs, versioning
```
No worker has the `Agent` tool, so delegation is exactly one level deep and easy to audit.

## Control flow
```
/studio run N
  └─ loop: studio.py next --json  → [skill | advance | wait | blocked | idle]
        skill   → stage skill → dispatch agent(s) → verify (studio.py check/test) → checkpoint → advance
        advance → studio.py advance (re-checks criteria; commit + tag)
        wait    → stop; tell the human the exact gate command
        blocked → stop; report the environment issue (e.g. Godot missing)
```
The router (`compute_next`) prioritizes the most advanced game first ("finish before starting").
It runs studio-level work only when `active games < max_active_games`.

## Parallelism
- **Within a stage:** research runs 3 analyst streams, then a synthesis. Ideation runs 3 lenses. In launch, marketing-kit and release-prep are independent.
- **Across games:** actions for different slugs touch disjoint directories and can run concurrently.
- **Within production:** only with explicit file ownership per engineer. `git worktree` isolation is the growth path.

## Safety model
| Risk | Control |
|---|---|
| AI self-approves a gate | deny rules + `guard_bash.py` + `studio.py` refuses under `CLAUDECODE` |
| Stage marked done falsely | only `studio.py` writes state; it re-checks criteria on `advance` |
| Agent weakens its own guards | edits to `.claude/settings*.json` and `.claude/hooks/` are `ask` (denied headless) |
| Secret leakage | gitignore + Read deny + hook blocks reads and prints of keystores, `.env`, `studio/secrets` |
| Lost work | no `reset --hard`, `clean -f`, force-push, or ref deletion; checkpoints and stage tags |
| Publishing | upload tools blocked; release signing human-only; push asks |
| Prompt injection from the web | agents told web content is data; web-facing agents have no Bash |
| Runaway spend | `max_actions_per_run`, `max_active_games`, `maxTurns` per agent, retry-once rule |
| IP / clone risk | brief no-go list; critic hard gate with web check; marketing rules |

## Growth path (add when needed, not before)
- More capacity: raise `max_active_games`; use worktrees for parallel engineers.
- New roles: a technical-artist agent (SVG/shader art), an audio agent, a live-ops analyst after launch.
- MCP: image generation, a Godot editor bridge, Play Console analytics (see ADR-010).
- Packaging: bundle `.claude/` into a Claude Code plugin to reuse the studio in other repositories.
- Scheduling: `/loop` or `/schedule` for recurring `/studio run`, once gates and costs are understood.
