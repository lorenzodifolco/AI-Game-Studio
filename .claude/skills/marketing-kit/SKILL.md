---
name: marketing-kit
description: Produce a game's marketing kit with the marketing-lead subagent - Google Play store listing with ASO keywords, screenshot and feature-graphic briefs, trailer storyboard and organic launch plan. Use in the launch stage (can run in parallel with release-prep).
argument-hint: "<slug>"
---

# Marketing kit

Game: `$ARGUMENTS`

## Steps
1. Read `games/<slug>/state.json` (stage `launch` expected; `qa` is acceptable for an early draft).
2. Dispatch the `marketing-lead` subagent. Brief: slug, the GDD and concept paths, the newest research report, and the template [store-listing-template.md](store-listing-template.md). Outputs: `marketing/store-listing.md`, `marketing/launch-plan.md`, `marketing/trailer-storyboard.md`.
3. **Verify:** `python scripts/studio.py check <slug> --fast` shows the marketing criteria passing. Check the character limits yourself (title ≤ 30, short description ≤ 80, full description ≤ 4000). Spot-check that every feature claimed in the listing exists in the backlog as ticked.
4. Checkpoint: `python scripts/studio.py checkpoint <slug> -m "marketing: store kit"`.
5. Report: the title, short description, top keywords, and which assets need human or tool production (screenshots, feature graphic, video).
