# Pipeline Reference

The machine source of truth is `studio/pipeline.json`, evaluated by `scripts/studio.py`.
Keep this page in sync when criteria change.

## Studio level (before a game exists)
Runs only while `active games < max_active_games`. Router priority:

| Condition | Action | Skill → agents | Output |
|---|---|---|---|
| concepts with `status: new` | evaluate | `/evaluate-concepts` → concept-critic | concept `score`/`status`, `## Evaluation`, `studio/concepts/RANKING.md` |
| shortlisted concepts exist | **WAIT: human greenlight** | (none) | `python scripts/studio.py greenlight <slug>` |
| no research, or older than `research_max_age_days` | research | `/market-research` → 3× market-analyst ∥ → synthesis | `studio/research/<date>-<focus>/{trends,competitors,economics,report}.md` |
| otherwise | ideate | `/ideate` → 3× game-ideator ∥ | `studio/concepts/<slug>.md` (`status: new`) |

Concept statuses: `new → shortlisted | rejected | parked → greenlit`.
`greenlight` (human) creates `games/<slug>/` with `state.json` (stage `design`), copies the concept, commits, and tags `<slug>/greenlight`.

## Game level
| Stage | Skill → agents | Exit criteria (all must pass) | Gate |
|---|---|---|---|
| design | `/design-game` → game-designer, concept-critic (scope review) | `design/gdd.md` has all 11 required sections · `design/backlog.md` exists | none |
| prototype | `/prototype` → godot-engineer, qa-tester | `project/project.godot` · Godot tests pass · `qa/prototype-report.md` has `Recommendation: GO\|ITERATE\|KILL` | **prototype** (human; may be set to `auto`) |
| production | `/develop` → godot-engineer (batched) | ≥ 1 `project/tests/test_*.gd` · every backlog item ticked · tests pass | none |
| qa | `/qa` → qa-tester ⇄ godot-engineer (≤ 3 fix cycles) | tests pass · `qa/qa-report.md` has `Verdict: PASS` | none |
| launch | `/marketing-kit` ∥ `/release-prep` → marketing-lead, release-manager | `marketing/store-listing.md` has its 6 sections · `marketing/launch-plan.md` · every `release/release-checklist.md` item ticked | **release** (always human) |
| released | (terminal) | (none) | (none) |

GDD required sections: Pitch, Design Pillars, Core Loop, Controls, Progression, Economy and
Monetization, Art Direction, Audio, Scope, Success Metrics, Prototype Hypothesis.

## Criterion types (`pipeline.json`)
| type | passes when |
|---|---|
| `file` | the file exists and is non-empty |
| `headings` | the file contains every listed `#`–`####` heading (case-insensitive; leading numbering ignored) |
| `glob` | at least one path matches |
| `checklist` | the file has at least one `- [ ]`/`- [x]` item and none are unticked |
| `contains` | the regex matches (multiline, case-insensitive) |
| `tests` | `studio.py test <slug>` exits 0 with no SCRIPT ERROR (BLOCKED if Godot is missing) |

## Commands
| Command | Who | Effect |
|---|---|---|
| `status [--brief]` · `next [--json] [--fast]` · `check <slug> [--fast]` | anyone | read-only views |
| `advance <slug>` | Producer | re-checks criteria + gate → next stage, commit, tag `<slug>/<stage>` |
| `checkpoint <slug\|studio\|infra> -m "..."` | Producer | commits only that scope |
| `scaffold <slug>` | Producer | copies `scripts/templates/godot-mobile` into `games/<slug>/project` |
| `test <slug>` · `build <slug>` | agents | headless tests · debug APK |
| `doctor` · `validate` | anyone | toolchain check · integrity check of agents, skills, pipeline, and data |
| `greenlight` · `approve` · `kill` · `build --release` | **human only** | gate decisions and signing |

Exit codes: 0 ok · 1 not ready/failed · 2 blocked by the environment · 3 waiting for a human gate.
