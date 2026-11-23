# AI Game Studio

An autonomous, AI-first mobile game studio built on Claude Code. It researches the Android
games market, generates and evaluates concepts, then designs, prototypes, develops, tests and
prepares Godot 4 games for Google Play. A human owner holds the key decisions.

```
research → ideate → evaluate → [greenlight] → design → prototype → [prototype] → production → qa → launch → [release]
                                    human                              human                               human
```

## Quick start
```bash
python scripts/studio.py doctor      # toolchain check
python scripts/studio.py validate    # studio integrity
```
Then, in Claude Code:
```
/studio            # status
/studio next       # what happens next, and why
/studio run 3      # run up to 3 pipeline actions, stopping at human gates
```
Headless: `.\scripts\autopilot.ps1 -Actions 3`

## Docs
- [docs/OPERATING-MANUAL.md](docs/OPERATING-MANUAL.md): setup, launch modes, gates, recovery
- [docs/PIPELINE.md](docs/PIPELINE.md): stages, exit criteria, commands
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): design, context budget, safety model
- [DECISIONS.md](DECISIONS.md): architecture decision log
- [CLAUDE.md](CLAUDE.md): the rules every Claude session follows
