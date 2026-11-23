# Decisions (ADR log)

Format: context → decision → consequences. Newest at the bottom. Add an entry for any change
to architecture, pipeline, gates, safety, or tooling.

---

### ADR-001: Layered, Claude Code-native architecture (2026-11-23)
**Context:** The studio must run many specialized workflows without loading all instructions into every session.
**Decision:** Separate the layers by how often they are needed:
CLAUDE.md (permanent rules, ~50 lines) · `.claude/rules/` (path-scoped, load on touch) · skills (procedures, load on invoke) · agents (roles with their own context and tools) · `studio/` and `games/` (data) · `scripts/studio.py` (deterministic logic) · hooks (guards).
**Consequences:** The always-on context stays at about 1.5k tokens. Templates and rubrics are read only by the subagent that needs them. Adding a stage means adding a skill and a pipeline entry, not editing CLAUDE.md.

### ADR-002: The main session is the Producer; stage skills run in the main thread (2026-11-23)
**Context:** Skills can run forked (`context: fork`) inside a subagent, or inline in the main session.
**Decision:** Stage skills run inline. The Producer (main session) dispatches role agents, then **verifies their output itself** with `studio.py`, commits, and handles human gates. Worker agents get no `Agent` tool, so they don't delegate further.
**Why:** Verification by a different actor than the producer of the work, parallel fan-out from one place (research streams, ideation lenses, multiple games), and gates stay in the conversation the human sees.
**Consequences:** Main context grows by one skill body per stage (~40 lines each), and agents return ≤15-line summaries. `context: fork` remains an option for future self-contained skills.

### ADR-003: Deterministic state machine owns pipeline truth (2026-11-23)
**Decision:** `studio/pipeline.json` defines stages, exit criteria (file, headings, glob, checklist, contains, tests) and gates. `scripts/studio.py` evaluates them, routes the next actions (`next`), and is the only writer of `games/*/state.json`, which a hook protects.
**Consequences:** An LLM can't declare a stage done; the checks are reproducible and unit-tested. Criteria are deliberately structural (presence, sections, verdict lines, passing tests). Quality judgment stays with the critic, the QA agent, and human gates.

### ADR-004: Human gates enforced in three layers (2026-11-23)
**Decision:** Greenlight, prototype approval, release approval, kill, and release signing are human decisions. Layer 1: permission `deny` rules. Layer 2: the `guard_bash.py` PreToolUse hook. Layer 3: `studio.py` refuses these commands when `CLAUDECODE` is set (inside Claude Code). The prototype gate may be set to `auto` in `config.json`; release is hard-coded human.
**Consequences:** Full autonomy runs up to a gate, then stops and tells the human the exact command. The layers protect against mistakes; they are not a sandbox against a determined adversary.

### ADR-005: Engine is Godot 4 (GDScript, GL Compatibility, portrait) (2026-11-23)
**Context:** Needs an AI-operable, CLI-drivable engine with a cheap Android export.
**Decision:** Godot 4.x (4.7.2 was current when this was decided).
**Alternatives rejected:** Unity (editor-centric, binary-heavy assets, licensing, poor headless ergonomics for agents). libGDX/Kotlin (no scene tooling, more boilerplate). Phaser + Capacitor (Node not installed, WebView performance). Flutter/Flame (smaller game ecosystem).
**Consequences:** Text-based scenes diff well in git. Headless test, import and export work from the CLI. The known risk is LLMs writing Godot 3 syntax, mitigated by the preloaded `godot-dev` pitfalls table and a SCRIPT ERROR scan. Export templates and SDK paths are a one-time human setup.

### ADR-006: Addon-free headless test runner (2026-11-23)
**Decision:** Each project carries `tests/test_runner.gd` + `test_case.gd` (from the template), with no GUT or gdUnit dependency. GDScript has no exceptions, so `studio.py test` also fails any run whose output contains `SCRIPT ERROR`, `Parse Error`, or `Failed to load script`.
**Consequences:** Zero install and deterministic output. Fewer features than GUT; that can be revisited if tests outgrow it.

### ADR-007: Git workflow: trunk-based with scoped checkpoints (2026-11-23)
**Decision:** One trunk. Only the Producer commits, via `studio.py checkpoint <scope>`, which commits only that scope's paths (`games/<slug>`, `studio`, or `infra`). Stage transitions are tagged `<slug>/<stage>`. Commits made inside Claude carry a `Co-Authored-By` trailer. Force-push, `reset --hard`, `clean -f`, and ref deletion are blocked; `git push` always asks.
**Why not a branch per game:** `studio.py` must see every game's state from one checkout. Parallel engineering can use `git worktree` (`isolation: worktree`) when needed.
**Consequences:** Easy rollback to any stage tag; the history reads as a production log.

### ADR-008: Secrets and release signing are human-only (2026-11-23)
**Decision:** Keystores and `.env` live outside git (`studio/secrets/` is gitignored and read-denied). Release builds need the `GODOT_ANDROID_KEYSTORE_RELEASE_*` env vars and are refused inside Claude. The studio never uploads to any store.

### ADR-009: Model allocation per role (2026-11-23)
**Decision:** opus for judgment and creativity (game-ideator, concept-critic, game-designer). `inherit` for godot-engineer (it follows the session model). sonnet for high-volume, well-specified work (market-analyst, qa-tester, marketing-lead, release-manager).
**Consequences:** Spend goes where quality matters most. Change it per agent in the frontmatter `model:`.

### ADR-010: No MCP servers at launch (2026-11-23)
**Decision:** Built-in WebSearch and WebFetch cover research. No MCP server is needed to make the studio operational.
**Candidates when the need is real:** an image-generation MCP (final art), a Godot editor MCP (screenshots and runtime inspection), a Play Console read-only analytics MCP (post-launch metrics). Add them per agent via `mcpServers:` so other sessions don't pay their context cost.

### ADR-011: Placeholder art is SVG or code-drawn (2026-11-23)
**Decision:** Concepts and GDDs must be achievable with hand-written SVG or `_draw()` shapes. Final art and audio are a known capability gap, handled by human or external tools, or a future art agent or MCP.

### ADR-012: Learning loops (2026-11-23)
**Decision:** godot-engineer and qa-tester use `memory: project` (`.claude/agent-memory/<agent>/`, committed with checkpoints) for technical lessons. Cross-game product lessons go to `studio/LEARNINGS.md`, which the ideator, critic, and designer read.

### ADR-013: Capacity gate controls spend (2026-11-23)
**Decision:** `max_active_games` (default 1). Studio-level work (research, ideation, evaluation) runs only when capacity is free. Each `/studio run N` executes at most N actions (default 3).
**Consequences:** No runaway token use. Raise the capacity to run games in parallel.

### ADR-014: Python stdlib only, invoked as `python` (2026-11-23)
**Decision:** Scripts and hooks use only the standard library (no pip install), and the hooks call `python`. On macOS/Linux, where only `python3` exists, change the command in `.claude/settings.json`.

### ADR-015: Headless runs need explicit Skill/Agent permissions (2026-11-23)
**Context:** Verification showed that in `claude -p` the Skill tool call was denied unless allowed, and that an untrusted workspace ignores the project allow-list.
**Decision:** `Skill` and `Agent` are in the allow-list. The workspace must be trusted once interactively before the autopilot will run.
