# Operating Manual

## 1. One-time setup
1. **Trust the workspace:** open Claude Code in this folder interactively once (terminal `claude` or the VS Code panel) and accept the trust dialog. Until then, headless runs ignore the project allow-list.
2. **Edit the charter:** review the ✏️ sections of `studio/brief.md`. Set `package_prefix` in `studio/config.json` (e.g. `com.yourname.games`). It becomes `<prefix>.<slug>` and can't change after a game is published.
3. **Godot 4.7.x:** download it from godotengine.org into `tools/godot/` (gitignored; auto-detected), or anywhere else with `GODOT_BIN` or `godot_bin` in `studio/config.json` set to the *console* executable.
4. **Android export (needed before the first playtest APK):** open the Godot editor once.
   - *Editor → Manage Export Templates → Download* (the exact version).
   - *Editor Settings → Export → Android*: set the Android SDK path (`%LOCALAPPDATA%\Android\Sdk`) and a JDK (17 is recommended; your 21 or Android Studio's `jbr` usually works).
5. **Check:** `python scripts/studio.py doctor` should show no `MISSING`.
6. **Git:** make the initial commit (e.g. `git add -A && git commit -m "infra: AI game studio"`). Optionally rename the branch: `git branch -m main`.
7. **Headless autopilot (optional):** put the `claude` CLI on PATH, or set `CLAUDE_BIN`. For unattended runs, use a long-lived token (`claude setup-token`).
8. **Release keystore (only at the first release):** create it with `keytool`, store it in `studio/secrets/` or outside the repo, and set the `GODOT_ANDROID_KEYSTORE_RELEASE_PATH/_USER/_PASSWORD` env vars in *your* shell.

## 2. Launching the studio
| Mode | How | When |
|---|---|---|
| Status | `/studio` | orientation (free; no agents run) |
| Preview | `/studio next` | see what would happen and why |
| Supervised run | `/studio run 3` | the default: runs up to 3 actions in front of you |
| Single stage | `/market-research puzzle`, `/ideate 6 cozy`, `/prototype <slug> <feedback>` … | targeted control |
| Headless | `.\scripts\autopilot.ps1 -Actions 3` (or `scripts/autopilot.sh 3`) | unattended; logs to `studio/logs/` |
| Recurring | `/loop 2h /studio run 2` (session) or `/schedule` (cloud) | after you trust the cost profile |

Every mode stops at human gates and reports the exact command for you to run.

## 3. Your decisions (run these in your own terminal, not through Claude)
```
python scripts/studio.py greenlight <concept-slug> [--note "why"]
python scripts/studio.py approve <slug> prototype   [--note "feedback"]
python scripts/studio.py approve <slug> release
python scripts/studio.py kill <slug> --reason "..."
python scripts/studio.py build <slug> --release --aab   # signed build, keystore env vars set
```
To iterate on a prototype instead of approving it, tell Claude: `/prototype <slug> <your feedback>`.
To have Claude approve prototypes automatically, set `"prototype": "auto"` in `studio/config.json`. Release is always human.

## 4. A first cycle (what to expect)
1. `/studio run 1` → market research (4 analyst runs; the most web-heavy step).
2. `/studio run 2` → ideation (9 concepts) → evaluation (ranking, ≤ 3 shortlisted).
3. **You:** read `studio/concepts/RANKING.md`, then `greenlight` one concept.
4. `/studio run 3` → design (GDD + backlog) → prototype (code + tests + QA report) → stops at the prototype gate.
5. **You:** play it (`godot --path games/<slug>/project`, or the debug APK on a phone), then approve, iterate, or kill.
6. `/studio run N` repeatedly → production batches → QA → launch kit → stops at the release gate.
7. **You:** review `release/` and `marketing/`, approve, sign, and upload to the internal testing track.

## 5. Monitoring and recovery
- **Where things are:** `python scripts/studio.py status`; `git log --oneline`; `git tag -l "<slug>/*"`.
- **A stage failed twice:** the Producer stops and reports. Fix the cause (brief, environment, scope), then rerun the stage skill.
- **Roll back a stage's work:** `git revert <commits>` (history is never rewritten). Stage tags mark the boundaries.
- **`BLOCKED` results:** environment problems (Godot or export templates missing). Run `python scripts/studio.py doctor`.
- **Integrity:** `python scripts/studio.py validate` and `python -m unittest discover -s tests`.

## 6. Customizing and extending
- **Tune behaviour:** `studio/config.json` (capacity, research freshness, actions per run, gate policy) and `studio/brief.md` (strategy).
- **Change the pipeline:** edit `studio/pipeline.json` (criteria and gates) and `docs/PIPELINE.md` together, run `validate`, and add an ADR.
- **Add an agent:** `.claude/agents/<name>.md` (name = filename; narrow tools; no `Agent` tool; a return contract). Reference it from a skill as `` `<name>` subagent ``.
- **Add a skill:** `.claude/skills/<name>/SKILL.md` (≤ ~50 lines; templates as sibling files). If it produces a stage artifact, reference it as `by` in `pipeline.json`.
- **Add an MCP server:** scope it to the agent that needs it (`mcpServers:` in agent frontmatter), not globally.
- **Safety files** (`.claude/settings.json`, `.claude/hooks/`): edits by Claude require your approval. Run the tests after you change them.

## 7. Troubleshooting
| Symptom | Fix |
|---|---|
| Headless run says Skill/Bash was denied | Trust the workspace (step 1.1); check the allow-list in `.claude/settings.json` |
| Hooks fail with "python not found" | Install Python 3.10+ or change `python` → `python3` in `.claude/settings.json` |
| Godot tests fail with class_name errors | Delete `games/<slug>/project/.godot/`; the next `studio.py test` re-imports |
| Custom agents not available | Agents load at session start: restart the session after adding one |
| Studio keeps researching | The research report is older than `research_max_age_days`, or `report.md` is missing |
